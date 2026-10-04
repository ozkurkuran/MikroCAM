"""Deterministic, hardware-free GRBL simulator with explicit fault injection."""

import math
from decimal import Decimal

from mikrocam.machine.manual_protocol import validate_command
from mikrocam.machine.job_protocol import validate_job_command
from mikrocam.machine.fake_job import FakeJob
from mikrocam.machine.fake_probe import FakeProbe
from mikrocam.machine import fake_firmware
from mikrocam.machine.fake_firmware import (GRBLHAL_SETTINGS, grblhal_modal, grblhal_parameters,
                                             grblhal_status, profile)
from mikrocam.machine.probe_protocol import validate_probe_command


class FakeGRBL:
    """Record exact requests and allow tests to supply delayed/chunked controller data."""

    def __init__(self, *, auto_respond: bool = True, report_units: str = 'mm',
                 status: bytes | None = None,
                 machine_position: tuple[float, float, float] = (0., 0., 0.),
                 work_system: str = 'G54',
                 offsets: dict[str, tuple[float, float, float]] | None = None,
                 g92: tuple[float, float, float] = (0., 0., 0.), tlo: float = 0.,
                 startup_blocks: tuple[str, str] = ('', ''), firmware: str | None = None,
                 build_reply: bytes | None = None) -> None:
        if report_units not in ('mm', 'inch'):
            raise ValueError('Expected mm or inch report units')
        self.auto_respond = auto_respond
        self.firmware = fake_firmware.DEFAULT_PROFILE if firmware is None else firmware
        self.banner, self.build_reply = profile(self.firmware)
        self.hal_modal_words: tuple[str, ...] = ()
        self.hal_tlo_xy = (0., 0.)
        self._reports = 0
        if build_reply is not None:
            if not isinstance(build_reply, bytes):
                raise ValueError('Build reply must be bytes')
            self.build_reply = build_reply
        self.report_units = report_units
        self.status = status
        if status is not None and not isinstance(status, bytes):
            raise ValueError('Static status must be bytes')
        if work_system not in ('G54', 'G55', 'G56', 'G57', 'G58', 'G59'):
            raise ValueError('Unsupported work system')
        self.machine_position = self._vector(machine_position)
        self.work_system = work_system
        supplied = {} if offsets is None else offsets
        if not isinstance(supplied, dict) or set(supplied) - set(f'G{i}' for i in range(54, 60)):
            raise ValueError('Unsupported work offsets')
        self.offsets = {f'G{i}': self._vector(supplied.get(f'G{i}', (0., 0., 0.)))
                        for i in range(54, 60)}
        self.g92 = self._vector(g92)
        if isinstance(tlo, bool) or not isinstance(tlo, (int, float)) or not math.isfinite(tlo):
            raise ValueError('TLO must be finite')
        self.tlo = float(tlo)
        if (not isinstance(startup_blocks, tuple) or len(startup_blocks) != 2
                or any(not isinstance(block, str) or len(block) > 80
                       or any(not 32 <= ord(char) <= 126 for char in block)
                       for block in startup_blocks)):
            raise ValueError('Expected two bounded printable startup blocks')
        self.startup_blocks = startup_blocks
        self.units, self.distance, self.spindle = 'G21', 'G90', 'M5'
        self.coolant = ('M9',)
        self.program_flow = ''
        self.state = 'Idle'
        self._jog_target = None
        self._jog_reported = False
        self.writes: list[bytes] = []
        self.is_open = False
        self.open_count = 0
        self.open_error: OSError | None = None
        self.read_error: OSError | None = None
        self.write_error: OSError | None = None
        self.close_error: OSError | None = None
        self.short_write = False
        self._incoming = bytearray()
        self.job_writes: list[bytes] = []
        self.job_settings = {13: 0 if report_units == 'mm' else 1, 30: 1000, 31: 0, 32: 0}
        self._job = FakeJob(self)
        self._probe = FakeProbe(self)
        self.probe_origin = 'simulated'

    def write_probe(self, data: bytes) -> int:
        """Simulate one independently validated vertical probe or linear travel."""
        validate_probe_command(data)
        if not self.is_open:
            raise OSError('Closed')
        if self.write_error:
            raise self.write_error
        self.writes.append(data)
        if self.short_write:
            return len(data) - 1
        if self.auto_respond:
            self._probe.respond(data)
        return len(data)

    @staticmethod
    def _vector(values) -> tuple[float, float, float]:
        if (not isinstance(values, (tuple, list)) or len(values) != 3
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) for value in values)):
            raise ValueError('Expected finite XYZ values')
        return tuple(float(value) for value in values)

    def open(self) -> None:
        if self.is_open:
            raise OSError('Already open')
        if self.open_error:
            raise self.open_error
        self.is_open = True
        self.open_count += 1

    def inject(self, data: bytes) -> None:
        """Queue externally scripted bytes; an empty read represents a delayed reply."""
        if not isinstance(data, bytes) or len(self._incoming) + len(data) > 65536:
            raise ValueError('Simulator input exceeds 65536 bytes')
        self._incoming.extend(data)

    def read(self, size: int) -> bytes:
        if type(size) is not int or not 1 <= size <= 4096:
            raise ValueError('Read size must be 1..4096')
        if not self.is_open:
            raise OSError('Closed')
        if self.read_error:
            raise self.read_error
        data = bytes(self._incoming[:size])
        del self._incoming[:size]
        return data

    def write(self, data: bytes) -> int:
        if not self.is_open:
            raise OSError('Closed')
        validate_command(data)
        if self.write_error:
            raise self.write_error
        self.writes.append(data)
        if self.short_write:
            return len(data) - 1
        if self.auto_respond:
            self._respond(data)
        return len(data)

    def _format(self, values) -> str:
        divisor = 25.4 if self.report_units == 'inch' else 1.
        return ','.join(format(Decimal(format(value / divisor, '.12g')), 'f') for value in values)

    def _status_report(self) -> bytes:
        if self.status is not None:
            return self.status
        self._job.poll()
        if self._jog_target is not None:
            if self._jog_reported:
                self.machine_position = self._jog_target
                self._jog_target = None
                self.state = 'Idle'
            else:
                self._jog_reported = True
        offset = tuple(self.offsets[self.work_system][i] + self.g92[i]
                       + (self.hal_tlo_xy + (self.tlo,))[i] for i in range(3))
        if self.firmware == 'grblhal':
            self._reports += 1
            return grblhal_status(self.state, self._format(self.machine_position),
                                  self._format(offset), self._reports == 1)
        return (f'<{self.state}|MPos:{self._format(self.machine_position)}'
                f'|WCO:{self._format(offset)}>\r\n').encode('ascii')

    def _respond(self, data: bytes) -> None:
        if data == b'?':
            self.inject(self._status_report())
        elif data == b'$$\n':
            extra = GRBLHAL_SETTINGS if self.firmware == 'grblhal' else ''
            self.inject((''.join(f'${key}={value}\r\n' for key, value in self.job_settings.items())
                         + extra).encode() + b'ok\r\n')
        elif data == b'$I\n':
            self.inject(self.build_reply)
        elif data == b'$N\n':
            self.inject(''.join(f'$N{i}={block}\r\n' for i, block in enumerate(
                self.startup_blocks)).encode('ascii') + b'ok\r\n')
        elif data == b'$G\n' and self.firmware == 'grblhal':
            self.inject(grblhal_modal(self.work_system, any(self.g92), self.units, self.distance,
                                      bool(self.tlo or any(self.hal_tlo_xy)), self.program_flow,
                                      self.spindle, self.coolant, self.hal_modal_words))
        elif data == b'$G\n':
            program = f'{self.program_flow} ' if self.program_flow else ''
            self.inject((f'[GC:G0 {self.work_system} G17 {self.units} {self.distance} '
                         f'G94 {program}{self.spindle} {" ".join(self.coolant)} T0 F0 S0]\r\nok\r\n').encode())
        elif data == b'$#\n':
            rows = ''.join(f'[{name}:{self._format(vector)}]\r\n'
                           for name, vector in self.offsets.items())
            if self.firmware == 'grblhal':
                self.inject(grblhal_parameters(rows, self._format(self.g92), self._format(
                    self.hal_tlo_xy + (self.tlo,)), self._format((0., 0., 0.))))
                return
            rows += f'[G92:{self._format(self.g92)}]\r\n[TLO:{self._format((self.tlo,))}]\r\n'
            self.inject(rows.encode('ascii') + b'ok\r\n')
        elif data in (b'\x85', b'\x18', b'\x84'):
            self._stop(data)
        else:
            if data == b'M5 M9\n' and self._job.defer_off():
                return
            self._execute(data)
            self.inject(b'ok\r\n')

    def _execute(self, data: bytes) -> None:
        if data == b'M5 M9\n':
            self.spindle, self.coolant = 'M5', ('M9',)
        elif data == b'G54\n':
            self.work_system = 'G54'
        elif data.startswith(b'G10 '):
            changed = list(self.offsets['G54'])
            for word in data.decode('ascii').split()[3:]:
                axis = 'XYZ'.index(word[0])
                changed[axis] = (self.machine_position[axis] - self.g92[axis]
                                 - (self.tlo if axis == 2 else 0.))
            self.offsets['G54'] = tuple(changed)
        else:
            word = data.decode('ascii').split()[2]
            target = list(self.machine_position)
            target['XYZ'.index(word[0])] += float(word[1:])
            self._jog_target = tuple(target)
            self._jog_reported = False
            self.state = 'Jog'

    def _stop(self, data: bytes) -> None:
        self._jog_target = None
        self._jog_reported = False
        if data == b'\x85':
            if self.state == 'Jog':
                self.state = 'Idle'
            return
        self._job.clear()
        self.spindle, self.coolant = 'M5', ('M9',)
        if data == b'\x84':
            self.state = 'Door:0'
            return
        self.state = 'Idle'
        self.units, self.distance, self.work_system = 'G21', 'G90', 'G54'
        self.g92, self.tlo = (0., 0., 0.), 0.
        self._reports = 0
        self.inject(self.banner)

    def close(self) -> None:
        self.is_open = False
        self._incoming.clear()
        self._jog_target = None
        self._job.clear()
        if self.close_error:
            raise self.close_error

    def write_job(self, data: bytes) -> int:
        """Record acceptance independently of the simulated planner's later endpoint."""
        if not self.is_open:
            raise OSError('Closed')
        validate_job_command(data)
        if self.write_error:
            raise self.write_error
        self.writes.append(data)
        if data not in (b'!', b'~'):
            self.job_writes.append(data)
        if self.short_write:
            return len(data) - 1
        if self.auto_respond:
            self._job.accept(data)
        return len(data)
