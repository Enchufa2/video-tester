# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import time
from gi.repository import Gst, GstRtspServer, GObject
from . import VTLOG, supported_codecs

class RTSPServer:
	'''
	GStreamer RTSP server.
	'''
	def __init__(self, port):
		'''
		**On init:** Some initialization code.

		:param integer port: RTSP server port.
		'''
		#: GStreamer RTSP server instance.
		self.server = GstRtspServer.RTSPServer()
		self.server.set_service(str(port))

	def addMedia(self, videos, bitrate, framerate, path):
		'''
		Add videos to the server.

		:param list videos: List of available videos.
		:param integer bitrate: The bitrate (in kbps).
		:param integer framerate: The framerate (in fps).
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
				factory = GstRtspServer.RTSPMediaFactory()
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
	def __init__(self, conf, video, port):
		'''
		**On init:** Some initialization code.

		:param dictionary conf: Parsed configuration file.
		:param string video: Path to the selected video.
		:param integer port: RTSP server port.
		'''
		#: Dictionary of configuration options (see :attr:`VideoTester.core.Client.conf`).
		self.conf = conf
		#: Path to the selected video (see :attr:`VideoTester.core.Client.video`).
		self.video = video
		#: Video size: ``(width, height)``.
		self.size = None
		#: Dictionary of paths to the processed video files: ``{'original':[<compressed>, <yuv>], 'coded':[<compressed>, <yuv>], 'received':[<compressed>, <yuv>]}``.
		self.files = {'original':[], 'coded':[], 'received':[]}
		#: Gstreamer pipeline.
		self.pipeline = None
		#: Gstreamer loop.
		self.loop = None
		#: Selected video URL.
		self.url = 'rtsp://%s:%s/%s.%s' % (
			self.conf['ip'],
			port,
			self.conf['video'],
			self.conf['codec']
		)

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
			e, d = msg.parse_error()
			VTLOG.error('GStreamer: Gst.MessageType.ERROR received')
			VTLOG.error(e)
			self.loop.quit()
		return True

	def __play(self):
		'''
		Attach event handler, set state to *playing* and run the loop (see :attr:`loop`).
		'''
		self.pipeline.get_bus().add_watch(0, self.__events)
		self.pipeline.set_state(Gst.State.PLAYING)
		self.loop = GObject.MainLoop()
		self.loop.run()
		VTLOG.debug('GStreamer: Loop stopped')

	def receiver(self):
		'''
		Connect to the RTSP server and receive the selected video (see :attr:`video`).
		'''
		VTLOG.info('Starting GStreamer receiver...')
		self.pipeline = Gst.parse_launch('rtspsrc name=source ! tee name=t ! queue ! %s %s ! filesink name=sink1 t. ! queue ! decodebin ! videorate skip-to-first=True ! video/x-raw,framerate=%s/1 ! filesink name=sink2' % (
			supported_codecs[self.conf['codec']]['rtpdepay'],
			supported_codecs[self.conf['codec']]['add'],
			self.conf['framerate']
		))
		source = self.pipeline.get_by_name('source')
		sink1 = self.pipeline.get_by_name('sink1')
		sink2 = self.pipeline.get_by_name('sink2')
		source.props.location = self.url
		source.props.protocols = self.conf['protocol']
		location = self.conf['tempdir'] + self.conf['num'] + '.' + self.conf['codec']
		self.files['received'].append(location)
		sink1.props.location = location
		location = self.conf['tempdir'] + self.conf['num'] + '.yuv'
		self.files['received'].append(location)
		sink2.props.location = location
		pad = sink2.get_static_pad('sink')
		pad.connect('notify::caps', self.__notifyCaps)
		self.__play()
		VTLOG.info('GStreamer receiver stopped')

	def reference(self):
		'''
		Make the reference videos.

		:returns: Paths to video files (see :attr:`files`) and video size (see :attr:`size`).
		:rtype: tuple
		'''
		VTLOG.info('Making reference...')
		self.pipeline = Gst.parse_launch('filesrc name=source ! decodebin ! videorate ! video/x-raw,framerate=%s/1 ! filesink name=sink1' % self.conf['framerate'])
		source = self.pipeline.get_by_name('source')
		sink1 = self.pipeline.get_by_name('sink1')
		location = self.video
		self.files['original'].append(location)
		source.props.location = location
		location = self.conf['tempdir'] + self.conf['num'] + '_ref_original.yuv'
		self.files['original'].append(location)
		sink1.props.location = location
		self.__play()
		self.pipeline = Gst.parse_launch('filesrc name=source ! decodebin ! videorate ! video/x-raw,framerate=%s/1 ! %s bitrate=%s ! tee name=t ! queue %s ! filesink name=sink2 t. ! queue ! decodebin ! filesink name=sink3' % (
			self.conf['framerate'],
			supported_codecs[self.conf['codec']]['encoder'],
			supported_codecs[self.conf['codec']]['bitrate_from_kbps'](self.conf['bitrate']),
			supported_codecs[self.conf['codec']]['add']
		))
		source = self.pipeline.get_by_name('source')
		sink2 = self.pipeline.get_by_name('sink2')
		sink3 = self.pipeline.get_by_name('sink3')
		location = self.video
		source.props.location = location
		location = self.conf['tempdir'] + self.conf['num'] + '_ref.' + self.conf['codec']
		self.files['coded'].append(location)
		sink2.props.location = location
		location = self.conf['tempdir'] + self.conf['num'] + '_ref.yuv'
		self.files['coded'].append(location)
		sink3.props.location = location
		self.__play()
		VTLOG.info('Reference made')
		return self.files, self.size

	def __notifyCaps(self, pad, args):
		'''
		Write caps to a file.

		:param pad: Gstreamer pad object.
		:param args: Other arguments.
		'''
		caps = pad.get_current_caps()
		if caps:
			caps = caps.to_string()
			aux = caps.split(', ')
			for x in aux:
				if x.find('width') != -1:
					width = int(x[11:len(x)])
				elif x.find('height') != -1:
					height = int(x[12:len(x)])
			self.size = (width, height)
			f = open(self.conf['tempdir'] + self.conf['num'] + '_caps.txt', 'wb')
			f.write(caps)
			f.close()
