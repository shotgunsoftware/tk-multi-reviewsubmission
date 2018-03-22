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
import traceback

try:
    import nuke
except:
    nuke = None


class Renderer(object):
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle()
        self._font = os.path.join(self.__app.disk_location, "resources", "liberationsans_regular.ttf")

        burnin_template = self.__app.get_template("burnin_path")
        self._burnin_nk = burnin_template.apply_fields({})
        # If a show specific burnin file has not been defined, take it from the default location
        if not os.path.isfile(self._burnin_nk):
            self._burnin_nk = os.path.join(self.__app.disk_location, "resources", "burnin.nk")

        self._logo = None
        logo_template = self.__app.get_template("slate_logo")
        if os.path.isfile(logo_template.apply_fields({})):
            self._logo = logo_template.apply_fields({})
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

        nuke_render_info = {}

        # First get Nuke executable path from project configuration environment
        setting_key_by_os = {'win32': 'nuke_windows_path',
                             'linux2': 'nuke_linux_path',
                             'darwin': 'nuke_mac_path'}
        nuke_exe_path = self.__app.get_setting(setting_key_by_os[sys.platform])

        if nuke:
            nuke_version_major = nuke.NUKE_VERSION_MAJOR
        else:
            # TODO: get from nuke context somehow? Is this even required?
            if os.path.split(nuke_exe_path)[0] != '':
                nuke_version_str = os.path.basename(os.path.dirname(nuke_exe_path))  # get Nuke version folder
            else:
                nuke_version_str = os.path.basename(nuke_exe_path).replace('.exe', '').replace('app', '')

            bits = nuke_version_str.split('v')
            nuke_version_release = None
            if len(bits) > 1:
                nuke_version_release = bits[1]
            nuke_version_major_minor = bits[0]
            nuke_version_major = nuke_version_major_minor.split('.')[0]

        # get the Write node settings we'll use for generating the Quicktime
        writenode_quicktime_settings = self.__app.execute_hook_method("codec_settings_hook",
                                                                      "get_quicktime_settings",
                                                                      nuke_version_major=nuke_version_major)

        render_script_path = os.path.join(self.__app.disk_location, "hooks",
                                          "nuke_batch_render_movie.py")
        ctx = self.__app.context

        shotgun_context = {}
        shotgun_context['entity'] = ctx.entity.copy()
        if ctx.task:
            shotgun_context['task'] = ctx.task.copy()
        if ctx.step:
            shotgun_context['step'] = ctx.step.copy()
        shotgun_context['project'] = ctx.project.copy()

        app_settings = {
            'version_number_padding': self.__app.get_setting('version_number_padding'),
            'slate_logo': self._logo,
        }

        render_info = {
            'burnin_nk': self._burnin_nk,
            'slate_font': self._font,
            'codec_settings': {'quicktime': writenode_quicktime_settings},
        }

        # set needed paths and force them to use forward slashes for use in Nuke (latter needed for Windows)
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
            'nuke_version_str': nuke_version_str,
            'render_script_path': render_script_path,
            'shotgun_context': shotgun_context,
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

        run_in_batch_mode = True if nuke is None else False  # if nuke module wasn't imported it will be None

        if run_in_batch_mode:
            # --------------------------------------------------------------------------------------------
            #
            #  Running within Nuke interactive ...
            #
            # --------------------------------------------------------------------------------------------

            # Set-up the subprocess command and arguments
            cmd_and_args = [
                render_info.get('nuke_exe_path'), '-t', render_info.get('render_script_path'),
                '--path', render_info.get('src_frames_path'),
                '--output_path', render_info.get('movie_output_path'),
                '--width', str(width), '--height', str(height), '--version', str(version), '--name',
                name,
                '--color_space', color_space,
                '--first_frame', str(first_frame),
                '--last_frame', str(last_frame),
                '--app_settings', str(render_info.get('app_settings')),
                '--shotgun_context', str(render_info.get('shotgun_context')),
                '--render_info', str(render_info.get('render_info')),
            ]

            p = subprocess.Popen(cmd_and_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            output_name = os.path.basename(render_info.get('movie_output_path'))

            # TODO: How is this supposed to work?
            progress_fn = progress_label = None
            if active_progress_info:
                progress_fn = active_progress_info.get('show_progress_fn')
                progress_label = active_progress_info.get('label')

            output_lines = []

            num_frames = last_frame - first_frame + 1
            write_count = 0

            while p.poll() is None:
                line = p.stdout.readline()
                if line != '':
                    output_lines.append(line.rstrip())

                percent_complete = float(write_count) / float(num_frames) * 100.0
                if progress_fn:
                    progress_fn(progress_label,
                                'Nuke: {0:03.1f}%, {1}'.format(percent_complete, output_name))

                if line.startswith('Writing '):
                    # The number of these lines will be number of frames + 1
                    write_count += 1

            if p.returncode != 0:
                output_str = '\n'.join(output_lines)
                print output_str
                # TODO: Confirm this indeed appears on stdout
                # status_info = output_str.split('[RETURN_STATUS_DATA]')[1]
                # return status_info
                return {'status': 'not OK'}

            return {'status': 'OK'}

        else:
            # --------------------------------------------------------------------------------------------
            #
            #  Running within Nuke interactive ...
            #
            # --------------------------------------------------------------------------------------------
            import importlib

            render_script_path = render_info.get('render_script_path')

            script_dir_path, script_filename = os.path.split(render_script_path)
            sys.path.append(script_dir_path)

            render_script_module = importlib.import_module(script_filename.replace('.py', ''))
            ret_status = render_script_module.render_movie_in_nuke(
                render_info.get('src_frames_path'),
                render_info.get('movie_output_path'),
                width, height,
                first_frame, last_frame,
                version, name, color_space,
                render_info.get('app_settings'),
                render_info.get('shotgun_context'),
                render_info.get('render_info'))
            return ret_status
