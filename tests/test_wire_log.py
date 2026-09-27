"""Bounded raw evidence, honest outcomes and exact omission/eviction accounting."""
from dataclasses import FrozenInstanceError, replace

import pytest

from mikrocam.machine.wire_log import (MAX_ENTRIES, MAX_PAYLOAD_BYTES, MAX_RECORD_BYTES,
                                      WireLog, WireRecord, WireSnapshot)


def record(sequence=1, payload=b'?', **changes):
    return replace(WireRecord(sequence, 1., 'TX', payload, 'complete', '', 0), **changes)


def test_record_is_frozen_preserves_exact_bytes_and_normalizes_timestamp():
    value = WireRecord(1, 0, 'RX', b'ok\r\n\x1b\xff', 'received', '', 2)
    assert value.timestamp == 0. and type(value.timestamp) is float
    assert value.payload == b'ok\r\n\x1b\xff' and value.omitted_bytes == 2
    with pytest.raises(FrozenInstanceError):
        value.payload = b''


@pytest.mark.parametrize('changes', [dict(sequence=0),dict(sequence=True),dict(sequence=1.),
    dict(timestamp=True),dict(timestamp=float('nan')),dict(timestamp=float('inf')),
    dict(direction='tx'),dict(direction='RX',outcome='complete'),
    dict(outcome='received'),dict(direction='IO',outcome='error'),
    dict(payload=bytearray(b'?')),dict(payload=b'x'*4097),dict(diagnostic='x'*257),
    dict(diagnostic=[]),dict(omitted_bytes=-1),dict(omitted_bytes=True)])
def test_record_rejects_mutable_nonfinite_and_inconsistent_evidence(changes):
    with pytest.raises(ValueError):
        record(**changes)


def test_all_allowed_pairs_and_empty_io_error():
    for direction, outcome, payload in [('TX','complete',b'?'),('TX','uncertain',b'$I\n'),
                                        ('RX','received',b''),('IO','error',b'')]:
        assert WireRecord(1, -1., direction, payload, outcome, '').direction == direction


@pytest.mark.parametrize('changes', [dict(records=[]),dict(records=(object(),)),
    dict(records=(record(2),record(1))),dict(records=(record(1),record(1))),
    dict(records=tuple(record(n+1,b'') for n in range(513))),
    dict(records=tuple(record(n+1,b'x'*4096) for n in range(65))),
    dict(dropped_entries=True),dict(dropped_entries=-1),dict(dropped_bytes=-1),
    dict(dropped_bytes=1.)])
def test_snapshot_enforces_both_caps_order_and_immutable_counters(changes):
    with pytest.raises(ValueError):
        WireSnapshot(**changes)


def test_snapshot_boundaries_and_sequence_gaps_are_valid():
    assert WireSnapshot().records == ()
    assert len(WireSnapshot(tuple(record(n+1,b'') for n in range(512))).records) == 512
    assert sum(len(r.payload) for r in WireSnapshot(tuple(record(n+10,b'x'*4096)
               for n in range(64))).records) == MAX_PAYLOAD_BYTES
    assert WireSnapshot((record(8),record(10)),7,90).dropped_entries == 7


def test_large_payload_omitted_once_and_oldest_whole_records_evicted_by_bytes():
    clock = iter(range(100)).__next__
    log = WireLog(clock)
    log.append('RX',b'a'*5000,'received')
    saved = log.snapshot()
    assert saved.records[0].payload == b'a'*4096
    assert saved.records[0].omitted_bytes == 904
    assert saved.dropped_entries == 0 and saved.dropped_bytes == 904
    for _ in range(64):
        log.append('RX',b'b'*4096,'received')
    result = log.snapshot()
    assert len(result.records) == 64 and result.records[0].sequence == 2
    assert result.dropped_entries == 1 and result.dropped_bytes == 5000
    assert saved.records[0].sequence == 1 and saved.dropped_bytes == 904


def test_entry_cap_evicts_even_zero_byte_records_and_reset_starts_new_session():
    log = WireLog(lambda:1.)
    for _ in range(MAX_ENTRIES+3):
        log.append('IO',b'','error','read failed')
    result = log.snapshot()
    assert len(result.records) == MAX_ENTRIES and result.records[0].sequence == 4
    assert result.dropped_entries == 3 and result.dropped_bytes == 0
    log.reset()
    assert log.snapshot() == WireSnapshot()
    log.append('TX',b'?','complete')
    assert log.snapshot().records[0].sequence == 1
    assert result.dropped_entries == 3


def test_empty_rx_does_not_consume_sequence_and_mixed_caps_account_exactly():
    log = WireLog(lambda:0.)
    for _ in range(10):
        log.append('RX',b'','received')
    assert log.snapshot() == WireSnapshot()
    for _ in range(600):
        log.append('TX',b'x'*5000,'uncertain')
    result = log.snapshot()
    assert len(result.records) == 64 and result.records[0].sequence == 537
    assert result.dropped_entries == 536
    assert result.dropped_bytes == 600*904 + 536*4096
    assert result.records[-1].sequence == 600


def test_invalid_append_and_clock_do_not_mutate_records_or_sequence():
    times = [1.]
    log = WireLog(lambda:times[0])
    log.append('TX',b'?','complete')
    before = log.snapshot()
    for direction, payload, outcome, diagnostic in [('TX',bytearray(b'?'),'complete',''),
        ('IO',b'?','error',''),('RX',b'a','uncertain',''),('TX',b'?','complete','x'*257)]:
        with pytest.raises(ValueError):
            log.append(direction,payload,outcome,diagnostic)
        assert log.snapshot() == before
    times[0] = float('nan')
    with pytest.raises(ValueError):
        log.append('TX',b'?','complete')
    assert log.snapshot() == before
    times[0] = 2.
    log.append('TX',b'$I\n','uncertain')
    assert log.snapshot().records[-1].sequence == 2


def test_constants_match_contract_and_clock_must_be_callable():
    assert (MAX_RECORD_BYTES,MAX_ENTRIES,MAX_PAYLOAD_BYTES) == (4096,512,262144)
    with pytest.raises(ValueError):
        WireLog(1.)
