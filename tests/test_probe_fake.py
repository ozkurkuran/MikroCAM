import pytest
from mikrocam.machine.fake import FakeGRBL
from mikrocam.machine.probe_protocol import probe_move, parse_probe_result


@pytest.mark.parametrize('units', ['mm', 'inch'])
def test_fake_plane_machine_report(units):
    fake = FakeGRBL(report_units=units, machine_position=(11., 22., 8.), offsets={'G54': (10., 20., 3.)})
    fake.open()
    fake.write_probe(probe_move(z=-1,feed=10,probing=True))
    lines = fake.read(4096).decode().splitlines()
    assert lines[-1] == 'ok'
    assert parse_probe_result(lines[0], units) == pytest.approx((11., 22., 3.05), abs=1e-8)
    assert fake.probe_origin == 'simulated'


def test_fake_travel_fault_and_raw_boundary():
    fake = FakeGRBL(); fake.open()
    fake.write_probe(probe_move(z=3.,feed=100.))
    assert fake.machine_position == (0.,0.,3.)
    assert fake.read(4096) == b'ok\r\n'
    fake._probe.fault = 'missing'
    fake.write_probe(probe_move(z=-1,feed=10,probing=True))
    assert fake.read(4096) == b'ok\r\n'
    with pytest.raises(ValueError):
        fake.write_probe(b'M3\n')
