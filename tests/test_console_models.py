"""Only the exact read-only query set can become an immutable owner request."""
from dataclasses import FrozenInstanceError, replace

import pytest

from mikrocam.machine.console_models import (CONSOLE_COMMANDS, ConsoleObservation,
                                             ConsolePhase, ConsoleRequest)


def test_exact_command_inventory_and_frozen_requests():
    assert CONSOLE_COMMANDS == ('?', '$$', '$G', '$#', '$N', '$I')
    for command in CONSOLE_COMMANDS:
        request = ConsoleRequest(command)
        assert request.command == command
        with pytest.raises(FrozenInstanceError):
            request.command = '?'


@pytest.mark.parametrize('command', ['', '$g', '$I\n', '$$ ', ' ?', '$H', '$X', '$13=0',
                                     'G1X1', '!', '~', '\x18', None, b'?', True, ['?']])
def test_queries_cannot_include_newline_suffix_or_arbitrary_wire_text(command):
    with pytest.raises(ValueError):
        ConsoleRequest(command)


def test_observation_defaults_and_complete_identity():
    result = ConsoleObservation()
    assert result.phase is ConsolePhase.READY and result.command is None
    assert result.diagnostic == '' and result.can_query is False
    assert tuple(phase.value for phase in ConsolePhase) == ('ready','pending','complete','failed')
    complete = replace(result, phase=ConsolePhase.COMPLETE, command='$I',
                       diagnostic='Build evidence received', can_query=True)
    assert complete.command == '$I' and complete.can_query
    with pytest.raises(FrozenInstanceError):
        complete.phase = ConsolePhase.PENDING


@pytest.mark.parametrize('changes', [dict(phase='ready'), dict(command='$H'), dict(command=['?']),
                                    dict(diagnostic='x'*257), dict(diagnostic=None),
                                    dict(can_query=1), dict(can_query='yes')])
def test_invalid_observation_values_cannot_enter_snapshot(changes):
    with pytest.raises(ValueError):
        ConsoleObservation(**changes)


def test_diagnostic_boundary_preserves_raw_text_without_interpreting_it():
    text = '<b>raw</b>\x1b[31m'+'x'*240
    text = text[:256]
    assert ConsoleObservation(diagnostic=text).diagnostic == text
