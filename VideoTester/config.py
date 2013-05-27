# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import logging
from platform import processor
from sys import exit
import os

def makeDir(dir):
    """
    Make the directory `dir` if not exists.
    """
    from os import mkdir
    try:
        mkdir(dir)
    except OSError:
        pass

def initLogger(args):
    """
    Initialize the VT logger: this function sets a formatter, the handlers and their logging levels.
    
    :param args: The command-line arguments returned by :func:`parseArgs()`.
    """
    if args.mode == "server":
        formatter = logging.Formatter("[%(asctime)s VTServer] %(levelname)s : %(message)s")
    else:
        logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
        formatter = logging.Formatter("[%(asctime)s VTClient] %(levelname)s : %(message)s")
    makeDir(TEMP)
    fh = logging.FileHandler(TEMP + 'VT.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    VTLOG.addHandler(fh)
    if not hasattr(args, 'gui') or not args.gui:
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        VTLOG.addHandler(ch)
    VTLOG.setLevel(logging.INFO)

def parseArgs():
    """
    Parse the command-line arguments with the standard module :mod:`argparse`.
    
    :returns: An object with the argument strings as attributes.
    """
    import textwrap
    import argparse
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=textwrap.dedent('''\
                VideoTester 0.1
                ===============
                  Video Quality Assessment Tool
                  Visit http://video-tester.googlecode.com for support and updates
                  
                  Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
                  This program is published under a GPLv3 license
                '''))
    subparsers = parser.add_subparsers(title='subcommands', dest='mode')
    parser_server = subparsers.add_parser('server', help='launch VT as server')
    parser_client = subparsers.add_parser('client', help='launch VT as client')
    parser_client.add_argument('-g', '--gui', dest='gui', action='store_true', help='launch graphical interface')
    parser_client.add_argument('-c', '--conf', dest='conf', nargs=1, help='client configuration file')
    return parser.parse_args()

def getIpAddress(ifname):
    """
    Get the IP address of a network interface.
    
    :param string ifname: The interface name.
    
    :returns: The IP address.
    :rtype: string
    """
    import socket
    import fcntl
    import struct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def bubbleSort(l, l1=None, l2=None):
    """
    Bubble sort algorithm modification. This function sorts the first list. Optionally, it sorts two additional lists with the same pattern than the first.
    
    :param list l: One list.
    :param list l1: Other list.
    :param list l2: Other list.
    """
    def swap(a, b):
        return b, a
    
    n = len(l)
    for i in range(0, n):
        for j in range(n-1, i, -1):
            if l[j-1] > l[j]:
                l[j-1], l[j] = swap(l[j-1], l[j])
                if l1:
                    l1[j-1], l1[j] = swap(l1[j-1], l1[j])
                if l2:
                    l2[j-1], l2[j] = swap(l2[j-1], l2[j])

#: VT logger.
VTLOG = logging.getLogger("VT")
#: Current working path (result of :func:`os.getcwd()` function).
USERPATH = os.getcwd()
#: Path to the default configuration file (relative to :const:`USERPATH`).
CONF = USERPATH + '/VT.conf'
#: Path to the temporary directory (relative to :const:`USERPATH`).
TEMP = USERPATH + '/temp/'
thispath = os.path.realpath(__file__)
thispath = thispath[0:thispath.rfind('/')]
#: Server interface.
SERVERIFACE = 'eth0'
#: Server IP address.
SERVERIP = getIpAddress(SERVERIFACE)
#: Server base port.
SERVERPORT = 8000
