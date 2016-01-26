# coding=UTF8
## This file is part of VideoTester
## See https://github.com/Enchufa2/video-tester for more information
## Copyright 2011-2016 Iñaki Úcar <i.ucar86@gmail.com>
## This program is published under a GPLv3 license

import wx, wx.aui, pickle, textwrap, logging
import matplotlib as mpl
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as Canvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as Toolbar
from gi.repository import Gst, GstVideo, GObject
from . import __version__, VTLOG, VTClient, netifaces, \
    supported_codecs, supported_protocols
from .resources import getVTIcon, getVTBitmap

class FuncLog(logging.Handler):
    '''
    A logging handler that sends logs to an update function.
    '''
    def __init__(self, textctrl):
        logging.Handler.__init__(self)
        self.textctrl = textctrl

    def emit(self, record):
        self.textctrl.SetInsertionPointEnd()
        self.textctrl.WriteText(self.format(record) + '\n')

class VTframe(wx.Frame):
    '''
    Main window.
    '''
    def __init__(self, conf):
        self.main = VTClient(conf)
        wx.Frame.__init__(self, None)
        self.SetIcon(getVTIcon())

        # Menu Bar
        self.vtmenubar = wx.MenuBar()
        menu = wx.Menu()
        self.m_files = menu.Append(wx.ID_OPEN, '&Open files...', 'Select Pickle files to plot')
        menu.AppendSeparator()
        self.m_exit = menu.Append(wx.ID_EXIT, 'E&xit', 'Exit program')
        self.vtmenubar.Append(menu, '&File')
        menu = wx.Menu()
        self.m_run = menu.Append(wx.ID_REFRESH, '&Run...', 'Run test')
        self.vtmenubar.Append(menu, 'R&un')
        menu = wx.Menu()
        self.m_about = menu.Append(wx.ID_ABOUT, '&About', 'About this program')
        self.vtmenubar.Append(menu, '&Help')
        self.SetMenuBar(self.vtmenubar)

        self.vtstatusbar = self.CreateStatusBar(1, 0)
        self.tabs = wx.Notebook(self, -1, style=0)
        self.conf_tab = wx.Panel(self.tabs, -1)

        self.video_label = wx.StaticText(self.conf_tab, -1, 'Choose a video:')
        self.video = wx.Choice(self.conf_tab, -1, choices=[x[0] for x in self.main.videos])
        self.codec_label = wx.StaticText(self.conf_tab, -1, 'Choose a codec:')
        self.codec = wx.Choice(self.conf_tab, -1, choices=supported_codecs.keys())
        self.bitrate_label = wx.StaticText(self.conf_tab, -1, 'Select the bitrate:')
        self.bitrate = wx.Slider(self.conf_tab, -1, self.main.conf['bitrate'], 64, 1024, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.framerate_label = wx.StaticText(self.conf_tab, -1, 'Select the framerate:')
        self.framerate = wx.Slider(self.conf_tab, -1, self.main.conf['framerate'], 1, 100, style=wx.SL_HORIZONTAL | wx.SL_LABELS)
        self.sb_video = wx.StaticBox(self.conf_tab, -1, 'Video options:')

        self.iface_label = wx.StaticText(self.conf_tab, -1, 'Interface:')
        self.iface = wx.Choice(self.conf_tab, -1, choices=netifaces)
        self.ip_label = wx.StaticText(self.conf_tab, -1, 'Server IP:')
        self.ip = wx.TextCtrl(self.conf_tab, -1, self.main.conf['ip'])
        self.port_label = wx.StaticText(self.conf_tab, -1, 'Server port:')
        self.port = wx.TextCtrl(self.conf_tab, -1, str(self.main.port))
        self.protocol = wx.RadioBox(self.conf_tab, -1, 'Protocol:', choices=supported_protocols, majorDimension=3, style=wx.RA_SPECIFY_COLS)
        self.sb_net = wx.StaticBox(self.conf_tab, -1, 'Net options:')

        self.qos = []
        self.qos.append(('latency', wx.CheckBox(self.conf_tab, -1, 'Latency')))
        self.qos.append(('delta', wx.CheckBox(self.conf_tab, -1, 'Delta')))
        self.qos.append(('jitter', wx.CheckBox(self.conf_tab, -1, 'Jitter')))
        self.qos.append(('skew', wx.CheckBox(self.conf_tab, -1, 'Skew')))
        self.qos.append(('bandwidth', wx.CheckBox(self.conf_tab, -1, 'Bandwidth')))
        self.qos.append(('plr', wx.CheckBox(self.conf_tab, -1, 'Packet Loss Rate')))
        self.qos.append(('pld', wx.CheckBox(self.conf_tab, -1, 'Packet Loss Distribution')))
        self.sb_qos = wx.StaticBox(self.conf_tab, -1, 'QoS measures:')

        self.bs = []
        self.bs.append(('streameye', wx.CheckBox(self.conf_tab, -1, 'Stream Eye')))
        self.bs.append(('refstreameye', wx.CheckBox(self.conf_tab, -1, 'refStream Eye')))
        self.bs.append(('gop', wx.CheckBox(self.conf_tab, -1, 'GOP size')))
        self.bs.append(('iflr', wx.CheckBox(self.conf_tab, -1, 'I Frame Loss Rate')))
        self.sb_bs = wx.StaticBox(self.conf_tab, -1, 'BitStream measures:')

        self.vq = []
        self.vq.append(('psnr', wx.CheckBox(self.conf_tab, -1, 'PSNR')))
        self.vq.append(('ssim', wx.CheckBox(self.conf_tab, -1, 'SSIM')))
        self.vq.append(('g1070', wx.CheckBox(self.conf_tab, -1, 'G.1070')))
        self.vq.append(('psnrtomos', wx.CheckBox(self.conf_tab, -1, 'PSNRtoMOS')))
        self.vq.append(('miv', wx.CheckBox(self.conf_tab, -1, 'MIV')))
        self.sb_vq = wx.StaticBox(self.conf_tab, -1, 'Video quality measures:')

        self.log_tab = wx.Panel(self.tabs, -1)
        self.log = wx.TextCtrl(self.log_tab, -1, '', style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.results_tab = PlotNotebook(self.tabs)
        self.video_tab = wx.Panel(self.tabs, -1)
        self.player = wx.Panel(self.video_tab, -1)
        self.player_button = wx.Button(self.video_tab, -1, 'Play', name='playvideo', size=(200, 50))

        self.__setProperties()
        self.__doLayout()
        self.__initVideo()

        self.Bind(wx.EVT_MENU, self.onOpen, self.m_files)
        self.Bind(wx.EVT_MENU, self.onExit, self.m_exit)
        self.Bind(wx.EVT_MENU, self.onRun, self.m_run)
        self.Bind(wx.EVT_MENU, self.onAbout, self.m_about)
        self.Bind(wx.EVT_CLOSE, self.onCloseWindow)
        self.player_button.Bind(wx.EVT_BUTTON, self.onPlay)

        # Logging
        console = VTLOG.handlers[0]
        self.hdlr = FuncLog(self.log)
        self.hdlr.setLevel(console.level)
        console.setLevel(40)
        self.hdlr.setFormatter(console.formatter)
        VTLOG.addHandler(self.hdlr)

    def __setProperties(self):
        self.SetTitle('Video Tester')
        self.SetSize((800, 600))
        self.Hide()
        self.vtstatusbar.SetStatusWidths([-1])
        vtstatusbar_fields = ['VT Client']
        for i in range(len(vtstatusbar_fields)):
            self.vtstatusbar.SetStatusText(vtstatusbar_fields[i], i)

        self.video_label.SetMinSize((160, 17))
        self.video.SetMinSize((120, 25))
        self.video.SetSelection(zip(*self.main.videos)[0].index(self.main.conf['video']))

        self.codec_label.SetMinSize((160, 17))
        self.codec.SetMinSize((120, 25))
        self.codec.SetSelection(supported_codecs.keys().index(self.main.conf['codec']))

        self.bitrate_label.SetMinSize((160, 17))
        self.bitrate.SetMinSize((210, 50))

        self.framerate_label.SetMinSize((160, 17))
        self.framerate.SetMinSize((210, 50))

        self.iface_label.SetMinSize((140, 17))
        self.iface.SetMinSize((80, 25))
        self.iface.SetSelection(netifaces.index(self.main.conf['iface']))

        self.ip_label.SetMinSize((140, 17))
        self.ip.SetMinSize((150, 25))

        self.port_label.SetMinSize((140, 17))

        self.protocol.SetSelection(supported_protocols.index(self.main.conf['protocol']))

        for name, el in self.qos + self.bs + self.vq:
            if name in self.main.conf['qos'] + self.main.conf['bs'] + self.main.conf['vq']:
                el.SetValue(True)

        self.results_tab.Hide()
        self.video_tab.Hide()

    def __doLayout(self):
        sizer_body = wx.BoxSizer(wx.VERTICAL)
        sizer_log_tab = wx.BoxSizer(wx.HORIZONTAL)
        sizer_video_tab = wx.BoxSizer(wx.VERTICAL)
        sizer_conf_tab = wx.GridSizer(2, 1, 3, 3)
        sizer_conf_up = wx.GridSizer(1, 2, 0, 0)
        sizer_conf_down = wx.GridSizer(1, 3, 0, 0)
        sizer_conf_tab.Add(sizer_conf_up, 1, wx.EXPAND, 0)
        sizer_conf_tab.Add(sizer_conf_down, 1, wx.EXPAND, 0)

        sizer_video = wx.GridSizer(4, 1, 0, 0)
        sizer_net = wx.GridSizer(4, 1, 0, 0)
        sizer_qos = wx.BoxSizer(wx.VERTICAL)
        sizer_bs = wx.BoxSizer(wx.VERTICAL)
        sizer_vq = wx.BoxSizer(wx.VERTICAL)

        self.sb_video.Lower()
        sizer_sb_video = wx.StaticBoxSizer(self.sb_video, wx.HORIZONTAL)
        sizer_sb_video.Add(sizer_video, 1, wx.EXPAND | wx.ALL, 10)
        self.sb_net.Lower()
        sizer_sb_net = wx.StaticBoxSizer(self.sb_net, wx.HORIZONTAL)
        sizer_sb_net.Add(sizer_net, 1, wx.EXPAND | wx.ALL, 10)
        self.sb_qos.Lower()
        sizer_sb_qos = wx.StaticBoxSizer(self.sb_qos, wx.HORIZONTAL)
        sizer_sb_qos.Add(sizer_qos, 1, wx.EXPAND | wx.ALL, 10)
        self.sb_bs.Lower()
        sizer_sb_bs = wx.StaticBoxSizer(self.sb_bs, wx.HORIZONTAL)
        sizer_sb_bs.Add(sizer_bs, 1, wx.EXPAND | wx.ALL, 10)
        self.sb_vq.Lower()
        sizer_sb_vq = wx.StaticBoxSizer(self.sb_vq, wx.HORIZONTAL)
        sizer_sb_vq.Add(sizer_vq, 1, wx.EXPAND | wx.ALL, 10)

        sizer_videobox = wx.BoxSizer(wx.HORIZONTAL)
        sizer_videobox.Add(self.video_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_videobox.Add(self.video, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_codec = wx.BoxSizer(wx.HORIZONTAL)
        sizer_codec.Add(self.codec_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_codec.Add(self.codec, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_bitrate = wx.BoxSizer(wx.HORIZONTAL)
        sizer_bitrate.Add(self.bitrate_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_bitrate.Add(self.bitrate, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_framerate = wx.BoxSizer(wx.HORIZONTAL)
        sizer_framerate.Add(self.framerate_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_framerate.Add(self.framerate, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)

        sizer_video.Add(sizer_videobox, 1, wx.EXPAND, 0)
        sizer_video.Add(sizer_codec, 1, wx.EXPAND, 0)
        sizer_video.Add(sizer_bitrate, 1, wx.EXPAND, 0)
        sizer_video.Add(sizer_framerate, 1, wx.EXPAND, 0)

        sizer_iface = wx.BoxSizer(wx.HORIZONTAL)
        sizer_iface.Add(self.iface_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_iface.Add(self.iface, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_ip = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ip.Add(self.ip_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_ip.Add(self.ip, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_port = wx.BoxSizer(wx.HORIZONTAL)
        sizer_port.Add(self.port_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        sizer_port.Add(self.port, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)

        sizer_net.Add(sizer_iface, 1, wx.EXPAND, 0)
        sizer_net.Add(sizer_ip, 1, wx.EXPAND, 0)
        sizer_net.Add(sizer_port, 1, wx.EXPAND, 0)
        sizer_net.Add(self.protocol, 0, wx.EXPAND, 0)

        for name, el in self.qos:
            sizer_qos.Add(el, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        for name, el in self.bs:
            sizer_bs.Add(el, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        for name, el in self.vq:
            sizer_vq.Add(el, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)

        sizer_conf_up.Add(sizer_sb_video, 1, wx.EXPAND | wx.ALL^wx.BOTTOM, 10)
        sizer_conf_up.Add(sizer_sb_net, 1, wx.EXPAND | wx.ALL^wx.BOTTOM, 10)
        sizer_conf_down.Add(sizer_sb_qos, 1, wx.EXPAND | wx.ALL, 10)
        sizer_conf_down.Add(sizer_sb_bs, 1, wx.EXPAND | wx.ALL, 10)
        sizer_conf_down.Add(sizer_sb_vq, 1, wx.EXPAND | wx.ALL, 10)
        self.conf_tab.SetSizer(sizer_conf_tab)

        sizer_log_tab.Add(self.log, 1, wx.EXPAND | wx.ADJUST_MINSIZE, 0)
        self.log_tab.SetSizer(sizer_log_tab)
        sizer_video_tab.Add(self.player, 1, wx.EXPAND, 0)
        sizer_video_tab.Add(self.player_button, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 30)
        self.video_tab.SetSizer(sizer_video_tab)
        self.video_tab.SetBackgroundColour((0, 0, 0))

        self.tabs.AddPage(self.conf_tab, 'Configuration')
        self.tabs.AddPage(self.log_tab, 'Log')
        self.tabs.AddPage(self.results_tab, 'Results')
        self.tabs.AddPage(self.video_tab, 'Video')
        sizer_body.Add(self.tabs, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_body)
        self.Layout()
        self.Centre()

    def __initVideo(self):
        self.pipeline = Gst.parse_launch(
        'filesrc name=video1 filesrc name=video2 filesrc name=video3 \
            videomixer name=mix ! xvimagesink \
            video1. \
                ! queue ! videoparse framerate=%s/1 name=parser1 \
                ! textoverlay font-desc="Sans 24" text="Original" \
                    valignment=top halignment=left shaded-background=true \
                ! videoscale \
                ! mix.sink_1 \
            video2. \
                ! queue ! videoparse framerate=%s/1 name=parser2 \
                ! textoverlay font-desc="Sans 24" text="Coded" \
                    valignment=top halignment=left shaded-background=true \
                ! videoscale \
                ! mix.sink_2 \
            video3. \
                ! queue ! videoparse framerate=%s/1 name=parser3 \
                ! textoverlay font-desc="Sans 24" text="Received" \
                    valignment=top halignment=left shaded-background=true \
                ! videoscale \
                ! mix.sink_3' % (
            self.main.conf['framerate'],
            self.main.conf['framerate'],
            self.main.conf['framerate']
        ))
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect('message', self.onMessage)
        bus.connect('sync-message::element', self.onSyncMessage)

    def onExit(self, event):
        self.Close(True)

    def onCloseWindow(self, event):
        '''
        Show a dialog to verify exit.
        '''
        # dialog to verify exit (including menuExit)
        dlg = wx.MessageDialog(self, 'Do you want to exit?', 'Exit', wx.YES_NO | wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_YES:
            try:
                self.pipeline.set_state(Gst.State.NULL)
            except:
                pass
            VTLOG.removeHandler(self.hdlr)
            self.Destroy() # frame

    def onAbout(self, event):
        '''
        Show *About* dialog.
        '''
        license = textwrap.dedent('''\
        This program is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        This program is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with this program.  If not, see <http://www.gnu.org/licenses/>.''')
        info = wx.AboutDialogInfo()
        info.SetIcon(getVTIcon())
        info.SetName('Video Tester')
        info.SetVersion('version ' + __version__)
        info.SetDescription('Video Quality Assessment Tool')
        info.SetCopyright('(C) 2011-2016 Iñaki Úcar')
        info.SetWebSite('https://github.com/Enchufa2/video-tester')
        info.SetLicense(license)
        info.AddDeveloper('Iñaki Úcar <i.ucar86@gmail.com>')
        info.AddDocWriter('Iñaki Úcar <i.ucar86@gmail.com>')
        info.AddArtist('Almudena M. Castro <almudena.m.castro@gmail.com>')
        wx.AboutBox(info)

    def onOpen(self, event):
        '''
        Show *Open files* dialog.
        '''
        self.video_tab.Hide()
        wildcard = u'Pickle files (*.pkl)|*.pkl'
        dlg = wx.FileDialog(self, u'Open files', '', '', wildcard, wx.FD_MULTIPLE)
        if dlg.ShowModal() == wx.ID_OK:
            results = []
            for filename in dlg.GetFilenames():
                f = open(dlg.GetDirectory() + '/' + filename, 'rb')
                results.append(pickle.load(f))
                f.close()
            dlg.Destroy()
            self.__setResults(results)
            self.tabs.SetSelection(2)

    def onRun(self, event):
        '''
        Run VT Client.
        '''
        self.conf_tab.Disable()
        self.vtmenubar.Disable()
        self.results_tab.Hide()
        self.video_tab.Hide()
        self.tabs.SetSelection(1)
        self.vtstatusbar.SetStatusText('Running...')
        self.__setValues()
        ret = self.main.run()
        if ret:
            self.paths, self.caps, results = ret
            self.__setResults(results)
            self.video_tab.Show()
        self.conf_tab.Enable()
        wx.Window.Enable(self.vtmenubar)
        self.vtstatusbar.SetStatusText('Stopped')

    def onPlay(self, event):
        '''
        Play video files.
        '''
        if self.player_button.GetLabel() == 'Play':
            self.player_button.SetLabel('Stop')
            video1 = self.pipeline.get_by_name('video1')
            video2 = self.pipeline.get_by_name('video2')
            video3 = self.pipeline.get_by_name('video3')
            video1.props.location = self.paths['original'][1]
            video2.props.location = self.paths['coded'][1]
            video3.props.location = self.paths['received'][1]
            parser1 = self.pipeline.get_by_name('parser1')
            parser2 = self.pipeline.get_by_name('parser2')
            parser3 = self.pipeline.get_by_name('parser3')
            mix = self.pipeline.get_by_name('mix')
            sink_2 = mix.get_child_by_name('sink_2')
            sink_3 = mix.get_child_by_name('sink_3')
            sink_2.props.xpos = self.caps['width'] * 2
            sink_3.props.xpos = self.caps['width']
            parser1.props.width = self.caps['width']
            parser1.props.height = self.caps['height']
            parser2.props.width = self.caps['width']
            parser2.props.height = self.caps['height']
            parser3.props.width = self.caps['width']
            parser3.props.height = self.caps['height']
            self.pipeline.set_state(Gst.State.PLAYING)
        else:
            self.player_button.SetLabel('Play')
            self.pipeline.set_state(Gst.State.NULL)

    def onSyncMessage(self, bus, message):
        if GstVideo.is_video_overlay_prepare_window_handle_message(message):
            message.src.set_property('force-aspect-ratio', True)
            message.src.set_window_handle(self.video_tab.GetHandle())

    def onMessage(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS or t == Gst.MessageType.ERROR:
            self.pipeline.set_state(Gst.State.NULL)
            self.player_button.SetLabel('Play')

    def __setValues(self):
        '''
        Set configuration options.
        '''
        self.main.conf['bitrate'] = int(self.bitrate.GetValue())
        self.main.conf['framerate'] = int(self.framerate.GetValue())
        self.main.conf['video'] = str(self.video.GetStringSelection())
        self.main.conf['codec'] = str(self.codec.GetStringSelection())
        self.main.conf['iface'] = str(self.iface.GetStringSelection())
        self.main.conf['ip'] = str(self.ip.GetValue())
        self.main.port = int(self.port.GetValue())
        self.main.conf['protocol'] = str(self.protocol.GetStringSelection())
        qos = []
        for name, el in self.qos:
            if el.GetValue():
                qos.append(name)
        self.main.conf['qos'] = qos
        bs = []
        for name, el in self.bs:
            if el.GetValue():
                bs.append(name)
        self.main.conf['bs'] = bs
        vq = []
        for name, el in self.vq:
            if el.GetValue():
                vq.append(name)
        self.main.conf['vq'] = vq

    def __setResults(self, results):
        '''
        Plot measures and show *Results* tab.
        '''
        self.results_tab.removePages()
        for measure in results:
            axes = self.results_tab.add(measure['name']).gca()
            if measure['type'] == 'plot':
                axes.plot(measure['axes'][0], measure['axes'][1], 'b')
                axes.plot(measure['axes'][0], [measure['mean'] for i in measure['axes'][0]], 'g')
                axes.plot(measure['axes'][0], [measure['max'][1] for i in measure['axes'][0]], 'r')
                axes.plot(measure['axes'][0], [measure['min'][1] for i in measure['axes'][0]], 'r')
                axes.set_xlabel(measure['units'][0])
                axes.set_ylabel(measure['units'][1])
            elif measure['type'] == 'value':
                width = 1
                axes.bar([0.5], measure['value'], width=width)
                axes.set_ylabel(measure['units'])
                axes.set_xticks([1])
                axes.set_xlim(0, 2)
                axes.set_xticklabels([measure['name']])
            elif measure['type'] == 'bar':
                axes.bar(measure['axes'][0], measure['axes'][1], width=measure['width'])
                axes.plot(measure['axes'][0], [measure['mean'] for i in measure['axes'][0]], 'g')
                axes.plot(measure['axes'][0], [measure['max'][1] for i in measure['axes'][0]], 'r')
                axes.plot(measure['axes'][0], [measure['min'][1] for i in measure['axes'][0]], 'r')
                axes.set_xlabel(measure['units'][0])
                axes.set_ylabel(measure['units'][1])
            elif measure['type'] == 'videoframes':
                axes.bar(measure['axes'][0], measure['axes'][1]['B'], width=1, color='g')
                axes.bar(measure['axes'][0], measure['axes'][1]['P'], width=1, color='b')
                axes.bar(measure['axes'][0], measure['axes'][1]['I'], width=1, color='r')
                axes.set_xlabel(measure['units'][0])
                axes.set_ylabel(measure['units'][1])
        self.results_tab.Show()

class Plot(wx.Panel):
    '''
    Plot panel.
    '''
    def __init__(self, parent, id = -1, dpi = None, **kwargs):
        wx.Panel.__init__(self, parent, id=id, **kwargs)
        self.figure = mpl.figure.Figure(dpi=dpi, figsize=(2,2))
        self.canvas = Canvas(self, -1, self.figure)
        self.toolbar = Toolbar(self.canvas)
        self.toolbar.Realize()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas,1,wx.EXPAND)
        sizer.Add(self.toolbar, 0 , wx.LEFT | wx.EXPAND)
        self.SetSizer(sizer)

class PlotNotebook(wx.Panel):
    '''
    Tab-style plotting panel.
    '''
    def __init__(self, parent, id = -1):
        wx.Panel.__init__(self, parent, id=id)
        self.nb = wx.aui.AuiNotebook(self)
        sizer = wx.BoxSizer()
        sizer.Add(self.nb, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.pages = []

    def add(self, name='plot'):
        '''
        Add a tab.
        '''
        page = Plot(self.nb)
        self.pages.append(page)
        self.nb.AddPage(page, name)
        return page.figure

    def removePages(self):
        '''
        Remove all tabs.
        '''
        for page in self.pages:
            self.nb.DeletePage(0)

class VTApp(wx.App):
    '''
    WxPython application class.
    '''
    def __init__(self, conf):
        self.conf = conf
        wx.App.__init__(self)

    def OnInit(self):
        vtframe = VTframe(self.conf)
        self.SetTopWindow(vtframe)
        vtframe.Show()
        return True
