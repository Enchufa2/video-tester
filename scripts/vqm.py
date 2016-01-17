#!/usr/bin/env python
# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2015 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

# A simple script to make use of the PSNR and SSIM methods

import sys, os
from VideoTester import YUVvideo
from VideoTester.measures import PSNR, SSIM

if len(sys.argv) != 4:
  print 'Usage: ./vqm.py <degraded_yuv> <original_yuv> <width>x<height>'
  sys.exit()

file1 = sys.argv[1]
file2 = sys.argv[2]
width, height = map(int, sys.argv[3].split('x'))

if not os.path.isfile(file1) or not os.path.isfile(file2):
  raise IOError, 'bad file(s)'

def save_to_file(name, res):
  with open(name, 'w') as f:
    for frame, value in zip(res['axes'][0], res['axes'][1]):
      f.write('%i %f\n' % (frame, value))

rawdata = {
  'received' : YUVvideo(file1, (width, height)),
  'original' : YUVvideo(file2, (width, height))
}

psnr = PSNR((None, rawdata, None, None))
ssim = SSIM((None, rawdata, None, None))

print "Calculating PSNR..."
res = psnr.calculate()
save_to_file('result_psnr.dat', res)

print "Calculating SSIM..."
res = ssim.calculate()
save_to_file('result_ssim.dat', res)
