"""Strict immutable schema for local KiCad production transfers (no process or Qt I/O)."""
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from mikrocam.core.manufacturing_models import validate_assignment

MAX_FILE=16*1024*1024
MAX_TOTAL=64*1024*1024
MAX_MANIFEST=256*1024


def text(value: str, limit: int = 256) -> None:
    if type(value) is not str or not value or not value.isprintable() or value!=value.strip() or len(value.encode('utf-8'))>limit:
        raise ValueError('Transfer requires bounded printable text')


def filename(value: str) -> None:
    text(value)
    device=value.split('.')[0].upper()
    if value.endswith('.') or device in ('CON','PRN','AUX','NUL') or re.fullmatch(r'(?:COM|LPT)[1-9¹²³]',device):
        raise ValueError('Transfer filename cannot name a Windows device')
    if value in ('.','..') or any(c in value for c in '/\\:'):
        raise ValueError('Transfer filename must be a local basename')


def digest(value: str) -> None:
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None:
        raise ValueError('Transfer requires lowercase SHA256')


def count(value: int, maximum: int = 100000) -> None:
    if type(value) is not int or not 0<=value<=maximum:
        raise ValueError('Transfer requires bounded nonnegative integer')


def json_object(data: bytes) -> dict:
    def pairs(items: list) -> dict:
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON field')
            out[k]=v
        return out
    try:
        value=json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    except (UnicodeError,json.JSONDecodeError,RecursionError) as error:
        raise ValueError('Invalid transfer JSON') from error
    if type(value) is not dict:raise ValueError('JSON object required')
    return value


def drc_counts(data: bytes) -> tuple[int,int,int]:
    if type(data) is not bytes or not 1<=len(data)<=MAX_FILE:raise ValueError('DRC report size invalid')
    report=json_object(data);errors=warnings=items=0
    for key in ('violations','unconnected_items','schematic_parity'):
        rows=report.get(key)
        if type(rows) is not list:raise ValueError('Incomplete DRC report')
        items+=len(rows)
        if items>100000:raise ValueError('DRC report has too many items')
        for row in rows:
            if type(row) is not dict or row.get('severity') not in ('error','warning','exclusion'):
                raise ValueError('Invalid DRC severity')
            errors+=row['severity']=='error';warnings+=row['severity']=='warning'
    return errors,warnings,len(report['unconnected_items'])


@dataclass(frozen=True)
class TransferFile:
    name: str
    kind: str
    role: str
    sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        filename(self.name);validate_assignment(self.kind,self.role);digest(self.sha256)
        count(self.byte_count,MAX_FILE)
        if not self.byte_count:raise ValueError('Empty transfer member')


@dataclass(frozen=True)
class TransferManifest:
    board_name: str
    board_sha256: str
    kicad_version: str
    files: tuple[TransferFile,...]
    skipped_empty: tuple[str,...]
    drc_sha256: str
    drc_errors: int
    drc_warnings: int
    drc_unconnected: int
    schema: int = 1
    units: str = 'MM'
    origin: str = 'absolute'

    def __post_init__(self) -> None:
        filename(self.board_name);digest(self.board_sha256);digest(self.drc_sha256)
        if type(self.schema) is not int or self.schema!=1 or self.units!='MM' or self.origin!='absolute':
            raise ValueError('Unsupported transfer schema/coordinate frame')
        if type(self.kicad_version) is not str or re.fullmatch(r'10\.0\.\d+(?:[-+][\w.]+)?',self.kicad_version) is None:
            raise ValueError('Transfer supports KiCad10.0 only')
        if type(self.files) is not tuple or not 1<=len(self.files)<=64 or any(type(f) is not TransferFile for f in self.files):
            raise ValueError('Transfer requires1..64 immutable file records')
        names=[f.name.casefold() for f in self.files]
        if len(set(names))!=len(names) or sum(f.byte_count for f in self.files)>MAX_TOTAL:
            raise ValueError('Duplicate members or total size exceeded')
        if type(self.skipped_empty) is not tuple or len(self.skipped_empty)>64:raise ValueError('Invalid empty-file inventory')
        for n in self.skipped_empty:filename(n)
        skipped=[n.casefold() for n in self.skipped_empty]
        if len(set(skipped))!=len(skipped) or set(skipped)&set(names):raise ValueError('Invalid empty-file inventory')
        for c in (self.drc_errors,self.drc_warnings,self.drc_unconnected):count(c)

    @property
    def needs_acknowledgement(self) -> bool:
        return bool(self.drc_errors or self.drc_unconnected)


@dataclass(frozen=True)
class TransferPackage:
    manifest: TransferManifest
    drc_bytes: bytes
    contents: tuple[bytes,...]

    def __post_init__(self) -> None:
        if type(self.manifest) is not TransferManifest or type(self.contents) is not tuple or len(self.contents)!=len(self.manifest.files):
            raise ValueError('Invalid transfer contents')
        if drc_counts(self.drc_bytes)!=(self.manifest.drc_errors,self.manifest.drc_warnings,self.manifest.drc_unconnected):
            raise ValueError('DRC counts mismatch')
        if sha256(self.drc_bytes).hexdigest()!=self.manifest.drc_sha256:raise ValueError('DRC hash mismatch')
        for row,data in zip(self.manifest.files,self.contents):
            if type(data) is not bytes or len(data)!=row.byte_count or sha256(data).hexdigest()!=row.sha256:
                raise ValueError('Transfer member size/hash mismatch')
        if sum(map(len,self.contents))+len(self.drc_bytes)>MAX_TOTAL:raise ValueError('Transfer total exceeded')


def manifest_to_dict(value: TransferManifest) -> dict:
    from dataclasses import asdict
    result=asdict(value);result['files']=[asdict(f) for f in value.files];result['skipped_empty']=list(value.skipped_empty)
    return result


def manifest_from_dict(value: dict) -> TransferManifest:
    fields={'board_name','board_sha256','kicad_version','files','skipped_empty','drc_sha256','drc_errors','drc_warnings','drc_unconnected','schema','units','origin'}
    if type(value) is not dict or set(value)!=fields or type(value['files']) is not list or type(value['skipped_empty']) is not list:
        raise ValueError('Invalid transfer manifest fields')
    try:
        rows=[]
        for f in value['files']:
            if type(f) is not dict or set(f)!={'name','kind','role','sha256','byte_count'}:raise ValueError('Invalid file fields')
            rows.append(TransferFile(**f))
        return TransferManifest(**{**value,'files':tuple(rows),'skipped_empty':tuple(value['skipped_empty'])})
    except TypeError as error:raise ValueError('Invalid transfer fields') from error
