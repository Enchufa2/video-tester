HOWTO: Implementing new metrics
===============================

Video Tester has three categories:

* QoS measures (located at :mod:`VideoTester.measures.qos`).
* Bitstream measures (located at :mod:`VideoTester.measures.bs`).
* Video quality measures (located at :mod:`VideoTester.measures.vq`).

A new metric MUST be a new class that SHOULD be placed in its corresponding module, and it MUST satisfy the following requirements:

* It MUST inherit from its type of measure (or from another measure):

 * :class:`VideoTester.measures.qos.QoSmeasure`
 * :class:`VideoTester.measures.bs.BSmeasure`
 * :class:`VideoTester.measures.vq.VQmeasure`

* It SHOULD implement a method called ``__init__()``.
* It MUST implement a method called ``calculate()``.

Here is an example of three new measures::

	class PlotMeasure(QoSmeasure):
		def __init__(self, data):
			QoSmeasure.__init__(self, data)
			self.data['name'] = '"plot" measure'
			self.data['type'] = 'plot'
			self.data['units'] = ('units for x axis', 'units for y axis')
		
		def calculate(self):
			# Some stuff...
			x = ... # List of values (x axis)
			y = ... # List of values (y axis)
			self.graph(x, y)
			return self.data

	class ValueMeasure(QoSmeasure):
		def __init__(self, data):
			QoSmeasure.__init__(self, data)
			self.data['name'] = '"value" measure'
			self.data['type'] = 'value'
			self.data['units'] = 'units'
		
		def calculate(self):
			# Some stuff...
			self.data['value'] = ... # Output value
			return self.data

	class BarMeasure(QoSmeasure):
		def __init__(self, data):
			QoSmeasure.__init__(self, data)
			self.data['name'] = '"bar" measure'
			self.data['type'] = 'bar'
			self.data['units'] = ('units for x axis', 'units for y axis')
			self.data['width'] = ... # Bar width
		
		def calculate(self):
			# Some stuff...
			x = ... # List of values (x axis)
			y = ... # List of values (y axis)
			self.graph(x, y)
			return self.data

Finally, each measure MUST be registered in its corresponding meter:

* :class:`VideoTester.measures.qos.QoSmeter`
* :class:`VideoTester.measures.bs.BSmeter`
* :class:`VideoTester.measures.vq.VQmeter`.

Here is an example::

	class QoSmeter(Meter):
		def __init__(self, selected, data):
			Meter.__init__(self)
			if 'latency' in selected:
				self.measures.append(Latency(data))
			
			# other measures
			
			if 'plotmeasure' in selected:
				self.measures.append(PlotMeasure(data))
			if 'valuemeasure' in selected:
				self.measures.append(ValueMeasure(data))
			if 'barmeasure' in selected:
				self.measures.append(BarMeasure(data))