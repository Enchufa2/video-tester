# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import os, time, pcap
from scapy.all import Packet, ByteField, ShortField, \
    IP, ICMP, TCP, UDP, RTP, send, rdpcap
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

class Sniffer:
    '''
    Network sniffer and packet parser.
    '''
    def __init__(self, iface, ip, proto, cap):
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
        #: Protocol selected.
        self.proto = proto
        #: Capture file.
        self.cap = cap
        #: SDP clock attribute.
        self.clock = None
        #: RTP payload type.
        self.ptype = None
        #: RTP source port (server).
        self.sport = None
        #: RTP destination port (client).
        self.dport = None
        #: RTSP PLAY packet found (boolean).
        self.play = False
        #: List of packet lengths.
        self.lengths = []
        #: List of packet arrival times.
        self.times = []
        #: List of RTP sequence numbers.
        self.sequences = []
        #: List of RTP timestamps.
        self.timestamps = []
        #: Ping information.
        self.__ping = {0:{}, 1:{}, 2:{}, 3:{}}
        self.__add = 0

    def ping(self):
        '''
        Ping to server (4 echoes).
        '''
        time.sleep(0.5)
        VTLOG.info('Pinging...')
        for i in range(0, 4):
            send(IP(dst=self.ip)/ICMP(seq=i), verbose=False)
            time.sleep(0.5)

    def run(self):
        '''
        Start packet sniffing and save a capture file.
        '''
        try:
            p = pcap.pcapObject()
            p.open_live(self.iface, 65536, 1, 0)
            p.setfilter('host ' + self.ip, 0, 0)
            p.dump_open(self.cap)
            while p.dispatch(-1, None) >= 0:
                pass
        except:
            pass

    def parsePkts(self):
        '''
        Parse packets and extract :attr:`lengths`, :attr:`times`, :attr:`sequences`, :attr:`timestamps` and :attr:`ping`.

        :returns: :attr:`lengths`, :attr:`times`, :attr:`sequences`, :attr:`timestamps` and :attr:`ping`.
        :rtype: tuple
        '''
        VTLOG.info('Starting packet parser...')
        self.cap = rdpcap(self.cap)
        if self.proto == 'tcp':
            self.__parseTCP()
        else:
            self.__parseUDP()
        self.__normalize()
        a = str(self.sequences[-1]-len(self.sequences)+1)
        b = str(len(self.sequences))
        VTLOG.debug(b + ' RTP packets received, ' + a + ' losses')
        VTLOG.info('Packet parser stopped')
        return self.lengths, self.times, self.sequences, self.timestamps, self.__ping

    def __prepare(self, p):
        '''
        Pre-process capture file. This method parses RTSP information and extracts :attr:`ping`, :attr:`ptype` and :attr:`clock`.

        :returns: True when a RTSP *PLAY* packet is found.
        :rtype: boolean
        '''
        if p.haslayer(ICMP):
            self.__ping[p[ICMP].seq][p[ICMP].type] = p.time
        elif str(p).find('Content-Type: application/sdp') != -1:
            lines = str(p[TCP].payload).splitlines()
            for line in lines:
                if line.find('m=video') != -1:
                    fields = line.split(' ')
                    self.ptype = int(fields[-1])
                    VTLOG.debug('Payload type found! Value: ' + str(self.ptype))
            for line in lines:
                if line.find('rtpmap:' + str(self.ptype)) != -1:
                    fields = line.split('/')
                    self.clock = int(fields[-1])
                    VTLOG.debug('Clock rate found! Value: ' + str(self.clock))
        elif (str(p).find('Transport: RTP') != -1) and (str(p).find('mode="PLAY"') != -1):
            if str(p).find('RTP/AVP/TCP') != -1:
                self.sport = int(p.sport)
                VTLOG.debug('Source port found! Value: ' + str(self.sport))
                self.dport = int(p.dport)
                VTLOG.debug('Destination port found! Value: ' + str(self.dport))
            else:
                fields = str(p[TCP].payload).split(';')
                for field in fields:
                    if field.find('server_port=') != -1:
                        self.sport = int(field[12:field.index('-')])
                        VTLOG.debug('Source port found! Value: ' + str(self.sport))
                    elif field.find('client_port=') != -1:
                        self.dport = int(field[12:field.index('-')])
                        VTLOG.debug('Destination port found! Value: ' + str(self.dport))
                    elif field.find('port=') != -1:
                        self.sport = int(field[5:field.index('-')])
                        self.dport = self.sport
                        VTLOG.debug('Source/destination port found! Value: ' + str(self.sport))
        elif (str(p).find('PLAY') != -1) and (str(p).find('Public:') == -1):
            self.play = True
            VTLOG.debug('PLAY found!')
        if self.play and self.sport and self.dport:
            play = True
        else:
            play = False
        return play

    def __parseUDP(self):
        '''
        Parse RTP over UDP session.
        '''
        def extract(p):
            '''
            Extract information from a UDP packet.

            :param Packet p: UDP packet.
            '''
            ptype = ord(str(p[UDP].payload)[1]) & 0x7F #Delete RTP marker
            p[UDP].decode_payload_as(RTP)
            if ptype == self.ptype:
                #Avoid duplicates while running on loopback interface
                if p[RTP].sequence not in self.sequences:
                    self.lengths.append(p.len)
                    self.times.append(p.time)
                    self.sequences.append(p[RTP].sequence + self.__add)
                    self.timestamps.append(p[RTP].timestamp)
                    VTLOG.debug('UDP/RTP packet found. Sequence: ' + str(p[RTP].sequence))
                    if p[RTP].sequence == 65535:
                        self.__add += 65536

        play = False
        for p in self.cap:
            if p.haslayer(IP):
                if (str(p).find('PAUSE') != -1) and play:
                    VTLOG.debug('PAUSE found!')
                    break
                if not play:
                    play = self.__prepare(p)
                elif play and (p[IP].src == self.ip) and (p.haslayer(UDP)) and (str(p).find('GStreamer') == -1):
                    if (p.sport == self.sport) and (p.dport == self.dport):
                        extract(p)
        self.sequences, self.times, self.timestamps = \
            multiSort(self.sequences, self.times, self.timestamps)
        VTLOG.debug('Sequence list sorted')

    def __parseTCP(self):
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
                ptype = ord(str(p[RTSPi].payload)[1]) & 0x7F #Delete RTP marker
                if ptype == self.ptype:
                    aux = str(p).split('ENDOFPACKET')
                    p[RTSPi].decode_payload_as(RTP)
                    #Avoid duplicates while running on loopback interface
                    if p[RTP].sequence not in self.sequences:
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
            ptype = ord(str(p[RTSPi].payload)[1]) & 0x7F
            #Let's find the next RTSP packet
            while not fin and not ((p[RTSPi].magic == 0x24) and (p[RTSPi].channel == 0x00) and (ptype == self.ptype)):
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
                    ptype = ord(str(p[RTSPi].payload)[1]) & 0x7F
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
        for p in self.cap:
            if p.haslayer(IP):
                if (str(p).find('PAUSE') != -1) and play:
                    VTLOG.debug('PAUSE found!')
                    break
                if not play:
                    play = self.__prepare(p)
                #Packets from server, with TCP layer. Avoid ACK's. Avoid RTSP packets
            elif play and (p[IP].src == self.ip) and p.haslayer(TCP) and (len(p) > 66) and (str(p).find('RTSP/1.0') == -1):
                    if (p.sport == self.sport) and (p.dport == self.dport):
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

    def __normalize(self):
        '''
        Normalize :attr:`sequences`, :attr:`times` and :attr:`timestamps`.
        '''
        seq = self.sequences[0]
        time = self.times[0]
        timest = float(self.timestamps[0])
        for i in range(0, len(self.sequences)):
            self.sequences[i] = self.sequences[i] - seq
            self.times[i] = self.times[i] - time
            self.timestamps[i] = (float(self.timestamps[i]) - timest) / self.clock
