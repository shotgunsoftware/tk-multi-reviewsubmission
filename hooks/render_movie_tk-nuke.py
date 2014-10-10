# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that renders a movie to be submitted for review from a set of rendered frames
"""
import sgtk
import os
import sys
import nuke

HookBaseClass = sgtk.get_hook_baseclass()

class NukeRenderer(HookBaseClass):
    """
    Nuke specific version of the renderer
    """
    def render_movie(self, path_to_frames, output_path, 
                     width, height, 
                     first_frame, last_frame, 
                     color_space, 
                     slate_text, slate_logo,
                     burnin_text,
                     *args, **kwargs):
        """
        :param path_to_frames:  Path to the input frames for the movie
        :param output_path:     Path to the output movie that will be rendered
        :param width:           Width of the output movie
        :param height:          Height of the output movie
        :param first_frame:     Start frame for the output movie
        :param last_frame:      End frame for the output movie
        :param color_space:     Colorspace of the input frames

        :param slate_text:      The text to include on the slate        
        :param slate_logo:      Path to a logo to include in the slate
        :param burnin_text:     A dictionary of strings to include in different
                                parts of the burnin.  This dictionary will contain
                                the following entries:
                                - top_left
                                - top_right
                                - bottom_left
        """
        # the tk-multi-reviewsubmission app is the hook's parent
        app = self.parent
        ctx = app.context
        
        # get the elements we need for the burnin and slate:        
        burnin_nk = self._get_burnin_nk()
        font = self._get_font()
        if slate_logo:
            slate_logo = slate_logo.replace(os.sep, "/")

        # create group where everything happens
        group = nuke.nodes.Group()
        
        # now operate inside this group
        group.begin()
        output_node = None
        try:
            # create read node
            read = nuke.nodes.Read(name="source", file=path_to_frames.replace(os.sep, "/"))
            read["on_error"].setValue("black")
            read["first"].setValue(first_frame)
            read["last"].setValue(last_frame)
            if color_space:
                read["colorspace"].setValue(color_space)
            
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
            burn.node("logo")["file"].setValue(slate_logo or "")
            
            # set-up the burnin text:
            for section, text in burnin_text.iteritems():
                node = burn.node("%s_text" % section)
                if node:
                    node["message"].setValue(text)
            
            # and the slate            
            burn.node("slate_info")["message"].setValue(slate_text)

            # create a scale node
            scale = self._create_scale_node(width, height)
            scale.setInput(0, burn)                

            # Create the output node
            output_node = self._create_output_node(output_path)
            output_node.setInput(0, scale)
        finally:
            group.end()
            
        try:
            if output_node:
                # Make sure the output folder exists
                output_folder = os.path.dirname(output_path)
                app.ensure_folder_exists(output_folder)
                
                # Render the outputs, first view only
                nuke.executeMultiple([output_node], ([first_frame-1, last_frame, 1],), [nuke.views()[0]])
        finally:
            # Cleanup after ourselves
            nuke.delete(group)
        
    def _get_burnin_nk(self):
        """
        Get the Nuke burnin script to use.  The base implementation returns the default
        script provided with the app but this can be overriden in a derived hook to
        return a custom script.
        """
        # get the default script:
        burnin_nk = os.path.join(self.parent.disk_location, "resources", "burnin.nk")
        # make it Nuke friendly:
        burnin_nk = burnin_nk.replace(os.sep, "/")
        return burnin_nk
    
    def _get_font(self):
        """
        Get the font to use for the slate and burnin.  The base implementation returns the default
        font provided with the app but this can be overriden in a derived hook to return a custom font.
        """
        # get the default font:
        font = os.path.join(self.parent.disk_location, "resources", "liberationsans_regular.ttf")
        # make it Nuke friendly:
        font = font.replace(os.sep, "/")
        return font
    
    def _create_scale_node(self, width, height):
        """
        Create the Nuke scale node to resize the content.
        
        :param width:   The width of the movie
        :param height:  The height of the movie
        :returns:       A new Nuke scale node that scales the input 
                        to the correct size for the movie
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

    def _create_output_node(self, path):
        """
        Create the Nuke output node for the movie.
        
        :param path: The output path for the movie
        :returns:    A new Nuke Write node that will output the movie
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