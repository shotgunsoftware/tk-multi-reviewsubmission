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
from sgtk.platform.qt import QtCore, QtGui

HookBaseClass = sgtk.get_hook_baseclass()


class RenderMedia(HookBaseClass):
    """
    RenderMedia hook implementation for the tk-photoshopcc engine.
    """

    def pre_render(
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
        Callback executed before the media rendering

        :param str path:            Path to the input frames for the movie
        :param str output_path:     Path to the output movie that will be rendered
        :param int width:           Width of the output movie
        :param int height:          Height of the output movie
        :param int first_frame:     The first frame of the sequence of frames.
        :param int last_frame:      The last frame of the sequence of frames.
        :param int version:         Version number to use for the output movie slate and burn-in
        :param str name:            Name to use in the slate for the output movie
        :param str color_space:     Colorspace of the input frames

        :returns:               Location of the rendered media
        :rtype:                 str
        """

        engine = sgtk.platform.current_engine()

        if not engine.adobe.get_active_document():
            QtGui.QMessageBox(
                QtGui.QMessageBox.Warning,
                "Unable to render",
                "No active document found.",
                flags=QtCore.Qt.Dialog
                | QtCore.Qt.MSWindowsFixedSizeDialogHint
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.X11BypassWindowManagerHint,
            ).exec_()

            raise RuntimeError("No active document found.")

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
        Render the media using the engine implementation of ``export_as_jpeg``

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
        engine = sgtk.platform.current_engine()

        if name == "Unnamed":
            name = engine.adobe.get_active_document().name

        if not output_path:
            output_path = self._get_temp_media_path(name, version, ".jpg")

        self.logger.info("Saving as a JPG to: %s " % output_path)

        output_path = engine.export_as_jpeg(None, output_path)

        self.logger.info("JPG written")

        return output_path
