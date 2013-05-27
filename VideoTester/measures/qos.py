# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from VideoTester.measures.core import Meter, Measure
from VideoTester.config import VTLOG, bubbleSort

class QoSmeter(Meter):
    """
    QoS meter.
    """
    def __init__(self, selected, data):
        """
        **On init:** Register selected QoS measures.
        
        :param selected: Selected QoS measures.
        :type selected: string or list
        :param tuple data: Collected QoS parameters.
        """
        Meter.__init__(self)
        VTLOG.info("Starting QoSmeter...")
        if 'latency' in selected:
            self.measures.append(Latency(data))
        if 'delta' in selected:
            self.measures.append(Delta(data))
        if 'jitter' in selected:
            self.measures.append(Jitter(data))
        if 'skew' in selected:
            self.measures.append(Skew(data))
        if 'bandwidth' in selected:
            self.measures.append(Bandwidth(data))
        if 'plr' in selected:
            self.measures.append(PacketLossRate(data))
        if 'pld' in selected:
            self.measures.append(PacketLossDist(data))

class QoSmeasure(Measure):
    """
    QoS measure type.
    """
    def __init__(self, (lengths, times, sequences, timestamps, ping)):
        """
        **On init:** Register QoS parameters.
        
        :param list lengths: List of packet lengths.
        :param list times: List of packet arrival times.
        :param list sequences: List of RTP sequence numbers.
        :param list timestamps: List of RTP timestamps.
        :param dictionary ping: Ping information.
        """
        Measure.__init__(self)
        #: List of packet lengths (see :attr:`VideoTester.sniffer.Sniffer.lengths`).
        self.lengths = lengths
        #: List of packet arrival times (see :attr:`VideoTester.sniffer.Sniffer.times`).
        self.times = times
        #: List of RTP sequence numbers (see :attr:`VideoTester.sniffer.Sniffer.sequences`).
        self.sequences = sequences
        #: List of RTP timestamps (see :attr:`VideoTester.sniffer.Sniffer.timestamps`).
        self.timestamps = timestamps
        #: Ping information (see :attr:`VideoTester.sniffer.Sniffer.ping`).
        self.ping = ping

class Latency(QoSmeasure):
    """
    Latency: end-to-end delay.
    
    * Type: `value`.
    * Units: `ms`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'Latency'
        self.data['type'] = 'value'
        self.data['units'] = 'ms'
    
    def calculate(self):
        sum = 0
        count = 0
        for i in range(0, 4):
            if len(self.ping[i]) == 2:
                sum = sum + (self.ping[i][0] - self.ping[i][8]) * 500
                count = count + 1
        self.data['value'] = sum / count
        return self.data

class Delta(QoSmeasure):
    """
    Delta: gap between two consecutive packets.
    
    * Type: `plot`.
    * Units: `ms per RTP packet`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'Delta'
        self.data['type'] = 'plot'
        self.data['units'] = ('RTP packet', 'ms')
    
    def calculate(self):
        x = self.sequences
        y = [0 for i in range(0, len(self.times))]
        for i in range(1, len(self.times)):
            y[i] = (self.times[i] - self.times[i-1]) * 1000
        self.graph(x, y)
        return self.data

class Jitter(QoSmeasure):
    """
    Jitter: latency deviation (see :rfc:`3550#page-94`).
    
    * Type: `plot`.
    * Units: `ms per RTP packet`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'Jitter'
        self.data['type'] = 'plot'
        self.data['units'] = ('RTP packet', 'ms')
    
    def calculate(self):
        x = self.sequences
        y = [0 for i in range(0, len(self.times))]
        for i in range(1, len(self.times)):
            d = ((self.times[i] - self.timestamps[i]) - (self.times[i-1] - self.timestamps[i-1])) * 1000
            y[i] = y[i-1] + (abs(d) - y[i-1]) / 16
        self.graph(x, y)
        return self.data

class Skew(QoSmeasure):
    """
    Skew: time deviation from RTP timestamp.
    
    * Type: `plot`.
    * Units: `ms per RTP packet`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'Skew'
        self.data['type'] = 'plot'
        self.data['units'] = ('RTP packet', 'ms')
    
    def calculate(self):
        x = self.sequences
        y = [0 for i in range(0, len(self.times))]
        for i in range(1, len(self.times)):
            y[i] = (self.timestamps[i] - self.times[i]) * 1000
        self.graph(x, y)
        return self.data

class Bandwidth(QoSmeasure):
    """
    Instantaneous bandwidth: data received in the last second.
    
    * Type: `plot`.
    * Units: `kbps per second`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'Bandwidth'
        self.data['type'] = 'plot'
        self.data['units'] = ('time (s)', 'kbps')
    
    def calculate(self):
        bubbleSort(self.times, self.lengths)
        x = self.times
        y = [0 for i in range(0, len(x))]
        for i in range(1, len(x)):
            if x[i] == x[i-1]:
                y[i] = -1
        supr = True
        while supr:
            try:
                x.pop(y.index(-1))
                y.pop(y.index(-1))
                self.lengths.pop(y.index(-1))
            except:
                supr = False
        for i in range(1, len(x)):
            length = 0
            j = i
            while x[j] + 1 > x[i] and j >= 0:
                length = length + self.lengths[j] * 8 / 1000
                j = j - 1
            y[i] = length
        self.graph(x, y)
        return self.data

class PacketLossRate(QoSmeasure):
    """
    Packet Loss Rate.
    
    * Type: `value`.
    * Units: `rate`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'PLR'
        self.data['type'] = 'value'
        self.data['units'] = 'rate'
    
    def calculate(self):
        loss = 0
        for i in range(1, len(self.sequences)):
            loss = loss + self.sequences[i] - self.sequences[i-1] - 1
        rate = float(loss) / float(self.sequences[-1] + 1)
        self.data['value'] = rate
        return self.data

class PacketLossDist(QoSmeasure):
    """
    Packet Loss Distribution: loss rate distribution.
    
    * Type: `bar`.
    * Units: `Packet Loss Rate per time`.
    """
    def __init__(self, data):
        QoSmeasure.__init__(self, data)
        self.data['name'] = 'PLD'
        self.data['type'] = 'bar'
        self.data['units'] = ('time (s)', 'Packet Loss Rate')
        self.data['width'] = 1 #seconds
    
    def calculate(self):
        edge = self.data['width']
        x = []
        y = []
        i = 1
        j = 1
        count = 1
        while i < len(self.times):
            x.append((j-1) * self.data['width'])
            loss = 0
            while i < len(self.times) and self.times[i] < edge:
                count = count + 1
                loss = loss + self.sequences[i] - self.sequences[i-1] - 1
                i = i + 1
            y.append(float(loss) / count)
            count = 0
            edge = edge + self.data['width']
            j = j + 1
        self.graph(x, y)
        return self.data
