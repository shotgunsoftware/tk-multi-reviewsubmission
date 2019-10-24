# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that controls various codec settings when submitting items for review
"""
import sgtk
import os
import sys
import tempfile
import maya

HookBaseClass = sgtk.get_hook_baseclass()


class MediaRenderer(HookBaseClass):
    def render(
        self,
        path,
        output_path,
        width,
        height,
        first_frame,
        last_frame,
        version,
        name,
        color_space,
    ):

        playblast_args = {"viewer": False, "forceOverwrite": True, "format": "qt"}

        if not output_path:
            name = name or ""

            temp_file = tempfile.NamedTemporaryFile(
                delete=False, prefix=name + ".", suffix=".mov"
            )
            temp_file.close
            output_path = temp_file.name

        playblast_args["filename"] = output_path

        if width:
            playblast_args["width"] = width

        if height:
            playblast_args["height"] = height

        self.logger.info(
            "Writing playblast to: %s using (%s)" % (output_path, playblast_args)
        )

        maya.cmds.playblast(**playblast_args)
        self.logger.info("Playblast written")

        return output_path
