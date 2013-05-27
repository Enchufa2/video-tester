# coding=UTF8
## This file is part of VideoTester
## See http://video-tester.googlecode.com for more information
## Copyright 2011 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

# Description: interactive .conf file generator

import sys

menu = [[False, '0: Interface', 'iface', ''],
        [False, '1: Server IP', 'ip', ''],
        [False, '2: Server port', 'port', ''],
        [False, '3: Protocol', 'protocols', ''],
        [False, '4: Video', 'video', ''],
        [False, '5: Codec', 'codec', ''],
        [False, '6: Bitrate', 'bitrate', ''],
        [False, '7: Framerate', 'framerate', ''],
        [False, '8: QoS measures', 'qos', ''],
        [False, '9: BS measures', 'bs', ''],
        [False, '10: VQ measures', 'vq', ''],
        [False, '11: Clear'],
        [False, '12: Done!'],
        [False, '13: Exit']]

while True:
    print 'Select common options:'
    for i, option in enumerate(menu):
        if i == 11:
            print '--------------------'
        if i < 11:
            add = ' (' + option[2] + ')'
        else:
            add = ''
        if option[0]:
            mark = ' -> '
        else:
            mark = '    '
        print mark + option[1] + add
    try:
        selection = int(raw_input('Add an option: '))
    except:
        selection = -1
    if selection == -1:
        continue
    elif selection == 11:
        for option in menu:
            option[0] = False
    elif selection == 12:
        break
    elif selection == 13:
        print 'Nothing to do. Exiting...'
        sys.exit()
    else:
        if menu[selection][0]:
            menu[selection][0] = False
        else:
            menu[selection][0] = True
print ''
for j in range(0, 11):
    if menu[j][0]:
        menu[j][3] = raw_input('Value for "' + menu[j][2] + '": ')
print ''
selection = int(raw_input('How many files do you want to generate?: '))
print ''
for i in range(0, selection):
    file = 'test-' + str(i) + '.conf'
    print 'Generating file "' + file + '"...'
    f = open(file, 'wb')
    f.write("[client]\n")
    for j in range(0, 11):
        if not menu[j][0]:
            value = raw_input('Value for "' + menu[j][2] + '": ')
        else:
            value = menu[j][3]
        line = menu[j][2] + '=' + value + "\n"
        f.write(line)
    f.close()
    print ''
print str(selection) + ' files generated!'