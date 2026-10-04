"""FluidNC behaviour for the FakeGRBL ``fluidnc`` (v4.1.1) and ``fluidnc3`` (v3.9.9) profiles.

Byte shapes follow specs/044-fluidnc-serial/research.md (bdring/FluidNC v3.9.9 / v4.1.1); values
are illustrative. It is a protocol simulator, not a FluidNC/ESP32 timing emulator. FakeGRBL keeps
owning motion, jog, probe, realtime bytes, ``$G`` and ``$I``; this helper answers the commands whose
FluidNC replies differ from GRBL and simulates the ESP32 boot sequence.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .fake import FakeGRBL

ROM_LOG = (b'ets Jul 29 2019 12:21:46\r\n\r\nrst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)\r\n'
           b'configsip: 0, SPIWP:0xee\r\nclk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00\r\n'
           b'mode:DIO, clock div:1\r\nload:0x3fff0030,len:1184\r\nentry 0x400805e4\r\n')
_MACROS = ('startup_line0', 'startup_line1', 'after_reset')
_CONFIG = ('board: Fake board', 'name: Fake FluidNC', 'stepping:', '  engine: RMT', 'axes:', '  x:',
           '    steps_per_mm: 80.000000', '  y:', '    steps_per_mm: 80.000000', '  z:',
           '    steps_per_mm: 400.000000', 'PWM:', "  speed_map: '0=0.000% 1000=100.000%'", 'macros:',
           '  startup_line0: ', '  after_reset: ')


class FakeFluidNC:
    def __init__(self, host: 'FakeGRBL', version: str) -> None:
        self.host = host
        self.version = version
        self.macros = dict.fromkeys(_MACROS, '')
        self.report_interval = 0
        self.message_info = True  # $Message/Level >= Info
        self.max_spindle = 1000
        self.laser_mode = 0
        self.tlo_xy = (0., 0.)
        self.booting: str | None = None  # None, 'rom' (input lost) or 'starting'

    @property
    def v4(self) -> bool:
        return self.version.startswith('4')

    def respond(self, data: bytes) -> bool:
        """Answer FluidNC-specific commands; False leaves the command to FakeGRBL."""
        host = self.host
        if self.booting is not None:
            if data == b'?' and self.booting == 'starting':
                host.inject(host._status_report().replace(f'<{host.state}|'.encode(), b'<Starting|', 1))
            return True  # Lines are dropped by the ROM/boot and flushRx before the greeting.
        name = data.decode('ascii', 'replace').rstrip('\n')
        if data == b'$$\n':
            host.inject(self._settings() + b'ok\r\n')
        elif data == b'$N\n':  # Not a FluidNC command: a partial-name settings listing.
            host.inject(b'$Config/Filename=config.yaml\r\n$Grbl/HomingCycleEnable=0\r\nok\r\n')
        elif name.startswith('$/macros/') and name[9:] in self.macros:
            host.inject(f'{name}={self.macros[name[9:]]}\r\nok\r\n'.encode('ascii'))
        elif data == b'$RI\n':
            if self.message_info:
                state = (f'auto report interval is {self.report_interval} ms' if self.report_interval
                         else 'auto reporting is off')
                host.inject(f'[MSG:INFO: uart_channel0 {state}]\r\n'.encode('ascii'))
            host.inject(b'ok\r\n')
        elif data == b'$CD\n':
            host.inject(''.join(line + '\r\n' for line in _CONFIG).encode('ascii') + b'ok\r\n')
        elif data == b'$#\n':
            host.inject(self._parameters() + b'ok\r\n')
        else:
            return False
        return True

    def _settings(self) -> bytes:
        rows = [(13, self.host.job_settings[13]), (20, 0), (21, 0), (22, 0), (23, 0),
                (30, self.max_spindle), (32, self.laser_mode)]
        text = ''.join(f'${key}={value}\r\n' for key, value in rows)
        for base, value in ((100, '80.000'), (110, '5000.000'), (120, '200.000'), (130, '300.000')):
            text += ''.join(f'${base + axis}={value}\r\n' for axis in range(3))
        return (text + '$10=1\r\n').encode('ascii')

    def _parameters(self) -> bytes:
        host = self.host
        rows = ''.join(f'[{name}:{host._format(vector)}]\r\n' for name, vector in host.offsets.items())
        rows += f'[G28:{host._format((0., 0., 0.))}]\r\n[G30:{host._format((0., 0., 0.))}]\r\n'
        rows += f'[G92:{host._format(host.g92)}]\r\n'
        if self.v4:
            rows += f'[TLO:{host._format((*self.tlo_xy, host.tlo))}]\r\n'
        else:
            rows += f'[TLO:{host._format((host.tlo,))}]\r\n'
        return rows.encode('ascii')

    def power_cycle(self) -> None:
        """ESP32 reset (e.g. DTR/RTS on port open): ROM log; input is lost until the greeting."""
        host = self.host
        host._incoming.clear()
        host._job.clear()
        host._jog_target = None
        host.state = 'Idle'
        host.spindle, host.coolant = 'M5', ('M9',)
        host.units, host.distance, host.work_system = 'G21', 'G90', 'G54'
        host.g92, host.tlo = (0., 0., 0.), 0.
        self.booting = 'rom'
        host.inject(ROM_LOG)

    def starting(self) -> None:
        """FluidNC setup() runs: status answers ``Starting``; lines are still flushed later."""
        self.booting = 'starting'
        self.host.inject(f'[MSG:INFO: FluidNC v{self.version} https://github.com/bdring/FluidNC]\r\n'
                         '[MSG:INFO: Machine Fake FluidNC]\r\n[MSG:INFO: Board Fake board]\r\n'.encode('ascii'))

    def finish_boot(self) -> None:
        """protocol_do_soft_restart(): flushRx, empty spacer line, then the (custom) greeting."""
        self.booting = None
        self.host.inject(b'\r\n' + self.host.banner)
