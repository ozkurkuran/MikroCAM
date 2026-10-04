"""Simulated greeting and $I replies for FakeGRBL profiles (spec 042).

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
