# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

from distutils.core import setup
from distutils.command.build import build as _build
from distutils import log
import os, fnmatch
from stat import ST_MODE

class build(_build):
    def run(self):
        _build.run(self)
        file = self.build_purelib + '/VideoTester/config.py'
        buffer = open(file).read()
        iface = raw_input('Select server interface [eth0]: ')
        port = raw_input('Select server port [8000]: ')
        if iface != '':
            log.info("changing SERVERIFACE of %s from eth0 to %s",
                        file, iface)
            buffer = buffer.replace("SERVERIFACE = 'eth0'", "SERVERIFACE = '" + iface + "'")
        if port != '':
            log.info("changing SERVERPORT of %s from 8000 to %s",
                        file, port)
            buffer = buffer.replace("SERVERPORT = 8000", "SERVERPORT = " + port)
        f = open(file, 'w')
        f.write(buffer)
        f.close()

# Code borrowed from wxPython's setup and config files
# Thanks to Robin Dunn for the suggestion.
# I am not 100% sure what's going on, but it works!
def opj(*args):
    path = os.path.join(*args)
    return os.path.normpath(path)

def find_data_files(base, srcdir, *wildcards, **kw):
    # get a list of all files under the srcdir matching wildcards,
    # returned in a format to be used for install_data
    def walk_helper(arg, dirname, files):
        if '.svn' in dirname:
            return
        names = []
        lst, wildcards = arg
        for wc in wildcards:
            wc_name = opj(dirname, wc)
            for f in files:
                filename = opj(dirname, f)
                
                if fnmatch.fnmatch(filename, wc_name) and not os.path.isdir(filename):
                    names.append(filename)
        if names:
            lst.append( (dirname.replace('doc', base), names ) )

    file_list = []
    recursive = kw.get('recursive', True)
    if recursive:
        os.path.walk(srcdir, walk_helper, (file_list, wildcards))
    else:
        walk_helper((file_list, wildcards), srcdir,
                    [os.path.basename(f) for f in glob.glob(opj(srcdir, '*'))])
    return file_list

version = "0.2"
files = find_data_files('share/doc/VideoTester-' + version, 'doc/', '*.*')

setup(name = "VideoTester",
    version = version,
    description = "Video Quality Assessment Tool",
    author = "Iñaki Úcar",
    author_email = "i.ucar86@gmail.com",
    url = "http://video-tester.googlecode.com",
    #download_url = "",
    packages = ['VideoTester', 'VideoTester.measures'],
    scripts = ["VT"],
    data_files = files,
    long_description = """Video Tester is a framework for the video quality assessment over a real or simulated IP network.""",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: X11 Applications',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Multimedia :: Video',
        'Topic :: Scientific/Engineering'
        ],
    keywords = ('video', 'tester', 'quality', 'assessment', 'measures', 'python', 'QoS', 'QoE'),
    platforms = ['Any'],
    license = "GPLv3",
    requires = ['scapy', 'wx', 'matplotlib', 'matplotlib.backends.backend_wxagg', 'pygst', 'gst', 'gobject', 'numpy', 'cv'],
    cmdclass = {'build': build}
)