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
import tempfile
import maya

HookBaseClass = sgtk.get_hook_baseclass()


class MediaRenderer(HookBaseClass):
    def render(self, **kwargs):
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close

        temp_file_name = temp_file.name

        self.logger.info("Writing playblast to: %s" % (temp_file_name))
        maya.cmds.playblast(filename=temp_file_name, forceOverwrite=True, viewer=False)
        self.logger.info("Playblast completed")

        return temp_file_name
