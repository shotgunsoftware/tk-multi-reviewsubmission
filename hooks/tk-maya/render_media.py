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
import maya
import os
import sys
import re
import json
import heapq

HookBaseClass = sgtk.get_hook_baseclass()

# Play with the regex here: https://regex101.com/r/S1ei8H/1
PLAYBLAST_ARG_RE = re.compile(r"^doPlayblastArgList.*(\{.*\});$")


class RenderMedia(HookBaseClass):
    """
    RenderMedia hook implementation for the tk-maya engine.
    """

    def render(
        self,
        input_path,
        output_path,
        width,
        height,
        first_frame,
        last_frame,
        version,
        name,
        color_space,
    ):
        """
        Render the media using the Maya Playblast API

        :param str input_path:      Path to the input frames for the movie      (Unused)
        :param str output_path:     Path to the output movie that will be rendered
        :param int width:           Width of the output movie                   (Unused)
        :param int height:          Height of the output movie                  (Unused)
        :param int first_frame:     The first frame of the sequence of frames.  (Unused)
        :param int last_frame:      The last frame of the sequence of frames.   (Unused)
        :param int version:         Version number to use for the output movie slate and burn-in
        :param str name:            Name to use in the slate for the output movie
        :param str color_space:     Colorspace of the input frames              (Unused)

        :returns:               Location of the rendered media
        :rtype:                 str
        """

        if name == "Unnamed":
            current_file_path = maya.cmds.file(query=True, sn=True)

            if current_file_path:
                name = os.path.basename(current_file_path)

        if not output_path:
            output_path = self._get_temp_media_path(name, version, "")

        playblast_args = self.get_default_playblastlast_args(output_path)

        self.logger.info(
            "Writing playblast to: %s using (%s)" % (output_path, playblast_args)
        )

        output_path = maya.cmds.playblast(**playblast_args)
        self.logger.info("Playblast maybe written to %s" % output_path)

        if os.path.exists(output_path):
            self.logger.info("Playblast written to %s" % output_path)
            return output_path

        # Now, we did a playblast and the file is not on disk
        # What's happening is that if you render a movie, Maya append the movie name to the file name
        # and if you render a file sequence, Maya append the sequence number and the extension to the file.
        # Now we need to find the file on disk given the prefix we provided to the playblast command.

        output_folder, output_file = os.path.split(playblast_args["filename"])

        files = []
        for f in os.listdir(output_folder):

            f_path = os.path.join(output_folder, f)
            if not f.startswith(output_file) or not os.path.isfile(f_path):
                continue

            try:
                # This method raise OSError if the file does not exist or is somehow inaccessible.
                m_time = os.path.getmtime(f_path)
            except OSError:
                continue
            else:
                # Insert with a negative access time so the first elment in the list is the most recent file
                heapq.heappush(files, (-m_time, f))

        if files:
            f = heapq.heappop(files)[1]

            output_path = os.path.join(output_folder, f)
            self.logger.info("Playblast written to %s" % output_path)
            return output_path

        raise RuntimeError(
            "Something went wrong with the playblast. Unable to find it on disk."
        )

    def get_default_playblastlast_args(self, output_path):
        """
        Build the playblast command arguments. This implementation grab the playblast arguments from Maya.

        For more informations about the playblast API,
        https://help.autodesk.com/view/MAYAUL/2020/ENU/?guid=__CommandsPython_playblast_html

        For more informations about the doPlayblastArgList mel function, look at the doPlayblastArgList.mel in the Autodesk Maya app bundle.

        :param str output_path:     Path to the output movie that will be rendered

        :returns:               Playblast arguments
        :rtype:                 dict

        """

        # This command returns something like "doPlayblastArgList 6 { } {  } { "0 ","movies/playblast","1","avfoundation","1","0.5","H.264","1","256","256","0","1","10","1","0","4","0","70","0"};"
        perform_playblast_output = maya.mel.eval("performPlayblast 2")
        self.logger.debug(
            "'mel.eval(performPlayblast 2)' output: " + perform_playblast_output
        )

        # And we only want to keep the last part of the string.. ({ "0 ","movies/playblast","1","avfoundation","1","0.5","H.264","1","256","256","0","1","10","1","0","4","0","70","0"})
        playblast_arg_match = PLAYBLAST_ARG_RE.match(perform_playblast_output)

        # If there's no match, there's nothing we can do...
        if not playblast_arg_match:
            raise RuntimeError("Failed to extract the playblast arguments.")

        # Store the value of the playblast args
        # We now have '{ "0 ","movies/playblast","1","avfoundation","1","0.5","H.264","1","256","256","0","1","10","1","0","4","0","70","0"}'
        playblast_arg_list_str = playblast_arg_match.group(1)

        # Remove the curly brackets arount the list and surround it with square brackets
        # We now have '[ "0 ","movies/playblast","1","avfoundation","1","0.5","H.264","1","256","256","0","1","10","1","0","4","0","70","0"]'
        playblast_arg_list_str = "[" + playblast_arg_list_str[1:-1] + "]"

        # Now that the argument list is a parsable JSON list, let's parse it.
        playblast_arg_list = json.loads(playblast_arg_list_str)

        playblast_args = {"filename": output_path, "forceOverwrite": True}
        try:
            # We don't need playblast_arg_list[0] because we want to save the file on disk
            # We don't need playblast_arg_list[1] because we provides the name of the movie

            # We don't need playblast_arg_list[2] because we do not need to show the viewer
            playblast_args["viewer"] = False

            # playblast_arg_list[3] is the playblast format to use
            playblast_args["format"] = playblast_arg_list[3]

            # playblast_arg_list[4] sets whether or not model view ornaments (e.g. the axis icon) should be displayed
            playblast_args["showOrnaments"] = playblast_arg_list[4] == "1"

            # playblast_arg_list[5] is the percentage of the current view to use during playblast
            playblast_args["percent"] = round(float(playblast_arg_list[5]) * 100)

            # playblast_arg_list[6] specify the compression to use for the movie file.
            playblast_args["compression"] = playblast_arg_list[6]

            # playblast_arg_list[7] is the displaySource
            # 1 : Use current view
            # 2 : Use Render Globals
            # 3 : Use values specified from option box
            if playblast_arg_list[7] == "1":
                pass  # Nothing to do, free pass !
            elif playblast_arg_list[7] == "2":
                # Grab the renderGlobals
                render_globals = maya.mel.eval("ls -type renderGlobals")
                if not render_globals:
                    raise RuntimeError("Unable to find renderGlobals in Maya")

                # List all the connected nodes
                connections = maya.mel.eval("listConnections %s" % render_globals[0])
                if not connections:
                    raise RuntimeError("Unable to list renderGlobals connections")

                # Grab the resolution node from the connections
                resolution_node = ""
                for connection in connections:
                    node_type = maya.mel.eval("nodeType %s" % connection)
                    if node_type == "resolution":
                        resolution_node = connection
                        break

                if not resolution_node:
                    raise RuntimeError("Unable to find a resolution node")

                # Collect the width and height from that node
                playblast_args["width"] = int(
                    maya.mel.eval("getAttr %s.width" % resolution_node)
                )
                playblast_args["height"] = int(
                    maya.mel.eval("getAttr %s.height" % resolution_node)
                )
            else:
                # Playblast setting is set to Custom, so let use the value provided
                # playblast_arg_list[8] is the display width
                playblast_args["width"] = int(playblast_arg_list[8])

                # playblast_arg_list[9] is the display height
                playblast_args["height"] = int(playblast_arg_list[9])

            # playblast_arg_list[10] is the flag telling to use the startTime and the endTime
            if playblast_arg_list[10] == "1":
                # playblast_arg_list[11] is the start time
                playblast_args["startTime"] = float(playblast_arg_list[11])

                # playblast_arg_list[12] is the end time
                playblast_args["endTime"] = float(playblast_arg_list[12])

            # playblast_arg_list[13] is the flag telling if we need to clean the unnamed cached playblasts
            playblast_args["clearCache"] = playblast_arg_list[13] == "1"

            # playblast_arg_list[14] is the flag telling if we should render offscreen
            playblast_args["offScreen"] = playblast_arg_list[14] == "1"

            # playblast_arg_list[15] is the number of zero to pad with
            playblast_args["framePadding"] = int(playblast_arg_list[15])

            # playblast_arg_list[16] is the flag telling to use the sequence time
            playblast_args["sequenceTime"] = playblast_arg_list[16] == "1"

            # playblast_arg_list[17] is the quality setting
            playblast_args["quality"] = int(playblast_arg_list[17])

            # playblast_arg_list[18] is the flag telling if we should output depth with image in 'iff' format
            playblast_args["saveDepth"] = playblast_arg_list[18] == "1"
        except IndexError:
            # If we run this function on an old version of Maya, we might end with an IndexError being raised
            # because the amount of arguments returned by "performPlayblast". Since we want to gracefully handle
            # the cases where the argument list is shorter and we access all argument in an incremental way, it's
            # ok to just catch the error and return the collected arguments.
            pass
        finally:
            return playblast_args
