"""Exact LF byte credit, FIFO identities, expiry and conservative capability admission."""
import pytest
from mikrocam.machine.job_stream import JobStream, verified_capacity
from mikrocam.machine.job_models import StreamingMode, StartJobRequest
from test_job_control import prepared


def test_mode_default_and_exact_intent():
    assert StartJobRequest(prepared(), True).streaming_mode is StreamingMode.SEND_RESPONSE
    with pytest.raises(ValueError):
        StartJobRequest(prepared(), True, "character-counting")


def test_exact_fit_fifo_deadline_and_rollback():
    stream = JobStream(16)
    first = stream.reserve(b"G1X1F60\n", 10.)
    second = stream.reserve(b"G1X2F60\n", 11.)
    assert stream.used == 16 and not stream.fits(b"M2\n")
    assert stream.ack() == first and stream.used == 8
    third = stream.reserve(b"M2\n", 12.)
    assert third.index == 2
    stream.cancel_last(third)
    assert stream.next_index == 2 and stream.used == 8
    stream.extend(20.)
    assert not stream.expired(30.999) and stream.expired(31.)
    assert stream.ack().index == 1 and stream.used == 0
    with pytest.raises(ValueError): stream.ack()


@pytest.mark.parametrize("data", [b"", b"G1X1", b"G1X1\r\n", b"?", b"G1X1\nM2\n", b"X"*16+b"\n"])
def test_reservation_refuses_noncanonical_or_oversize(data):
    with pytest.raises(ValueError): JobStream(16).reserve(data, 10.)


@pytest.mark.parametrize("records,expected", [({"ver":"1.1h:Fake", "opt": "V,15,128"},128),
    ({"ver":"1.1f:build", "opt":",15,64"},64),
    ({"ver":"1.1h.20190825:", "opt":"V,15,128"},128),
    ({"ver":"1.1d.20161014:OEM", "opt":"VL*$#2,15,128"},128),
    ({"ver":"1.1h:build", "opt":"V,15,256"},128)])
def test_verified_compiled_capacity_is_capped(records, expected):
    assert verified_capacity(records) == expected


@pytest.mark.parametrize("records", [{}, {"ver":"1.1h:Fake"}, {"ver":"0.9j:","opt":"V,15,128"},
    {"ver":"1.1h:","opt":"V,15,0"}, {"ver":"1.1h:","opt":"V,15,-1"},
    {"ver":"FluidNC:","opt":"V,15,128"}, {"ver":"1.1h:","opt":"V,15,abc"}])
def test_missing_or_malformed_capability_refuses(records):
    with pytest.raises(ValueError): verified_capacity(records)


@pytest.mark.parametrize("options", ["V0,15,128", "V+,15,128", "VNMCPZHTAD0SRL+*$#IEW2,15,128"])
def test_every_documented_grbl11_option_letter_keeps_capacity(options):
    """gnea/grbl bfb67f0c report.c:375-441 prints '0' and '+' as OPT letters."""
    assert verified_capacity({"ver": "1.1h.20190830:", "opt": options}) == 128
