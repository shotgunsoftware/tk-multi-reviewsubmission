# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import subprocess
from sgtk.platform.qt import QtCore

try:
    import nuke
except ImportError:
    nuke = None


class Renderer(object):
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle()
        self._font = os.path.join(self.__app.disk_location, "resources", "liberationsans_regular.ttf")
        context_fields = self.__app.context.as_template_fields()

        burnin_template = self.__app.get_template("burnin_path")
        self._burnin_nk = burnin_template.apply_fields(context_fields)
        # If a show specific burnin file has not been defined, take it from the default location
        if not os.path.isfile(self._burnin_nk):
            self._burnin_nk = os.path.join(self.__app.disk_location, "resources", "burnin.nk")

        self._logo = None
        logo_template = self.__app.get_template("slate_logo")
        logo_file_path = logo_template.apply_fields(context_fields)
        if os.path.isfile(logo_file_path):
            self._logo = logo_file_path
        else:
            self._logo = ""

        # now transform paths to be forward slashes, otherwise it wont work on windows.
        if sys.platform == "win32":
            self._font = self._font.replace(os.sep, "/")
            self._logo = self._logo.replace(os.sep, "/")
            self._burnin_nk = self._burnin_nk.replace(os.sep, "/")

    def gather_nuke_render_info(self, path, output_path,
                                width, height,
                                first_frame, last_frame,
                                version, name,
                                color_space):
        # First get Nuke executable path from project configuration environment
        setting_key_by_os = {'win32': 'nuke_windows_path',
                             'linux2': 'nuke_linux_path',
                             'darwin': 'nuke_mac_path'}
        nuke_exe_path = self.__app.get_setting(setting_key_by_os[sys.platform])

        # get the Write node settings we'll use for generating the Quicktime
        writenode_quicktime_settings = self.__app.execute_hook_method("codec_settings_hook",
                                                                      "get_quicktime_settings")

        render_script_path = os.path.join(self.__app.disk_location, "hooks",
                                          "nuke_batch_render_movie.py")

        serialized_context = self.__app.context.serialize()

        app_settings = {
            'version_number_padding': self.__app.get_setting('version_number_padding'),
            'slate_logo': self._logo,
        }

        render_info = {
            'burnin_nk': self._burnin_nk,
            'slate_font': self._font,
            'codec_settings': {'quicktime': writenode_quicktime_settings},
        }

        # set needed paths and force them to use forward slashes for use in Nuke (for Windows)
        src_frames_path = path.replace('\\', '/')
        movie_output_path = output_path.replace('\\', '/')

        nuke_render_info = {
            'width': width,
            'height': height,
            'first_frame': first_frame,
            'last_frame': last_frame,
            'version': version,
            'name': name,
            'color_space': color_space,
            'nuke_exe_path': nuke_exe_path,
            'render_script_path': render_script_path,
            'serialized_context': serialized_context,
            'app_settings': app_settings,
            'render_info': render_info,
            'src_frames_path': src_frames_path,
            'movie_output_path': movie_output_path,
        }
        return nuke_render_info

    def render_movie_in_nuke(self, path, output_path,
                             width, height,
                             first_frame, last_frame,
                             version, name,
                             color_space,
                             active_progress_info=None):

        render_info = self.gather_nuke_render_info(path, output_path, width, height, first_frame,
                                                   last_frame, version, name, color_space)
        run_in_batch_mode = True if nuke is None else False

        event_loop = QtCore.QEventLoop()
        thread = ShooterThread(render_info, run_in_batch_mode)
        thread.finished.connect(event_loop.quit)
        thread.start()
        event_loop.exec_()

        # log any errors generated in the thread
        thread_error_msg = thread.get_errors()
        if thread_error_msg:
            self.__app.log_error("OUTPUT:\n" + thread.get_output())
            self.__app.log_error("ERROR:\n" + thread_error_msg)

            # Do not clutter user message with any warnings etc from Nuke. Print only traceback.
            # TODO: is there a better way?
            try:
                subproc_traceback = 'Traceback' + thread_error_msg.split('Traceback')[1]
            except IndexError:
                subproc_traceback = thread_error_msg
            # Make sure we don't display a success message. TODO: Custom exception?
            raise Exception("Error in tk-multi-reviewsubmission: " + subproc_traceback)

class ShooterThread(QtCore.QThread):
    def __init__(self, render_info, batch_mode=True, active_progress_info=None):
        QtCore.QThread.__init__(self)
        self.render_info = render_info
        self.batch_mode = batch_mode
        self.active_progress_info = active_progress_info
        self.subproc_error_msg = ''
        self.subproc_output = ''

    def get_errors(self):
        return self.subproc_error_msg

    def get_output(self):
        return self.subproc_output

    def run(self):
        if self.batch_mode:
            nuke_flag = '-t'
        else:
            nuke_flag = '-it'

        cmd_and_args = [
            self.render_info['nuke_exe_path'], nuke_flag, self.render_info['render_script_path'],
            '--path', self.render_info['src_frames_path'],
            '--output_path', self.render_info['movie_output_path'],
            '--width', str(self.render_info['width']),
            '--height', str(self.render_info['height']),
            '--version', str(self.render_info['version']),
            '--name', self.render_info['name'],
            '--color_space', self.render_info['color_space'],
            '--first_frame', str(self.render_info['first_frame']),
            '--last_frame', str(self.render_info['last_frame']),
            '--app_settings', str(self.render_info['app_settings']),
            '--shotgun_context', str(self.render_info['serialized_context']),
            '--render_info', str(self.render_info['render_info']),
        ]

        p = subprocess.Popen(cmd_and_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        output_name = os.path.basename(self.render_info['movie_output_path'])
        # TODO: How is this supposed to work?
        progress_fn = progress_label = None
        if self.active_progress_info:
            progress_fn = self.active_progress_info.get('show_progress_fn')
            progress_label = self.active_progress_info.get('label')

        output_lines = []
        error_lines = []

        num_frames = self.render_info['last_frame'] - self.render_info['first_frame'] + 1
        write_count = 0

        while p.poll() is None:
            stdout_line = p.stdout.readline()
            stderr_line = p.stderr.readline()

            if stdout_line != '':
                output_lines.append(stdout_line.rstrip())
            if stderr_line != '':
                error_lines.append(stderr_line.rstrip())

            percent_complete = float(write_count) / float(num_frames) * 100.0
            if progress_fn:
                progress_fn(progress_label,
                            'Nuke: {0:03.1f}%, {1}'.format(percent_complete, output_name))
                # TODO: emit a signal to be captured by calling thread to update UI?

            if stdout_line.startswith('Writing '):
                # The number of these lines will be number of frames + 1
                write_count += 1

        self.subproc_output = '\n'.join(output_lines)
        if p.returncode != 0:
            self.subproc_error_msg = '\n'.join(error_lines)
