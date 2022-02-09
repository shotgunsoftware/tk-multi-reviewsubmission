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
import os
import sys
import re
import json
import heapq
import pymxs
from pymxs import runtime as mxs

HookBaseClass = sgtk.get_hook_baseclass()


# https://github.com/ADN-DevTech/3dsMax-Python-HowTos/blob/master/src/packages/quickpreview/README.md for more information


class RenderMedia(HookBaseClass):
    """
    RenderMedia hook implementation for the tk-3dsmax engine.
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
        Render the media using pymxs for 3dsmax

        :param str input_path:      Path to the input frames for the movie      (Unused)
        :param str output_path:     Path to the output movie that will be rendered
        :param int width:           Width of the output movie                   (Unused)
        :param int height:          Height of the output movie                  (Unused)
        :param int first_frame:     The first frame of the sequence of frames.  (Unused)
        :param int last_frame:      The last frame of the sequence of frames.   (Unused)
        :param int version:         Version number to use for the output movie slate and burn-in
        :param str name:            Name to use in the slate for the output movie
        :param str color_space:     Colorspace of the input frames              (Unused)

        :returns:               Location of the rendered media
        :rtype:                 str
        """
        #current_engine = sgtk.platform.current_engine()
        #tk = current_engine.sgtk
        #if pymxs.runtime.maxFilePath and pymxs.runtime.maxFileName:
        #    path_name = os.path.join(pymxs.runtime.maxFilePath, pymxs.runtime.maxFileName)
        file_no_ext = os.path.splitext(pymxs.runtime.maxFileName)[0]
        filename = file_no_ext + ".mov"
        base_path = os.path.dirname(pymxs.runtime.maxFilePath)
        output_path = os.path.join(pymxs.runtime.getDir(pymxs.runtime.Name("preview")), filename)
        view_size = pymxs.runtime.getViewSize()
        anim_bmp = pymxs.runtime.bitmap(view_size.x, view_size.y, filename=output_path)
        for t in range(int(pymxs.runtime.animationRange.start), int(pymxs.runtime.animationRange.end)):
            pymxs.runtime.sliderTime = t
            dib = pymxs.runtime.gw.getViewportDib()
            pymxs.runtime.copy(dib, anim_bmp)
            pymxs.runtime.save(anim_bmp)
        pymxs.runtime.close(anim_bmp)
        pymxs.runtime.gc()

        return output_path
