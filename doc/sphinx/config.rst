``VideoTester.config`` --- Common constants and functions
=========================================================

.. module:: VideoTester.config

Constants
---------

.. data:: VTLOG

	VT logger.
	
.. data:: USERPATH

	Current working path (result of :func:`os.getcwd()` function).
	
.. data:: CONF

	Path to the default configuration file (relative to :const:`USERPATH`).
	
.. data:: TEMP

	Path to the temporary directory (relative to :const:`USERPATH`).
	
.. data:: SERVERIFACE

	Server interface.
	
.. data:: SERVERIP

	Server IP address.
	
.. data:: SERVERPORT

	Server base port.

.. note::

    :const:`CONF`, :const:`TEMP` and :const:`SERVERPORT` MAY be replaced by more suitable values.

.. warning::

    :const:`SERVERIFACE` MUST be replaced according to your network configuration, and :const:`SERVERIP` will be set automatically.

Functions
---------

.. autofunction:: makeDir
.. autofunction:: initLogger
.. autofunction:: parseArgs
.. autofunction:: getIpAddress
.. autofunction:: bubbleSort