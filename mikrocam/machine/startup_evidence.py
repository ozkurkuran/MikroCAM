"""Family-specific readonly proof that a reset runs no stored G-code (specs 011/025/044).

GRBL keeps its single ``$N`` query. FluidNC has no ``$N``: its YAML ``macros/startup_line0/1`` and
``macros/after_reset`` are read back individually, followed by the ``$RI`` auto-report state.
Manual, job and probe owners each hold one instance for their startup transaction.
"""
from .firmware import FirmwareFamily
from .fluidnc import STARTUP_QUERIES, parse_startup_record, startup_problem
from .manual_protocol import parse_startup

GRBL_STARTUP_QUERY = b'$N\n'


class StartupEvidence:
    def __init__(self, family: FirmwareFamily) -> None:
        self.fluidnc = family is FirmwareFamily.FLUIDNC
        self._queries = list(STARTUP_QUERIES if self.fluidnc else (GRBL_STARTUP_QUERY,))
        self.records: dict = {}

    def next_query(self) -> bytes | None:
        """The next readonly query, or None once every query was acknowledged."""
        return self._queries.pop(0) if self._queries else None

    def record(self, line: str) -> tuple | None:
        if self.fluidnc:
            return parse_startup_record(line)
        item = parse_startup(line)
        return None if item is None else (item.index, item.block)

    def add(self, records: dict) -> None:
        for key, value in records.items():
            if key in self.records:
                raise ValueError('Duplicate startup evidence')
            self.records[key] = value

    def problem(self, grbl_message: str) -> str | None:
        """None when verified; GRBL keeps each owner's established refusal text."""
        if self.fluidnc:
            return startup_problem(self.records)
        return None if self.records == {0: '', 1: ''} else grbl_message
