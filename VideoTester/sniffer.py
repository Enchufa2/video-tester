# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import os, time, pcap
from struct import unpack_from
from scapy.all import Packet, ByteField, ShortField, IP, TCP, RTP, rdpcap
from . import VTLOG
from .utils import multiSort

class RTSPi(Packet):
    '''
    *RTSP interleaved* packet decoder.
    '''
    name = 'RTSP interleaved'
    fields_desc = [ ByteField('magic', 24),
                    ByteField('channel', 0),
                    ShortField('length', None) ]

class PcapIter(pcap.pcapObject):
    '''
    *Iterable PCAP Object*.
    '''
    def __init__(self, cap, filter=''):
        pcap.pcapObject.__init__(self)
        self.open_offline(cap)
        self.setfilter(filter, 0, 0)

    def __iter__(self):
        return self

    def next(self):
        res = pcap.pcapObject.next(self)
        if res is None:
            raise StopIteration
        return res

    def getOffsets(self, pkt):
        # Datalink offset
        try:
            dlt = {
                pcap.DLT_EN10MB: 14,
                pcap.DLT_LINUX_SLL: 16
            }[self.datalink()]
        except KeyError:
            raise Exception('Datalink protocol not supported')
        # IP offset
        ipv = unpack_from('!B', pkt, dlt)[0] >> 4
        if ipv == 4:
            net = 4 * (unpack_from('!B', pkt, dlt)[0] & 0x0F)
            proto = unpack_from('!B', pkt, dlt + 9)[0]
        elif ipv == 6:
            net = 40
            proto = unpack_from('!B', pkt, dlt + 6)[0]
        else:
            net = None
            proto = None
        # TCP/UDP offset
        if proto == 6:
            trans = 4 * (unpack_from('!B', pkt, dlt + net + 12)[0] >> 4)
        elif proto == 17:
            trans = 8
        else:
            trans = None

        return dlt, net, trans

class Sniffer:
    '''
    Network sniffer and packet parser.
    '''
    def __init__(self, iface, ip, cap):
        '''
        **On init:** Some initialization code.

        :param string iface: Network interface.
        :param string ip: Server IP to perform packet filtering.
        :param string proto: Protocol selected for the RTP transmission.
        :param string filename: PCAP filename to store packets.
        '''
        #: Network interface.
        self.iface = iface
        #: Server IP.
        self.ip = ip
        #: Capture file.
        self.captureFile = cap
        #: List of packet lengths.
        self.lengths = []
        #: List of packet arrival times.
        self.times = []
        #: List of RTP sequence numbers.
        self.sequences = []
        #: List of RTP timestamps.
        self.timestamps = []
        #: Round-trip time information (list of request-response pairs).
        self.rtt = []
        self.__add = 0

    def run(self):
        '''
        Start packet sniffing and save a capture file.
        '''
        try:
            p = pcap.pcapObject()
            p.open_live(self.iface, 65536, 1, 0)
            p.setfilter('host ' + self.ip, 0, 0)
            p.dump_open(self.captureFile)
            while p.dispatch(-1, None) >= 0:
                pass
        except:
            pass

    def parsePkts(self, proto, caps):
        '''
        Parse packets and extract :attr:`lengths`, :attr:`times`, :attr:`sequences`, :attr:`timestamps` and :attr:`rtt`.

        :param dictionary caps: Caps recolected from the GStreamer pipeline (see :attr:`VideoTester.gstreamer.RTSPClient.caps`).

        :returns: :attr:`lengths`, :attr:`times`, :attr:`sequences`, :attr:`timestamps` and :attr:`rtt`.
        :rtype: tuple
        '''
        VTLOG.info('Starting packet parser...')
        rtspDport = self.__getDport(caps['sdp-id'])
        self.__getRTT(caps['rtsp-sport'], rtspDport)

        if proto == 'tcp':
            self.captureFile = rdpcap(self.captureFile)
            self.__parseTCP(caps['rtsp-sport'], rtspDport, caps['ptype'])
        else:
            self.__parseUDP(caps['udp-dport'], caps['ptype'])
        self.__normalize(caps['seq-base'], caps['clock-rate'])

        VTLOG.debug('%s RTP packets received, %s losses' % (
            self.sequences[-1] - len(self.sequences) + 1,
            len(self.sequences)
        ))
        VTLOG.info('Packet parser stopped')

        return self.lengths, self.times, self.sequences, self.timestamps, self.rtt

    def __getDport(self, sid):
        p = PcapIter(self.captureFile, 'host %s' % self.ip)
        for plen, pkt, ts in p:
            if sid in pkt:
                offset = sum(p.getOffsets(pkt)[0:2])
                return unpack_from('!H', pkt, offset + 2)[0]

    def __getRTT(self, sport, dport):
        # PUSHes from client (24) and ACKs from server (16)
        filt = 'host %s and ((src port %s and dst port %s and tcp[13] = 24) or (src port %s and dst port %s and tcp[13] = 16))' % (self.ip, dport, sport, sport, dport)
        p = PcapIter(self.captureFile, filt)
        for i in range(0, 3):
            plen, pkt, ts1 = p.next()
            plen, pkt, ts2 = p.next()
            self.rtt.append((ts1, ts2))

    def __parseUDP(self, dport, ptype):
        '''
        Parse RTP over UDP session.
        '''
        p = PcapIter(self.captureFile,
            'host %s and udp and dst port %s' % (self.ip, dport))
        offsets = None
        offset = 0
        for plen, pkt, ts in p:
            if not offset:
                offsets = p.getOffsets(pkt)
                offset = sum(offsets)
            if ptype == unpack_from('!xB', pkt, offset)[0] & 0x7F:
                self.lengths.append(plen - offsets[0])
                self.times.append(ts)
                seq = unpack_from('!xxH', pkt, offset)[0]
                self.sequences.append(seq + self.__add)
                self.timestamps.append(unpack_from('!xxxxI', pkt, offset)[0])
                VTLOG.debug('UDP/RTP packet found. Sequence: %s' % seq)
                if seq == 65535:
                    self.__add += seq
        VTLOG.debug('RTP session parsed')
        self.sequences, self.times, self.timestamps = \
            multiSort(self.sequences, self.times, self.timestamps)
        VTLOG.debug('Sequence list sorted')

    def __parseTCP(self, rtspSport, rtspDport, ptype):
        '''
        Parse RTP over TCP session.
        '''
        def extract(p):
            '''
            Extract many RTSP packets from a TCP stream recursively.

            :param Packet p: TCP stream.
            '''
            fin = False
            a = p[RTSPi].length
            b = p[RTSPi].payload
            c = str(b)[0:a]
            loss = c.find('PACKETLOSS')
            if loss == -1:
                #No loss: look inside then
                extptype = ord(str(p[RTSPi].payload)[1]) & 0x7F #Delete RTP marker
                if ptype == extptype:
                    aux = str(p).split('ENDOFPACKET')
                    p[RTSPi].decode_payload_as(RTP)
                    self.lengths.append(int(aux[2]))
                    self.times.append(float(aux[1]) / 1000000)
                    self.sequences.append(p[RTP].sequence + self.__add)
                    self.timestamps.append(p[RTP].timestamp)
                    VTLOG.debug('TCP/RTP packet found. Sequence: ' + str(p[RTP].sequence))
                    if p[RTP].sequence == 65535:
                        self.__add += 65536
            else:
                #Avoid PACKETLOSS
                a = loss + len('PACKETLOSS')
                VTLOG.debug('PACKETLOSS!')

            p = RTSPi(str(b)[a:len(b)])
            extptype = ord(str(p[RTSPi].payload)[1]) & 0x7F
            #Let's find the next RTSP packet
            while not fin and not ((p[RTSPi].magic == 0x24) and (p[RTSPi].channel == 0x00) and (ptype == extptype)):
                stream = str(p)
                if stream.find('PACKETLOSS') == 0:
                    #Avoid PACKETLOSS
                    stream = stream[len('PACKETLOSS'):len(stream)]
                    VTLOG.debug('PACKETLOSS!')
                else:
                    #Find next packet
                    stream = stream[1:len(stream)]
                if len(stream) > 5:
                    p = RTSPi(stream)
                    extptype = ord(str(p[RTSPi].payload)[1]) & 0x7F
                else:
                    #Yep! We're done!
                    fin = True
            if not fin:
                extract(p)

        def fillGaps(seqlist, lenlist):
            '''
            Locate packet losses.

            :param list seqlist: List of RTP sequence numbers.
            :param list lenlist: List of packet lengths.

            :returns: List of losses (0 -> no loss, 1 -> loss).
            :rtype: list
            '''
            fill = [0 for i in range(0, len(seqlist))]
            for i in range(0, len(seqlist)-1):
                if seqlist[i] + lenlist[i] < seqlist[i+1]:
                    fill[i] = 1
            return fill

        play = False
        packetlist = []
        seqlist = []
        lenlist = []
        for p in self.captureFile:
            if p.haslayer(IP):
                if (str(p).find('PAUSE') != -1) and play:
                    VTLOG.debug('PAUSE found!')
                    break
                if not play:
                    if (str(p).find('PLAY') != -1) and (str(p).find('Public:') == -1):
                        play = True
                        VTLOG.debug('PLAY found!')
                #Packets from server, with TCP layer. Avoid ACK's. Avoid RTSP packets
                elif play and (p[IP].src == self.ip) and p.haslayer(TCP) and (len(p) > 66) and (str(p).find('RTSP/1.0') == -1):
                    if p.sport == rtspSport:
                        packetlist.append(p)
                        seqlist.append(p[TCP].seq)
                        lenlist.append(len(p[TCP].payload))
                        VTLOG.debug('TCP packet appended. Sequence: ' + str(p[TCP].seq))
        seqlist, packetlist, lenlist = multiSort(seqlist, packetlist, lenlist)
        VTLOG.debug('Sequence list sorted')
        #Locate packet losses
        fill = fillGaps(seqlist, lenlist)
        stream = ''
        for i, p in enumerate(packetlist):
            stream = ''.join([stream, str(p[TCP].payload)])
            #Mark ENDOFPACKET and save time and length
            stream = ''.join([stream, 'ENDOFPACKET'])
            stream = ''.join([stream, str(int(p.time * 1000000))])
            stream = ''.join([stream, 'ENDOFPACKET'])
            stream = ''.join([stream, str(p.len)])
            stream = ''.join([stream, 'ENDOFPACKET'])
            if fill[i]:
                #Mark PACKETLOSS
                VTLOG.debug('PACKETLOSS!')
                stream = ''.join([stream, 'PACKETLOSS'])
        VTLOG.debug('TCP payloads assembled')
        stream = RTSPi(stream)
        extract(stream)
        VTLOG.debug('RTP session parsed')

    def __normalize(self, seqbase, clock):
        '''
        Normalize :attr:`sequences`, :attr:`times` and :attr:`timestamps`.
        '''
        time = self.times[0]
        timest = float(self.timestamps[0])
        for i in range(0, len(self.sequences)):
            self.sequences[i] = self.sequences[i] - seqbase
            self.times[i] = self.times[i] - time
            self.timestamps[i] = (float(self.timestamps[i]) - timest) / clock
