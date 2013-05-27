# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from VideoTester.measures.core import Meter, Measure
from VideoTester.config import VTLOG
from numpy import *

class BSmeter(Meter):
    """
    Bit-stream meter.
    """
    def __init__(self, selected, data):
        """
        **On init:** Register selected bit-stream measures.
        
        :param selected: Selected bit-stream measures.
        :type selected: string or list
        :param tuple data: Collected bit-stream parameters.
        """
        Meter.__init__(self)
        VTLOG.info("Starting BSmeter...")
        if 'streameye' in selected:
            self.measures.append(StreamEye(data))
        if 'refstreameye' in selected:
            self.measures.append(RefStreamEye(data))
        if 'gop' in selected:
            self.measures.append(GOP(data))
        if 'iflr' in selected:
            self.measures.append(IFrameLossRate(data))

class BSmeasure(Measure):
    """
    Bit-stream measure type.
    """
    def __init__(self, codecdata):
        """
        **On init:** Register bit-stream parameters.
        
        :param dictionary codecdata: Frame information from compressed videos (`received` and `coded`).
        """
        Measure.__init__(self)
        #: Frame information from received video.
        self.coded = codecdata['received']
        #: Frame information from coded video.
        self.codedref = codecdata['coded']

class StreamEye(BSmeasure):
    """
    Stream Eye: visualization of the compressed frames (received video).
    
    * Type: `videoframes`.
    * Units: `bytes per frame`.
    """
    def __init__(self, data, video=''):
        BSmeasure.__init__(self, data)
        self.data['name'] = 'StreamEye'
        self.data['type'] = 'videoframes'
        self.data['units'] = ('frame', 'bytes')
        if video == 'ref':
            self.v = self.codedref
        elif video == '':
            self.v = self.coded
        self.data['name'] = video + self.data['name']
    
    def calculate(self):
        x = range(len(self.v.frames['lengths']))
        Iframes = [0 for i in x]
        Pframes = [0 for i in x]
        Bframes = [0 for i in x]
        for i in x:
            type = self.v.frames['types'][i]
            if type == 'I':
                Iframes[i] = self.v.frames['lengths'][i]
            elif type == 'P':
                Pframes[i] = self.v.frames['lengths'][i]
            elif type == 'B':
                Bframes[i] = self.v.frames['lengths'][i]
        y = {'I':Iframes, 'P':Pframes, 'B':Bframes}
        self.data['axes'] = [x, y]
        return self.data

class RefStreamEye(StreamEye):
    """
    ref Stream Eye: visualization of the compressed frames (reference video).
    
    * Type: `videoframes`.
    * Units: `bytes per frame`.
    """
    def __init__(self, data):
        StreamEye.__init__(self, data, 'ref')

class GOP(BSmeasure):
    """
    GOP: estimation of *Group Of Pictures* size for received video.
    
    * Type: `value`.
    * Units: `GOP size`.
    """
    def __init__(self, data):
        BSmeasure.__init__(self, data)
        self.data['name'] = 'GOP'
        self.data['type'] = 'value'
        self.data['units'] = 'GOP size'
    
    def calculate(self):
        gops = []
        gop = 0
        for i in range(len(self.coded.frames['types'])):
            gop += 1
            if self.coded.frames['types'][i] == 'I':
                if i != 0:
                    gops.append(gop)
                gop = 0
        gops.append(gop)
        gops = array(gops, dtype=float)
        loss = []
        lim1 = mean(gops) - std(gops)/2
        lim2 = mean(gops) + std(gops)/2
        for i in range(len(gops)):
            if (gops[i] < lim1) or (gops[i] > lim2):
                loss.append(i)
        gops = delete(gops, loss)
        self.data['value'] = int(round(mean(gops)))
        return self.data

class IFrameLossRate(BSmeasure):
    """
    I-Frame Loss Rate.
    
    * Type: `value`.
    * Units: `rate`.
    """
    def __init__(self, data):
        BSmeasure.__init__(self, data)
        self.data['name'] = 'IFLR'
        self.data['type'] = 'value'
        self.data['units'] = 'rate'
    
    def calculate(self):
        count = 0
        gops = []
        gop = 0
        for i in range(len(self.coded.frames['types'])):
            gop += 1
            if self.coded.frames['types'][i] == 'I':
                count += 1
                if i != 0:
                    gops.append(gop)
                gop = 0
        gops.append(gop)
        gops = array(gops, dtype=float)
        loss = []
        lim = mean(gops) + std(gops)
        for i in range(len(gops)):
            if gops[i] > lim:
                loss.append(i)
        rate = float(len(loss)) / float(count + len(loss))
        self.data['value'] = rate
        return self.data