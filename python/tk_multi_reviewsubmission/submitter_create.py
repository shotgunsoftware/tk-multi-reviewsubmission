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


class CreateSubmitter(object):
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle()
        self.__create_client_module = sgtk.platform.import_framework(
            "tk-framework-desktopclient", "create_client"
        )

        if not self.__create_client_module.is_create_installed():
            raise RuntimeError("Shotgun Create is not installed")

    def submit_version(
        self,
        path_to_frames,
        path_to_movie,
        thumbnail_path,
        sg_publishes,
        sg_task,
        comment,
        store_on_disk,
        first_frame,
        last_frame,
        upload_to_shotgun,
    ):

        self.__create_client_module.ensure_create_server_is_running(
            self.__app.sgtk.shotgun
        )

        client = self.__create_client_module.CreateClient(self.__app.sgtk.shotgun)

        if not sg_task:
            sg_task = self.__app.context.task

        client.call_server_method(
            "sgc_open_version_draft", {"task_id": sg_task["id"], "path": path_to_movie}
        )
