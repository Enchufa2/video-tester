Configuration
=============

Videos
------

Both the client and the server MUST share the same video repository. Video Tester may use almost any kind of source, but we encourage the use lossless-coded video files. For example, EvalVid project has `YUV CIF samples compressed with lossless H.264 <http://www.tkn.tu-berlin.de/research/evalvid/cif.html>`_. Unfortunately, that file format is not recognised by GStreamer without a container, so you need to _containerise_ it properly. For instance, the following ``ffmpeg`` command will convert any input file to lossless H.264 video inside a Matroska container::

	ffmpeg -i akiyo_cif.264 -c:v libx264 -qp 0 akiyo_cif.mkv

Configuration files
-------------------

A Video Tester configuration file has the following format::

	[section]
	# this is a comment
	key=value

Both client and server modes require a common section called ``general`` as follows::

	[general]

	port=the_server_port

	path=the_path_to_the_video_directory

	video0=one_video_file
	video1=another
	video2=and_another
	# and so on

.. note::

	By default, Video Tester looks for a configuration file called ``VT.conf`` in the current working directory. You can specify another file and location using the global command-line option ``-c``.

This media mapping must be the same on both client and server side. The client mode also requires a section called ``client`` as follows::

	[client]

	# Video parameters
	video=one_key_from_video_section # E.g.: video0
	codec=the_codec # Options (select one): h263, h264, mpeg4, theora
	bitrate=the_bitrate_in_kbps
	framerate=the_framerate_in_fps

	# Network parameters
	iface=the_network_interface
	ip=the_server_ip_address
	protocol=transport_protocol # Options (select one): udp, tcp, udp-mcast

	# Measures (multiple selection, comma separated)
	qos=qos_measures # Options: latency, delta, jitter, skew, bandwidth, plr, pld
	bs=bs_measures # Options: streameye, refstreameye, gop, iflr
	vq=vq_measures # Options: psnr, ssim, g1070, psnrtomos, miv
