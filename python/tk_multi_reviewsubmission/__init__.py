# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from .submitter_create import CreateSubmitter
from .submitter_sgtk import SGTKSubmitter

from .renderer import Renderer
from .actions import Actions


def send_for_review(app):
    action = Actions()
    action.send_for_review()


def render_and_submit_version(
    app,
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
