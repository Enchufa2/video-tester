# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import sys, os, ConfigParser, signal, pickle, time, socket
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
    """
    Superclass that gathers several common functionalities shared by the client and the server.
    """
    def __init__(self, conf=None):
        """
        **On init:** Parse the `video` section.

        :param conf: Path to a configuration file.
        :type conf: string

        .. warning::
            This section MUST be present in the default configuration file
            and MUST contain the same videos at the client and the server.
        """
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
        """
        Do nothing.

        .. note::
            This method MUST be overwritten by the subclasses.
        """
        VTLOG.error("Not implemented")
        sys.exit()

    def parseConf(self, file, section):
        """
        Extract a section from a configuration file.

        :param string file:
        :param string section: Path to the configuration file.

        :returns: A list of ``(name, value)`` pairs for each option in the given section.
        :rtype: list of tuples
        """
        try:
            config = ConfigParser.RawConfigParser()
            config.read(file)
            return config.items(section)
        except Exception as e:
            VTLOG.error(e)
            sys.exit()

class VTServer(VTBase, SimpleXMLRPCServer):
    """
    VT Server class.
    """
    def __init__(self, conf=None):
        """
        **On init:** Some initialization code.

        :param conf: Path to a configuration file.
        :type conf: string
        """
        VTBase.__init__(self, conf)
        SimpleXMLRPCServer.__init__(self, ('0.0.0.0', self.port), logRequests=False)

        #: List of available videos.
        self.videos = [x[1] for x in self.videos]
        #: Dictionary of running RTSP servers.
        self.servers = dict()
        #: List of exported methods (:meth:`run` and :meth:`stop`).
        self.exports = ['run', 'stop']

    def _dispatch(self, method, params):
        """
        Dispatch remote calls only if they are in :attr:`exports`.
        """
        if method in self.exports:
            func = getattr(self, method)
            return func(*params)
        else:
            raise Exception('method "%s" is not supported' % method)

    def serve_forever(self):
        VTLOG.info('XMLRPC Server at 0.0.0.0:%s, use Ctrl-C to exit' % (self.port))
        SimpleXMLRPCServer.serve_forever(self)

    def run(self, bitrate, framerate):
        """
        Run a subprocess for an RTSP server with a given bitrate and framerate (if not running)
        or add a client (if running).

        :param integer bitrate: The bitrate (in kbps).
        :param integer framerate: The framerate (in fps).

        :returns: The RTSP server port.
        :rtype: integer
        """
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
                sys.exit()
            self.servers[key]['port'] = port
            self.servers[key]['clients'] = 1
            VTLOG.info('PID: %s | RTSP Server at 0.0.0.0:%s, %s' % (self.servers[key]['server'].pid, port, key))

        VTLOG.info('PID: %s | Client started | Connections: %s' % (self.servers[key]['server'].pid, self.servers[key]['clients']))
        return self.servers[key]['port']

    def stop(self, bitrate, framerate):
        """
        Stop an RTSP server with a given bitrate and framerate (if no remaining clients)
        or remove a client (if remaining clients).

        :param integer bitrate: The bitrate (in kbps).
        :param integer framerate: The framerate (in fps).

        :returns: True.
        :rtype: boolean
        """
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
        """
        Find an unused port starting from :attr:`VideoTester.core.Server.port`.

        :returns: an unused port number.
        :rtype: integer
        """
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
    """
    VT Client class.
    """
    def __init__(self, conf=None):
        """
        **On init:** Some initialization code.

        :param conf: Path to a configuration file.
        :type conf: string
        """
        VTBase.__init__(self, conf)
        #: Parsed configuration.
        self.conf = dict(self.parseConf(self.CONF, 'client'))
        self.conf['temp'] = os.path.abspath(self.conf['temp'])
        self.conf['bitrate'] = int(self.conf['bitrate'])
        self.conf['framerate'] = int(self.conf['framerate'])
        #: Selected video.
        self.video = '/'.join([self.path, dict(self.videos)[self.conf['video']]])
        if self.conf['codec'] not in supported_codecs.keys():
            VTLOG.error('Codec %s not supported' % self.conf['codec'])
            sys.exit()
        if self.conf['protocol'] not in supported_protocols:
            VTLOG.error('Protocol %s not supported' % self.conf['protocol'])
            sys.exit()
        if self.conf['iface'] not in netifaces:
            VTLOG.error('Interface %s not found' % self.conf['iface'])
            sys.exit()
        #: Results from all measures.
        self.results = []

    def __set_tempdir(self):
        self.conf['tempdir'] = '%s/%s_%s_%s_%s_%s/' % (self.conf['temp'], self.conf['video'], self.conf['codec'], self.conf['bitrate'], self.conf['framerate'], self.conf['protocol'])
        try:
            os.makedirs(self.conf['tempdir'])
        except OSError:
            pass
        i , j = 0, True
        while j and i < 100:
            if i < 10:
                num = '0' + str(i)
            else:
                num = str(i)
            i = i + 1
            j = os.path.exists(self.conf['tempdir'] + num + '.yuv')
        if j:
            VTLOG.error("The temp directory is full")
            sys.exit()
        #: Numerical prefix for temporary files.
        self.conf['num'] = num

    def run(self):
        """
        Run the client and perform all the operations:
         * Connect to the server.
         * Receive video while sniffing packets.
         * Close connection.
         * Process data and extract information.
         * Run meters.

        :returns: A list of measures (see :attr:`VideoTester.measures.core.Meter.measures`) and the path to the temporary directory plus files prefix: ``<path-to-tempdir>/<prefix>``.
        :rtype: tuple
        """
        VTLOG.info('Client running!')
        self.__set_tempdir()
        try:
            server = ServerProxy('http://%s:%s' % (self.conf['ip'], self.port))
            rtspport = server.run(self.conf['bitrate'], self.conf['framerate'])
        except Exception as e:
            VTLOG.error(e)
            sys.exit()
        VTLOG.info('Connected to XMLRPC Server at %s:%s' % (self.conf['ip'], self.port))
        VTLOG.info('Evaluating: %s, %s, %s kbps, %s fps, %s' % (self.conf['video'], self.conf['codec'], self.conf['bitrate'], self.conf['framerate'], self.conf['protocol']))

        sniffer = Sniffer(self.conf['iface'],
                          self.conf['ip'],
                          self.conf['protocol'],
                          '%s%s.cap' % (self.conf['tempdir'], self.conf['num']))
        rtspclient = RTSPClient(self.conf, self.video, rtspport)
        child = Process(target=sniffer.run)
        try:
            child.start()
            sniffer.ping()
            rtspclient.receiver()
        except KeyboardInterrupt:
            VTLOG.warning("Keyboard interrupt!")
            server.stop(self.conf['bitrate'], self.conf['framerate'])
            child.terminate()
            child.join()
            sys.exit()
        server.stop(self.conf['bitrate'], self.conf['framerate'])
        child.terminate()
        child.join()

        videodata, size = rtspclient.reference()
        conf = {
            'codec': self.conf['codec'],
            'bitrate': self.conf['bitrate'],
            'framerate': self.conf['framerate'],
            'size': size
        }
        packetdata = sniffer.parsePkts()
        codecdata, rawdata = self.__loadData(videodata, size, self.conf['codec'])

        self.results = []
        self.results.extend(QoSmeter(self.conf['qos'], packetdata).run())
        self.results.extend(BSmeter(self.conf['bs'], codecdata).run())
        self.results.extend(VQmeter(self.conf['vq'], (conf, rawdata, codecdata, packetdata)).run())

        VTLOG.info('Saving measures...')
        for measure in self.results:
            f = open(self.conf['tempdir'] + self.conf['num'] + '_' + measure['name'] + '.pkl', 'wb')
            pickle.dump(measure, f)
            f.close()
        VTLOG.info('Client stopped!')

    def __loadData(self, videodata, size, codec):
        """
        Load raw video data and coded video data.

        :param videodata: (see :attr:`VideoTester.gstreamer.RTSPclient.files`)

        :returns: Coded video data object (see :class:`VideoTester.video.YUVVideo`) and raw video data object (see :class:`VideoTester.video.CodedVideo`).
        :rtype: tuple
        """
        VTLOG.info("Loading videos...")
        codecdata = {}
        rawdata = {}
        for x in videodata.keys():
            if x != 'original':
                codecdata[x] = CodedVideo(videodata[x][0], codec)
            rawdata[x] = YUVVideo(videodata[x][1], size)
            VTLOG.info("+++")
        return codecdata, rawdata
