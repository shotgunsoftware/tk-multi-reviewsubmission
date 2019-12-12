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
import tempfile

HookBaseClass = sgtk.get_hook_baseclass()


class RenderMedia(HookBaseClass):
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
        Render the media

        :param path:            Path to the input frames for the movie      (Unused)
        :param output_path:     Path to the output movie that will be rendered
        :param width:           Width of the output movie                   (Unused)
        :param height:          Height of the output movie                  (Unused)
        :param first_frame:     The first frame of the sequence of frames.  (Unused)
        :param last_frame:      The last frame of the sequence of frames.   (Unused)
        :param version:         Version number to use for the output movie slate and burn-in
        :param name:            Name to use in the slate for the output movie
        :param color_space:     Colorspace of the input frames              (Unused)

        :returns:               Location of the rendered media
        :rtype:                 str
        """
        raise NotImplementedError()

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

        :param path:            Path to the input frames for the movie
        :param output_path:     Path to the output movie that will be rendered
        :param width:           Width of the output movie
        :param height:          Height of the output movie
        :param first_frame:     The first frame of the sequence of frames.
        :param last_frame:      The last frame of the sequence of frames.
        :param version:         Version number to use for the output movie slate and burn-in
        :param name:            Name to use in the slate for the output movie
        :param color_space:     Colorspace of the input frames

        :returns:               Location of the rendered media
        :rtype:                 str
        """

        pass

    def post_render(
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
        Callback executed after the media rendering

        :param input_path:      Path to the input frames for the movie
        :param output_path:     Path to the output movie that will be rendered
        :param width:           Width of the output movie
        :param height:          Height of the output movie
        :param first_frame:     The first frame of the sequence of frames.
        :param last_frame:      The last frame of the sequence of frames.
        :param version:         Version number to use for the output movie slate and burn-in
        :param name:            Name to use in the slate for the output movie
        :param color_space:     Colorspace of the input frames

        :returns:               Location of the rendered media
        :rtype:                 str
        """

        pass

    def _get_temp_media_path(self, name, version, extension):
        """
        Build a temporary path to put the rendered media.

        :param name:            Name of the media being rendered
        :param version:         Version number of the media being rendered
        :param extension:       Extension of the media being rendered

        :returns:               Temporary path to put the rendered version
        :rtype:                 str
        """

        name = name or ""

        if version:
            suffix = "_v" + version + extension
        else:
            suffix = extension

        with tempfile.NamedTemporaryFile(
            delete=False, prefix=name + ".", suffix=suffix
        ) as temp_file:
            return temp_file.name
