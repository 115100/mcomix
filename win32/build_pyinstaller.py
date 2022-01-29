#!/usr/bin/env python3
import os
import sys
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
    args = ['pyinstaller', 'win32/MComix.spec']
    proc_result = subprocess.run(args, shell=True)

    return proc_result.returncode

def win32_newline(source, dest):
    """ Converts Unix newlines to Windows newlines. """
    from_fp = open(source, "r", encoding='utf-8')

    dest_dir = os.path.split(dest)[0]
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
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
    win32_newline('COPYING', 'dist/MComix/licenses/mcomix/COPYING.txt')

    if os.path.isdir('../mcomix-other/unrar'):
        shutil.copy('../mcomix-other/unrar/UnRar64.dll', 'dist/MComix/UnRar64.dll')
        win32_newline('../mcomix-other/unrar/license.txt', 'dist/MComix/licenses/unrar/license.txt')

    if os.path.isdir('../mcomix-other/7z'):
        shutil.copy('../mcomix-other/7z/7z.dll', 'dist/MComix/7z.dll')
        shutil.copy('../mcomix-other/7z/7z.exe', 'dist/MComix/7z.exe')
        win32_newline('../mcomix-other/7z/License.txt', 'dist/MComix/licenses/unrar/License.txt')

    if os.path.isdir('../mcomix-other/mutool'):
        shutil.copy('../mcomix-other/mutool/mutool.exe', 'dist/MComix/mutool.exe')
        win32_newline('../mcomix-other/mutool/COPYING.txt', 'dist/MComix/licenses/mupdf/COPYING.txt')

    licenses_basedir = '/mingw64/share/licenses'
    components = ('atk', 'cairo', 'fontconfig', 'freetype', 'gdk-pixbuf2', 'glib2', 'gtk3', 'pango',
                  'python-cairo', 'python-Pillow')
    if os.path.isdir(licenses_basedir):
        for entry in components:
            path = os.path.join(licenses_basedir, entry)
            if os.path.isdir(path):
                shutil.copytree(path, os.path.join('dist/MComix/licenses', entry))

if __name__ == '__main__':
    clear_distdir('dist/MComix')

    success = run_pyinstaller() == 0

    if not success: sys.exit(1)

    copy_other_files()

# vim: expandtab:sw=4:ts=4
