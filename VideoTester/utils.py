# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from itertools import izip

def multiSort(*args):
    '''
    Efficient sort of multiple lists as the first one passed.
    '''
    return map(list, izip(*sorted(izip(*args))))
