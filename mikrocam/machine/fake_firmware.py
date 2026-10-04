"""Simulated greeting, $I replies and grblHAL report shapes for FakeGRBL profiles (spec 042/043).

Byte shapes follow the cited primary-source formats in specs/042-firmware-identification/research.md;
values (build dates, boards) are illustrative. The ``grbl`` profile keeps FakeGRBL's original bytes.
D2/D3 extend their own profile here (status/alarm/MSG behaviour) instead of adding a new simulator.
"""

PROFILES: dict[str, tuple[bytes, bytes]] = {
    'grbl': (b"Grbl 1.1h ['$' for help]\r\n",
             b'[VER:1.1h:FakeGRBL]\r\n[OPT:V,15,128]\r\nok\r\n'),
    'grblhal': (b"GrblHAL 1.1f ['$' or '$HELP' for help]\r\n",
                b'[VER:1.1f.20250101:]\r\n[OPT:VNMSL,35,1024,3,0]\r\n[AXS:3:XYZ]\r\n'
                b'[NEWOPT:ENUMS,RT+,HOME,SED]\r\n[FIRMWARE:grblHAL]\r\n[SIGNALS:XYZ]\r\n'
                b'[DRIVER:FakeHAL@168MHz]\r\n[BOARD:Fake board]\r\nok\r\n'),
    'fluidnc': (b"Grbl 3.9 [FluidNC v3.9.9 (fake-noradio) '$' for help]\r\n",
                b'[VER:3.9 FluidNC v3.9.9 (fake-noradio) :]\r\n[OPT:PHSEW]\r\n[CLUSTER:16]\r\n'
                b'[MSG: Machine: Fake FluidNC]\r\nok\r\n'),
    'unknown': (b"Grbl 0.9j ['$' for help]\r\n", b'[0.9j.20160316:]\r\nok\r\n'),
}


def profile(name: str) -> tuple[bytes, bytes]:
    if name not in PROFILES:
        raise ValueError('Unknown FakeGRBL firmware profile')
    return PROFILES[name]


# --- grblHAL dialect (spec 043): shapes from grblHAL/core c3a887e3, see 043 research R4-R7. ---
DEFAULT_PROFILE = 'grbl'
GRBLHAL_SETTINGS = '$10=511\r\n$300=grblHAL\r\n$341=0\r\n$396=N/A\r\n$481=0\r\n'


def grblhal_status(state: str, position: str, offset: str, first: bool) -> bytes:
    """Default-settings report: buffer state, feed/speed, WCO; overrides on the first report."""
    overrides = '|Ov:100,100,100' if first else ''
    return f'<{state}|MPos:{position}|Bf:35,1023|FS:0,0|WCO:{offset}{overrides}>\r\n'.encode('ascii')


def grblhal_modal(work_system: str, g92_active: bool, units: str, distance: str, tool_offset: bool,
                  program: str, spindle: str, coolant: tuple[str, ...], extra: tuple[str, ...]) -> bytes:
    """$G in grblHAL order with its additional G92/G40/G49/G98/G50 words (report.c:757-888)."""
    words = ['G0', work_system] + (['G92'] if g92_active else []) + ['G17', units, distance, 'G94',
             'G40', 'G43.1' if tool_offset else 'G49', 'G98', 'G50'] + ([program] if program else [])
    words += [spindle, *coolant, *extra, 'T0', 'F0', 'S0']
    return ('[GC:' + ' '.join(words) + ']\r\nok\r\n').encode('ascii')


def grblhal_parameters(rows: str, g92: str, tlo: str, zero: str) -> bytes:
    """$# with G59.1-3, G28/G30, vector TLO (TOOL_LENGTH_OFFSET_AXIS -1) and PRB (report.c:613-724)."""
    extra = ''.join(f'[{name}:{zero}]\r\n' for name in ('G59.1', 'G59.2', 'G59.3', 'G28', 'G30'))
    tail = f'[G92:{g92}]\r\n[TLO:{tlo}]\r\n[PRB:{zero}:0]\r\n'
    return (rows + extra + tail).encode('ascii') + b'ok\r\n'
