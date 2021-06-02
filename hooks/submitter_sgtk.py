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

import os

HookBaseClass = sgtk.get_hook_baseclass()


class SubmitterSGTK(HookBaseClass):
    """
    This hook allow to submit a Version to Shotgun using Shotgun Toolkit.
    """

    def __init__(self, *args, **kwargs):
        super(SubmitterSGTK, self).__init__(*args, **kwargs)

        self.__app = self.parent

        self._upload_to_shotgun = self.__app.get_setting("upload_to_shotgun")
        self._store_on_disk = self.__app.get_setting("store_on_disk")

    def can_submit(self):
        """
        Checks if it's possible to submit versions given the current context/environment.

        :returns:               Flag telling if the hook can submit a version.
        :rtype:                 bool
        """

        if not self._upload_to_shotgun and not self._store_on_disk:
            QtGui.QMessageBox(
                QtGui.QMessageBox.Warning,
                "Cannot submit to ShotGrid",
                "Application is not configured to store images on disk or upload to shotgun!",
                flags=QtCore.Qt.Dialog
                | QtCore.Qt.MSWindowsFixedSizeDialogHint
                | QtCore.Qt.WindowStaysOnTopHint
                | QtCore.Qt.X11BypassWindowManagerHint,
            ).exec_()

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
        :param str thumbnail_path: Path to the thumbnail representing the version.
        :param list(dict) sg_publishes: Published files that have to be linked to the version.
        :param dict sg_task: Task that have to be linked to the version.
        :param str description: Description of the version.
        :param int first_frame: Version first frame.
        :param int last_frame: Version last frame.

        :returns:               The Version Shotgun entity dictionary that was created.
        :rtype:                 dict
        """

        # get current shotgun user
        current_user = sgtk.util.get_current_user(self.__app.sgtk)

        # create a name for the version based on the file name
        # grab the file name, strip off extension
        name = os.path.splitext(os.path.basename(path_to_movie))[0]
        # do some replacements
        name = name.replace("_", " ")
        # and capitalize
        name = name.capitalize()

        # Create the version in Shotgun
        ctx = self.__app.context
        data = {
            "code": name,
            "sg_status_list": self.__app.get_setting("new_version_status"),
            "entity": ctx.entity,
            "sg_task": sg_task,
            "sg_first_frame": first_frame,
            "sg_last_frame": last_frame,
            "sg_frames_have_slate": False,
            "created_by": current_user,
            "user": current_user,
            "description": description,
            "sg_path_to_frames": path_to_frames,
            "sg_movie_has_slate": True,
            "project": ctx.project,
        }

        if first_frame and last_frame:
            data["frame_count"] = last_frame - first_frame + 1
            data["frame_range"] = "%s-%s" % (first_frame, last_frame)

        if sgtk.util.get_published_file_entity_type(self.__app.sgtk) == "PublishedFile":
            data["published_files"] = sg_publishes
        else:  # == "TankPublishedFile"
            if len(sg_publishes) > 0:
                if len(sg_publishes) > 1:
                    self.__app.log_warning(
                        "Only the first publish of %d can be registered for the new version!"
                        % len(sg_publishes)
                    )
                data["tank_published_file"] = sg_publishes[0]

        if self._store_on_disk:
            data["sg_path_to_movie"] = path_to_movie

        sg_version = self.__app.sgtk.shotgun.create("Version", data)
        self.__app.log_debug("Created version in shotgun: %s" % str(data))

        # upload files:
        self._upload_files(sg_version, path_to_movie, thumbnail_path)

        # Remove from filesystem if required
        if not self._store_on_disk and os.path.exists(path_to_movie):
            os.unlink(path_to_movie)

        return sg_version

    def _upload_files(self, sg_version, output_path, thumbnail_path):
        """
        Upload the required files to Shotgun.

        :param dict sg_version:      Version to which uploaded files should be linked.
        :param str output_path:     Media to upload to Shotgun.
        :param str thumbnail_path:  Thumbnail to upload to Shotgun.
        """
        # Upload in a new thread and make our own event loop to wait for the
        # thread to finish.
        event_loop = QtCore.QEventLoop()
        thread = UploaderThread(
            self.__app, sg_version, output_path, thumbnail_path, self._upload_to_shotgun
        )
        thread.finished.connect(event_loop.quit)
        thread.start()
        event_loop.exec_()

        # log any errors generated in the thread
        for e in thread.get_errors():
            self.__app.log_error(e)


class UploaderThread(QtCore.QThread):
    """
    Simple worker thread that encapsulates uploading to shotgun.
    Broken out of the main loop so that the UI can remain responsive
    even though an upload is happening.
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
        Returns the errors collected while uploading files to Shotgun.

        :returns:   List of errors
        :rtype:     [str]
        """
        return self._errors

    def run(self):
        """
        This function implements what get executed in the UploaderThread.
        """
        upload_error = False

        if self._upload_to_shotgun:
            try:
                self._app.sgtk.shotgun.upload(
                    "Version",
                    self._version["id"],
                    self._path_to_movie,
                    "sg_uploaded_movie",
                )
            except Exception as e:
                self._errors.append("Movie upload to SG failed: %s" % e)
                upload_error = True

        if not self._upload_to_shotgun or upload_error:
            try:
                self._app.sgtk.shotgun.upload_thumbnail(
                    "Version", self._version["id"], self._thumbnail_path
                )
            except Exception as e:
                self._errors.append("Thumbnail upload to SG failed: %s" % e)
