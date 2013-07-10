"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Example code for a quicktime creator app that runs in Nuke
"""

import copy
import os
import sys

import nuke
import tank
import tank.templatekey


class QuicktimeGenerator(tank.platform.Application):
    def __init__(self, *args, **kwargs):
        super(QuicktimeGenerator, self).__init__(*args, **kwargs)
        self._logo = None
        self._burnin_nk = None
        self._font = None

    def init_app(self):
        
        self._burnin_nk = os.path.join(self.disk_location, "resources", "burnin.nk")
        self._font = os.path.join(self.disk_location, "resources", "liberationsans_regular.ttf")

        # If the slate_logo supplied was an empty string, the result of getting 
        # the setting will be the config folder which is invalid so catch that
        # and make our logo path an empty string which Nuke won't have issues with.
        if os.path.isfile( self.get_setting("slate_logo", "") ):
            self._logo = self.get_setting("slate_logo", "")
        else:
            self._logo = ""

        # now transform paths to be forward slashes, otherwise it wont work on windows.
        # stupid nuke ;(
        if sys.platform == "win32":
            self._font = self._font.replace(os.sep, "/")
            self._logo = self._logo.replace(os.sep, "/")
            self._burnin_nk = self._burnin_nk.replace(os.sep, "/")        

    def render_and_submit(self, template, fields, first_frame, last_frame, sg_publishes, sg_task, comment):
        """
        Main application entry point to be called by other applications / hooks.

        :template: SGTK Template object. The template defining the path where
                   frames should be found.
                        
        :fields: Fields to be used to fill out the template with.
               
        :first_frame: int. The first frame of the sequence of frames.
                        
        :last_frame: int. The last frame of the sequence of frames.
                        
        :sg_publishes: A list of shotgun published file objects to link the publish against.
                     
        :sg_task: A Shotgun task object to link against. Can be None.
                        
        :comment: str. A description to add to the Version in Shotgun. 

        Returns the Version that was created in Shotgun.
        """

        # Is the app configured to do anything?
        upload_to_shotgun = self.get_setting("upload_to_shotgun")
        store_on_disk = self.get_setting("store_on_disk")
        if not upload_to_shotgun and not store_on_disk:
            self.log_warning("App is not configured to store images on disk nor upload to shotgun!")
            return None

        # Make sure we don't overwrite the caller's fields
        fields = copy.copy(fields)

        # Tweak fields so that we'll be getting nuke formated sequence markers (%03d, %04d etc):
        for key_name in [key.name for key in template.keys.values() if isinstance(key, tank.templatekey.SequenceKey)]:
            fields[key_name] = "FORMAT: %d"

        # Get our input path for frames to convert to movie
        path = template.apply_fields(fields)

        # Movie output width and height
        width = self.get_setting("movie_width")
        height = self.get_setting("movie_height")
        fields["width"] = width
        fields["height"] = height

        # Get an output path for the movie.
        output_path_template = self.get_template("movie_path_template")
        output_path = output_path_template.apply_fields(fields)

        # Render and Submit
        self._render_movie_in_nuke(fields, path, output_path, width, height, first_frame, last_frame)
        sg_version = self._submit_version(path, 
                                          output_path,
                                          sg_publishes, 
                                          sg_task, 
                                          comment, 
                                          upload_to_shotgun, 
                                          store_on_disk,
                                          first_frame, 
                                          last_frame)

        # Remove the movie if no local copy was requested.
        if not store_on_disk:
            os.unlink(output_path)

        return sg_version
    
    def _submit_version(self, path_to_frames, path_to_movie, sg_publishes, 
                        sg_task, comment, upload, store_on_disk, first_frame, last_frame):
        """
        Create a version in Shotgun for this path and linked to this publish.
        """
        
        # get current shotgun user
        current_user = tank.util.get_current_user(self.tank)
        
        # create a name for the version based on the file name
        # grab the file name, strip off extension
        name = os.path.splitext(os.path.basename(path_to_movie))[0]
        # do some replacements
        name = name.replace("_", " ")
        # and capitalize
        name = name.capitalize()
        
        # Create the version in Shotgun
        data = {
            "code": name,
            "sg_status_list": self.get_setting("new_version_status"),
            "entity": self.context.entity,
            "sg_task": sg_task,
            "sg_first_frame": first_frame,
            "sg_last_frame": last_frame,
            "frame_count": (last_frame-first_frame+1),
            "frame_range": "%s-%s" % (first_frame, last_frame),
            "sg_frames_have_slate": False,
            "published_files": sg_publishes,
            "created_by": current_user,
            "description": comment,
            "sg_path_to_frames": path_to_frames,
            "sg_movie_has_slate": True,
            "project": self.context.project,
        }

        data["sg_path_to_movie"] = path_to_movie

        sg_version = self.tank.shotgun.create("Version", data)
        self.log_debug("Created version in shotgun: %s" % str(data))

        # Upload the movie to Shotgun
        if upload:
            self.log_debug("Uploading movie to shotgun...")
            self.tank.shotgun.upload("Version", sg_version['id'], path_to_movie, "sg_uploaded_movie")

        return sg_version

    def _render_movie_in_nuke(self, fields, path, output_path, width, height, first_frame, last_frame):
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
            burn = nuke.nodePaste(self._burnin_nk) 
            burn.setInput(0, read)
        
            # set the fonts for all text fields
            burn.node("top_left_text")["font"].setValue(self._font)
            burn.node("top_right_text")["font"].setValue(self._font)
            burn.node("bottom_left_text")["font"].setValue(self._font)
            burn.node("framecounter")["font"].setValue(self._font)
            burn.node("slate_info")["font"].setValue(self._font)
        
            # add the logo
            burn.node("logo")["file"].setValue(self._logo)
            
            # format the burnins
            version_padding_format = "%%0%dd" % self.get_setting("version_number_padding")
            version_str = version_padding_format % fields.get("version", 0)
            
            
            if self.context.task:
                version = "%s, v%s" % (self.context.task["name"], version_str)
            elif self.context.step:
                version = "%s, v%s" % (self.context.step["name"], version_str)
            else:
                version = "v%s" % version_str
            
            burn.node("top_left_text")["message"].setValue(self.context.project["name"])
            burn.node("top_right_text")["message"].setValue(self.context.entity["name"])
            burn.node("bottom_left_text")["message"].setValue(version)
            
            # and the slate            
            slate_str =  "Project: %s\n" % self.context.project["name"]
            slate_str += "%s: %s\n" % (self.context.entity["type"], self.context.entity["name"])
            slate_str += "Name: %s\n" % fields.get("name", "Unnamed").capitalize()
            slate_str += "Version: %s\n" % version_str
            
            if self.context.task:
                slate_str += "Task: %s\n" % self.context.task["name"]
            elif self.context.step:
                slate_str += "Step: %s\n" % self.context.step["name"]
            
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
            self.ensure_folder_exists(output_folder)
            
            # Render the outputs, first view only
            nuke.executeMultiple([output_node], ([first_frame-1, last_frame, 1],), [nuke.views()[0]])

        # Cleanup after ourselves
        nuke.delete(group)
    
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
            node["codec"].setValue("MOV format (mov)")

        node["file"].setValue(path.replace(os.sep, "/"))
        return node        
