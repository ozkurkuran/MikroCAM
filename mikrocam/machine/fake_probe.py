"""Deterministic analytic-plane probe behavior, without a reader or worker."""
from typing import TYPE_CHECKING
from .probe_protocol import validate_probe_command

if TYPE_CHECKING:
    from .fake import FakeGRBL


class FakeProbe:
    def __init__(self, host: 'FakeGRBL') -> None:
        self.host = host
        self.plane = (0., .01, .02)
        self.fault: str | None = None

    def respond(self, data: bytes) -> None:
        validate_probe_command(data)
        host = self.host
        words = data.decode('ascii').split()
        axes = {word[0]: float(word[1:]) for word in words[4:]}
        offset = host.offsets[host.work_system]
        target = tuple(axes.get(axis, host.machine_position[i] - offset[i]) + offset[i]
                       for i, axis in enumerate('XYZ'))
        if words[3] != 'G38.2':
            host.machine_position = target
            host.state = 'Idle'
            host.inject(b'ok\r\n')
            return
        x, y = (target[i] - offset[i] for i in (0, 1))
        z = self.plane[0] + self.plane[1] * x + self.plane[2] * y + offset[2]
        success = target[2] <= z < host.machine_position[2]
        host.machine_position = (target[0], target[1], z if success else target[2])
        host.state = 'Idle' if success else 'Alarm'
        record = f'[PRB:{host._format(host.machine_position)}:{int(success)}]\r\n'.encode('ascii')
        if self.fault == 'failed':
            record = f'[PRB:{host._format(host.machine_position)}:0]\r\n'.encode('ascii')
        elif self.fault == 'malformed':
            record = b'[PRB:invalid:1]\r\n'
        elif self.fault == 'duplicate':
            record *= 2
        elif self.fault == 'missing':
            record = b''
        elif self.fault == 'delay':
            return
        elif self.fault == 'alarm':
            host.state = 'Alarm'
            host.inject(b'ALARM:4\r\n')
            return
        host.inject(record + (b'ok\r\n' if success else b'ALARM:5\r\n'))
