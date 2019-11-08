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
        Render the media using the engine implementation of ``export_as_jpeg``

        :param input_path:      Path to the input frames for the movie      (Unused)
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

        if not output_path:
            name = name or ""

            if version:
                suffix = "_v" + version + ".jpg"
            else:
                suffix = ".jpg"

            temp_file = tempfile.NamedTemporaryFile(
                delete=False, prefix=name, suffix=suffix
            )

            temp_file.close
            output_path = temp_file.name

        self.logger.info("Saving as a JPG to: %s " % output_path)

        engine = sgtk.platform.current_engine()
        output_path = engine.export_as_jpeg(None, output_path)

        self.logger.info("JPG written")

        return output_path
