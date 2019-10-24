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
import sys
import copy

from .submitter_create import CreateSubmitter
from .submitter_sgtk import SGTKSubmitter


class Actions(object):
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle()
        self.submit_with_create = self.__app.get_setting("submit_using_create")

        if self.submit_with_create:
            self.submitter = CreateSubmitter()
        else:
            self.submitter = SGTKSubmitter()

    def send_for_review(self):
        self.render_and_submit_version()

    def render_and_submit_version(
        self,
        template=None,
        fields=None,
        first_frame=None,
        last_frame=None,
        sg_publishes=None,
        sg_task=None,
        comment=None,
        thumbnail_path=None,
        progress_cb=None,
        color_space=None,
    ):
        """
        Main application entry point to be called by other applications / hooks.

        :param template:        The template defining the path where frames should be found.
        :param fields:          Dictionary of fields to be used to fill out the template with.
        :param first_frame:     The first frame of the sequence of frames.
        :param last_frame:      The last frame of the sequence of frames.
        :param sg_publishes:    A list of shotgun published file objects to link the publish against.
        :param sg_task:         A Shotgun task object to link against. Can be None.
        :param comment:         A description to add to the Version in Shotgun.
        :param thumbnail_path:  The path to a thumbnail to use for the version when the movie isn't
                                being uploaded to Shotgun (this is set in the config)
        :param progress_cb:     A callback to report progress with.
        :param color_space:     The colorspace of the rendered frames

        :returns:               The Version Shotgun entity dictionary that was created.
        """

        # Is the app configured to do anything?
        upload_to_shotgun = self.__app.get_setting("upload_to_shotgun")
        store_on_disk = self.__app.get_setting("store_on_disk")

        if not store_on_disk:
            if not upload_to_shotgun and not self.submit_with_create:
                self.__app.log_warning(
                    "App is not configured to store images on disk nor upload to shotgun!"
                )
                return None

        if not fields:
            fields = {}

        if not sg_publishes:
            sg_publishes = []

        if progress_cb:
            progress_cb(10, "Preparing")

        # Make sure we don't overwrite the caller's fields
        fields = copy.copy(fields)

        width = self.__app.get_setting("movie_width")
        height = self.__app.get_setting("movie_height")
        fields["width"] = width
        fields["height"] = height

        if template:
            for key_name in [
                key.name
                for key in template.keys.values()
                if isinstance(key, sgtk.templatekey.SequenceKey)
            ]:
                fields[key_name] = "FORMAT: %d"

            # Get our input path for frames to convert to movie
            path = template.apply_fields(fields)
        else:
            path = None
            output_path = None

        # Get an output path for the movie.
        output_path_template = self.__app.get_template("movie_path_template")

        if output_path_template:
            output_path = output_path_template.apply_fields(fields)
        else:
            output_path = None

        if progress_cb:
            progress_cb(20, "Rendering movie")

        output_path = self.__app.execute_hook_method(
            key="render_media_hook",
            method_name="render",
            base_class=None,
            **{
                "path": path,
                "output_path": output_path,
                "width": width,
                "height": height,
                "first_frame": first_frame,
                "last_frame": last_frame,
                "version": fields.get("version", 0),
                "name": fields.get("name", "Unnamed"),
                "color_space": color_space,
            }
        )

        if progress_cb:
            progress_cb(50, "Creating Shotgun Version and uploading movie")

        sg_version = self.submitter.submit_version(
            path,
            output_path,
            thumbnail_path,
            sg_publishes,
            sg_task,
            comment,
            store_on_disk,
            first_frame,
            last_frame,
            upload_to_shotgun,
        )

        # Remove from filesystem if required
        if not self.submit_with_create:
            if not store_on_disk and os.path.exists(output_path):
                if progress_cb:
                    progress_cb(90, "Deleting rendered movie")

                os.unlink(output_path)

        # log metrics for this app's usage
        try:
            self.__app.log_metric("Render & Submit Version", log_version=True)
        except:
            # ingore any errors. ex: metrics logging not supported
            pass

        return sg_version
