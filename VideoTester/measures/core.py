# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from VideoTester.config import VTLOG

class Meter:
    """
    Generic meter.
    """
    def __init__(self):
        #: List of measures.
        self.measures = []
    
    def run(self):
        """
        Run registered measures. For each measure in :attr:`measures`, this method calls :meth:`Measure.calculate`.
        
        :returns: The list of measures.
        :rtype: list
        """
        measures = []
        for measure in self.measures:
            VTLOG.info("- Measuring: " + measure.data['name'])
            try:
                measures.append(measure.calculate())
            except Exception, e:
                VTLOG.error(e)
        return measures

class Measure:
    """
    Generic measure.
    """
    def __init__(self):
        self.data = dict()
        """
        Dictionary of results. Contents:
        
        * `name`: The name.
        * `units`: The units (e.g.: ``'ms'``, ``['time (s)', 'kbps']``, etc.).
        * `type`: The type: `plot`, `bar`, `value` or `videoframes`.
            * If ``type = 'plot'``: `axes`, `max`, `min`, `mean`.
            * If ``type = 'bar'``: `axes`, `max`, `min`, `mean`, `width`.
            * If ``type = 'value'``: `value`.
            * If ``type = 'videoframes'``: `axes`.
        """
        self.data['name'] = None
        self.data['type'] = None
        self.data['units'] = None
    
    def calculate(self):
        """
        Compute the measure.
        
        :returns: Results (see :attr:`data`).
        :rtype: dictionary
        
        .. note::
            This method MUST be overwritten by the subclasses.
        """
        pass
    
    def __max(self, x, y):
        """
        Find the maximum value.
        
        :param list x: x axis.
        :param list y: y axis.
        
        :returns: Maximum value.
        :rtype: tuple
        """
        i = y.index(max(y))
        return (x[i], y[i])
    
    def __min(self, x, y):
        """
        Find the minimum value.
        
        :param list x: x axis.
        :param list y: y axis.
        
        :returns: Minimum value.
        :rtype: tuple
        """
        i = y.index(min(y))
        return (x[i], y[i])
    
    def __mean(self, y):
        """
        Calculate the mean.
        
        :param list y: y axis.
        
        :returns: Mean.
        :rtype: float
        """
        sum = 0
        for x in y:
            sum = sum + x
        return float(sum) / len(y)
    
    def graph(self, x, y):
        """
        Set `axes`, `max`, `min` and `mean` for `bar` or `plot` graphs (see :attr:`data`).
        
        :param list x: x axis.
        :param list y: y axis.
        """
        self.data['axes'] = (x, y)
        self.data['max'] = self.__max(x, y)
        self.data['min'] = self.__min(x, y)
        self.data['mean'] = self.__mean(y)