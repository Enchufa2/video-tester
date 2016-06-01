# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import time
from urlparse import urlparse
from gi.repository import Gst, GstRtspServer, GObject
from . import VTLOG, supported_codecs

#Gst.debug_set_active(True)
#Gst.debug_set_default_threshold(3)

class RTSPServer:
	'''
	GStreamer RTSP server.
	'''
	def __init__(self, port):
		'''
		**On init:** Some initialization code.

		:param int port: RTSP server port.
		'''
		#: GStreamer RTSP server instance.
		self.server = GstRtspServer.RTSPServer()
		self.server.set_service(str(port))

	def addMedia(self, videos, bitrate, framerate, path):
		'''
		Add videos to the server.

		:param list videos: List of available videos.
		:param int bitrate: The bitrate (in kbps).
		:param int framerate: The framerate (in fps).
		:param string path: Path to the video directory.
		'''
		for i, video in enumerate(videos):
			for codec, items in supported_codecs.iteritems():
				launch = 'filesrc location=%s/%s ! decodebin ! videorate ! video/x-raw,framerate=%s/1 ! %s bitrate=%s ! %s name=pay0' % (
					path,
					video,
					framerate,
					items['encoder'],
					items['bitrate_from_kbps'](bitrate),
					items['rtppay']
				)
				pool = GstRtspServer.RTSPAddressPool()
				pool.add_range("224.3.0.0", "224.3.0.10", 5000, 5010, 10)
				factory = GstRtspServer.RTSPMediaFactory()
				factory.set_address_pool(pool)
				factory.set_launch(launch)
				factory.set_shared(True)
				factory.set_eos_shutdown(True)
				name = '/video%s.' % (i) + codec
				self.server.get_mount_points().add_factory(name, factory)

	def run(self):
		'''
		Attach server and run the loop.
		'''
		if self.server.attach():
			GObject.MainLoop().run()

class RTSPClient:
	'''
	GStreamer RTSP client.
	'''
	def __init__(self, path, codec, bitrate, framerate):
		'''
		**On init:** Some initialization code.

		:param string path: Path for the output files.
		:param string codec: Selected codec.
		:param int bitrate: Selected bitrate.
		:param int framerate: Selected framerate.
		'''
		#: Path for the output files.
		self.path = path
		#: Selected codec.
		self.codec = codec
		#: Selected bitrate.
		self.bitrate = bitrate
		#: Selected framerate.
		self.framerate = framerate
		#: Dictionary of paths to the processed video files: ``{'original':[<compressed>, <yuv>], 'coded':[<compressed>, <yuv>], 'received':[<compressed>, <yuv>]}``.
		self.files = {'original':[], 'coded':[], 'received':[]}
		#: Various caps recolected from the pipeline.
		self.caps = {
			'rtsp-sport': None, 'sdp-id': None, 'udp-dport': None,	# RTSP/UDP
			'ptype': None, 'clock-rate': None, 'seq-base': None,	# RTP
			'width': None, 'height': None, 'format': None			# YUV
		}
		#: Gstreamer pipeline.
		self.pipeline = None
		#: Gstreamer loop.
		self.loop = None
		self.__exception = None

	def __events(self, bus, msg):
		'''
		Event handler.

		:param bus: Gstreamer bus object.
		:param msg: Gstreamer message object.

		:returns: True.
		:rtype: boolean
		'''
		t = msg.type
		if t == Gst.MessageType.EOS:
			self.pipeline.set_state(Gst.State.PAUSED)
			time.sleep(0.5)
			self.pipeline.set_state(Gst.State.READY)
			self.pipeline.set_state(Gst.State.NULL)
			VTLOG.debug('GStreamer: Gst.MessageType.EOS received')
			self.loop.quit()
		elif t == Gst.MessageType.ERROR:
			self.pipeline.set_state(Gst.State.PAUSED)
			time.sleep(0.5)
			self.pipeline.set_state(Gst.State.READY)
			self.pipeline.set_state(Gst.State.NULL)
			self.__exception, d = msg.parse_error()
			VTLOG.error('GStreamer: Gst.MessageType.ERROR received')
			self.loop.quit()
		return True

	def __play(self):
		'''
		Attach event handler, set state to *playing* and run the loop (see :attr:`loop`).
		'''
		bus = self.pipeline.get_bus()
		bus.add_signal_watch()
		bus.connect('message', self.__events)
		self.pipeline.set_state(Gst.State.PLAYING)
		self.loop = GObject.MainLoop()
		self.loop.run()

	def __capsSDP(self, elem, sdp):
		if sdp:
			self.caps['sdp-id'] = sdp.get_origin().sess_id
			VTLOG.debug('SDP ID: %s' % self.caps['sdp-id'])

	def __capsUDP(self, elem, new_elem):
		if 'udpsrc' in new_elem.name:
			elem.disconnect(self.__shdlr)
			self.caps['udp-dport'], = new_elem.get_properties('port')
			VTLOG.debug('UDP dport: %s' % self.caps['udp-dport'])

	def __capsRTP(self, pad, args):
		caps = pad.get_current_caps()
		if caps:
			struct = caps.get_structure(0)
			self.caps['ptype'] = struct.get_int('payload')[1]
			self.caps['clock-rate'] = struct.get_int('clock-rate')[1]
			self.caps['seq-base'] = struct.get_uint('seqnum-base')[1]
			VTLOG.debug('RTP ptype: %s' % self.caps['ptype'])
			VTLOG.debug('RTP clock: %s' % self.caps['clock-rate'])
			VTLOG.debug('RTP seq base: %s' % self.caps['seq-base'])

	def __capsYUV(self, pad, args):
		caps = pad.get_current_caps()
		if caps:
			struct = caps.get_structure(0)
			self.caps['width'] = struct.get_int('width')[1]
			self.caps['height'] = struct.get_int('height')[1]
			self.caps['format'] = struct.get_string('format')
			VTLOG.debug('YUV width: %s' % self.caps['width'])
			VTLOG.debug('YUV height: %s' % self.caps['height'])
			VTLOG.debug('YUV format: %s' % self.caps['format'])

	def receive(self, url, proto):
		'''
		Connect to the RTSP server and receive the selected video (see :attr:`video`).

		:param string url: RTSP server URL.
		:param int proto: Transport protocol for the RTP transmission.
		'''
		VTLOG.info('Starting GStreamer receiver...')
		self.pipeline = Gst.parse_launch('rtspsrc name=source ! tee name=t ! queue ! %s name=depay %s ! filesink name=sink1 t. ! queue ! decodebin ! videorate skip-to-first=True ! video/x-raw,framerate=%s/1 ! filesink name=sink2' % (
			supported_codecs[self.codec]['rtpdepay'],
			supported_codecs[self.codec]['add'],
			self.framerate
		))
		source = self.pipeline.get_by_name('source')
		depay = self.pipeline.get_by_name('depay')
		sink1 = self.pipeline.get_by_name('sink1')
		sink2 = self.pipeline.get_by_name('sink2')
		source.props.location = url
		source.props.protocols = proto
		location = self.path + '.' + self.codec
		self.files['received'].append(location)
		sink1.props.location = location
		location = self.path + '.yuv'
		self.files['received'].append(location)
		sink2.props.location = location

		port = urlparse(url).port
		if port:
			self.caps['rtsp-sport'] = port
		else:
			self.caps['rtsp-sport'] = 554
		source.connect('on-sdp', self.__capsSDP)
		self.__shdlr = source.connect('element-added', self.__capsUDP)
		depay.get_static_pad('sink').connect('notify::caps', self.__capsRTP)
		sink2.get_static_pad('sink').connect('notify::caps', self.__capsYUV)

		self.__play()
		if self.__exception:
			raise Exception(self.__exception)
		VTLOG.info('GStreamer receiver stopped')

	def makeReference(self, video):
		'''
		Make the reference videos.

		:param string video: Path to the selected video.
		'''
		VTLOG.info('Making reference...')
		self.pipeline = Gst.parse_launch('filesrc name=source ! decodebin ! videorate ! video/x-raw,framerate=%s/1 ! filesink name=sink1' % self.framerate)
		source = self.pipeline.get_by_name('source')
		sink1 = self.pipeline.get_by_name('sink1')
		self.files['original'].append(video)
		source.props.location = video
		location = self.path + '_ref_original.yuv'
		self.files['original'].append(location)
		sink1.props.location = location
		self.__play()
		self.pipeline = Gst.parse_launch('filesrc name=source ! decodebin ! videorate ! video/x-raw,framerate=%s/1 ! %s bitrate=%s ! tee name=t ! queue %s ! filesink name=sink2 t. ! queue ! decodebin ! filesink name=sink3' % (
			self.framerate,
			supported_codecs[self.codec]['encoder'],
			supported_codecs[self.codec]['bitrate_from_kbps'](self.bitrate),
			supported_codecs[self.codec]['add']
		))
		source = self.pipeline.get_by_name('source')
		sink2 = self.pipeline.get_by_name('sink2')
		sink3 = self.pipeline.get_by_name('sink3')
		source.props.location = video
		location = self.path + '_ref.' + self.codec
		self.files['coded'].append(location)
		sink2.props.location = location
		location = self.path + '_ref.yuv'
		self.files['coded'].append(location)
		sink3.props.location = location
		self.__play()
		VTLOG.info('Reference made')
