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
import copy


class Actions(object):
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle()
        self.__create_client_module = sgtk.platform.import_framework(
            "tk-framework-desktopclient", "create_client"
        )

        # Ensure that Shotgun Create is installed on the workstation.
        if not self.__create_client_module.is_create_installed():
            raise RuntimeError("Shotgun Create is not installed")

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
        """

        # Wrap the method so we don't have to worry about process_cb being None
        dispatch_progress = lambda *args: progress_cb is None or process_cb(*args)

        dispatch_progress(20, "Building the rendering options dictionary")

        if not fields:
            fields = {}

        if not sg_publishes:
            sg_publishes = []

        dispatch_progress(10, "Preparing")

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

            # Get our input_path for frames to convert to movie
            input_path = template.apply_fields(fields)
        else:
            input_path = None
            output_path = None

        # Get an output path for the movie.
        output_path_template = self.__app.get_template("movie_path_template")

        if output_path_template:
            output_path = output_path_template.apply_fields(fields)
        else:
            output_path = None

        render_media_hook_args = {
            "input_path": input_path,
            "output_path": output_path,
            "width": width,
            "height": height,
            "first_frame": first_frame,
            "last_frame": last_frame,
            "version": fields.get("version", 0),
            "name": fields.get("name", "Unnamed"),
            "color_space": color_space,
        }

        dispatch_progress(20, "Executing the pre-rende hook")

        self.__app.execute_hook_method(
            key="render_media_hook",
            method_name="pre_render",
            base_class=None,
            **render_media_hook_args
        )

        try:
            dispatch_progress(30, "Executing the render hook")

            output_path = self.__app.execute_hook_method(
                key="render_media_hook",
                method_name="render",
                base_class=None,
                **render_media_hook_args
            )

        finally:
            dispatch_progress(40, "Executing the post-render hook")

            self.__app.execute_hook_method(
                key="render_media_hook",
                method_name="post_render",
                base_class=None,
                **render_media_hook_args
            )

        dispatch_progress(50, "Creating Shotgun Version and uploading movie")

        # Submit the media to Shotgun Create.
        self.submit(output_path, sg_task, sg_publishes)

        # Log metrics for this app's usage
        try:
            self.__app.log_metric("Render & Submit Version", log_version=True)
        except Exception:
            # ingore any errors. ex: metrics logging not supported
            pass

    def submit(self, path_to_media, sg_task, sg_publishes):
        """
        Submit the media to Shotgun Create as a version Draft.

        :param path_to_media:   Draft media path
        :param sg_task:         Task on which the Version should be linked
        :param sg_publishes:    Publish files to link to the new Version
        """

        # Starts create in the right context if not already running.
        self.__create_client_module.ensure_create_server_is_running(
            self.__app.sgtk.shotgun
        )

        client = self.__create_client_module.CreateClient(self.__app.sgtk.shotgun)

        if not sg_task:
            sg_task = self.__app.context.task

        args = dict()
        args["task_id"] = sg_task["id"]
        args["path"] = path_to_media
        args["version_data"] = dict()

        if sg_publishes:
            args["version_data"]["published_files"] = sg_publishes

        client.call_server_method("sgc_open_version_draft", args)
