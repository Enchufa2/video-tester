# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from SimpleXMLRPCServer import SimpleXMLRPCServer
import sys, os, ConfigParser, logging

VTLOG = logging.getLogger("VT")

class VT:
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
        #: Configuration file path.
        self.CONF = conf
        if not conf:
            self.CONF = os.getcwd() + '/VT.conf'
        else:
            if not os.path.isabs(conf):
                self.CONF = os.getcwd() + '/' + conf

        #: List of ``(id, name)`` pairs for each available video.
        self.videos = dict(self.parseConf(self.CONF, "video"))
        #: Video path.
        self.path = self.videos.pop('path')
        self.videos = self.videos.items()

    def run(self):
        """
        Do nothing.

        .. note::
            This method MUST be overwritten by the subclasses.

        :raises: Not implemented.
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

        :raises: Bad configuration file or path.
        """
        try:
            config = ConfigParser.RawConfigParser()
            config.read(file)
            return config.items(section)
        except:
            VTLOG.error("Bad configuration file or path")
            sys.exit()

class Server(VT, SimpleXMLRPCServer):
    """
    VT Server class.
    """
    def __init__(self, conf=None):
        """
        **On init:** Some initialization code.

        :param conf: Path to a configuration file.
        :type conf: string
        """
        VT.__init__(self, conf)
        #: Dictionary of configuration options.
        self.conf = dict(self.parseConf(self.CONF, 'server'))
        self.conf['port'] = int(self.conf['port'])

        SimpleXMLRPCServer.__init__(self, ('0.0.0.0', self.conf['port']), logRequests=False)
        #: List of available videos.
        self.videos = [x[1] for x in self.videos]
        #: Dictionary of running RTSP servers.
        self.servers = dict()
        #: Next RTSP port (integer). It increases each time by one.
        self.port = self.conf['port'] + 1
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

    def run(self, bitrate, framerate):
        """
        Run a subprocess for an RTSP server with a given bitrate and framerate (if not running)
        or add a client (if running).

        :param bitrate: The bitrate (in kbps).
        :type bitrate: string or integer
        :param framerate: The framerate (in fps).
        :type framerate: string or integer

        :returns: The RTSP server port.
        :rtype: integer

        :raises OSError: An error ocurred while running subprocess.
        """
        from multiprocessing import Process
        from VideoTester.gstreamer import RTSPserver

        key = str(bitrate) + ' kbps - ' + str(framerate) + ' fps'
        if key in self.servers:
            self.servers[key]['clients'] = self.servers[key]['clients'] + 1
        else:
            self.servers[key] = dict()
            while not self.__freePort():
                self.port = self.port + 1
            self.servers[key]['server'] = Process(target=RTSPserver(self.port, bitrate, framerate, self.path, self.videos).run)
            try:
                self.servers[key]['server'].start()
            except e:
                VTLOG.error(e)
                self.servers[key]['server'].terminate()
                self.servers[key]['server'].join()
                sys.exit()
            self.servers[key]['port'] = self.port
            self.servers[key]['clients'] = 1
            VTLOG.info("RTSP Server running!")

        VTLOG.info("PID: " + str(self.servers[key]['server'].pid) + ", " + key + " server, connected clients: " + str(self.servers[key]['clients']))
        return self.servers[key]['port']

    def stop(self, bitrate, framerate):
        """
        Stop an RTSP server with a given bitrate and framerate (if no remaining clients)
        or remove a client (if remaining clients).

        :param bitrate: The bitrate (in kbps).
        :type bitrate: string or integer
        :param framerate: The framerate (in fps).
        :type framerate: string or integer

        :returns: True.
        :rtype: boolean
        """
        key = str(bitrate) + ' kbps - ' + str(framerate) + ' fps'
        self.servers[key]['clients'] = self.servers[key]['clients'] - 1
        if self.servers[key]['clients'] == 0:
            self.servers[key]['server'].terminate()
            self.servers[key]['server'].join()
            VTLOG.info(key + " server: last client disconnected and server stopped")
            self.servers.pop(key)
        else:
            VTLOG.info(key + " server: client disconnected. Remaining: " + str(self.servers[key]['clients']))
        return True

    def __freePort(self):
        """
        Check that the :attr:`VideoTester.core.Server.port` is unused.

        :returns: True if port is unused. False if port is in use.
        :rtype: boolean
        """
        from socket import socket
        try:
            s = socket()
            s.bind(('localhost', self.port))
        except:
            return False
        s.close()
        return True

class Client(VT):
    """
    VT Client class.
    """
    def __init__(self, conf=None, gui=False):
        """
        **On init:** Some initialization code.

        :param conf: Path to a configuration file (string) or parsed configuration file (dictionary).
        :type conf: string or dictionary
        :param boolean gui: True if :class:`Client` is called from GUI. False otherwise.

        .. warning::
            If ``gui == True``, `file` MUST be a dictionary. Otherwise, `file` MUST be a string.
        """
        if gui:
            VT.__init__(self)
            #: Dictionary of configuration options.
            self.conf = conf
        else:
            VT.__init__(self, conf)
            self.conf = dict(self.parseConf(self.CONF, "client"))

        #: Path to the selected video.
        if not os.path.isabs(self.conf['temp']):
            self.conf['temp'] = os.getcwd() + self.conf['temp']
        self.video = '/'.join([self.path, dict(self.videos)[self.conf['video']]])
        self.conf['tempdir'] = self.conf['temp'] + self.conf['video'] + '_' + self.conf['codec'] + '_' + self.conf['bitrate'] + '_' + self.conf['framerate'] + '_' + self.conf['protocols'] + '/'
        try:
            os.mkdir(self.conf['tempdir'])
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
        VTLOG.info("Client running!")
        VTLOG.info("XMLRPC Server at " + self.conf['ip'] + ':' + self.conf['port'])
        VTLOG.info("Evaluating: " + self.conf['video'] + " + " + self.conf['codec'] + " at " + self.conf['bitrate'] + " kbps and " + self.conf['framerate'] + " fps under " + self.conf['protocols'])

        from xmlrpclib import ServerProxy
        from scapy.all import rdpcap
        from multiprocessing import Process, Queue
        from VideoTester.gstreamer import RTSPclient
        from VideoTester.sniffer import Sniffer
        from VideoTester.measures.qos import QoSmeter
        from VideoTester.measures.bs import BSmeter
        from VideoTester.measures.vq import VQmeter

        try:
            server = ServerProxy('http://' + self.conf['ip'] + ':' + self.conf['port'])
            self.conf['rtspport'] = str(server.run(self.conf['bitrate'], self.conf['framerate']))
        except:
            VTLOG.error("Bad IP or port")
            sys.exit()

        sniffer = Sniffer(self.conf)
        rtspclient = RTSPclient(self.conf, self.video)
        q = Queue()
        child = Process(target=sniffer.run, args=(q,))
        try:
            child.start()
            self.__ping()
            rtspclient.receiver()
            sniffer.cap = rdpcap(q.get())
            child.join()
        except KeyboardInterrupt:
            VTLOG.warning("Keyboard interrupt!")
            server.stop(self.conf['bitrate'], self.conf['framerate'])
            child.terminate()
            child.join()
            sys.exit()
        server.stop(self.conf['bitrate'], self.conf['framerate'])

        videodata, size = rtspclient.reference()
        conf = {'codec':self.conf['codec'], 'bitrate':float(self.conf['bitrate']), 'framerate':float(self.conf['framerate']), 'size':size}
        packetdata = sniffer.parsePkts()
        codecdata, rawdata = self.__loadData(videodata, size, self.conf['codec'])
        qosm = QoSmeter(self.conf['qos'], packetdata).run()
        bsm = BSmeter(self.conf['bs'], codecdata).run()
        vqm = VQmeter(self.conf['vq'], (conf, rawdata, codecdata, packetdata)).run()

        self.__saveMeasures(qosm + bsm + vqm)
        VTLOG.info("Client stopped!")
        return qosm + bsm + vqm, self.conf['tempdir'] + self.conf['num']

    def __ping(self):
        """
        Ping to server (4 echoes).
        """
        from scapy.all import IP, ICMP, send
        from time import sleep
        sleep(0.5)
        VTLOG.info("Pinging...")
        for i in range(0, 4):
            send(IP(dst=self.conf['ip'])/ICMP(seq=i), verbose=False)
            sleep(0.5)

    def __loadData(self, videodata, size, codec):
        """
        Load raw video data and coded video data.

        :param videodata: (see :attr:`VideoTester.gstreamer.RTSPclient.files`)

        :returns: Coded video data object (see :class:`VideoTester.video.YUVvideo`) and raw video data object (see :class:`VideoTester.video.CodedVideo`).
        :rtype: tuple
        """
        VTLOG.info("Loading videos...")
        from VideoTester.video import YUVvideo, CodedVideo
        codecdata = {}
        rawdata = {}
        for x in videodata.keys():
            if x != 'original':
                codecdata[x] = CodedVideo(videodata[x][0], codec)
            rawdata[x] = YUVvideo(videodata[x][1], size)
            VTLOG.info("+++")
        return codecdata, rawdata

    def __saveMeasures(self, measures):
        """
        Save measures to disc (with standard module :mod:`pickle`).

        :param list measures: List of measures.
        """
        VTLOG.info("Saving measures...")
        from pickle import dump
        for measure in measures:
            f = open(self.conf['tempdir'] + self.conf['num'] + '_' + measure['name'] + '.pkl', "wb")
            dump(measure, f)
            f.close()
