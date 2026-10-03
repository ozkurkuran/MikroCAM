"""Resolve explicit SVG text fonts offline; never silently replace missing families."""
from importlib.util import find_spec
import os
from pathlib import Path
import re

GENERIC = {'sans-serif': 'DejaVu Sans', 'serif': 'DejaVu Serif', 'monospace': 'DejaVu Sans Mono',
           'cursive': 'DejaVu Sans', 'fantasy': 'DejaVu Sans'}


def _font_paths() -> list[Path]:
    roots = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts',
             Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft/Windows/Fonts',
             Path('/usr/share/fonts'), Path.home() / '.local/share/fonts']
    spec = find_spec('matplotlib')
    if spec is not None and spec.origin:
        roots.append(Path(spec.origin).parent / 'mpl-data/fonts/ttf')
    paths = []
    for root in roots:
        if root.is_dir():
            paths.extend(p for p in root.rglob('*') if p.suffix.lower() in ('.ttf', '.otf', '.ttc', '.otc'))
        if len(paths) > 5000: raise ValueError('FONT_MISSING: font inventory exceeds limit; convert text to paths')
    return sorted(set(paths))


def _font_inventory() -> dict:
    try: from fontTools.ttLib import TTFont, TTCollection, TTLibError
    except ImportError as error: raise ValueError('FONT_MISSING: fontTools unavailable; convert text to paths') from error
    families = {}
    for path in _font_paths():
        if path.stat().st_size > 32 * 1024 * 1024: continue
        try:
            collection = path.suffix.lower() in ('.ttc', '.otc')
            with (TTCollection(path, lazy=True) if collection else TTFont(path, lazy=True)) as opened:
                for font in (opened.fonts if collection else [opened]):
                    family = font['name'].getDebugName(16) or font['name'].getDebugName(1)
                    if family: families.setdefault(family.casefold(), []).append((str(path), frozenset(font.getBestCmap() or {})))
        except (OSError, TTLibError): continue
    return families


def svg_font_options(root: object) -> dict:
    text_nodes = [node for node in root.iter() if node.tag.rsplit('}', 1)[-1] in ('text', 'tspan', 'textPath')]
    if not text_nodes: return {'skip_system_fonts': True}
    declarations = []
    for node in root.iter():
        if 'font-family' in node.attrib: declarations.append(node.attrib['font-family'])
        css = node.attrib.get('style', '')
        if node.tag.rsplit('}', 1)[-1] == 'style': css += node.text or ''
        if re.search(r'(?<![\w-])font\s*:', css, re.I):
            raise ValueError('SVG_UNSUPPORTED_FEATURE: expand font shorthand or convert text to paths')
        declarations.extend(re.findall(r'font-family\s*:\s*([^;}]+)', css, re.I))
    inventory = _font_inventory()
    selected = set()
    glyphs = set()
    # Explicit default families are bundled in the already pinned matplotlib data.
    for declaration in (*declarations, *GENERIC.values()):
        declaration = re.sub(r'\s*!important\s*$', '', declaration, flags=re.I).strip()
        # The renderer resolves CSS-wide values through its cascade; parent/default
        # declarations are independently loaded here, without substituting a family.
        if declaration.casefold() in ('inherit', 'initial', 'unset', 'revert', 'revert-layer'): continue
        candidates = [value.strip().strip('"').strip("'") for value in declaration.split(',')]
        resolved = None
        for family in candidates:
            key = GENERIC.get(family.casefold(), family).casefold()
            if key in inventory:
                resolved = inventory[key]; break
        if resolved is None: raise ValueError('FONT_MISSING: ' + declaration + '; install font or convert text to paths')
        for filename, coverage in resolved:
            selected.add(filename); glyphs.update(coverage)
    characters = set(ord(char) for node in text_nodes for char in ''.join(node.itertext()) if not char.isspace())
    if not characters <= glyphs: raise ValueError('FONT_MISSING: missing glyphs; convert text to paths')
    return {'skip_system_fonts': True, 'font_files': sorted(selected), 'font_family': 'DejaVu Sans',
            'sans_serif_family': 'DejaVu Sans', 'serif_family': 'DejaVu Serif', 'monospace_family': 'DejaVu Sans Mono',
            'cursive_family': 'DejaVu Sans', 'fantasy_family': 'DejaVu Sans'}
