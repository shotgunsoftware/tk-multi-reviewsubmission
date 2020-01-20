# Copyright (c) 2019 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .actions import Actions

import sgtk

logger = sgtk.platform.get_logger(__name__)


def send_for_review():
    """
    Main application entry point to be called by the engine command.

    :returns:               The Version Shotgun entity dictionary that was created.
    :rtype:                 dict
    """

    try:
        action = Actions()
        return action.render_and_submit_version()
    except RuntimeError as e:
        logger.error(str(e))


def render_and_submit_version(
    template,
    fields,
    first_frame,
    last_frame,
    sg_publishes,
    sg_task,
    comment,
    thumbnail_path,
    progress_cb,
    color_space,
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
    try:
        action = Actions()
        return action.render_and_submit_version(
            template,
            fields,
            first_frame,
            last_frame,
            sg_publishes,
            sg_task,
            comment,
            thumbnail_path,
            progress_cb,
            color_space,
            *args,
            **kwargs
        )
    except Exception as e:
        logger.error(str(e))
