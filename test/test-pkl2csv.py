# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

# Description: convert .pkl files to .csv from <dir> (and all subdirs)

import os, fnmatch, sys, pickle, csv

if len(sys.argv) != 2:
    print "Usage: test-pkl2csv.py <dir>"
    sys.exit()

def opj(*args):
    path = os.path.join(*args)
    return os.path.normpath(path)

def find_data_files(srcdir, *wildcards, **kw):
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
                    names.append(f)
        if names:
            lst.append( (dirname, names ) )

    file_list = []
    recursive = kw.get('recursive', True)
    if recursive:
        os.path.walk(srcdir, walk_helper, (file_list, wildcards))
    else:
        walk_helper((file_list, wildcards), srcdir,
                    [os.path.basename(f) for f in glob.glob(opj(srcdir, '*'))])
    return file_list

dirs = find_data_files(sys.argv[1], '*.pkl')

for dir in dirs:
    path = dir[0]
    files = dir[1]
    for file in files:
        print 'Processing ' + file + '...'
        csvfile = file[0:-4] + '.csv'
        f = open(path + '/' + file,'rb')
        data = pickle.load(f)
        f.close()
        f = open(path + '/' + csvfile, 'wb')
        if 'axes' in data:
            writer = csv.writer(f)
            writer.writerow(data['axes'][0])
            if type(data['axes'][1]).__name__ == 'dict':
                writer.writerow(data['axes'][1]['I'])
                writer.writerow(data['axes'][1]['P'])
                writer.writerow(data['axes'][1]['B'])
            else:
                writer.writerow(data['axes'][1])
            f.close()
        elif 'value' in data:
            writer = csv.writer(f)
            writer.writerow([data['value']])
        f.close()
print "\nFinished"