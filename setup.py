# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <iucar@fedoraproject.org>
## This program is published under a GPLv3 license

from distutils.core import setup
import os, fnmatch
from VideoTester import __version__

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

files = find_data_files('share/doc/VideoTester-' + __version__, 'doc/', '*.*')

setup(name = 'VideoTester',
    version = __version__,
    description = 'Video Quality Assessment Tool',
    author = 'Iñaki Úcar',
    author_email = 'iucar@fedoraproject.org',
    url = 'https://github.com/Enchufa2/video-tester',
    download_url = 'https://github.com/Enchufa2/video-tester/tarball/master',
    packages = ['VideoTester', 'VideoTester.measures'],
    scripts = ['VT'],
    data_files = files,
    long_description = '''Video Tester is a framework for the video quality assessment over a real or simulated IP network.''',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
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
    platforms = ['Linux', 'Unix'],
    license = 'GPLv3',
    install_requires = [
        'gi>=3.18.2',
        'pcap>=0.6.4',
        'numpy>=1.4.1',
        'cv>=2.1',
        'wx>=2.8.11',
        'matplotlib>=1.0.1',
        'matplotlib.backends.backend_wxagg']
)
