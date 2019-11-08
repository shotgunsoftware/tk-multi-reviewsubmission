# Copyright (c) 201 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .actions import Actions

__all__ = ["send_for_review", "render_and_submit_version"]


def send_for_review():
    action = Actions()
    action.render_and_submit_version()


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
    action = Actions()
    action.render_and_submit_version(
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
