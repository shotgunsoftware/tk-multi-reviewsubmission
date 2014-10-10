# Copyright (c) 2013 Shotgun Software Inc.
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

class Renderer(object):
    
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle() 
        
        # If the slate_logo supplied was an empty string, the result of getting 
        # the setting will be the config folder which is invalid so catch that
        # and make our logo path an empty string which Nuke won't have issues with.
        self._slate_logo = None
        if os.path.isfile( self.__app.get_setting("slate_logo", "") ):
            self._slate_logo = self.__app.get_setting("slate_logo", "")
        else:
            self._slate_logo = ""

    def render_movie(self, path, output_path,
                     width, height,
                     first_frame, last_frame,
                     version, name,
                     color_space):
        """
        Use Nuke to render a movie. This assumes we're running _inside_ Nuke.
                        
        :param path:        Path to the input frames for the movie
        :param output_path: Path to the output movie that will be rendered
        :param width:       Width of the output movie
        :param height:      Height of the output movie
        :param first_frame: Start frame for the output movie
        :param last_frame:  End frame for the output movie
        :param version:     Version number to use for the output movie slate and burn-in
        :param name:        Name to use in the slate for the output movie
        :param color_space: Colorspace of the input frames
        """
        ctx = self.__app.context
        
        # Construct the burnin and slate text.  Currently this is hard-coded but could be
        # template driven at some point if needed
        version_padding_format = "%%0%dd" % self.__app.get_setting("version_number_padding")
        version_str = version_padding_format % version
        
        if ctx.task:
            version_label = "%s, v%s" % (ctx.task["name"], version_str)
        elif ctx.step:
            version_label = "%s, v%s" % (ctx.step["name"], version_str)
        else:
            version_label = "v%s" % version_str
        
        burnin_text = {
            "top_left":ctx.project["name"],
            "top_right":ctx.entity["name"],
            "bottom_left":version_label
        }
        
        # and the slate
        slate_text =  "Project: %s\n" % ctx.project["name"]
        slate_text += "%s: %s\n" % (ctx.entity["type"], ctx.entity["name"])
        slate_text += "Name: %s\n" % name.capitalize()
        slate_text += "Version: %s\n" % version_str
        
        if ctx.task:
            slate_text += "Task: %s\n" % ctx.task["name"]
        elif ctx.step:
            slate_text += "Step: %s\n" % ctx.step["name"]
        
        slate_text += "Frames: %s - %s\n" % (first_frame, last_frame)

        # call hook to do the actual render:
        self.__app.execute_hook_method("hook_render_movie", 
                                       "render_movie",
                                       path_to_frames = path,
                                       output_path = output_path,
                                       width = width, 
                                       height = height, 
                                       first_frame = first_frame, 
                                       last_frame = last_frame, 
                                       color_space = color_space, 
                                       slate_text = slate_text,
                                       slate_logo = self._slate_logo,
                                       burnin_text = burnin_text)
