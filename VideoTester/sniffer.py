# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import os, time, pcap
from struct import unpack_from
from . import VTLOG
from .utils import multiSort

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
            p.setfilter('host %s and (tcp or udp)' % self.ip, 0, 0)
            p.dump_open(self.captureFile)
            while p.dispatch(-1, None) >= 0:
                pass
        except:
            pass

    def parsePkts(self, proto, caps):
        '''
        Parse packets and extract :attr:`lengths`, :attr:`times`, :attr:`sequences`, :attr:`timestamps` and :attr:`rtt`.

        :param dict caps: Caps recolected from the GStreamer pipeline (see :attr:`VideoTester.gstreamer.RTSPClient.caps`).

        :returns: :attr:`lengths`, :attr:`times`, :attr:`sequences`, :attr:`timestamps` and :attr:`rtt`.
        :rtype: tuple
        '''
        VTLOG.info('Starting packet parser...')
        rtspDport = self.__getDport(caps['sdp-id'])
        self.__getRTT(caps['rtsp-sport'], rtspDport)

        if proto == 'tcp':
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
        for plen, pkt, ts in p:
            if not offsets:
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
        # Parse packets
        p = PcapIter(self.captureFile,
            'host %s and tcp and src port %s and dst port %s' % (
                self.ip, rtspSport, rtspDport))
        offsets = None
        packetlist = []
        seqlist = []
        lenlist = []
        tslist = []
        for plen, pkt, ts in p:
            if plen > 74 and 'RTSP/1.0' not in pkt and 'GStreamer' not in pkt:
                if not offsets:
                    offsets = p.getOffsets(pkt)
                packetlist.append(pkt)
                seq = unpack_from('!xxxxI', pkt, sum(offsets[0:2]))[0]
                seqlist.append(seq)
                lenlist.append(plen - offsets[0])
                tslist.append(ts)
                VTLOG.debug('TCP packet appended. Sequence: %s' % seq)
        seqlist, packetlist, lenlist, tslist = \
            multiSort(seqlist, packetlist, lenlist, tslist)
        VTLOG.debug('Sequence list sorted')

        # Locate packet losses
        fill = [0 for i in range(0, len(seqlist))]
        for i in range(0, len(seqlist)-1):
            if seqlist[i] + lenlist[i] < seqlist[i+1]:
                fill[i] = 1

        # Assemble the complete stream
        stream = ''
        for i in range(0, len(packetlist)):
            stream += packetlist[i][sum(offsets):]
            #Mark ENDOFPACKET and save time and length
            stream += 'ENDOFPACKET'
            stream += str(int(tslist[i] * 1000000))
            stream += 'ENDOFPACKET'
            stream += str(lenlist[i])
            stream += 'ENDOFPACKET'
            if fill[i]:
                #Mark PACKETLOSS
                VTLOG.debug('PACKETLOSS!')
                stream += 'PACKETLOSS'
        VTLOG.debug('TCP payloads assembled')

        # Parse the stream
        offset = 0
        parsing = True
        while parsing:
            plen = unpack_from('!xxH', stream, offset)[0]
            loss = stream[offset+4:offset+plen].find('PACKETLOSS')
            if loss == -1:
                #No loss: look inside then
                if ptype == unpack_from('!xB', stream, offset+4)[0] & 0x7F:
                    aux = stream[offset:].split('ENDOFPACKET')
                    self.lengths.append(int(aux[2]))
                    self.times.append(float(aux[1]) / 1000000)
                    seq = unpack_from('!xxH', stream, offset+4)[0]
                    self.sequences.append(seq + self.__add)
                    self.timestamps.append(unpack_from('!xxxxI', stream, offset+4)[0])
                    VTLOG.debug('TCP/RTP packet found. Sequence: %s' % seq)
                    if seq == 65535:
                        self.__add += seq
            else:
                #Avoid PACKETLOSS
                plen = loss + 10
                VTLOG.debug('PACKETLOSS!')

            offset += 4 + plen
            #Let's find the next RTSPi packet
            while parsing and not (
                (0x24, 0x00) == unpack_from('!BB', stream, offset) \
                and ptype == unpack_from('!xB', stream, offset+4)[0] & 0x7F):
                if stream[offset:offset+10] == 'PACKETLOSS':
                    #Avoid PACKETLOSS
                    offset += 10
                    VTLOG.debug('PACKETLOSS!')
                else:
                    #Find next packet
                    offset += 1
                if len(stream) - offset <= 5:
                    #Yep! We're done!
                    parsing = False
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
