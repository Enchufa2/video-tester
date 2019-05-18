# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <iucar@fedoraproject.org>
## This program is published under a GPLv3 license

import numpy as np

class YUVVideo:
    '''
    YUV parser.
    '''
    def __init__(self, file, (width, height, fmt)):
        '''
        **On init:** Call the proper parser.

        :param string file: Path to the file.
        :param int width: Frame width.
        :param int height: Frame height.
        :param string format: YUV format.

        .. note::
            Supported formats: I420.
        '''
        #: Frame width.
        self.width = width
        #: Frame height.
        self.height = height
        #: File descriptor.
        self.f = open(file, 'rb')

        if fmt == 'I420':
            frame = self.width * self.height
            self.yblock = frame
            self.uvblock = frame / 4
            self.chunk = self.yblock + 2 * self.uvblock
        else:
            raise IOError('Format %s not supported' % fmt)

        self.f.seek(0, 2)
        #: Number of frames in the video.
        self.frames = self.f.tell()/self.chunk
        self.f.seek(0)

    def __iter__(self):
        self.f.seek(0)
        return self

    def next(self):
        data = self.f.read(self.chunk)
        if not data:
            raise StopIteration
        else:
            yu = self.yblock
            uv = self.yblock + self.uvblock
            return {
                'Y' : np.frombuffer(data[0:yu], dtype=np.uint8).reshape(self.height, self.width),
                'U' : np.frombuffer(data[yu:uv], dtype=np.uint8).reshape(self.height/2, self.width/2),
                'V' : np.frombuffer(data[uv:], dtype=np.uint8).reshape(self.height/2, self.width/2)
            }

class CodedVideo:
    '''
    Coded video parser.
    '''
    def __init__(self, file, codec):
        '''
        **On init:** Call the proper parser.

        :param string file: Path to the file.
        :param string codec: Codec type.

        .. note::
            Supported formats: H263, H264, MPEG4 and Theora.
        '''
        #: Numpy np.array with all the data.
        self.raw = np.fromfile(file, dtype=np.uint8)
        #: Dictionary that contains the `types` and the `lengths` for all the frames found.
        self.frames = {'types':[], 'lengths':[]}
        if codec == 'h263':
            self.__parseH263()
        elif codec == 'h264':
            self.__parseH264()
        elif codec == 'mpeg4':
            self.__parseMPEG4()
        elif codec == 'theora':
            self.__parseTheora()
        else:
            raise IOError('Format %s not supported' % codec)

    def __parseH263(self):
        '''
        H263 format parser.
        '''
        PSC = np.array([0x00, 0x00, 0x80], dtype=np.uint8)
        mask = np.array([0xff, 0xff, 0xfc], dtype=np.uint8)
        first = -1
        i = 0
        while i < len(self.raw)-3:
            if np.all((self.raw[i:i+3] & mask) == PSC):
                if (i != 0) and (first > -1):
                    self.frames['lengths'].append(i-first)
                first = i
                i += 4
                if (self.raw[i] & 0x02) == 0:
                    self.frames['types'].append('I')
                else:
                    self.frames['types'].append('P')
            i += 1

    def __parseH264(self):
        '''
        H264 format parser.
        '''
        def getType(byte):
            comp = byte & 0x7f
            if comp >= 0x40:
                codeNum = 0
            elif comp >= 0x30:
                codeNum = 2
            elif comp >= 0x20:
                codeNum = 1
            elif comp >= 0x1c:
                codeNum = 6
            elif comp >= 0x18:
                codeNum = 5
            elif comp >= 0x14:
                codeNum = 4
            elif comp >= 0x10:
                codeNum = 3
            elif comp >= 0x0a:
                codeNum = 9
            elif comp >= 0x09:
                codeNum = 8
            elif comp >= 0x08:
                codeNum = 7
            if codeNum == 2 or codeNum == 7:
                type = 'I'
            elif codeNum == 0 or codeNum == 5:
                type = 'P'
            elif codeNum == 1 or codeNum == 6:
                type = 'B'
            elif codeNum == 3 or codeNum == 8:
                type = 'SP'
            elif codeNum == 4 or codeNum == 9:
                type = 'SI'
            return type

        SC = np.array([0x00, 0x00, 0x00, 0x01], dtype=np.uint8)
        SCmask = np.array([0xff, 0xff, 0xff, 0xff], dtype=np.uint8)
        typeI = 0x05
        typePB = 0x01
        typemask = 0x1f
        flag = True
        first = 0
        i = 0
        while i < len(self.raw)-4:
            if np.all((self.raw[i:i+4] & SCmask) == SC):
                if flag:
                    if i != 0:
                        self.frames['lengths'].append(i-first)
                    first = i
                    flag = False
                i += 4
                if ((self.raw[i] & typemask) == typeI) or ((self.raw[i] & typemask) == typePB):
                    flag = True
                    i += 1
                    self.frames['types'].append(getType(self.raw[i:i+1]))
            i += 1

    def __parseMPEG4(self):
        '''
        MPEG4 format parser.
        '''
        SC = np.array([0x00, 0x00, 0x01, 0xb6], dtype=np.uint8)
        mask = np.array([0xff, 0xff, 0xff, 0xff], dtype=np.uint8)
        first = -1
        i = 0
        while i < len(self.raw)-4:
            if np.all((self.raw[i:i+4] & mask) == SC):
                if (i != 0) and (first > -1):
                    self.frames['lengths'].append(i-first)
                first = i
                i += 4
                comp = self.raw[i] & 0xc0
                if comp == 0x00:
                    self.frames['types'].append('I')
                elif comp == 0x40:
                    self.frames['types'].append('P')
                elif comp == 0x80:
                    self.frames['types'].append('B')
                elif comp == 0xc0:
                    self.frames['types'].append('S')
            i += 1

    def __parseTheora(self):
        '''
        Theora over Matroska format parser.
        '''
        SC1 = [np.array([0xa3, 0x00, 0x00, 0x81, 0x00, 0x00, 0x00], dtype=np.uint8),
                np.array([0xa3, 0x00, 0x00, 0x81, 0x00, 0x00, 0x80], dtype=np.uint8),
                np.array([0xa3, 0x00, 0x81, 0x00, 0x00, 0x00], dtype=np.uint8)]
        mask1 = [np.array([0xff, 0x00, 0x00, 0xff, 0x00, 0x00, 0xff], dtype=np.uint8),
                np.array([0xff, 0x00, 0xff, 0x00, 0x00, 0xff], dtype=np.uint8)]
        SC2 = np.array([0x1f, 0x43, 0xb6, 0x75], dtype=np.uint8)
        mask2 = np.array([0xff, 0xff, 0xff, 0xff], dtype=np.uint8)
        first = -1
        i = 0
        while i < len(self.raw)-7:
            if np.all((self.raw[i:i+7] & mask1[0]) == SC1[0]) or np.all((self.raw[i:i+7] & mask1[0]) == SC1[1]) or np.all((self.raw[i:i+6] & mask1[1]) == SC1[2]):
                if not np.all((self.raw[i:i+7] & mask1[0]) == SC1[1]):
                    self.frames['lengths'].append(i-first)
                if not np.all((self.raw[i:i+6] & mask1[1]) == SC1[2]):
                    i += 7
                else:
                    i += 6
                first = i
                if self.raw[i] & 0x40 == 0:
                    self.frames['types'].append('I')
                else:
                    self.frames['types'].append('P')
                i += 1
            elif np.all((self.raw[i:i+4] & mask2) == SC2):
                if not self.raw[i-6:i-1].tostring() == 'Video':
                    self.frames['lengths'].append(i-first)
            i += 1
