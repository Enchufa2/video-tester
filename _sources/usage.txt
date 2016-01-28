Usage
=====

.. note::

	By default, Video Tester looks for a configuration file called ``VT.conf`` in the current working directory. You can specify another file and location using the global command-line option ``-c`` (or ``--conf``)::

		$ VT -c path/to/another.conf [server|client]

Server mode
-----------

You can run Video Tester in server mode with the following command::

	$ VT server

No more operation is required. The server waits for client requests in standalone mode.

.. note::

	Use ``Ctrl + C`` to stop it.

Client mode
-----------

You can launch Video Tester in client mode with the following command::

	$ VT client

.. note::

		VT client requires root privileges (for network sniffing).

You can use VT client with a graphical user interface (GUI). Activate it with the option ``-g`` (or ``--gui``)::

	$ VT client -g

Generated files
---------------

After the client execution, you will find a set of result files inside your temporary directory organised as follows: ``temp/<video>_<codec>_<bitrate>_<framerate>_<protocol>/*`` (e. g., ``temp/video0_h263_128_25_udp-unicast/*``). The name of those files starts with a numerical prefix (e. g., ``00``, ``01``...):

* ``00.cap``: PCAP file.
* ``00.h263``: received video (coded).
* ``00.yuv``: received video (YUV).
* ``00_ref.h263``: reference video (coded but not transmitted).
* ``00_ref.yuv``: reference video (coded and decoded).
* ``00_ref_original.yuv``: original reference video (uncompressed original file).
* ``00_<measure>.pkl``: serialized measure in Pickle format.

Pickle files can be read with the GUI (:menuselection:`File --> Open files...`).

Measures output
---------------

Video Tester returns a list of measures. Each measure is a Python dictionary with the following keys:

* ``name`` (mandatory): the name.
* ``type`` (mandatory): the type (``plot``, ``bar`` or ``value``).
* ``units`` (mandatory): the units (a string for ``value`` measures, a tuple of strings for ``plot`` or ``bar`` measures).
* ``axes`` (only for ``plot`` and ``bar`` measures): a tuple with X and Y axes. Each axis is a list of values.
* ``min`` (only for ``plot`` and ``bar`` measures): minimum value.
* ``max`` (only for ``plot`` and ``bar`` measures): maximum value.
* ``mean`` (only for ``plot`` and ``bar`` measures): mean value.
* ``value`` (only for ``value`` measures): the value.
* ``width`` (only for ``bar`` measures): bar width.

An example of ``plot`` measure::

	{ 'name':'Bandwidth', 'type':'plot', 'units':('time (s)', 'kbps'), 'axes':([...], [...]), 'min':(3, 7), 'max':(5, 0), 'mean':5 }

An example of ``bar`` measure::

	{ 'name':'PLD', 'type':'bar', 'units':('time (s)', 'Packet Loss Rate'), 'axes':([...], [...]), 'min':(3, 7), 'max':(5, 0), 'mean':5, 'width':1 }

An example of ``value`` measure::

	{ 'name':'Latency', 'type':'value', 'units':'ms', 'value':50 }
