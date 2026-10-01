"""Deterministic planner/hold simulation; it is not a firmware or timing emulator."""
from collections import deque
from typing import TYPE_CHECKING

from mikrocam.core.gcode_lexer import iter_blocks
from mikrocam.core.gcode_parser import ModalInterpreter

if TYPE_CHECKING:
    from .fake import FakeGRBL


class FakeJob:
    def __init__(self, host: 'FakeGRBL') -> None:
        self.host = host
        self.interpreter: ModalInterpreter | None = None
        self.targets: deque = deque()
        self.pending_target: tuple | None = None
        self.off_pending = False
        self.hold_reported = False

    def accept(self, data: bytes) -> None:
        host = self.host
        if data == b'!':
            host.state = 'Hold:1'
            self.hold_reported = False
            return
        if data == b'~':
            if host.state == 'Hold:0':
                host.state = 'Run' if self.targets else 'Idle'
            return
        if self.interpreter is None:
            offset = host.offsets[host.work_system]
            initial = tuple(host.machine_position[i] - offset[i] for i in range(3))
            self.interpreter = ModalInterpreter(initial)
        try:
            block = next(iter_blocks(data.decode('ascii')))
            event = self.interpreter.consume(block)
        except ValueError:
            host.inject(b'error:20\r\n')
            return
        host.program_flow = ''
        for letter, value in block.words:
            if letter == 'G' and value in (20, 21):
                host.units = f'G{int(value)}'
            elif letter == 'G' and value in (90, 91):
                host.distance = f'G{int(value)}'
            elif letter == 'M' and value in (3, 4, 5):
                host.spindle = f'M{int(value)}'
            elif letter == 'M' and value in (0, 1, 2, 30):
                host.program_flow = f'M{int(value)}'
            elif letter == 'M' and value in (8, 9):
                host.coolant = (f'M{int(value)}',)
        if event.motion is not None and event.start != event.end:
            target = tuple(event.end[i] + host.offsets[host.work_system][i] for i in range(3))
            if len(self.targets) >= 16:
                if self.pending_target is not None:
                    raise ValueError('Fake has more than one unacknowledged source block')
                self.pending_target = target
                return
            self.targets.append(target)
            host.state = 'Run'
        host.inject(b'ok\r\n')

    def poll(self) -> None:
        host = self.host
        if host.state in ('Hold:1', 'Hold:0'):
            if self.hold_reported:
                host.state = 'Hold:0'
            self.hold_reported = True
            return
        if host.state == 'Run' and self.targets:
            host.machine_position = self.targets.popleft()
            if self.pending_target is not None:
                self.targets.append(self.pending_target)
                self.pending_target = None
                host.inject(b'ok\r\n')
            if not self.targets:
                host.state = 'Idle'
        if self.off_pending and not self.targets:
            host.spindle, host.coolant = 'M5', ('M9',)
            self.off_pending = False
            self.interpreter = None
            host.inject(b'ok\r\n')

    def defer_off(self) -> bool:
        if self.targets:
            self.off_pending = True
            return True
        self.interpreter = None
        return False

    def clear(self) -> None:
        self.host.program_flow = ''
        self.targets.clear()
        self.pending_target = self.interpreter = None
        self.off_pending = False
