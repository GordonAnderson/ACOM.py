# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['ACOM.py'],
             pathex=['/Users/gordonanderson/GAACE/PyCharmProjects/ACOM'],
             binaries=[('/Library/Frameworks/Python.framework/Versions/3.7/lib/libtcl8.6.dylib', 'tcl'), ('/Library/Frameworks/Python.framework/Versions/3.7/lib/libtk8.6.dylib', 'tk')],
             datas=[],
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
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='ACOM',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None , icon='ACOM.ico')
app = BUNDLE(exe,
             name='ACOM.app',
             icon='ACOM.ico',
             bundle_identifier='ACOM')
