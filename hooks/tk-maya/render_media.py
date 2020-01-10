# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import sgtk
import maya
import os
import sys

HookBaseClass = sgtk.get_hook_baseclass()


class RenderMedia(HookBaseClass):
    """
    RenderMedia hook implementation for the tk-maya engine.
    """

    def render(
        self,
        input_path,
        output_path,
        width,
        height,
        first_frame,
        last_frame,
        version,
        name,
        color_space,
    ):
        """
        Render the media using the Maya Playblast API

        :param str input_path:      Path to the input frames for the movie      (Unused)
        :param str output_path:     Path to the output movie that will be rendered
        :param int width:           Width of the output movie
        :param int height:          Height of the output movie
        :param int first_frame:     The first frame of the sequence of frames.  (Unused)
        :param int last_frame:      The last frame of the sequence of frames.   (Unused)
        :param int version:         Version number to use for the output movie slate and burn-in
        :param str name:            Name to use in the slate for the output movie
        :param str color_space:     Colorspace of the input frames              (Unused)

        :returns:               Location of the rendered media
        :rtype:                 str
        """
        # For more informations about the playblast API,
        # https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__CommandsPython_playblast_html

        playblast_args = {
            "viewer": False,  # Specify whether a viewer should be launched for the playblast.
            "forceOverwrite": True,  # Overwrite existing playblast files which may have the the same name as the one specified with the "-f" flag
            "percent": 100,  # Percentage of current view size to use during blasting.
            # The format of the output of this playblast.
        }

        playblast_format, playblast_extension = self.get_playblast_format_param()

        if name == "Unnamed":
            current_file_path = maya.cmds.file(query=True, sn=True)

            if current_file_path:
                name = os.path.basename(current_file_path)

        if not output_path:
            output_path = self._get_temp_media_path(name, version, playblast_extension)

        # The filename to use for the output of this playblast.
        playblast_args["filename"] = output_path

        if width:
            # Width of the final image. This value will be clamped if larger than the width of the active window.
            playblast_args["width"] = width

        if height:
            # Height of the final image. This value will be clamped if larger than the width of the active window.
            playblast_args["height"] = height

        self.logger.info(
            "Writing playblast to: %s using (%s)" % (output_path, playblast_args)
        )

        maya.cmds.playblast(**playblast_args)
        self.logger.info("Playblast written")

        return output_path

    def get_playblast_format_param(self):
        """
        Build the playblast format related parameters.

        WARNING:
        Rendering a .mov does not work out of the box on Windows because it requires to have
        QuickTime installed. Since Shotgun Create supports avi files, it's a safe move to render
        this type on Windows so we can have an higher success rate on playblast.
        This is not an issue on MacOS and on Linux.

        :returns:               Tuple representing the playblast format and the playblast file extension
        :rtype:                 (str, str)

        """

        is_windows = sys.platform == "win32"
        return ("avi", ".avi") if is_windows else ("qt", ".mov")
