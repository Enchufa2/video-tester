Configuration
=============

Videos
------

It's essential that the client and the server have a local repository with the same video files. Video Tester is designed to use lossless-coded video files. For example, EvalVid project has `YUV CIF samples compressed with lossless H.264 <http://www.tkn.tu-berlin.de/research/evalvid/cif.html>`_.


Configuration files
-------------------

A Video Tester configuration file has the following format::

	[section]
	# this is a comment
	key=value

Both client and server mode require a section called ``video`` in a file called ``VT.conf`` like this::

	[video]

	path=the_path_to_the_video_directory

	video0=one_video_file
	video1=another
	video2=and_another
	# and so on

.. warning::

	``VT.conf`` MUST be in the current working directory.

This media mapping must be the same on both client and server side. The client mode, moreover, requires a section called ``client`` like this::

	[client]

	# Video parameters
	video=one_key_from_video_section # E. g.: video0
	codec=the_codec # Options: h263, h264, mpeg4, theora
	bitrate=the_bitrate_in_kbps
	framerate=the_framerate_in_fps

	# Network parameters
	iface=the_network_interface
	ip=the_server_ip_address
	port=the_server_port
	protocols=transport_protocol # Options: udp-unicast, tcp, udp-multicast

	# Selected measures (comma separated)
	qos=qos_measures # Options: latency, delta, jitter, skew, bandwidth, plr, pld
	bs=bs_measures # Options: streameye, refstreameye, gop, iflr
	vq=vq_measures # Options: psnr, ssim, g1070, psnrtomos, miv

.. note::

	By default, Video Tester search this section in ``VT.conf``. You can specify another configuration file from the command line.