"""Plain-text presentation of the firmware capability record (spec 042); no decisions here."""
import builtins
import gettext

from mikrocam.machine.firmware import FirmwareFamily, FirmwareObservation, IdentificationPhase


_ = getattr(builtins, '_', gettext.gettext)
_NAMES = {FirmwareFamily.GRBL: 'GRBL', FirmwareFamily.GRBLHAL: 'grblHAL',
          FirmwareFamily.FLUIDNC: 'FluidNC', FirmwareFamily.UNKNOWN: 'Unknown'}


def describe_firmware(observation: FirmwareObservation) -> str:
    """One line: family/version, buffers, char-counting budget and motion eligibility."""
    if observation.phase is IdentificationPhase.NONE:
        return _('Not identified')
    if observation.phase is IdentificationPhase.PENDING:
        return _('Identifying…')
    caps = observation.capabilities
    name = _(_NAMES[caps.family])
    if caps.version:
        name += ' ' + caps.version
    if caps.build:
        name += ' (' + _('build') + ' ' + caps.build + ')'
    parts = [name]
    parts.append(_('RX unknown') if caps.rx_buffer_bytes is None else f'RX {caps.rx_buffer_bytes} B')
    if caps.streaming_rx_budget is None:
        parts.append(_('char-counting unavailable'))
    else:
        parts.append(_('char-counting budget') + f' {caps.streaming_rx_budget} B')
    if observation.motion_allowed:
        parts.append(_('motion enabled'))
    else:
        reason = observation.diagnostic or caps.note
        parts.append(_('motion disabled') + (f' — {_(reason)}' if reason else ''))
    return '; '.join(parts)


def firmware_details(observation: FirmwareObservation) -> str:
    """Tooltip: documented realtime commands, extra states, status fields and raw evidence."""
    caps = observation.capabilities
    rows = [_('Options') + ': ' + (caps.options or '-')]
    if caps.extended_options:
        rows.append('NEWOPT: ' + ','.join(caps.extended_options))
    rows.append(_('Extra states') + ': ' + (', '.join(caps.extra_states) or '-'))
    rows.append(_('Status fields') + ': ' + (', '.join(caps.status_fields) or '-'))
    rows.append(_('Realtime commands') + ': ' + (', '.join(
        f'0x{code:02X} {name}' for code, name in caps.realtime_commands) or '-'))
    if observation.banner:
        rows.append(_('Greeting') + ': ' + observation.banner)
    rows.extend(observation.evidence)
    return '\n'.join(rows)
