#!/usr/bin/env python3
import os
import sys
import glob
import zipfile
import shutil
import subprocess

""" Wrapper for pyinstaller, to compensate some shortcomings of the build process.

This file should be run from MComix' root directory, in order to avoid
having to play around with relative path names.

    Build instructions:

    0. To begin with, follow the installation instructions of PyGObject
       on Windows. At the time of this writing, using MSYS2 is recommended.
    1. Using the MSYS2 mingw64 shell, install mingw-w64-x86_64-gtk3,
       mingw-w64-x86_64-python3, mingw-w64-x86_64-python3-gobject,
       mingw-w64-x86_64-python3-pil, mingw-w64-x86_64-python3-pillow
    2. In the same shell, install pyinstaller with pip:
       python3 -m pip install --user pyinstaller
       Make sure that the installed pyinstaller executable is on PATH.
    3. 'win32/build_pyinstaller.py' will create the folder dist and copy relevant
       libraries.
    4. This script will copy images, translations and documentation
       into the created distribution folder.
"""

def list_files(basedir, *patterns):
    """ Locates all files in <basedir> that match one of <patterns>. """

    all_files = []
    for dirpath, _, _ in os.walk(basedir):

        for pattern in patterns:
            cur_pattern = os.path.join(dirpath, pattern)
            all_files.extend([ os.path.normpath(path) for path in glob.glob(cur_pattern) ])

    return all_files

def add_files_to_directory(directory, files):
    """ Add the files passed as <files> to <directory>, using the same
    relative path. """

    for file in files:
        destdir = os.path.split(os.path.join(directory, file))[0]
        if not os.path.isdir(destdir):
            os.makedirs(destdir)

        shutil.copy(file, os.path.join(directory, file))

def clear_distdir(distdir):
    """ Removes files from <distdir>. """
    if not os.path.isdir(distdir):
        return

    files = [os.path.join(distdir, file)
            for file in os.listdir(distdir)]

    print('Cleaning %s...' % distdir)
    for file in files:
        if os.path.isfile(file):
            os.unlink(file)
        elif os.path.isdir(file):
            shutil.rmtree(file)

def run_pyinstaller():
    """ Runs setup.py py2exe. """
    print('Executing pyinstaller...')
    proc_result = subprocess.run(
        ['pyinstaller', '--icon', 'mcomix/images/mcomix.ico', '--name', 'MComix', '--noconsole', 'mcomixstarter.py'],
        shell=True)

    return proc_result.returncode

def add_nonpython_data():
    """ Adds required data files the distribution. """

    library = zipfile.ZipFile('dist/MComix/base_library.zip', 'a')

    messages = list_files('mcomix/messages', '*.mo')
    print('Adding messages to distribution...')
    add_files_to_directory('dist/MComix', messages)

    images = list_files('mcomix/images', '*.png')
    to_remove = ('mcomix/images/mcomix-large.png', )

    for img in to_remove:
        fixed_path = os.path.normpath(img)
        if fixed_path in images:
            images.remove(fixed_path)

    print('Adding images to distribution...')
    add_files_to_directory('dist/MComix', images)

    library.close()

def win32_newline(source, dest):
    """ Converts Unix newlines to Windows newlines. """
    from_fp = open(source, "r", encoding='utf-8')
    to_fp = open(dest, "w", encoding='utf-8')

    for line in from_fp:
        to_fp.write(line.rstrip())
        to_fp.write("\r\n")

    from_fp.close()
    to_fp.close()

def copy_other_files():
    """ Copy other relevant files into dist directory. """
    print("Copying misc files into dist directory...")
    win32_newline('ChangeLog', 'dist/MComix/ChangeLog.txt')
    win32_newline('README', 'dist/MComix/README.txt')
    win32_newline('COPYING', 'dist/MComix/COPYING.txt')

    if os.path.isfile('unrar.dll'):
        shutil.copy('unrar.dll', 'dist/MComix/unrar.dll')

if __name__ == '__main__':
    clear_distdir('dist')

    success = run_pyinstaller() == 0

    if not success: sys.exit(1)

    add_nonpython_data()

    copy_other_files()

# vim: expandtab:sw=4:ts=4
