.. VideoTester documentation master file, created by
   sphinx-quickstart on Sat Mar 26 18:03:37 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to VideoTester's documentation!
=======================================

What's this?
------------

Video Tester is a framework for the video quality assessment over a real or simulated IP network. Parameter extraction is performed on the three levels involved in the video processing and transmission ---packet level, bitstream level and picture level--- in order to gather as much information as possible. Therefore, it's suitable to implement any kind of metric: data metrics, picture metrics, packet-based metrics, bitstream-based metrics or hybrid metrics; with full-reference, reduced-reference or no-reference.

It's a Linux application programmed in Python with the aim of promoting extensibility, and the election of the GStreamer framework for video processing is due to its broad support in this area. Video Tester covers `EvalVid <http://www.tkn.tu-berlin.de/research/evalvid/>`_ features and adds further improvements in terms of usability, extensibility, codec support, support of transmission methods and reliability in case of losses.

**Features:**

* Codec support: H.263, H.264, MPEG-4 part 2, Theora.
* Implemented metrics:

 * QoS metrics: latency, delta, jitter, skew, bandwidth, packet loss rate, packet loss distribution.
 * Bitstream metrics: stream eye, reference stream eye, gop size, I-frame loss rate.
 * Video quality metrics: PSNR, SSIM, ITU-T G.1070, MOS (PSNR to MOS mapping from EvalVid), MIV (from EvalVid).
 
**Publications:**

If you use this framework for your research, we would appreciate if you could cite the following reference:

	Ucar, I.; Navarro-Ortiz, J.; Ameigeiras, P.; Lopez-Soler, J.M., **Video Tester — A multiple-metric framework for video quality assessment over IP networks**, *Broadband Multimedia Systems and Broadcasting (BMSB), 2012 IEEE International Symposium on*, pp.1-5, 27-29 June 2012, DOI: `10.1109/BMSB.2012.6264243 <http://dx.doi.org/10.1109/BMSB.2012.6264243>`_, `arXiv:1301.5793 <http://arxiv.org/abs/1301.5793>`_ [cs.MM]

Contents
--------

.. toctree::
   :maxdepth: 2

   installation
   configuration
   usage
   howto
   modules

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

