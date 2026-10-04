# -*- mode: python -*-
# PyInstaller 6.22.3 spec for the MikroCAM Windows binary. Run through release/windows/build.py,
# which pins the interpreter/requirements, sanitizes PATH and validates the collected payload.
#
# One Analysis and one PYZ feed two executables: the shipped GUI MikroCAM.exe and the console
# MikroCAMSmoke.exe used only by the binary smoke test. Both therefore contain identical
# modules; build.py removes the smoke executable from the release payload.
import os
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

HERE = Path(SPECPATH).resolve()
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import release_layout as layout  # noqa: E402
from mikrocam.core import identity  # noqa: E402

VERSION_FILE = os.environ['MIKROCAM_VERSION_FILE']
ICON = str(ROOT / 'docs' / 'branding' / 'mikrocam.ico')

datas = [(str(ROOT / source), destination) for source, destination in layout.DATA_ENTRIES]
datas += [(str(path), path.parent.relative_to(ROOT).as_posix())
          for path in sorted((ROOT / 'mikrocam').rglob('*.json'))]
datas += collect_data_files('vispy')

hiddenimports = sorted(set(collect_submodules('tclCommands') + collect_submodules('mikrocam')
                           + collect_submodules('appPlugins')))

analysis = Analysis(
    [str(ROOT / 'flatcam.py'), str(HERE / 'frozen_smoke.py')],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(HERE / 'hooks')],
    excludes=list(layout.EXCLUDED_MODULES),
    # LGPL-3.0-or-later pure Python stays replaceable as plain source next to the executable.
    module_collection_mode={'svglib': 'py'},
    noarchive=False,
)
analysis.binaries = [entry for entry in analysis.binaries if not layout.is_excluded_destination(entry[0])]
analysis.datas = [entry for entry in analysis.datas if not layout.is_excluded_destination(entry[0])]

pyz = PYZ(analysis.pure)


def scripts_for(name):
    """Keep PyInstaller's bootstrap/runtime hooks and exactly one entry script."""
    entry = {'flatcam', 'frozen_smoke'}
    return [item for item in analysis.scripts if item[0] not in entry or item[0] == name]


app = EXE(pyz, scripts_for('flatcam'), [], exclude_binaries=True, name='MikroCAM', console=False,
          icon=ICON, version=VERSION_FILE, upx=False, disable_windowed_traceback=False)
smoke = EXE(pyz, scripts_for('frozen_smoke'), [], exclude_binaries=True, name='MikroCAMSmoke',
            console=True, icon=ICON, version=VERSION_FILE, upx=False)
COLLECT(app, smoke, analysis.binaries, analysis.datas, name=identity.NAME, upx=False)
