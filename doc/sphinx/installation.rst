Installation
============

Video Tester has the following dependencies:

* Python 2.7.
* GStreamer (>=1.0) + plugins: base, good, ugly, bad, libav.
* GStreamer RTSP server (>=1.0).
* PyGObject (>=3.18.2).
* Pylibpcap (>=0.6.4).
* Numpy (>=1.4.1).
* OpenCV (>=2.1) with Python bindings.
* Matplotlib (>=1.0.1).
* WxPython (>=2.8.11) + Matplotlib backend.

Method 1 (Fedora only):
-----------------------

If you are using **Fedora**, you can build an RPM and let DNF/YUM manage all dependencies for you. First of all, enable the `RPM Fusion <http://rpmfusion.org/>`_ repositories. Then, you can download the latest RPM, if available, or build it by yourself::

  $ git clone https://github.com/Enchufa2/video-tester.git
  $ cd video-tester
  $ make bdist_rpm
  $ cd dist

and then install it::

  $ sudo dnf install VideoTester-x.x.x-1.noarch.rpm

Method 2 (all distributions):
-----------------------------

You need to manually install all the required dependencies.

.. note::

	If you are using **Fedora**, first of all, enable the `RPM Fusion <http://rpmfusion.org/>`_ repositories. Then, these dependencies can be installed with the following command::

		$ sudo dnf install gstreamer1 gstreamer1-libav gstreamer1-plugins-base gstreamer1-plugins-good gstreamer1-plugins-ugly gstreamer1-plugins-bad-free gstreamer1-plugins-bad-freeworld gstreamer1-rtsp-server python-gobject pylibpcap numpy python2-matplotlib python2-matplotlib-wx wxPython opencv-python

Then, download the latest version of Video Tester and follow these steps::

  $ tar xf VideoTester-x.x.x.tar.gz
  $ cd VideoTester-x.x.x
  $ sudo python setup.py install

After the installation, Video Tester will be located in ``/usr/lib/python2.7/site-packages/VideoTester``, and this documentation, in ``/usr/share/doc/VideoTester-x.x.x``. You should be able to launch the application with the command ``VT``.
