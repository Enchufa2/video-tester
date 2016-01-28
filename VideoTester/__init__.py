# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

__author__ = 'Iñaki Úcar <i.ucar86@gmail.com>'
__version__ = '1.0.0'

__all__ = []

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GObject
GObject.threads_init()
Gst.init(None)
del(gi, Gst, GObject)

__all__.extend(['VTLOG'])
import logging
VTLOG = logging.getLogger(__name__)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s : %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
VTLOG.addHandler(ch)
VTLOG.setLevel(logging.ERROR)
del(logging, formatter, ch)

__all__.extend(['netifaces'])
import pcap
netifaces = [_[0] for _ in pcap.findalldevs() if _[1]==None]
del(pcap, _)

__all__.extend(['supported_protocols', 'supported_codecs'])
supported_protocols = ['udp', 'tcp', 'udp-mcast']
supported_codecs = {
    'h263': {
        'encoder': 'avenc_h263',
        'rtppay': 'rtph263pay',
        'rtpdepay': 'rtph263depay',
        'bitrate_from_kbps': lambda x: x*1000,
        'add': ''
    },
    'h264': {
        'encoder': 'x264enc',
        'rtppay': 'rtph264pay',
        'rtpdepay': 'rtph264depay',
        'bitrate_from_kbps': lambda x: x,
        'add': ''
    },
    'mpeg4': {
        'encoder': 'avenc_mpeg4',
        'rtppay': 'rtpmp4vpay',
        'rtpdepay': 'rtpmp4vdepay',
        'bitrate_from_kbps': lambda x: x*1000,
        'add': ''
    },
    'theora': {
        'encoder': 'theoraenc',
        'rtppay': 'rtptheorapay',
        'rtpdepay': 'rtptheoradepay ! theoraparse',
        'bitrate_from_kbps': lambda x: x,
        'add': '! matroskamux'
    }
}

__all__.extend([
    'VTBase', 'VTServer', 'VTClient',
    'RTSPServer', 'RTSPClient',
    'VTApp',
    'Sniffer',
    'multiSort',
    'YUVVideo', 'CodedVideo',
    'measures'
])
from .core import VTBase, VTServer, VTClient
from .gstreamer import RTSPServer, RTSPClient
from .gui import VTApp
from .sniffer import Sniffer
from .utils import multiSort
from .video import YUVVideo, CodedVideo

del(core, gstreamer, gui, resources, sniffer, video)
