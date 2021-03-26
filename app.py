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
Sgtk Application for handling Quicktime generation and review submission
"""

import sgtk
import sgtk.templatekey
import copy
import os


class MultiReviewSubmissionApp(sgtk.platform.Application):
    """
    Main Application class
    """

    def init_app(self):
        """
        App initialization

        Note, this app doesn't register any commands at the moment as all it's functionality is
        provided through it's API.
        """

        app = self.import_module("tk_multi_reviewsubmission")

        display_name = self.get_setting("display_name")

        # Only register the command to the engine if the display name is explicitely added to the config.
        # There's cases where someone would want to have this app in his environment without the menu item.
        if display_name:
            menu_caption = "%s..." % display_name
            menu_options = {
                "short_name": "send_for_review",
                "description": "Send a version for review using SG Create",
                # dark themed icon for engines that recognize this format
                "icons": {
                    "dark": {
                        "png": os.path.join(self.disk_location, "icon_256_dark.png")
                    }
                },
            }

            self.engine.register_command(
                menu_caption, lambda: app.send_for_review(), menu_options
            )

    @property
    def context_change_allowed(self):
        """
        Specifies that context changes are allowed.
        """
        return True

    def render_and_submit_version(
        self,
        template,
        fields,
        first_frame,
        last_frame,
        sg_publishes,
        sg_task,
        comment,
        thumbnail_path,
        progress_cb,
        color_space=None,
        *args,
        **kwargs
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
        :rtype:                 dict
        """
        app = self.import_module("tk_multi_reviewsubmission")

        return app.render_and_submit_version(
            template,
            fields,
            first_frame,
            last_frame,
            sg_publishes,
            sg_task,
            comment,
            thumbnail_path,
            progress_cb,
            color_space=None,
            *args,
            **kwargs
        )
