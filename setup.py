#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" MComix installation routines.

Example usage:
    Normal installation (all files are copied into a directory in python/lib/site-packages/mcomix)
    $ ./setup.py install

    For distribution packaging (All files are installed relative to /tmp/mcomix)
    $ ./setup.py install --single-version-externally-managed --root /tmp/mcomix --prefix /usr
"""

import setuptools

from mcomix import constants


setuptools.setup(
    name = constants.APPNAME.lower(),
    version = constants.VERSION,
    packages = ['mcomix', 'mcomix.archive', 'mcomix.library'],
    include_package_data=True,
    entry_points = {
        'console_scripts' : [ 'mcomix = mcomix.run:run' ],
        'setuptools.installation': [ 'eggsecutable=mcomix.run:run' ],
    },
    test_suite = "test",
    install_requires = ['PyGObject (>=3.36.0)', 'PyCairo (>= 1.16.0)', 'Pillow (>=6.0.0)'],
    zip_safe = False,

    # Various MIME files that need to be copied to certain system locations on Linux.
    # Note that these files are only installed correctly if
    # --single-version-externally-managed is used as argument to "setup.py install".
    # Otherwise, these files end up in a MComix egg directory in site-packages.
    # (Thank you, setuptools!)
    data_files = [
        ('share/man/man1', ['mcomix.1.gz']),
        ('share/applications', ['mime/mcomix.desktop']),
        ('share/appdata', ['mime/mcomix.appdata.xml']),
        ('share/mime/packages', ['mime/mcomix.xml']),
        ('share/icons/hicolor/16x16/apps', ['mcomix/images/16x16/mcomix.png']),
        ('share/icons/hicolor/22x22/apps', ['mcomix/images/22x22/mcomix.png']),
        ('share/icons/hicolor/24x24/apps', ['mcomix/images/24x24/mcomix.png']),
        ('share/icons/hicolor/32x32/apps', ['mcomix/images/32x32/mcomix.png']),
        ('share/icons/hicolor/48x48/apps', ['mcomix/images/48x48/mcomix.png']),
        ('share/icons/hicolor/16x16/mimetypes',
            ['mime/icons/16x16/application-x-cbz.png',
             'mime/icons/16x16/application-x-cbr.png',
             'mime/icons/16x16/application-x-cbt.png']),
        ('share/icons/hicolor/22x22/mimetypes',
            ['mime/icons/22x22/application-x-cbz.png',
             'mime/icons/22x22/application-x-cbr.png',
             'mime/icons/22x22/application-x-cbt.png']),
        ('share/icons/hicolor/24x24/mimetypes',
            ['mime/icons/24x24/application-x-cbz.png',
             'mime/icons/24x24/application-x-cbr.png',
             'mime/icons/24x24/application-x-cbt.png']),
        ('share/icons/hicolor/32x32/mimetypes',
            ['mime/icons/32x32/application-x-cbz.png',
             'mime/icons/32x32/application-x-cbr.png',
             'mime/icons/32x32/application-x-cbt.png']),
        ('share/icons/hicolor/48x48/mimetypes',
            ['mime/icons/48x48/application-x-cbz.png',
             'mime/icons/48x48/application-x-cbr.png',
             'mime/icons/48x48/application-x-cbt.png'])],

    # Package metadata
    maintainer = 'The MComix Team',
    maintainer_email = 'https://sourceforge.net/projects/mcomix/',
    url = 'http://mcomix.sourceforge.net',
    description = 'GTK comic book viewer',
    long_description = 'MComix is a user-friendly, customizable image viewer. '
        'It is specifically designed to handle comic books (both Western comics and manga) '
        'and supports a variety of container formats (including CBR, CBZ, CB7, CBT, LHA and PDF). '
        'MComix is a fork of Comix.',
    license = "License :: OSI Approved :: GNU General Public License (GPL)",
    download_url = "http://sourceforge.net/projects/mcomix/files",
    platforms = ['Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: BSD'],
)

# vim: expandtab:sw=4:ts=4
