# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import nuke
from tank import Hook

class RenderMovieInNuke(Hook):
    """
    Hook called to perform an operation with the current scene
    """

    @staticmethod
    def _create_scale_node(width, height):
        """
        Create the Nuke scale node to resize the content.
        """
        scale = nuke.nodes.Reformat()
        scale["type"].setValue("to box")
        scale["box_width"].setValue(width)
        scale["box_height"].setValue(height)
        scale["resize"].setValue("fit")
        scale["box_fixed"].setValue(True)
        scale["center"].setValue(True)
        scale["black_outside"].setValue(True)
        return scale

    @staticmethod
    def _create_output_node(path):
        """
        Create the Nuke output node for the movie.
        """
        node = nuke.nodes.Write()

        # Example output settings
        #
        # These are either hard coded by a studio in a quicktime generation app
        # itself (like here) or part of the configuration - however there is
        # often the need to have special rules to for example handle multi
        # platform cases.
        #

        if sys.platform in ["darwin", "win32"]:
            # On the mac and windows, we use the quicktime codec
            node["file_type"].setValue("mov")
            node["codec"].setValue("jpeg")

        elif sys.platform == "linux2":
            # On linux, use ffmpeg
            node["file_type"].setValue("ffmpeg")
            node["format"].setValue("MOV format (mov)")

        node["file"].setValue(path.replace(os.sep, "/"))
        return node

    def execute(self, burnin_nk, font, logo, context, fields, path, output_path,
                width, height, first_frame, last_frame, **kwargs):
        """
        Use Nuke to render a movie. This assumes we're running _inside_ Nuke.
        """
        output_node = None

        # create group where everything happens
        group = nuke.nodes.Group()

        # now operate inside this group
        group.begin()
        try:
            # create read node
            read = nuke.nodes.Read(name="source", file=path)
            read["on_error"].setValue("black")
            read["first"].setValue(first_frame)
            read["last"].setValue(last_frame)

            # now create the slate/burnin node
            burn = nuke.nodePaste(burnin_nk)
            burn.setInput(0, read)

            # set the fonts for all text fields
            burn.node("top_left_text")["font"].setValue(font)
            burn.node("top_right_text")["font"].setValue(font)
            burn.node("bottom_left_text")["font"].setValue(font)
            burn.node("framecounter")["font"].setValue(font)
            burn.node("slate_info")["font"].setValue(font)

            # add the logo
            burn.node("logo")["file"].setValue(logo)

            # format the burnins
            version_padding_format = "%%0%dd" % self.parent.get_setting("version_number_padding")
            version_str = version_padding_format % fields.get("version", 0)


            if context.task:
                version = "%s, v%s" % (context.task["name"], version_str)
            elif context.step:
                version = "%s, v%s" % (context.step["name"], version_str)
            else:
                version = "v%s" % version_str

            burn.node("top_left_text")["message"].setValue(context.project["name"])
            burn.node("top_right_text")["message"].setValue(context.entity["name"])
            burn.node("bottom_left_text")["message"].setValue(version)

            # and the slate
            slate_str =  "Project: %s\n" % context.project["name"]
            slate_str += "%s: %s\n" % (context.entity["type"], context.entity["name"])
            slate_str += "Name: %s\n" % fields.get("name", "Unnamed").capitalize()
            slate_str += "Version: %s\n" % version_str

            if context.task:
                slate_str += "Task: %s\n" % context.task["name"]
            elif context.step:
                slate_str += "Step: %s\n" % context.step["name"]

            slate_str += "Frames: %s - %s\n" % (first_frame, last_frame)

            burn.node("slate_info")["message"].setValue(slate_str)

            # create a scale node
            scale = self._create_scale_node(width, height)
            scale.setInput(0, burn)

            # Create the output node
            output_node = self._create_output_node(output_path)
            output_node.setInput(0, scale)
        finally:
            group.end()

        if output_node:
            # Make sure the output folder exists
            output_folder = os.path.dirname(output_path)
            self.parent.ensure_folder_exists(output_folder)

            # Render the outputs, first view only
            nuke.executeMultiple([output_node], ([first_frame-1, last_frame, 1],), [nuke.views()[0]])

        # Cleanup after ourselves
        nuke.delete(group)
