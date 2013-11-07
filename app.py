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
Example code for a quicktime creator app that runs in Nuke
"""

import copy
import os
import sys

import tank
import tank.templatekey
from tank.platform.qt import QtCore


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

    def render_and_submit(self, template, fields, first_frame, last_frame, sg_publishes, sg_task,
                          comment, thumbnail_path, progress_cb, **kwargs):
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

        progress_cb(10, "Preparing")

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
        progress_cb(20, "Rendering movie")
        self.app.execute_hook("hook_render_movie_in_nuke",
                              burnin_nk=self._burnin_nk,
                              font=self._font,
                              logo=self._logo,
                              context=self.context
                              fields=fields,
                              path=path,
                              output_path=output_path,
                              width=width,
                              height=height,
                              first_frame=first_frame,
                              last_frame=last_frame,
                              **kwargs)

        progress_cb(50, "Creating Shotgun Version")
        sg_version = self._submit_version(path,
                                          output_path,
                                          sg_publishes,
                                          sg_task,
                                          comment,
                                          store_on_disk,
                                          first_frame,
                                          last_frame)

        # Upload in a new thread and make our own event loop to wait for the
        # thread to finish.
        progress_cb(60, "Uploading to Shotgun")
        event_loop = QtCore.QEventLoop()
        thread = UploaderThread(self, sg_version, output_path, thumbnail_path, upload_to_shotgun)
        thread.finished.connect(event_loop.quit)
        thread.start()
        event_loop.exec_()

        # log any errors generated in the thread
        for e in thread.get_errors():
            self.log_error(e)

        # Remove from filesystem if required
        if not store_on_disk and os.path.exists(output_path):
            os.unlink(output_path)

        return sg_version

    def _submit_version(self, path_to_frames, path_to_movie, sg_publishes,
                        sg_task, comment, store_on_disk, first_frame, last_frame):
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
            "created_by": current_user,
            "user": current_user,
            "description": comment,
            "sg_path_to_frames": path_to_frames,
            "sg_movie_has_slate": True,
            "project": self.context.project,
        }

        if tank.util.get_published_file_entity_type(self.tank) == "PublishedFile":
            data["published_files"] = sg_publishes
        else:# == "TankPublishedFile"
            if len(sg_publishes) > 0:
                if len(sg_publishes) > 1:
                    self.log_warning("Only the first publish of %d can be registered for the new version!" % len(sg_publishes))
                data["tank_published_file"] = sg_publishes[0]

        if store_on_disk:
            data["sg_path_to_movie"] = path_to_movie

        sg_version = self.tank.shotgun.create("Version", data)
        self.log_debug("Created version in shotgun: %s" % str(data))
        return sg_version

class UploaderThread(QtCore.QThread):
    """
    Simple worker thread that encapsulates uploading to shotgun.
    Broken out of the main loop so that the UI can remain responsive
    even though an upload is happening
    """
    def __init__(self, app, version, path_to_movie, thumbnail_path, upload_to_shotgun):
        QtCore.QThread.__init__(self)
        self._app = app
        self._version = version
        self._path_to_movie = path_to_movie
        self._thumbnail_path = thumbnail_path
        self._upload_to_shotgun = upload_to_shotgun
        self._errors = []

    def get_errors(self):
        """
        can be called after execution to retrieve a list of errors
        """
        return self._errors

    def run(self):
        """
        Thread loop
        """
        upload_error = False

        if self._upload_to_shotgun:
            try:
                self._app.tank.shotgun.upload("Version", self._version["id"], self._path_to_movie, "sg_uploaded_movie")
            except Exception, e:
                self._errors.append("Movie upload to Shotgun failed: %s" % e)
                upload_error = True

        if not self._upload_to_shotgun or upload_error:
            try:
                self._app.tank.shotgun.upload_thumbnail("Version", self._version["id"], self._thumbnail_path)
            except Exception, e:
                self._errors.append("Thumbnail upload to Shotgun failed: %s" % e)
