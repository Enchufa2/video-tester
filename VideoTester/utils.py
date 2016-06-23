# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from itertools import izip
from multiprocessing import Manager, Process, JoinableQueue

def multiSort(*args):
    '''
    Efficient sort of multiple lists as the first one passed.
    '''
    return map(list, izip(*sorted(izip(*args))))

class Worker(Process):
    def __init__(self, qin, lout):
        Process.__init__(self)
        self.qin = qin
        self.lout = lout
        self.daemon = True
        self.start()

    def run(self):
        while True:
            i, func, args, kargs = self.qin.get()
            try:
                self.lout.append((i, func(*args, **kargs)))
            except Exception, e:
                print e
            finally:
                self.qin.task_done()

class ProcessingPool:
    def __init__(self, N):
        self.qin = JoinableQueue(N)
        self.lout = Manager().list()
        self.task = 0
        self.workers = []
        for _ in range(N):
            self.workers.append(Worker(self.qin, self.lout))

    def add_task(self, func, *args, **kargs):
        self.qin.put((self.task, func, args, kargs))
        self.task += 1

    def join(self):
        self.qin.join()

    def get_results(self, ordered=True):
        if ordered:
            return zip(*sorted(self.lout))[1]
        else:
            return zip(*self.lout)[1]
