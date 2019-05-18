# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <iucar@fedoraproject.org>
## This program is published under a GPLv3 license

import os, ConfigParser, signal, pickle, time, socket
from SimpleXMLRPCServer import SimpleXMLRPCServer
from xmlrpclib import ServerProxy
from multiprocessing import Process
from . import VTLOG, netifaces, supported_codecs, supported_protocols
from .gstreamer import RTSPServer, RTSPClient
from .sniffer import Sniffer
from .measures.qos import QoSmeter
from .measures.bs import BSmeter
from .measures.vq import VQmeter
from .video import YUVVideo, CodedVideo

class VTBase:
    '''
    Superclass that gathers several common functionalities shared by the client and the server.
    '''
    def __init__(self, conf=None):
        '''
        **On init:** Parse the `video` section.

        :param conf: Path to a configuration file.
        :type conf: string

        .. warning::
            This section MUST be present in the default configuration file
            and MUST contain the same videos at the client and the server.
        '''
        if not conf:
            #: Configuration file path.
            self.CONF = os.path.abspath('VT.conf')
        else:
            self.CONF = os.path.abspath(conf)
        self.conf = dict(self.parseConf(self.CONF, 'general'))
        #: Server port.
        self.port = int(self.conf.pop('port'))
        #: Video path.
        self.path = self.conf.pop('path')
        #: List of ``(id, name)`` pairs for each available video.
        self.videos = self.conf.items()

    def run(self):
        '''
        Do nothing.

        .. note::
            This method MUST be overwritten by the subclasses.
        '''
        VTLOG.error('Not implemented')

    def parseConf(self, file, section):
        '''
        Extract a section from a configuration file.

        :param string file:
        :param string section: Path to the configuration file.

        :returns: A list of ``(name, value)`` pairs for each option in the given section.
        :rtype: list of tuples
        '''
        config = ConfigParser.RawConfigParser()
        config.read(file)
        return config.items(section)

class VTServer(VTBase, SimpleXMLRPCServer):
    '''
    VT Server class.
    '''
    def __init__(self, conf=None):
        '''
        **On init:** Some initialization code.

        :param conf: Path to a configuration file.
        :type conf: string
        '''
        VTBase.__init__(self, conf)
        SimpleXMLRPCServer.__init__(self, ('0.0.0.0', self.port), logRequests=False)

        #: List of available videos.
        self.videos = [x[1] for x in self.videos]
        #: Dictionary of running RTSP servers.
        self.servers = dict()
        #: List of exported methods (:meth:`run` and :meth:`stop`).
        self.exports = ['run', 'stop']

    def _dispatch(self, method, params):
        '''
        Dispatch remote calls only if they are in :attr:`exports`.
        '''
        if method in self.exports:
            func = getattr(self, method)
            return func(*params)
        else:
            raise Exception('method "%s" is not supported' % method)

    def serve_forever(self):
        VTLOG.info('XMLRPC Server at 0.0.0.0:%s, use Ctrl-C to exit' % (self.port))
        SimpleXMLRPCServer.serve_forever(self)

    def run(self, bitrate, framerate):
        '''
        Run a subprocess for an RTSP server with a given bitrate and framerate (if not running)
        or add a client (if running).

        :param int bitrate: The bitrate (in kbps).
        :param int framerate: The framerate (in fps).

        :returns: The RTSP server port.
        :rtype: int
        '''
        key = '%s kbps, %s fps' % (bitrate, framerate)
        if key in self.servers:
            self.servers[key]['clients'] = self.servers[key]['clients'] + 1
        else:
            self.servers[key] = dict()
            port = self.__freePort()
            server = RTSPServer(port)
            server.addMedia(self.videos, bitrate, framerate, self.path)
            self.servers[key]['server'] = Process(target=server.run)
            try:
                self.servers[key]['server'].start()
            except Exception as e:
                VTLOG.error(e)
                self.servers[key]['server'].terminate()
                self.servers[key]['server'].join()
                raise e
            self.servers[key]['port'] = port
            self.servers[key]['clients'] = 1
            VTLOG.info('PID: %s | RTSP Server at 0.0.0.0:%s, %s' % (self.servers[key]['server'].pid, port, key))

        VTLOG.info('PID: %s | Client started | Connections: %s' % (self.servers[key]['server'].pid, self.servers[key]['clients']))
        return self.servers[key]['port']

    def stop(self, bitrate, framerate):
        '''
        Stop an RTSP server with a given bitrate and framerate (if no remaining clients)
        or remove a client (if remaining clients).

        :param int bitrate: The bitrate (in kbps).
        :param int framerate: The framerate (in fps).

        :returns: True.
        :rtype: boolean
        '''
        key = '%s kbps, %s fps' % (bitrate, framerate)
        self.servers[key]['clients'] = self.servers[key]['clients'] - 1
        VTLOG.info('PID: %s | Client stopped | Connections: %s' % (self.servers[key]['server'].pid, self.servers[key]['clients']))
        if self.servers[key]['clients'] == 0:
            self.servers[key]['server'].terminate()
            self.servers[key]['server'].join()
            VTLOG.info('PID: %s | Terminated' % (self.servers[key]['server'].pid))
            self.servers.pop(key)
        return True

    def __freePort(self):
        '''
        Find an unused port starting from :attr:`VideoTester.core.VTServer.port`.

        :returns: An unused port number.
        :rtype: int
        '''
        port = self.port
        while True:
            port += 1
            try:
                s = socket.socket()
                s.bind(('localhost', port))
                break
            except:
                continue
        s.close()
        return port

class VTClient(VTBase):
    '''
    VT Client class.
    '''
    def __init__(self, conf=None):
        '''
        **On init:** Some initialization code.

        :param conf: Path to a configuration file.
        :type conf: string
        '''
        VTBase.__init__(self, conf)
        #: Parsed configuration.
        self.conf = dict(self.parseConf(self.CONF, 'client'))
        self.conf['temp'] = os.path.abspath(self.conf['temp'])
        self.conf['bitrate'] = int(self.conf['bitrate'])
        self.conf['framerate'] = int(self.conf['framerate'])
        if self.conf['codec'] not in supported_codecs.keys():
            raise Exception('Codec %s not supported' % self.conf['codec'])
        if self.conf['protocol'] not in supported_protocols:
            raise Exception('Protocol %s not supported' % self.conf['protocol'])
        if self.conf['iface'] not in netifaces:
            raise Exception('Interface %s not found' % self.conf['iface'])

    def __get_tempdir(self):
        tempdir = '%s/%s_%s_%s_%s_%s/' % (self.conf['temp'], self.conf['video'], self.conf['codec'], self.conf['bitrate'], self.conf['framerate'], self.conf['protocol'])
        try:
            os.makedirs(tempdir)
        except OSError:
            pass
        i , j = 0, True
        while j and i < 100:
            if i < 10:
                num = '0' + str(i)
            else:
                num = str(i)
            i = i + 1
            j = os.path.exists(tempdir + num + '.yuv')
        if j:
            raise Exception('The temp directory is full')
        return tempdir, num

    def run(self):
        '''
        Run the client and perform all the operations:
         * Connect to the server.
         * Receive video while sniffing packets.
         * Close connection.
         * Process data and extract information.
         * Run measures.

        :returns: A dictionary of video files received (see :attr:`VideoTester.gstreamer.RTSPClient.files`), a dictionary of caps (see :attr:`VideoTester.gstreamer.RTSPClient.caps`) and a list of results
        :rtype: list
        '''
        VTLOG.info('Client running!')
        try:
            tempdir, num = self.__get_tempdir()
            server = ServerProxy('http://%s:%s' % (self.conf['ip'], self.port))
            rtspport = server.run(self.conf['bitrate'], self.conf['framerate'])
        except Exception as e:
            VTLOG.error(e)
            return None
        VTLOG.info('Connected to XMLRPC Server at %s:%s' % (self.conf['ip'], self.port))
        VTLOG.info('Evaluating: %s, %s, %s kbps, %s fps, %s' % (self.conf['video'], self.conf['codec'], self.conf['bitrate'], self.conf['framerate'], self.conf['protocol']))

        sniffer = Sniffer(self.conf['iface'],
                          self.conf['ip'],
                          '%s%s.cap' % (tempdir, num))
        rtspclient = RTSPClient(
            tempdir + num,
            self.conf['codec'],
            self.conf['bitrate'],
            self.conf['framerate']
        )
        url = 'rtsp://%s:%s/%s.%s' % (
			self.conf['ip'],
			rtspport,
			self.conf['video'],
			self.conf['codec']
		)
        child = Process(target=sniffer.run)
        ret = True
        try:
            child.start()
            VTLOG.info('PID: %s | Sniffer started' % child.pid)
            time.sleep(1)
            rtspclient.receive(url, self.conf['protocol'])
        except KeyboardInterrupt:
            VTLOG.warning('Keyboard interrupt!')
        except Exception as e:
            VTLOG.error(e)
        else:
            ret = False
        server.stop(self.conf['bitrate'], self.conf['framerate'])
        child.terminate()
        child.join()
        VTLOG.info('PID: %s | Sniffer stopped' % child.pid)
        if ret:
            return None

        video = '/'.join([self.path, dict(self.videos)[self.conf['video']]])
        rtspclient.makeReference(video)
        conf = {
            'codec': self.conf['codec'],
            'bitrate': self.conf['bitrate'],
            'framerate': self.conf['framerate'],
            'caps': rtspclient.caps
        }
        packetdata = sniffer.parsePkts(self.conf['protocol'], rtspclient.caps)
        codecdata, rawdata = self.__parseVideo(
            rtspclient.files, rtspclient.caps, self.conf['codec'])

        results = []
        results.extend(QoSmeter(self.conf['qos'], packetdata).run())
        results.extend(BSmeter(self.conf['bs'], codecdata).run())
        results.extend(VQmeter(self.conf['vq'], (conf, rawdata, codecdata, packetdata)).run())

        VTLOG.info('Saving measures...')
        for measure in results:
            f = open(tempdir + num + '_' + measure['name'] + '.pkl', 'wb')
            pickle.dump(measure, f)
            f.close()
        VTLOG.info('Client stopped!')

        return rtspclient.files, rtspclient.caps, results

    def __parseVideo(self, videofiles, caps, codec):
        VTLOG.info('Parsing videos...')
        codecdata = {}
        rawdata = {}
        for x in videofiles.keys():
            if x != 'original':
                codecdata[x] = CodedVideo(videofiles[x][0], codec)
            rawdata[x] = YUVVideo(videofiles[x][1], (
                caps['width'], caps['height'], caps['format']
            ))
        return codecdata, rawdata
