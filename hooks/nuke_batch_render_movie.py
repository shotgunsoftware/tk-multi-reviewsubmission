import ast
import os
import sys
import traceback
import getopt

from sgtk.context import Context

import nuke


def __create_scale_node(width, height):
    """
    Create the Nuke scale node to resize the content.
    """
    scale = nuke.nodes.Reformat()
    scale["type"].setValue("to box")
    scale["box_width"].setValue(width)
    scale["box_height"].setValue(height)
    scale["resize"].setValue("fit")
    scale["box_fixed"].setValue(True)
    scale["center"].setValue(True)
    scale["black_outside"].setValue(True)
    return scale


def __create_output_node(path, codec_settings, logger=None):
    """
    Create the Nuke output node for the movie.
    """
    # get the Write node settings we'll use for generating the Quicktime

    wn_settings = codec_settings.get('quicktime', {})

    node = nuke.nodes.Write(file_type=wn_settings.get("file_type", ''))

    # apply any additional knob settings provided by the hook. Now that the knob has been
    # created, we can be sure specific file_type settings will be valid.
    for knob_name, knob_value in wn_settings.iteritems():
        if knob_name != "file_type":
            node.knob(knob_name).setValue(knob_value)

    # Don't fail if we're in proxy mode. The default Nuke publish will fail if
    # you try and publish while in proxy mode. But in earlier versions of
    # tk-multi-publish (< v0.6.9) if there is no proxy template set, it falls
    # back on the full-res version and will succeed. This handles that case
    # and any custom cases where you may want to send your proxy render to
    # screening room.
    root_node = nuke.root()
    is_proxy = root_node['proxy'].value()
    if is_proxy:
        if logger:
            logger.info("Proxy mode is ON. Rendering proxy.")
        node["proxy"].setValue(path.replace(os.sep, "/"))
    else:
        node["file"].setValue(path.replace(os.sep, "/"))

    return node


def render_movie_in_nuke(path, output_path,
                         width, height,
                         first_frame, last_frame,
                         version, name,
                         color_space,
                         app_settings,
                         ctx, render_info,
                         is_subprocess=False):
    """
    Use Nuke to render a movie. This assumes we're running _inside_ Nuke.

    :param path:        Path to the input frames for the movie
    :param output_path: Path to the output movie that will be rendered
    :param width:       Width of the output movie
    :param height:      Height of the output movie
    :param first_frame: Start frame for the output movie
    :param last_frame:  End frame for the output movie
    :param version:     Version number to use for the output movie slate and burn-in
    :param name:        Name to use in the slate for the output movie
    :param color_space: Colorspace of the input frames
    """
    output_node = None
    root_node = nuke.root()

    if is_subprocess:
        # set Nuke root settings (since this is a subprocess with a fresh session)
        root_node["first_frame"].setValue(first_frame)
        root_node["last_frame"].setValue(last_frame)

    # create group where everything happens
    group = nuke.nodes.Group()

    # now operate inside this group
    group.begin()

    try:
        # create read node
        read = nuke.nodes.Read(name="source", file=path.replace(os.sep, "/"))
        read["on_error"].setValue("black")
        read["first"].setValue(first_frame)
        read["last"].setValue(last_frame)
        if color_space:
            read["colorspace"].setValue(color_space)

        if is_subprocess:
            # set root_format = res of read node
            read_format = read.format()
            read_format.add('READ_FORMAT')
            root_node.knob('format').setValue('READ_FORMAT')

        # now create the slate/burnin node
        burn = nuke.nodePaste(render_info.get('burnin_nk'))
        burn.setInput(0, read)

        font = render_info.get('slate_font')

        # set the fonts for all text fields
        # TODO: find by class instead of using node names
        burn.node("top_left_text")["font"].setValue(font)
        burn.node("top_right_text")["font"].setValue(font)
        burn.node("bottom_left_text")["font"].setValue(font)
        burn.node("framecounter")["font"].setValue(font)
        burn.node("slate_info")["font"].setValue(font)

        # add the logo
        logo = app_settings.get('slate_logo', '')
        if not os.path.isfile(logo):
            logo = ''

        burn.node("logo")["file"].setValue(logo)

        # format the burnins
        ver_num_pad = app_settings.get('version_number_padding', 4)
        version_padding_format = "%%0%dd" % ver_num_pad
        version_str = version_padding_format % version

        if ctx.task:
            version_label = "%s, v%s" % (ctx.task["name"], version_str)
        elif ctx.step:
            version_label = "%s, v%s" % (ctx.step["name"], version_str)
        else:
            version_label = "v%s" % version_str

        # TODO: use context names instead positional so that the nodes can be moved around
        burn.node("top_left_text")["message"].setValue(ctx.project["name"])
        burn.node("top_right_text")["message"].setValue(ctx.entity["name"])
        burn.node("bottom_left_text")["message"].setValue(version_label)

        # and the slate
        slate_str = "Project: %s\n" % ctx.project["name"]
        slate_str += "%s: %s\n" % (ctx.entity["type"], ctx.entity["name"])
        slate_str += "Name: %s\n" % name.capitalize()
        slate_str += "Version: %s\n" % version_str

        if ctx.task:
            slate_str += "Task: %s\n" % ctx.task["name"]
        elif ctx.step:
            slate_str += "Step: %s\n" % ctx.step["name"]

        slate_str += "Frames: %s - %s\n" % (first_frame, last_frame)

        burn.node("slate_info")["message"].setValue(slate_str)

        # Create a scale node
        scale = __create_scale_node(width, height)
        scale.setInput(0, burn)

        # Create the output node
        output_node = __create_output_node(output_path, render_info.get('codec_settings', {}))
        output_node.setInput(0, scale)
    finally:
        group.end()

    if output_node:
        # Make sure the output folder exists
        output_folder = os.path.dirname(output_path)
        # TODO: jsmk stuff?
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder)

        # Render the outputs, first view only
        nuke.executeMultiple([output_node], ([first_frame-1, last_frame, 1],),
                             [nuke.views()[0]])

    # Cleanup after ourselves
    nuke.delete(group)


def get_usage():
    return '''
  Usage: python {0} [ OPTIONS ]
         -h | --help ... print this usage message and exit.
         --path <FRAME_PATH> ... specify full path to frames, with frame spec ... e.g. ".%04d.exr"
         --output_path <OUTPUT_MOVIE_PATH> ... specify full path to output movie
         --width <WIDTH> ... specify width for output movie
         --height <HEIGHT> ... specify height for output movie
         --first_frame <FIRST_FRAME> ... specify first frame number of the input frames
         --last_frame <LAST_FRAME> ... specify last frame number of the input frames
         --version <VERSION> ... specify version number for the slate
         --name <NAME> ... specify name for the slate
         --color_space <COLOR_SPACE> ... specify color space to use for the movie generation
         --app_settings <APP_SETTINGS> ... specify app settings from the Toolkit app calling this
         --shotgun_context <SHOTGUN_CONTEXT> ... specify shotgun context from the Toolkit app calling this
         --render_info <RENDER_INFO> ... specify render info from the Toolkit app calling this
'''.format(os.path.basename(sys.argv[0]))


if __name__ == '__main__':
    # TODO: copied maquino's code. Refactor?
    data_keys = [
        'path', 'output_path', 'width', 'height', 'first_frame', 'last_frame',
        'version', 'name', 'color_space', 'app_settings', 'shotgun_context', 'render_info',
    ]

    non_str_data_list = {
        'width', 'height', 'first_frame', 'last_frame', 'version',
        'app_settings', 'shotgun_context', 'render_info',
    }

    short_opt_str = "h"
    long_opt_list = ['help'] + ['{0}='.format(k) for k in data_keys]

    input_data = {}
    try:
        opt_list, arg_list = getopt.getopt(sys.argv[1:], short_opt_str, long_opt_list)
    except getopt.GetoptError as err:
        sys.stderr.write(str(err))
        sys.stderr.write(get_usage())
        sys.exit(1)

    for opt, opt_value in opt_list:
        if opt in ('-h', '--help'):
            print get_usage()
            sys.exit(0)
        elif opt.replace('--', '') in data_keys:
            d_key = opt.replace('--', '')
            if d_key == 'shotgun_context':
                input_data[d_key] = Context.deserialize(opt_value)
            elif d_key in non_str_data_list:
                input_data[d_key] = ast.literal_eval('''{0}'''.format(opt_value))
            else:
                input_data[d_key] = opt_value

    for d_key in data_keys:
        if d_key not in input_data:
            sys.stderr.write('ERROR - missing input argument for "--{0}". Aborting'.format(d_key))
            sys.stderr.write(get_usage())
            sys.exit(2)

    render_movie_in_nuke(input_data['path'], input_data['output_path'],
                         input_data['width'], input_data['height'],
                         input_data['first_frame'], input_data['last_frame'],
                         input_data['version'], input_data['name'],
                         input_data['color_space'],
                         input_data['app_settings'],
                         input_data['shotgun_context'],
                         input_data['render_info'],
                         is_subprocess=True)
