# Copyright (c) 2020 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


import sgtk
from sgtk.platform.qt import QtCore, QtGui

HookBaseClass = sgtk.get_hook_baseclass()


class SubmitterCreate(HookBaseClass):
    """
    This hook allow to submit a Version to Shotgun using Shotgun Create.
    """

    def __init__(self, *args, **kwargs):
        super(SubmitterCreate, self).__init__(*args, **kwargs)

        self.__app = self.parent

        desktopclient_framework = self.load_framework(
            "tk-framework-desktopclient_v0.x.x"
        )
        self.__create_client_module = desktopclient_framework.import_module(
            "create_client"
        )

    def can_submit(self):
        """
        Checks if it's possible to submit versions given the current context/environment.

        :returns:               Flag telling if the hook can submit a version.
        :rtype:                 bool
        """

        if not self.__create_client_module.is_create_installed():

            QtGui.QMessageBox(
                QtGui.QMessageBox.Warning,
                "Cannot submit to ShotGrid",
                "SG Create is not installed!",
                flags=QtCore.Qt.Dialog
                | QtCore.Qt.MSWindowsFixedSizeDialogHint
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.X11BypassWindowManagerHint,
            ).exec_()

            self.__create_client_module.open_shotgun_create_download_page(
                self.__app.sgtk.shotgun
            )

            return False

        return True

    def submit_version(
        self,
        path_to_frames,
        path_to_movie,
        thumbnail_path,
        sg_publishes,
        sg_task,
        description,
        first_frame,
        last_frame,
    ):
        """
        Create a version in Shotgun for a given path and linked to the specified publishes.

        :param str path_to_frames: Path to the frames.
        :param str path_to_movie: Path to the movie.
        :param str thumbnail_path: Path to the thumbnail representing the version. ( Unused )
        :param list(dict) sg_publishes: Published files that have to be linked to the version.
        :param dict sg_task: Task that have to be linked to the version.
        :param str description: Description of the version.
        :param int first_frame: Version first frame ( Unused )
        :param int last_frame: Version last frame ( Unused )

        Note: Shotgun Create will create the thumbnail for the movie passed in and
        will inspect the media to get the first and last frame, so these parameters are ignored.

        :returns:               The Version Shotgun entity dictionary that was created.
        :rtype:                 dict

        Because of the asynchronous nature of this hook. It doesn't returns any Version Shotgun entity dictionary.
        """

        path_to_media = path_to_movie or path_to_frames

        # Starts Shotgun Create in the right context if not already running.
        ok = self.__create_client_module.ensure_create_server_is_running(
            self.__app.sgtk.shotgun
        )

        if not ok:
            raise RuntimeError("Unable to connect to SG Create.")

        client = self.__create_client_module.CreateClient(self.__app.sgtk.shotgun)

        if not sg_task:
            sg_task = self.__app.context.task

        version_draft_args = dict()
        version_draft_args["task_id"] = sg_task["id"]
        version_draft_args["path"] = path_to_media
        version_draft_args["version_data"] = dict()

        if sg_publishes:
            version_draft_args["version_data"]["published_files"] = sg_publishes

        if description:
            version_draft_args["version_data"]["description"] = description

        client.call_server_method("sgc_open_version_draft", version_draft_args)

        # Because of the asynchronous nature of this hook. It doesn't returns any Version Shotgun entity dictionary.
        return None
