# Copyright (C) 2017-2018 DLR
#
# All rights reserved. This program and the accompanying materials are made
# available under the terms of the Eclipse Public License v1.0 which
# accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
#
# Contributors:
# Franz Steinmetz <franz.steinmetz@dlr.de>
# Sebastian Brunner <sebastian.brunner@dlr.de>

import os
from os import path
import sys
from imp import load_source
import shutil
import subprocess
import distutils.log
from distutils.dir_util import copy_tree

try:
    from rafcon.utils import resources
except ImportError:
    script_path = path.realpath(__file__)
    resources_script_path = path.join(path.dirname(script_path), "resources.py")
    resources = load_source("resources", resources_script_path)


def started_without_installation():
    import rafcon
    pt_file_path = join(dirname(dirname(dirname(abspath(rafcon.__file__)))), "rafcon.pt")
    if isfile(pt_file_path):
        return True

def install_fonts(logger=None, restart=False):
    if logger:
        log = logger
    else:
        log = distutils.log
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    except (ImportError, ValueError):
        log.warn("No GTK found. Will not install fonts.")
        return

    font_names_to_be_installed = ["Source Sans Pro", "FontAwesome"]

    try:
        tv = Gtk.TextView()
        context = tv.get_pango_context()
    except Exception as e:
        log.error("Could not get pango context. Will not install fonts: {}".format(e))
        return
    if not context:  # A Pango context is not always available
        log.warn("Could not get pango context. Will not install fonts.")
        return
    existing_fonts = context.list_families()
    existing_font_faces = {font.get_name(): [face.get_face_name() for face in font.list_faces()]
                           for font in existing_fonts
                           if font.get_name() in font_names_to_be_installed}

    user_otf_fonts_folder = os.path.join(os.path.expanduser('~'), '.fonts')

    font_installed = False
    try:
        for font_name in font_names_to_be_installed:
            # A font is a folder one or more font faces
            fonts_folder = resources.get_data_file_path("rafcon", "gui", "fonts", font_name)
            # fonts_folder = os.path.join(assets_path, "fonts", font_name)
            num_faces_to_be_installed = len([name for name in os.listdir(fonts_folder) if name.endswith(".otf")])
            num_faces_installed = 0
            # default case: font is not installed yet!
            if font_name in existing_font_faces.keys():
                num_faces_installed = len(existing_font_faces[font_name])

            if num_faces_to_be_installed <= num_faces_installed:
                log.debug("Font '{0}' already installed".format(font_name))
                continue

            specific_user_otf_fonts_folder = user_otf_fonts_folder
            if num_faces_to_be_installed > 1:
                specific_user_otf_fonts_folder = os.path.join(user_otf_fonts_folder, font_name)

            log.info("Installing font '{0}' to {1}".format(font_name, specific_user_otf_fonts_folder))
            if not os.path.isdir(specific_user_otf_fonts_folder):
                os.makedirs(specific_user_otf_fonts_folder)
            for font_face in os.listdir(fonts_folder):
                target_font_file = os.path.join(specific_user_otf_fonts_folder, font_face)
                source_font_file = os.path.join(fonts_folder, font_face)
                shutil.copy(source_font_file, target_font_file)
            font_installed = True
    except IOError as e:
        log.error("Could not install fonts, IOError: {}".format(e))
        return

    if font_installed:
        log.info("Running font detection ...")
        fail = subprocess.call(['fc-cache', '-fv', user_otf_fonts_folder])
        if fail:
            log.warn("Could not run font detection. RAFCON might not find the correct fonts.")
        if restart:
            log.info("Restarting RAFCON to apply new fonts...")
            python = sys.executable
            environ = dict(**os.environ)
            # Passing this to the new RAFCON environment will prevent further checks and thus restarts
            environ["RAFCON_CHECK_INSTALLATION"] = "False"
            args_and_env = list(sys.argv)
            args_and_env.append(environ)
            os.execle(python, python, *args_and_env)


def install_locally_required_files():
    local_user_data_folder = resources.installation_share_folder
    source_share_folder = resources.get_relative_share_path()

    for folder in ["gtksourceview-3.0", "icons"]:
        try:
            logger.info("Copying '{}' files...".format(folder))
            copy_tree(join(source_share_folder, folder), join(local_user_data_folder, folder), update=1)
        except IOError as e:
            logger.error("Could not copy '{}' files: {}".format(folder, str(e)))


def create_mo_files():
    data_files = []
    domain = "rafcon"
    assert "setup.py" in os.listdir(os.curdir)
    rel_localedir = path.join('share', 'rafcon', 'locale')
    localedir = os.path.join(os.curdir, rel_localedir)
    # Assert that we are in the root directory of the RAFCON repository
    po_files = [po_file
                for po_file in next(os.walk(localedir))[2]
                if path.splitext(po_file)[1] == '.po']
    for po_file in po_files:
        po_path = path.join(localedir, po_file)
        lang, extension = path.splitext(po_file)
        mo_file = domain + '.mo'
        mo_dir = path.join(localedir, lang, 'LC_MESSAGES')
        mo_path = path.join(mo_dir, mo_file)
        mo_dir_rel = path.join(rel_localedir, lang, 'LC_MESSAGES')
        mo_path_rel = path.join(mo_dir_rel, mo_file)
        try:
            os.makedirs(mo_dir)
        except os.error:  # already exists
            pass
        msgfmt_cmd = 'msgfmt -o {} {}'.format(mo_path, po_path)
        result = subprocess.call(msgfmt_cmd, shell=True)
        if result != 0:  # Compilation successful
            distutils.log.warn("Could not compile translation '{}'. RAFCON will not be available in this "
                               "language.".format(lang))
