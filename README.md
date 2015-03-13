Video Tester - Video Quality Assessment Tool
============================================

Video Tester is a framework for the video quality assessment over a real or simulated IP network. Parameter extraction is performed on the three levels involved in the video processing and transmission ---packet level, bitstream level and picture level--- in order to gather as much information as possible. Therefore, it's suitable to implement any kind of metric: data metrics, picture metrics, packet-based metrics, bitstream-based metrics or hybrid metrics; with full-reference, reduced-reference or no-reference.

It's a Linux application programmed in Python with the aim of promoting extensibility, and the election of the GStreamer framework for video processing is due to its broad support in this area. Video Tester covers [EvalVid](http://www.tkn.tu-berlin.de/research/evalvid/) features and adds further improvements in terms of usability, extensibility, codec support, support of transmission methods and reliability in case of losses.

Features
--------

* Codec support: H.263, H.264, MPEG-4 part 2, Theora.
* Implemented metrics:
 * QoS metrics: latency, delta, jitter, skew, bandwidth, packet loss rate, packet loss distribution.
 * Bitstream metrics: stream eye, reference stream eye, gop size, I-frame loss rate.
 * Video quality metrics: PSNR, SSIM, ITU-T G.1070, MOS (PSNR to MOS mapping from EvalVid), MIV (from EvalVid).

Publications
------------

If you use this framework for your research, we would appreciate if you could cite the following reference:

  Ucar, I.; Navarro-Ortiz, J.; Ameigeiras, P.; Lopez-Soler, J.M., **Video Tester — A multiple-metric framework for video quality assessment over IP networks**, *Broadband Multimedia Systems and Broadcasting (BMSB), 2012 IEEE International Symposium on*, pp.1-5, 27-29 June 2012, DOI: [10.1109/BMSB.2012.6264243](http://dx.doi.org/10.1109/BMSB.2012.6264243), [arXiv:1301.5793](http://arxiv.org/abs/1301.5793) **[cs.MM]**

Installation
------------

Video Tester has the following dependencies:

* Python 2.7.
* GStreamer 0.10.35 with Python bindings.
* GStreamer plugins: base, good, ugly, bad.
* GStreamer FFmpeg plugins.
* GStreamer RTSP server 0.10.8 (at least) with Python bindings. 
* Scapy 2.0.
* Matplotlib 1.0.1.
* Numpy 1.4.1.
* WxPython 2.8.11 with Matplotlib backend.
* OpenCV 2.1 with Python bindings.

First of all, enable [RPM Fusion](http://rpmfusion.org) repositories:

	$ su -c 'yum localinstall --nogpgcheck http://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm http://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm'

This dependencies can be installed with the following command (only for Fedora):

	$ su -c 'yum install gstreamer gstreamer-plugins-base gstreamer-plugins-good gstreamer-plugins-ugly gstreamer-plugins-bad-free gstreamer-plugins-bad-nonfree gstreamer-python gstreamer-ffmpeg gstreamer-rtsp gstreamer-rtsp-python scapy numpy python-matplotlib python-matplotlib-wx wxPython opencv-python'

Now, you can download the latest version of Video Tester. Then, follow this steps:

	$ tar xzf VideoTester-x.x.tar.gz
	$ cd VideoTester-x.x
	$ sudo python setup.py install

During the installation, you'll be asked for two configuration parameters:

* The server interface (default: `eth0`).
* The server port (default: `8000`).

The documentation will be placed at `/usr/share/doc/VideoTester-x.x`.

Usage
-----

NOTE: the current working directory MUST contain the `VT.conf` file. Check the [documentation](http://enchufa2.github.io/video-tester/).

VT in server mode:

	$ VT server

VT in client mode:

	$ VT client

VT in client mode specifying another configuration file:

	$ VT client -c another.conf

VT in client mode with GUI:

	$ VT client -g
