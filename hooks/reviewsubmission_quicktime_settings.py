# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys

from tank import Hook
import nuke

class ReviewSubmissionGetQuicktimeSettings(Hook):
    """
    Allows modifying default settings for Quicktime generation.
    """
    def execute(self, **kwargs):
        """
        Returns a dictionary of settings to be used for the Write Node that generates
        the Quicktime in Nuke.
        """
        settings = {}
        if sys.platform in ["darwin", "win32"]:
            # On Mac and Windows, we use the Quicktime codec
            settings["file_type"] = "mov"
            # Nuke 9.0v1 changed the codec knob name to meta_codec and added an encoder knob
            # (which defaults to the new mov64 encoder/decoder).  
            if nuke.NUKE_VERSION_MAJOR > 8:
                settings["meta_codec"] = "jpeg"
            else:
                settings["codec"] = "jpeg"

        elif sys.platform == "linux2":
            # On linux, use ffmpeg
            settings["file_type"] = "ffmpeg"
            settings["format"] = "MOV format (mov)"

        return settings

