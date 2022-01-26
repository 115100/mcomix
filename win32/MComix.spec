# -*- mode: python ; coding: utf-8 -*-


import glob
import os

block_cipher = None


def list_files(basedir, *patterns):
    """ Locates all files in <basedir> that match one of <patterns>. """

    all_files = []
    for dirpath, _, _ in os.walk(basedir):

        for pattern in patterns:
            cur_pattern = os.path.join(dirpath, pattern)
            all_files.extend([ os.path.normpath(path)
                               for path in glob.glob(cur_pattern) ])

    return all_files


added_files = [(os.path.join('..', path),
                os.path.split(path)[0])
               for path in list_files('mcomix/messages', '*.mo')]
added_files.extend([(os.path.join('..', path),
                     os.path.split(path)[0])
                    for path in list_files('mcomix/images', '*.png')])


a = Analysis(['../mcomixstarter.py'],
             pathex=[],
             binaries=[],
             datas=added_files,
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='MComix',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='../mcomix/images/mcomix.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='MComix')
