"""Immutable historical application claims, separate from geometry and authorship."""
from dataclasses import dataclass
import re


CAD_APPLICATIONS = ('KiCad', 'Illustrator', 'Inkscape', 'Proteus', 'Unknown')
MAX_CAD_SOURCE_BYTES = 16777216
_STATUSES = ('identified', 'unknown', 'conflicting', 'unavailable')


def _text(value: str, limit: int, label: str) -> None:
    if type(value) is not str or not 1 <= len(value) <= limit:
        raise ValueError(f'{label} requires nonempty text within {limit} characters')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError(f'{label} requires strict UTF-8') from error


def _application(value: str) -> None:
    if type(value) is not str or value not in CAD_APPLICATIONS:
        raise ValueError('Unsupported CAD application identity')


@dataclass(frozen=True)
class CadSourceEvidence:
    application: str
    field: str
    value: str

    def __post_init__(self) -> None:
        _application(self.application)
        _text(self.field, 80, 'Evidence field')
        _text(self.value, 512, 'Evidence value')


@dataclass(frozen=True)
class CadSourceAssessment:
    source_name: str
    source_format: str
    source_sha256: str | None
    application: str
    status: str
    evidence: tuple[CadSourceEvidence, ...]
    reason: str

    def __post_init__(self) -> None:
        _text(self.source_name, 256, 'Source name')
        _text(self.reason, 512, 'Assessment reason')
        _application(self.application)
        if type(self.source_format) is not str or self.source_format not in ('SVG', 'DXF'):
            raise ValueError('Source format must be SVG or DXF')
        if type(self.status) is not str or self.status not in _STATUSES:
            raise ValueError('Unsupported source assessment status')
        if self.source_sha256 is None:
            if self.status != 'unavailable':
                raise ValueError('Only unavailable source assessments may omit SHA256')
        elif (type(self.source_sha256) is not str
              or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None):
            raise ValueError('Source SHA256 requires 64 lowercase hexadecimal characters')
        if (type(self.evidence) is not tuple or len(self.evidence) > 32
                or any(type(claim) is not CadSourceEvidence for claim in self.evidence)):
            raise ValueError('Evidence requires at most 32 exact immutable records')
        for claim in self.evidence:
            claim.__post_init__()
        if len(set(self.evidence)) != len(self.evidence):
            raise ValueError('Source assessment cannot contain duplicate evidence')
        applications = {claim.application for claim in self.evidence}
        if self.status == 'identified':
            if self.application == 'Unknown' or applications != {self.application}:
                raise ValueError('Identified source requires consistent positive evidence')
        else:
            if self.application != 'Unknown':
                raise ValueError('Nonidentified source application must be Unknown')
            if self.status == 'unknown' and applications - {'Unknown'}:
                raise ValueError('Unknown source cannot contain positive evidence')
            if self.status == 'conflicting' and len(applications) < 2:
                raise ValueError('Conflicting source requires at least two application claims')
            if self.status == 'unavailable' and self.evidence:
                raise ValueError('Unavailable source cannot retain partial evidence')
