"""Canvas text must render when fonts live below a non-ASCII path.

freetype-py passes UTF-8 bytes to FreeType's narrow fopen on Windows, so a VisPy font below
for example ``C:\\Users\\Şükrü\\AppData\\Local\\Programs\\MikroCAM`` failed with
"cannot open resource" and the first axis-label draw crashed the application.
"""
from pathlib import Path
import shutil
import sys

import pytest


@pytest.mark.skipif(sys.platform != 'win32', reason='narrow fopen path encoding is Windows-specific')
def test_freetype_face_loads_from_non_ascii_directory(tmp_path):
    import freetype
    import vispy.util.fonts as fonts
    from appGUI import VisPyPatches
    source = Path(fonts.__file__).parent / 'data' / 'OpenSans-Regular.ttf'
    target = tmp_path / 'Kullanıcı Şükrü ğ' / 'OpenSans-Regular.ttf'
    target.parent.mkdir()
    shutil.copyfile(source, target)
    VisPyPatches.apply_patches()
    face = freetype.Face(str(target))
    face.set_char_size(12 * 64)
    face.load_char('M')
    assert face.glyph.bitmap.width > 0
