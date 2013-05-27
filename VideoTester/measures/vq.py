# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from VideoTester.measures.core import Meter, Measure
from VideoTester.measures.qos import QoSmeter
from VideoTester.measures.bs import BSmeter
from VideoTester.config import VTLOG
import math
import cv

class VQmeter(Meter):
    """
    Video quality meter.
    """
    def __init__(self, selected, data):
        """
        **On init:** Register selected video quality measures.
        
        :param selected: Selected video quality measures.
        :type selected: string or list
        :param tuple data: Collected QoS + bit-stream + video parameters.
        """
        Meter.__init__(self)
        VTLOG.info("Starting VQmeter...")
        if 'psnr' in selected:
            self.measures.append(PSNR(data))
        if 'ssim' in selected:
            self.measures.append(SSIM(data))
        if 'g1070' in selected:
            self.measures.append(G1070(data))
        if 'psnrtomos' in selected:
            self.measures.append(PSNRtoMOS(data))
        if 'miv' in selected:
            self.measures.append(MIV(data))

class VQmeasure(Measure):
    """
    Video quality measure type.
    """
    def __init__(self, (conf, rawdata, codecdata, packetdata)):
        """
        **On init:** Register QoS + bit-stream + video parameters.
        
        :param string conf: Video parameters: `codec`, `bitrate`, `framerate` and `size`.
        :param dictionary rawdata: Frame information from YUV videos (`original`, `received` and `coded`).
        :param dictionary codecdata: Frame information from compressed videos (`received` and `coded`).
        :param tuple packetdata: QoS parameters.
        """
        Measure.__init__(self)
        #: Video parameters: `codec`, `bitrate`, `framerate` and `size`.
        self.conf = conf
        self.rawdata = rawdata
        #: Frame information from received YUV.
        self.yuv = rawdata['received']
        #: Frame information from original YUV.
        self.yuvref = rawdata['original']
        #: Frame information from compressed videos (`received` and `coded`).
        self.codecdata = codecdata
        #: QoS parameters.
        self.packetdata = packetdata
    
    def getQoSm(self, measures):
        """
        Get QoS measures.
        
        :param measures: Selected QoS measures.
        :type measures: string or list
        
        :returns: Calculated QoS measures.
        :rtype: list
        """
        VTLOG.info("----------getQoSm----------")
        measures = QoSmeter(measures, self.packetdata).run()
        VTLOG.info("---------------------------")
        return measures
    
    def getBSm(self, measures):
        """
        Get bit-stream measures.
        
        :param measures: Selected bit-stream measures.
        :type measures: string or list
        
        :returns: Calculated bit-stream measures.
        :rtype: list
        """
        VTLOG.info("----------getBSm-----------")
        measures = BSmeter(measures, self.codecdata).run()
        VTLOG.info("---------------------------")
        return measures

class PSNR(VQmeasure):
    """
    PSNR: Peak Signal to Noise Ratio (Y component).
    
    * Type: `plot`.
    * Units: `dB per frame`.
    """
    def __init__(self, data, yuv=False, yuvref=False):
        VQmeasure.__init__(self, data)
        self.data['name'] = 'PSNR'
        self.data['type'] = 'plot'
        self.data['units'] = ('frame', 'dB')
        if yuv:
            self.yuv = self.rawdata['coded']
        if yuvref:
            self.yuvref = self.rawdata['coded']
    
    def calculate(self):
        L = 255
        width = self.yuv.video['Y'][0].shape[0]
        height = self.yuv.video['Y'][0].shape[1]
        fin = min(self.yuv.frames, self.yuvref.frames)
        x = range(0, fin)
        y = []
        for i in x:
            sum = (self.yuv.video['Y'][i].astype(int) - self.yuvref.video['Y'][i].astype(int))**2
            mse = sum.sum() / width / height
            if mse != 0:
                y.append(20 * math.log(L / math.sqrt(mse), 10))
            else:
                y.append(100)
        self.graph(x, y)
        return self.data

class SSIM(VQmeasure):
    """
    SSIM: Structural Similarity index (Y component).
    
    * Type: `plot`.
    * Units: `SSIM index per frame`.
    """
    def __init__(self, data):
        VQmeasure.__init__(self, data)
        self.data['name'] = 'SSIM'
        self.data['type'] = 'plot'
        self.data['units'] = ('frame', 'SSIM index')
    
    def __array2cv(self, a):
        dtype2depth = {
            'uint8':   cv.IPL_DEPTH_8U,
            'int8':    cv.IPL_DEPTH_8S,
            'uint16':  cv.IPL_DEPTH_16U,
            'int16':   cv.IPL_DEPTH_16S,
            'int32':   cv.IPL_DEPTH_32S,
            'float32': cv.IPL_DEPTH_32F,
            'float64': cv.IPL_DEPTH_64F,
        }
        try:
            nChannels = a.shape[2]
        except:
            nChannels = 1
        cv_im = cv.CreateImageHeader((a.shape[1],a.shape[0]), dtype2depth[str(a.dtype)], nChannels)
        cv.SetData(cv_im, a.tostring(), a.dtype.itemsize*nChannels*a.shape[1])
        return cv_im
    
    def __SSIM(self, frame1, frame2):
        """
            The equivalent of Zhou Wang's SSIM matlab code using OpenCV.
            from http://www.cns.nyu.edu/~zwang/files/research/ssim/index.html
            The measure is described in :
            "Image quality assessment: From error measurement to structural similarity"
            C++ code by Rabah Mehdi. http://mehdi.rabah.free.fr/SSIM
            
            C++ to Python translation and adaptation by Iñaki Úcar
        """
        C1 = 6.5025
        C2 = 58.5225
        img1_temp = self.__array2cv(frame1)
        img2_temp = self.__array2cv(frame2)
        nChan = img1_temp.nChannels
        d = cv.IPL_DEPTH_32F
        size = img1_temp.width, img1_temp.height
        img1 = cv.CreateImage(size, d, nChan)
        img2 = cv.CreateImage(size, d, nChan)
        cv.Convert(img1_temp, img1)
        cv.Convert(img2_temp, img2)
        img1_sq = cv.CreateImage(size, d, nChan)
        img2_sq = cv.CreateImage(size, d, nChan)
        img1_img2 = cv.CreateImage(size, d, nChan)
        cv.Pow(img1, img1_sq, 2)
        cv.Pow(img2, img2_sq, 2)
        cv.Mul(img1, img2, img1_img2, 1)
        mu1 = cv.CreateImage(size, d, nChan)
        mu2 = cv.CreateImage(size, d, nChan)
        mu1_sq = cv.CreateImage(size, d, nChan)
        mu2_sq = cv.CreateImage(size, d, nChan)
        mu1_mu2 = cv.CreateImage(size, d, nChan)
        sigma1_sq = cv.CreateImage(size, d, nChan)
        sigma2_sq = cv.CreateImage(size, d, nChan)
        sigma12 = cv.CreateImage(size, d, nChan)
        temp1 = cv.CreateImage(size, d, nChan)
        temp2 = cv.CreateImage(size, d, nChan)
        temp3 = cv.CreateImage(size, d, nChan)
        ssim_map = cv.CreateImage(size, d, nChan)
        #/*************************** END INITS **********************************/
        #// PRELIMINARY COMPUTING
        cv.Smooth(img1, mu1, cv.CV_GAUSSIAN, 11, 11, 1.5)
        cv.Smooth(img2, mu2, cv.CV_GAUSSIAN, 11, 11, 1.5)
        cv.Pow(mu1, mu1_sq, 2)
        cv.Pow(mu2, mu2_sq, 2)
        cv.Mul(mu1, mu2, mu1_mu2, 1)
        cv.Smooth(img1_sq, sigma1_sq, cv.CV_GAUSSIAN, 11, 11, 1.5)
        cv.AddWeighted(sigma1_sq, 1, mu1_sq, -1, 0, sigma1_sq)
        cv.Smooth(img2_sq, sigma2_sq, cv.CV_GAUSSIAN, 11, 11, 1.5)
        cv.AddWeighted(sigma2_sq, 1, mu2_sq, -1, 0, sigma2_sq)
        cv.Smooth(img1_img2, sigma12, cv.CV_GAUSSIAN, 11, 11, 1.5)
        cv.AddWeighted(sigma12, 1, mu1_mu2, -1, 0, sigma12)
        #//////////////////////////////////////////////////////////////////////////
        #// FORMULA
        #// (2*mu1_mu2 + C1)
        cv.Scale(mu1_mu2, temp1, 2)
        cv.AddS(temp1, C1, temp1)
        #// (2*sigma12 + C2)
        cv.Scale(sigma12, temp2, 2)
        cv.AddS(temp2, C2, temp2)
        #// ((2*mu1_mu2 + C1).*(2*sigma12 + C2))
        cv.Mul(temp1, temp2, temp3, 1)
        #// (mu1_sq + mu2_sq + C1)
        cv.Add(mu1_sq, mu2_sq, temp1)
        cv.AddS(temp1, C1, temp1)
        #// (sigma1_sq + sigma2_sq + C2)
        cv.Add(sigma1_sq, sigma2_sq, temp2)
        cv.AddS(temp2, C2, temp2)
        #// ((mu1_sq + mu2_sq + C1).*(sigma1_sq + sigma2_sq + C2))
        cv.Mul(temp1, temp2, temp1, 1)
        #// ((2*mu1_mu2 + C1).*(2*sigma12 + C2))./((mu1_sq + mu2_sq + C1).*(sigma1_sq + sigma2_sq + C2))
        cv.Div(temp3, temp1, ssim_map, 1)
        index_scalar = cv.Avg(ssim_map)
        #// through observation, there is approximately 
        #// 1% error max with the original matlab program
        return index_scalar[0]
    
    def calculate(self):
        fin = min(self.yuv.frames, self.yuvref.frames)
        x = range(0, fin)
        y = []
        for i in x:
            y.append(self.__SSIM(self.yuv.video['Y'][i], self.yuvref.video['Y'][i]))
        self.graph(x, y)
        return self.data

class G1070(VQmeasure):
    """
    ITU-T G.1070 video quality estimation.
    
    * Type: `value`.
    * Units: `-`.
    """
    def __init__(self, data):
        VQmeasure.__init__(self, data)
        self.data['name'] = 'G.1070'
        self.data['type'] = 'value'
        self.data['units'] = ''
    
    def calculate(self):
        v = [0, 1.431, 2.228e-2, 3.759, 184.1, 1.161, 1.446, 3.881e-4, 2.116, 467.4, 2.736, 15.28, 4.170]
        
        Dfrv = v[6] + v[7] * self.conf['bitrate']
        Iofr = v[3] - v[3] / (1 + (self.conf['bitrate'] / v[4])**v[5])
        Ofr = v[1] + v[2] * self.conf['bitrate']
        
        Ic = Iofr * math.exp(-(math.log(self.conf['framerate']) - math.log(Ofr))**2 / (2 * Dfrv**2))
        Dpplv = v[10] + v[11] * math.exp(-self.conf['framerate'] / v[8]) + v[12] * math.exp(-self.conf['bitrate'] / v[9])
        
        self.data['value'] = 1 + Ic * math.exp(-self.getQoSm('plr')[0]['value'] * 100 / Dpplv)
        return self.data

class PSNRtoMOS(VQmeasure):
    """
    PSNR to MOS mapping used on `Evalvid <http://www.tkn.tu-berlin.de/research/evalvid/>`.
    
    * Type: `plot`.
    * Units: `MOS per frame`.
    """
    def __init__(self, data, yuv=False, yuvref=False):
        VQmeasure.__init__(self, data)
        self.data['name'] = 'PSNRtoMOS'
        self.data['type'] = 'plot'
        self.data['units'] = ('frame', 'MOS')
        self.yuv = yuv
        self.yuvref = yuvref
    
    def calculate(self):
        x, y = PSNR((None, self.rawdata, None, None), yuv=self.yuv, yuvref=self.yuvref).calculate()['axes']
        for i in range(0, len(y)):
            if y[i] < 20:
                y[i] = 1
            elif 20 <= y[i] < 25:
                y[i] = 2
            elif 25 <= y[i] < 31:
                y[i] = 3
            elif 31 <= y[i] < 37:
                y[i] = 4
            else:
                y[i] = 5
        self.graph(x, y)
        return self.data

class MIV(VQmeasure):
    """
    MIV metric used on `Evalvid <http://www.tkn.tu-berlin.de/research/evalvid/>`.
    
    * Type: `plot`.
    * Units: `Distortion in Interval`.
    """
    def __init__(self, data):
        VQmeasure.__init__(self, data)
        self.data['name'] = 'MIV'
        self.data['type'] = 'plot'
        self.interval = 25
        self.data['units'] = ('frame', '% of frames with a MOS worse than the reference')
    
    def calculate(self):
        x, refmos = PSNRtoMOS((None, self.rawdata, None, None), yuv=True).calculate()['axes']
        x, mos = PSNRtoMOS((None, self.rawdata, None, None)).calculate()['axes']
        y = [0 for i in range(0, self.interval)]
        for l in range(0, min(len(refmos), len(mos)) - self.interval):
            i = 0
            for j in range(l, l + self.interval):
                if mos[j] < refmos[j] and mos[j] < 4:
                    i += 1
            y.append(100 * float(i) / self.interval)
        x = [x for x in range(0, len(y))]
        self.graph(x, y)
        return self.data