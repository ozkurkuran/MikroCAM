"""Deterministic GRBL 1.1 FakeGRBL journeys whose exact TX bytes are pinned (spec 042).

The golden file was generated from main 70800e5b (before firmware identification) with
``python tests/firmware_wire_scenarios.py --write``. Each scenario uses fixed clock steps,
so the only permitted wire difference after 042 is the documented read-only ``$I`` query.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mikrocam.core.probe_map import ProbeGrid, ProbePlan  # noqa: E402
from mikrocam.machine.console_models import ConsoleRequest  # noqa: E402
from mikrocam.machine.controller import MachineController  # noqa: E402
from mikrocam.machine.fake import FakeGRBL  # noqa: E402
from mikrocam.machine.job_models import StartJobRequest, StreamingMode  # noqa: E402
from mikrocam.machine.manual_models import JogRequest, SelectG54Request, ZeroRequest  # noqa: E402
from mikrocam.machine.probe_models import StartProbeGridRequest  # noqa: E402
from test_job_control import prepared  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / 'fixtures' / 'grbl11_wire_golden.json'
BANNER = b"Grbl 1.1h ['$' for help]\r\n"


class Clock:
    value = 0.

    def __call__(self) -> float:
        return self.value


def _session(**kwargs):
    fake, clock = FakeGRBL(**kwargs), Clock()
    controller = MachineController(fake, clock)
    controller.connect()
    return controller, fake, clock


def _steps(controller, clock, count, seconds=.1):
    for _ in range(count):
        clock.value += seconds
        controller.tick()


def _summary(controller) -> dict:
    snap = controller.snapshot()
    return {'connection': snap.connection.value, 'state': snap.state.value, 'raw': snap.raw_state,
            'mpos': snap.machine_position_mm, 'units': snap.report_units,
            'manual': [snap.manual.phase.value, snap.manual.action],
            'job': [snap.job.phase.value, snap.job.acknowledged, snap.job.total],
            'probe': snap.probe.phase.value, 'console': snap.console.phase.value}


def connect_idle():
    controller, fake, clock = _session()
    _steps(controller, clock, 12)
    return controller, fake


def jog():
    controller, fake, clock = _session()
    _steps(controller, clock, 8)
    controller.request_manual(JogRequest('X', 1., 100.))
    _steps(controller, clock, 60)
    return controller, fake


def jog_cancel():
    controller, fake, clock = _session()
    _steps(controller, clock, 8)
    controller.request_manual(JogRequest('Y', 10., 100.))
    for _ in range(40):
        if any(write.startswith(b'$J=') for write in fake.writes):
            break
        _steps(controller, clock, 1)
    controller.cancel_jog()
    _steps(controller, clock, 30)
    return controller, fake


def zero_xy():
    controller, fake, clock = _session(machine_position=(3., 4., 5.))
    _steps(controller, clock, 8)
    controller.request_manual(ZeroRequest(('X', 'Y')))
    _steps(controller, clock, 60)
    return controller, fake


def select_g54():
    controller, fake, clock = _session(work_system='G55')
    _steps(controller, clock, 8)
    controller.request_manual(SelectG54Request())
    _steps(controller, clock, 40)
    return controller, fake


def _job(mode: StreamingMode):
    controller, fake, clock = _session()
    _steps(controller, clock, 8)
    text = 'G21G90G17G94\nF60\n' + ''.join(f'G1X{1 + i % 2}\n' for i in range(12)) + 'M2\n'
    controller.request_job(StartJobRequest(prepared(text), True, mode))
    _steps(controller, clock, 300)
    return controller, fake


def job_send_response():
    return _job(StreamingMode.SEND_RESPONSE)


def job_character_counting():
    return _job(StreamingMode.CHARACTER_COUNTING)


def job_abort():
    controller, fake, clock = _session()
    _steps(controller, clock, 8)
    controller.request_job(StartJobRequest(prepared(), True))
    _steps(controller, clock, 14)
    controller.abort()
    _steps(controller, clock, 10)
    return controller, fake


def probe_grid():
    controller, fake, clock = _session(machine_position=(0., 0., 2.))
    _steps(controller, clock, 8)
    state = controller.snapshot()
    plan = ProbePlan(ProbeGrid((0., 1., 2.), (0., 1.)), 5., -1., 30., 200.,
                     (-100., -100., -100.), (100., 100., 100.),
                     state.machine_position_mm, state.work_offset_mm, 30.)
    controller.request_probe(StartProbeGridRequest(plan))
    _steps(controller, clock, 400)
    return controller, fake


def console_queries():
    controller, fake, clock = _session()
    _steps(controller, clock, 8)
    for command in ('?', '$$', '$G', '$#', '$N', '$I'):
        controller.request_console(ConsoleRequest(command))
        _steps(controller, clock, 6)
    return controller, fake


def reset_mid_session():
    controller, fake, clock = _session()
    _steps(controller, clock, 8)
    fake.inject(BANNER)
    _steps(controller, clock, 12)
    return controller, fake


def reset_on_open():
    controller, fake, clock = _session()
    fake._incoming.clear()  # Bytes written during the bootloader window are lost.
    fake.inject(BANNER)
    _steps(controller, clock, 12)
    return controller, fake


def disconnect_reconnect():
    controller, fake, clock = _session()
    _steps(controller, clock, 6)
    controller.disconnect()
    controller.connect()
    _steps(controller, clock, 6)
    return controller, fake


SCENARIOS = {function.__name__: function for function in (
    connect_idle, jog, jog_cancel, zero_xy, select_g54, job_send_response,
    job_character_counting, job_abort, probe_grid, console_queries,
    reset_mid_session, reset_on_open, disconnect_reconnect)}


def run(name: str) -> tuple[list[bytes], dict]:
    controller, fake = SCENARIOS[name]()
    return list(fake.writes), _summary(controller)


def encode(writes: list[bytes]) -> list[str]:
    return [write.hex() for write in writes]


def load_golden() -> dict:
    return json.loads(GOLDEN.read_text(encoding='utf-8'))


if __name__ == '__main__':
    result = {}
    for scenario in SCENARIOS:
        writes, summary = run(scenario)
        result[scenario] = {'writes': encode(writes), 'summary': json.loads(json.dumps(summary))}
    if '--write' in sys.argv:
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    for scenario, data in result.items():
        print(scenario, len(data['writes']), data['summary'])
