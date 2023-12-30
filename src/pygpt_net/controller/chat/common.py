#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 20:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Common:
    def __init__(self, window=None):
        """
        Chat common controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Set up UI"""
        # stream mode
        if self.window.core.config.get('stream'):
            self.window.ui.nodes['input.stream'].setChecked(True)
        else:
            self.window.ui.nodes['input.stream'].setChecked(False)

        # send clear
        if self.window.core.config.get('send_clear'):
            self.window.ui.nodes['input.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.core.config.get('send_mode')
        if mode == 2:
            self.window.ui.nodes['input.send_shift_enter'].setChecked(True)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 1:
            self.window.ui.nodes['input.send_enter'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 0:
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(True)

        # cmd enabled
        if self.window.core.config.get('cmd'):
            self.window.ui.nodes['cmd.enabled'].setChecked(True)
        else:
            self.window.ui.nodes['cmd.enabled'].setChecked(False)

        # output timestamps
        self.window.ui.nodes['output.timestamp'].setChecked(self.window.core.config.get('output_timestamp'))

        # images generation
        if self.window.core.config.get('img_raw'):
            self.window.ui.config_option['img_raw'].setChecked(True)
        else:
            self.window.ui.config_option['img_raw'].setChecked(False)

        # set focus to input
        self.window.ui.nodes['input'].setFocus()

    def toggle_stream(self, value):
        """
        Toggle stream

        :param value: value of the checkbox
        """
        self.window.core.config.set('stream', value)

    def toggle_cmd(self, value):
        """
        Toggle cmd enabled

        :param value: value of the checkbox
        """
        self.window.core.config.set('cmd', value)

        # stop commands thread if running
        if not value:
            self.window.controller.command.force_stop = True
        else:
            self.window.controller.command.force_stop = False

        self.window.controller.ui.update_tokens()  # update tokens counters

    def toggle_send_clear(self, value):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.core.config.set('send_clear', value)

    def toggle_send_shift(self, value):
        """
        Toggle send with shift

        :param value: value of the checkbox
        """
        self.window.core.config.set('send_mode', value)

    def lock_input(self):
        """Lock input"""
        self.window.controller.chat.input.locked = True
        self.window.ui.nodes['input.send_btn'].setEnabled(False)
        self.window.ui.nodes['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """Unlock input"""
        self.window.controller.chat.input.locked = False
        self.window.ui.nodes['input.send_btn'].setEnabled(True)
        self.window.ui.nodes['input.stop_btn'].setVisible(False)

    def stop(self):
        """Stop input"""
        event = Event('audio.input.toggle', {"value": False})
        self.window.controller.assistant.threads.force_stop = True
        self.window.core.dispatcher.dispatch(event)  # stop audio input
        self.window.controller.chat.input.force_stop = True
        self.window.core.gpt.stop()
        self.unlock_input()
        self.window.controller.chat.input.generating = False
        self.window.set_status(trans('status.stopped'))

    def check_api_key(self):
        result = True
        if self.window.core.config.get('api_key') is None or self.window.core.config.get('api_key') == '':
            self.window.controller.launcher.show_api_monit()
            self.window.set_status("Missing API KEY!")
            result = False
        return result

    def toggle_timestamp(self, value):
        """
        Toggle timestamp

        :param value: value of the checkbox
        """
        self.window.core.config.set('output_timestamp', value)
        self.window.core.config.save()
        self.window.controller.ctx.refresh()

    def img_enable_raw(self):
        """Enable help for images"""
        self.window.core.config.set('img_raw', True)
        self.window.core.config.save()

    def img_disable_raw(self):
        """Disable help for images"""
        self.window.core.config.set('img_raw', False)
        self.window.core.config.save()

    def img_toggle_raw(self, state):
        """
        Toggle help for images

        :param state: state of checkbox
        """
        if not state:
            self.img_disable_raw()
        else:
            self.img_enable_raw()
