"""Firmware family/version identification and the immutable capability record (spec 042).

Formats come from the primary sources listed in specs/042-firmware-identification/research.md.
No firmware source code is copied. D2 (grblHAL, spec 043) and D3 (FluidNC) change only their family
entry in ``_PROFILES``, their budget in ``_streaming_budget`` and their own evidence gate; no separate
controller is added.
"""
from dataclasses import dataclass, replace
from enum import Enum
import re


MAX_EVIDENCE_LINES = 32
MAX_TEXT = 256
GRBL_STREAMING_CAP = 128


class FirmwareFamily(Enum):
    GRBL = 'grbl'
    GRBLHAL = 'grblhal'
    FLUIDNC = 'fluidnc'
    UNKNOWN = 'unknown'


class IdentificationPhase(Enum):
    NONE = 'none'
    PENDING = 'pending'
    IDENTIFIED = 'identified'
    FAILED = 'failed'


def _printable(text: object, label: str, limit: int = MAX_TEXT) -> None:
    if type(text) is not str or len(text) > limit or any(not 32 <= ord(c) <= 126 for c in text):
        raise ValueError(f'{label} must be printable ASCII text of at most {limit} characters')


def _count(value: object, label: str) -> None:
    if value is not None and (type(value) is not int or not 1 <= value <= 65535):
        raise ValueError(f'{label} must be None or an integer 1..65535')


@dataclass(frozen=True)
class FirmwareCapabilities:
    """What one controller reported about itself plus documented family facts."""
    family: FirmwareFamily = FirmwareFamily.UNKNOWN
    version: str = ''
    build: str = ''
    protocol: str = ''
    build_info: str = ''
    options: str = ''
    extended_options: tuple[str, ...] = ()
    planner_blocks: int | None = None
    rx_buffer_bytes: int | None = None
    streaming_rx_budget: int | None = None
    extra_states: tuple[str, ...] = ()
    realtime_commands: tuple[tuple[int, str], ...] = ()
    status_fields: tuple[str, ...] = ()
    motion_supported: bool = False
    note: str = ''

    def __post_init__(self) -> None:
        if type(self.family) is not FirmwareFamily:
            raise ValueError('Firmware family must be FirmwareFamily')
        for name in ('version', 'build', 'protocol', 'build_info', 'options', 'note'):
            _printable(getattr(self, name), name)
        for name in ('extended_options', 'extra_states', 'status_fields'):
            value = getattr(self, name)
            if type(value) is not tuple or len(value) > 64:
                raise ValueError(f'{name} must be a bounded tuple')
            for item in value:
                _printable(item, name, 64)
        if type(self.realtime_commands) is not tuple or any(
                type(item) is not tuple or len(item) != 2 or type(item[0]) is not int
                or not 0 <= item[0] <= 255 or type(item[1]) is not str for item in self.realtime_commands):
            raise ValueError('Realtime commands must be (byte, name) pairs')
        _count(self.planner_blocks, 'Planner blocks')
        _count(self.rx_buffer_bytes, 'RX buffer')
        _count(self.streaming_rx_budget, 'Streaming budget')
        if self.streaming_rx_budget is not None and (
                self.rx_buffer_bytes is None or self.streaming_rx_budget > self.rx_buffer_bytes):
            raise ValueError('A streaming budget requires a reported RX buffer at least as large')
        if type(self.motion_supported) is not bool:
            raise ValueError('Motion support must be boolean')
        if self.motion_supported and self.family is FirmwareFamily.UNKNOWN:
            raise ValueError('Unknown firmware can never support motion')


@dataclass(frozen=True)
class FirmwareObservation:
    """Session identification state published in MachineSnapshot.firmware."""
    phase: IdentificationPhase = IdentificationPhase.NONE
    capabilities: FirmwareCapabilities = FirmwareCapabilities()
    banner: str = ''
    evidence: tuple[str, ...] = ()
    diagnostic: str = ''

    def __post_init__(self) -> None:
        if type(self.phase) is not IdentificationPhase or type(self.capabilities) is not FirmwareCapabilities:
            raise ValueError('Firmware observation requires a phase and a capability record')
        _printable(self.banner, 'Banner')
        _printable(self.diagnostic, 'Firmware diagnostic')
        if type(self.evidence) is not tuple or len(self.evidence) > MAX_EVIDENCE_LINES:
            raise ValueError('Firmware evidence must be a tuple of at most 32 lines')
        for line in self.evidence:
            _printable(line, 'Firmware evidence line')
        unknown = self.capabilities.family is FirmwareFamily.UNKNOWN
        if (self.phase is IdentificationPhase.IDENTIFIED and unknown) or (
                self.phase is IdentificationPhase.FAILED and not unknown):
            raise ValueError('Identified firmware needs a known family; failure means unknown')

    @property
    def motion_allowed(self) -> bool:
        return self.phase is IdentificationPhase.IDENTIFIED and self.capabilities.motion_supported


_COMMON_REALTIME = ((0x18, 'reset'), (0x3F, 'status'), (0x7E, 'cycle-start'), (0x21, 'feed-hold'),
                    (0x84, 'safety-door'), (0x85, 'jog-cancel'))
_OVERRIDES = ((0x90, 'feed-override-reset'), (0x91, 'feed-override-coarse-plus'),
              (0x92, 'feed-override-coarse-minus'), (0x93, 'feed-override-fine-plus'),
              (0x94, 'feed-override-fine-minus'), (0x95, 'rapid-override-reset'),
              (0x96, 'rapid-override-medium'), (0x97, 'rapid-override-low'),
              (0x99, 'spindle-override-reset'), (0x9A, 'spindle-override-coarse-plus'),
              (0x9B, 'spindle-override-coarse-minus'), (0x9C, 'spindle-override-fine-plus'),
              (0x9D, 'spindle-override-fine-minus'), (0x9E, 'spindle-stop'),
              (0xA0, 'flood-toggle'), (0xA1, 'mist-toggle'))
_GRBLHAL_REALTIME = ((0x19, 'stop'), (0x80, 'status-top-bit'), (0x81, 'cycle-start-top-bit'),
                     (0x82, 'feed-hold-top-bit'), (0x83, 'gcode-report'), (0x87, 'full-status'),
                     (0x88, 'optional-stop-toggle'), (0x89, 'single-block-toggle'),
                     (0x8A, 'fan0-toggle'), (0x8B, 'mpg-mode-toggle'), (0x8C, 'auto-report-toggle'),
                     (0x98, 'rapid-override-extra-low'), (0x9F, 'soft-estop'), (0xA2, 'pid-report'),
                     (0xA3, 'tool-ack'), (0xA4, 'probe-connected-toggle'))
_FLUIDNC_REALTIME = ((0x87, 'macro-0'), (0x88, 'macro-1'), (0x89, 'macro-2'), (0x8A, 'macro-3'))
_GRBL_FIELDS = ('MPos', 'WPos', 'Bf', 'Ln', 'FS', 'F', 'Pn', 'WCO', 'Ov', 'A')
_PROFILES = {
    FirmwareFamily.GRBL: dict(
        realtime_commands=_COMMON_REALTIME + _OVERRIDES, status_fields=_GRBL_FIELDS,
        motion_supported=True),
    FirmwareFamily.GRBLHAL: dict(
        realtime_commands=_COMMON_REALTIME + _OVERRIDES + _GRBLHAL_REALTIME, extra_states=('Tool',),
        status_fields=_GRBL_FIELDS + ('WCS', 'MPG', 'H', 'D', 'Sc', 'TLR', 'FW', 'In', 'DTG', 'AR',
                                      'P', 'S', 'T'),
        motion_supported=True),
    FirmwareFamily.FLUIDNC: dict(
        realtime_commands=_COMMON_REALTIME + _OVERRIDES + _FLUIDNC_REALTIME, extra_states=('Starting',),
        status_fields=('MPos', 'WPos', 'Bf', 'Ln', 'FS', 'Pn', 'WCO', 'Ov', 'A', 'Heap', 'ISRs'),
        note='FluidNC identified; motion stays disabled until spec 044 (D3) validates its profile'),
    FirmwareFamily.UNKNOWN: dict(note='Firmware not identified; motion features are disabled'),
}


def capabilities_for(family: FirmwareFamily) -> FirmwareCapabilities:
    """Return the documented static profile of one family, without board evidence."""
    return FirmwareCapabilities(family=family, **_PROFILES[family])


def _streaming_budget(family: FirmwareFamily, rx: int | None) -> int | None:
    """A reported RX feeds C3, capped at its validated 128-byte window (043 UA-2); FluidNC awaits D3."""
    if family in (FirmwareFamily.GRBL, FirmwareFamily.GRBLHAL) and rx is not None:
        return min(rx, GRBL_STREAMING_CAP)
    return None


def _grblhal_motion_blocker(fields: list[str], tags: dict[str, str], extended: tuple[str, ...]) -> str:
    """Spec 043 FR-001: the 3-axis parsers and printable realtime bytes need this board evidence."""
    if len(fields) < 3 or fields[2] != '3':
        return 'grblHAL motion requires a reported axis count of 3 (XYZ)'
    if tags.get('AXS', '3:XYZ') != '3:XYZ':
        return 'grblHAL motion requires the XYZ axis set [AXS:3:XYZ]'
    if 'LATHE' in extended:
        return 'grblHAL lathe mode is not supported for motion'
    if 'RT+' not in extended:
        return 'grblHAL motion requires legacy realtime commands enabled (NEWOPT RT+)'
    return ''


_BANNER = re.compile(r'(Grbl|GrblHAL) ([0-9]+\.[0-9]+[a-z]?)(?: .*)?\Z')
_TAG = re.compile(r'\[([A-Za-z][A-Za-z ]{0,31}):([^\[\]]*)\]\Z')
_FLUID_VER = re.compile(r'([0-9]+\.[0-9]+) FluidNC v([0-9]+\.[0-9]+\.[0-9]+)(?: \([ -~]*\))? ?\Z')
_HAL_VER = re.compile(r'([0-9]+\.[0-9]+[a-z])\.([0-9]{8})\Z')
_GRBL_VER = re.compile(r'(1\.1[a-z]?)(?:\.([0-9]{8}))?\Z')
_GRBL_OPTIONS = re.compile(r'[VNMCPZHTAD0SRL+*$#IEW2]*\Z')
_TOKEN = re.compile(r'[0-9]+\.[0-9]+[a-z]?')


def is_reset_banner(line: str) -> bool:
    """GRBL/grblHAL/FluidNC (default) startup lines; grblHAL level 0 says ``GrblHAL``."""
    return isinstance(line, str) and line.startswith(('Grbl ', 'GrblHAL '))


def parse_banner(line: str) -> tuple[str, str] | None:
    match = _BANNER.match(line) if isinstance(line, str) else None
    return None if match is None else (match[1], match[2])


class _Unknown(ValueError):
    def __init__(self, message: str, version: str = '') -> None:
        super().__init__(message)
        self.version = version


def _tags(lines: tuple[str, ...]) -> dict[str, str]:
    if type(lines) is not tuple or len(lines) > MAX_EVIDENCE_LINES:
        raise _Unknown('Identification evidence is not a bounded tuple')
    tags: dict[str, str] = {}
    for line in lines:
        try:
            _printable(line, 'Evidence line')
        except ValueError as error:
            raise _Unknown(str(error)) from None
        match = _TAG.fullmatch(line)
        if match is None:
            raise _Unknown(f'Unrecognized build-info record {line[:40]}')
        if match[1] in tags:
            raise _Unknown(f'Duplicate [{match[1]}:] record')
        tags[match[1]] = match[2]
    return tags


def _numbers(fields: list[str], limit: int, version: str) -> list[int]:
    if any(re.fullmatch(r'[0-9]{1,5}', field) is None for field in fields):
        raise _Unknown('OPT buffer values must be decimal integers', version)
    values = [int(field) for field in fields]
    if any(not 1 <= value <= 65535 for value in values):
        raise _Unknown('OPT buffer values must be 1..65535', version)
    if any(value > limit for value in values):
        raise _Unknown('OPT values exceed GRBL 1.1 uint8 limit 255; possibly grblHAL compatibility mode', version)
    return values


def identify(banner: str, lines: tuple[str, ...]) -> FirmwareCapabilities:
    """Classify read-only evidence; anything contradictory or unsupported becomes UNKNOWN."""
    try:
        return _classify(banner if isinstance(banner, str) else '', lines)
    except _Unknown as reason:
        return replace(capabilities_for(FirmwareFamily.UNKNOWN), version=reason.version,
                       note=str(reason)[:MAX_TEXT])


def _classify(banner: str, lines: tuple[str, ...]) -> FirmwareCapabilities:
    tags = _tags(lines)
    if 'VER' not in tags:
        raise _Unknown('$I reply has no [VER:] record')
    head, separator, info = tags['VER'].partition(':')
    if not separator:
        raise _Unknown('Malformed [VER:] record')
    token = _TOKEN.match(head)
    version = token[0] if token else ''
    greeting = parse_banner(banner) if banner else None
    fluid = _FLUID_VER.fullmatch(head)
    if fluid:
        return _fluidnc(fluid, info, tags, greeting)
    if 'FIRMWARE' in tags or (greeting and greeting[0] == 'GrblHAL'):
        return _grblhal(head, info, tags, greeting, version)
    return _grbl(head, info, tags, banner, version)


def _fluidnc(fluid: re.Match, info: str, tags: dict[str, str], greeting) -> FirmwareCapabilities:
    protocol, release = fluid[1], fluid[2]
    if release.rpartition('.')[0] != protocol:
        raise _Unknown('FluidNC protocol and release versions disagree', release)
    if 'FIRMWARE' in tags or (greeting is not None and greeting != ('Grbl', protocol)):
        raise _Unknown('FluidNC build info contradicts the controller greeting', release)
    options = tags.get('OPT', '')
    if re.fullmatch(r'[A-Za-z]*', options) is None:
        raise _Unknown('FluidNC OPT record must contain option letters only', release)
    return replace(capabilities_for(FirmwareFamily.FLUIDNC), version=release, protocol=protocol,
                   build_info=info, options=options)


def _grblhal(head: str, info: str, tags: dict[str, str], greeting, version: str) -> FirmwareCapabilities:
    if tags.get('FIRMWARE', 'grblHAL') != 'grblHAL':
        raise _Unknown('Unsupported [FIRMWARE:] identity', version)
    match = _HAL_VER.fullmatch(head)
    if match is None or 'OPT' not in tags:
        raise _Unknown('grblHAL build info requires <version>.<YYYYMMDD> and an OPT record', version)
    if greeting is not None and greeting[1] != match[1]:
        raise _Unknown('grblHAL build info contradicts the controller greeting', version)
    letters, *fields = tags['OPT'].split(',')
    if not 2 <= len(fields) <= 4 or re.fullmatch(r'[A-Za-z0-9+*$#]*', letters) is None:
        raise _Unknown('Malformed grblHAL OPT record', version)
    planner, rx = _numbers(fields[:2], 65535, version)
    if any(re.fullmatch(r'[0-9]{1,5}', field) is None for field in fields[2:]):
        raise _Unknown('Malformed grblHAL OPT axis/tool count', version)
    extended = tuple(item for item in tags.get('NEWOPT', '').split(',') if item)
    if any(re.fullmatch(r'[A-Za-z0-9=+-]{1,32}', item) is None for item in extended):
        raise _Unknown('Malformed grblHAL NEWOPT record', version)
    blocker = _grblhal_motion_blocker(fields, tags, extended)
    return replace(capabilities_for(FirmwareFamily.GRBLHAL), version=match[1], build=match[2],
                   protocol=match[1], build_info=info, options=letters, extended_options=extended,
                   planner_blocks=planner, rx_buffer_bytes=rx,
                   streaming_rx_budget=_streaming_budget(FirmwareFamily.GRBLHAL, rx),
                   motion_supported=not blocker, note=blocker)


def _grbl(head: str, info: str, tags: dict[str, str], banner: str, version: str) -> FirmwareCapabilities:
    match = _GRBL_VER.fullmatch(head)
    if match is None:
        raise _Unknown(f'Unsupported GRBL-like version {version or head[:16]}', version)
    if set(tags) - {'VER', 'OPT'}:
        raise _Unknown('Unexpected build-info record for GRBL 1.1', version)
    if banner and banner != f"Grbl {match[1]} ['$' for help]":
        raise _Unknown('GRBL build info contradicts the controller greeting', version)
    letters, planner, rx = '', None, None
    if 'OPT' in tags:
        letters, *fields = tags['OPT'].split(',')
        if len(fields) != 2 or _GRBL_OPTIONS.fullmatch(letters) is None:
            raise _Unknown('GRBL 1.1 OPT record must be <letters>,<blocks>,<rx>', version)
        planner, rx = _numbers(fields, 255, version)
    return replace(capabilities_for(FirmwareFamily.GRBL), version=match[1], build=match[2] or '',
                   protocol=match[1], build_info=info, options=letters, planner_blocks=planner,
                   rx_buffer_bytes=rx, streaming_rx_budget=_streaming_budget(FirmwareFamily.GRBL, rx))


def banner_consistent(capabilities: FirmwareCapabilities, banner: str) -> bool:
    """True when a reset greeting matches the identified firmware, so $I need not repeat."""
    greeting = parse_banner(banner)
    if greeting is None or type(capabilities) is not FirmwareCapabilities:
        return False
    family = capabilities.family
    if family is FirmwareFamily.GRBL:
        return banner == f"Grbl {capabilities.version} ['$' for help]"
    if family is FirmwareFamily.GRBLHAL:
        return greeting[1] == capabilities.version
    if family is FirmwareFamily.FLUIDNC:
        return greeting == ('Grbl', capabilities.protocol) and f'FluidNC v{capabilities.version}' in banner
    return False
