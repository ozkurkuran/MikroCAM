"""Conservative manufacturing proposals from bounded source facts and filenames."""
from hashlib import sha256
import re

from mikrocam.core.manufacturing_models import (
    MAX_MANUFACTURING_BYTES, ManufacturingEvidence, ManufacturingInspection,
)
from mikrocam.importers.gerber_statements import gerber_statements
from mikrocam.importers.manufacturing_lines import excellon_lines

_LAYER_MAX = 1000000
_MASKS = frozenset(('Soldermask', 'Legend', 'Carbonmask', 'Goldmask',
                   'Heatsinkmask', 'Peelablemask', 'Silvermask', 'Tinmask'))


def _layer(value: str) -> int:
    if re.fullmatch(r'[1-9][0-9]{0,6}', value) is None or int(value) > _LAYER_MAX:
        raise ValueError('FileFunction layer requires a positive bounded integer')
    return int(value)


def _role(value: str) -> str:
    fields = value.split(',')
    kind = fields[0]
    if kind == 'Copper' and len(fields) in (3, 4):
        layer = _layer(fields[1].removeprefix('L')) if fields[1].startswith('L') else 0
        side = fields[2]
        if (side not in ('Top', 'Bot', 'Inr') or layer == 0
                or (side == 'Top') != (layer == 1)
                or len(fields) == 4 and fields[3] not in ('Plane', 'Signal', 'Mixed', 'Hatched')):
            raise ValueError('Invalid copper layer, side or type')
        return {'Top': 'F.Cu', 'Bot': 'B.Cu', 'Inr': 'Other'}[side]
    if kind == 'Profile' and len(fields) == 2 and fields[1] in ('P', 'NP'):
        return 'Edge.Cuts'
    if kind in ('Plated', 'NonPlated') and len(fields) in (4, 5):
        start, end = _layer(fields[1]), _layer(fields[2])
        through = 'PTH' if kind == 'Plated' else 'NPTH'
        if (start == end or fields[3] not in (through, 'Blind', 'Buried')
                or len(fields) == 5 and fields[4] not in ('Drill', 'Rout', 'Mixed')):
            raise ValueError('Invalid drill layer span, plating or label')
        return through if fields[3] == through else 'Other'
    if kind in _MASKS and len(fields) in (2, 3) and fields[1] in ('Top', 'Bot'):
        if len(fields) == 3:
            _layer(fields[2])
        return 'Other'
    if kind == 'Other' and len(fields) == 2 and fields[1].strip():
        return 'Other'
    raise ValueError('Unrecognized or malformed FileFunction')


def _add(evidence: list, item: ManufacturingEvidence) -> None:
    if item not in evidence:
        if len(evidence) >= 32:
            raise ValueError('Manufacturing evidence exceeds the 32-item limit')
        evidence.append(item)


def _issue(issues: list, text: str) -> None:
    if text not in issues:
        if len(issues) >= 20:
            raise ValueError('Manufacturing issues exceed the 20-item limit')
        issues.append(text)


def _metadata(body: str, kind: str, evidence: list, issues: list) -> bool:
    if not body.lower().startswith('tf.filefunction'):
        return False
    if len(body.encode('utf-8')) > 512:
        _issue(issues, 'FileFunction metadata exceeds the 512-byte detail limit; role is unresolved.')
        return True
    try:
        if not body.startswith('TF.FileFunction,'):
            raise ValueError('FileFunction requires exact standard spelling and fields')
        role = _role(body[len('TF.FileFunction,'):])
    except ValueError:
        _add(evidence, ManufacturingEvidence('metadata', kind, detail=body or 'Empty FileFunction'))
        _issue(issues, 'Unrecognized or malformed FileFunction metadata; role is unresolved.')
        return True
    _add(evidence, ManufacturingEvidence('metadata', kind, role, detail=body))
    return False


def _filename(name: str, evidence: list) -> None:
    lower = name.replace('\\', '/').rsplit('/', 1)[-1].lower()
    extension = lower.rsplit('.', 1)[-1] if '.' in lower else ''
    formats = {'gbr': 'gerber', 'ger': 'gerber', 'gerber': 'gerber',
               'gtl': 'gerber', 'gbl': 'gerber', 'gko': 'gerber',
               'drl': 'excellon', 'xln': 'excellon', 'exc': 'excellon'}
    kind = formats.get(extension, 'unknown')
    if kind != 'unknown':
        _add(evidence, ManufacturingEvidence('filename', kind, detail=f'Filename extension .{extension}'))
    roles = [('f[_.]cu', 'F.Cu'), ('b[_.]cu', 'B.Cu'),
             ('edge[_.]cuts', 'Edge.Cuts'), ('npth', 'NPTH'), ('pth', 'PTH')]
    for pattern, role in roles:
        if re.search(r'(?<![^\W_])' + pattern + r'(?![^\W_])', lower):
            _add(evidence, ManufacturingEvidence('filename', role_hint=role,
                                                detail=f'Filename token for {role}: {name}'))
    if extension in ('gtl', 'gbl', 'gko'):
        role = {'gtl': 'F.Cu', 'gbl': 'B.Cu', 'gko': 'Edge.Cuts'}[extension]
        _add(evidence, ManufacturingEvidence('filename', role_hint=role,
                                            detail=f'Filename extension .{extension} indicates {role}'))


def _excellon(text: str, evidence: list, issues: list) -> bool:
    invalid = False
    # A multiline Gerber comment or AM body may contain example drill headers.
    # Exclude complete Gerber scopes before considering physical Excellon lines.
    text = re.sub(r'%(?:FS|MO|AD|AM|TF|TA|TO|TD|LP|IP|OF|SF|AS|MI|SR|LM|LR|LS)[^%]*%', '\n', text)
    text = re.sub(r'(?m)(?:^|(?<=[*%]))\s*G0?4\b[^*]*\*', '\n', text)
    lines = excellon_lines(text.encode('latin1')) if text else ()
    for line in lines:
        line = line.strip()
        if line.startswith(';'):
            match = re.match(r';\s*#@!\s*%?(.*)', line)
            if match:
                invalid |= _metadata(match[1].removesuffix('%').removesuffix('*'),
                                     'unknown', evidence, issues)
            continue
        if line == 'M48' or re.fullmatch(r'T[0-9]+C[0-9]+(?:\.[0-9]+)?', line):
            _add(evidence, ManufacturingEvidence('contents', 'excellon',
                                                detail='Excellon M48 or tool definition header'))
        unit = None
        if re.fullmatch(r'METRIC(?:,[A-Z0-9.,]+)?', line) or line == 'M71':
            unit = 'MM'
        elif re.fullmatch(r'INCH(?:,[A-Z0-9.,]+)?', line) or line == 'M72':
            unit = 'IN'
        if unit:
            kind = 'excellon' if line.startswith(('METRIC', 'INCH')) else 'unknown'
            _add(evidence, ManufacturingEvidence('contents', kind, units_hint=unit,
                                                detail=f'Excellon {line} unit marker'))
    return invalid


def _gerber(data: bytes, text: str, evidence: list, issues: list) -> tuple[bool, bool]:
    # Ignore ordinary comments in the rough gate. The shared lexer then supplies
    # complete commands, preserving real attributes and whole aperture macros.
    uncommented = re.sub(r'(?m)^\s*;[^\r\n]*', '', text)
    uncommented = re.sub(r'G0?4\b[^*]*\*', '', uncommented)
    candidate = (re.search(r'%(?:FS|MO|AD|TF\.FileFunction)', uncommented)
                 or re.search(r'%TF\.FileFunction', uncommented, re.IGNORECASE)
                 or re.search(r'(?<![A-Z0-9])G7[01]\s*\*', uncommented)
                 or re.search(r'G0?4\s*#@!\s*%?TF\.FileFunction', text, re.IGNORECASE))
    if not candidate:
        return False, False
    try:
        commands = gerber_statements(data, retain_attributes=True)
    except ValueError:
        _issue(issues, 'Malformed Gerber command boundaries; format and role are unresolved.')
        return True, True
    invalid_role = False
    for command in commands:
        if command.startswith(('G04', 'G4 ')):
            match = re.match(r'G0?4\s*#@!\s*%?(.*)\*$', command)
            if match:
                invalid_role |= _metadata(match[1], 'gerber', evidence, issues)
            continue
        body = command[1:-2] if command.startswith('%') else command[:-1]
        if command.startswith('%'):
            invalid_role |= _metadata(body, 'gerber', evidence, issues)
        if (re.fullmatch(r'FS[LT]?[AI]?X[0-9]{2}Y[0-9]{2}', body)
                or re.fullmatch(r'ADD[1-9][0-9]*[A-Za-z_][A-Za-z_0-9]*(?:,[^*]*)?', body)):
            _add(evidence, ManufacturingEvidence('contents', 'gerber', detail='Gerber FS or aperture definition command'))
        unit = {'MOMM': 'MM', 'MOIN': 'IN', 'G71': 'MM', 'G70': 'IN'}.get(body)
        if unit:
            _add(evidence, ManufacturingEvidence('contents', 'gerber', units_hint=unit,
                                                detail=f'Gerber {body} unit command'))
    return invalid_role, False


def _proposal(evidence: list, field: str, issues: list) -> str:
    hints = {getattr(item, field) for item in evidence} - {'unknown'}
    if len(hints) > 1:
        _issue(issues, f'Conflicting {field.replace("_hint", "")} evidence; proposal is unresolved.')
    return next(iter(hints)) if len(hints) == 1 else 'unknown'


def inspect_manufacturing_bytes(data: bytes, name: str) -> ManufacturingInspection:
    """Inspect exact immutable bytes without parsing geometry or changing units."""
    if type(data) is not bytes or not 1 <= len(data) <= MAX_MANUFACTURING_BYTES:
        raise ValueError('Manufacturing source requires bounded nonempty immutable bytes')
    if type(name) is not str or not name or len(name.encode('utf-8')) > 256:
        raise ValueError('Manufacturing source name requires 1..256 UTF8 bytes')
    text = data.removeprefix(b'\xef\xbb\xbf').decode('latin1')
    evidence, issues = [], []
    _filename(name, evidence)
    invalid_role = _excellon(text, evidence, issues)
    invalid_gerber_role, malformed = _gerber(data, text, evidence, issues)
    kind = _proposal(evidence, 'format_hint', issues)
    role = _proposal(evidence, 'role_hint', issues)
    units = _proposal(evidence, 'units_hint', issues)
    if invalid_role or invalid_gerber_role or malformed:
        role = 'unknown'
    if malformed:
        kind = 'unknown'
    if units == 'unknown':
        _issue(issues, 'Units are missing or conflicting; the parser will make a unit assumption.')
    return ManufacturingInspection(name, sha256(data).hexdigest(), len(data), kind,
                                   role, units, tuple(evidence), tuple(issues))
