"""
Copyright (c) 2012 Shotgun Software, Inc
----------------------------------------------------

Example code for a quicktime creator app that runs in Nuke
"""

import os
import platform

import nuke
import tank

class QuicktimeGenerator(tank.platform.Application):
    def __init__(self, *args, **kwargs):
        super(QuicktimeGenerator, self).__init__(*args, **kwargs)
        self._logo = None
        self._burnin_nk = None
        self._font = None

    def init_app(self):
        self._logo = os.path.join(self.disk_location, "resources", "logo.png")
        self._burnin_nk = os.path.join(self.disk_location, "resources", "burnin.nk")
        self._font = os.path.join(self.disk_location, "resources", "liberationsans_regular.ttf")
        # now transform paths to be forward slashes, otherwise it wont work on windows.
        # stupid nuke ;(
        if platform.system() == 'Windows':
            self._font = self._font.replace(os.sep, "/")
            self._logo = self._logo.replace(os.sep, "/")
            self._burnin_nk = self._burnin_nk.replace(os.sep, "/")        

    @staticmethod
    def get_first_frame():
        """
        returns the first frame for this session
        """
        return int(nuke.root()["first_frame"].value())
        
    @staticmethod
    def get_last_frame():
        """
        returns the last frame for this session
        """
        return int(nuke.root()["last_frame"].value())

    def render_and_submit(self, path, sg_publish, sg_task, comment):
        # Movie output width and height
        width = self.get_setting("movie_width")
        height = self.get_setting("movie_height")

        # Get an output path for the movie given the input path.
        template = self.tank.template_from_path(path)
        fields = template.get_fields(path)
        fields["width"] = width
        fields["height"] = height

        output_path_template = self.get_template("movie_path_template")
        output_path = output_path_template.apply_fields(fields)

        self.render_movie(path, output_path, width, height)
        self.submit_version(path, output_path, sg_publish, sg_task, comment)
    
    def submit_version(self, path_to_frames, path_to_movie, sg_publish=None, sg_task=None, comment=None):
        """
        Create a version in Shotgun for this path and linked to this publish.
        """
        # Create the version in Shotgun
        context = self.tank.context_from_path(path_to_frames)
        data = {
            "code": os.path.splitext(os.path.basename(path_to_movie))[0],
            "sg_status_list": self.get_setting("new_version_status"),
            "entity": context.entity,
            "sg_task": sg_task,
            "tank_published_file": sg_publish,
            "description": comment,
            "sg_path_to_frames": path_to_frames,
            "sg_path_to_movie": path_to_movie,
            "sg_movie_has_slate": True,
            "project": context.project,
        }
        sg_version = self.tank.shotgun.create("Version", data)

        # Upload the movie to Shotgun
        self.tank.shotgun.upload("Version", sg_version['id'], path_to_movie, "sg_uploaded_movie")

    def render_movie(self, path, output_path, width, height):
        """
        Main hook entry point
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
            read["first"].setValue(self.get_first_frame())
            read["last"].setValue(self.get_last_frame())
            
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
        
            # pull some metadata out of the context and the file
            template = self.tank.template_from_path(path)
            fields = template.get_fields(path)
            context = self.tank.context_from_path(path)
    
            # format the burnins  
            ver = fields.get("version", 0)
            version_padding_format = "%%0%dd" % self.get_setting("version_number_padding")
            if context.task:
                version = ("%s, version " + version_padding_format) % (context.task["name"], ver)
            elif context.step:
                version = ("%s, version " + version_padding_format) % (context.step["name"], ver)
            else:
                version = ("Version " + version_padding_format) % ver
            
            burn.node("top_left_text")["message"].setValue(context.project["name"])
            burn.node("top_right_text")["message"].setValue(context.entity["name"])
            burn.node("bottom_left_text")["message"].setValue(version)
            
            # and the slate
            slate_str =  "Project: %s\n" % context.project["name"]
            slate_str += "%s: %s\n" % (context.entity["type"], context.entity["name"])
            slate_str += ("Version: " + version_padding_format + "\n") % ver
            
            if context.task:
                slate_str += "Task: %s\n" % context.task["name"]
            elif context.step:
                slate_str += "Step: %s\n" % context.step["name"]
            
            slate_str += "Frames: %s - %s\n" % (self.get_first_frame(), self.get_last_frame())
            
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
            nuke.executeMultiple(
                [output_node],
                ([self.get_first_frame()-1, self.get_last_frame(), 1],),
                [nuke.views()[0]]
            )

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
        if platform.system() in ["Darwin", "Windows"]:
            node["file_type"].setValue("mov")
            node["codec"].setValue("jpeg")
        elif platform.system() == "Linux":
            node["file_type"].setValue("ffmpeg")
            node["codec"].setValue("MOV format (mov)")
        node["file"].setValue(path.replace(os.sep, "/"))
        return node        
