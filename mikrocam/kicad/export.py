"""KiCad10 CLI production export on a private board/project snapshot."""
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from mikrocam.core.kicad_transfer import MAX_FILE,TransferFile,TransferManifest,TransferPackage,drc_counts
from mikrocam.kicad.package import write_package


def _windows_candidates() -> tuple[Path,...]:
    if os.name!='nt':return ()
    root=Path(os.environ.get('ProgramFiles','C:/Program Files'))/'KiCad'
    return tuple(sorted(root.glob('10.0/bin/kicad-cli.exe'),reverse=True))


def discover_cli(explicit: str | None = None) -> str:
    if explicit:
        return str(explicit)
    found=shutil.which('kicad-cli')
    if found:return found
    for candidate in _windows_candidates():
        if candidate.is_file():return str(candidate)
    raise ValueError('KiCad10 kicad-cli not found. Install KiCad10 or choose its executable.')


def _run(cli: str, args: list[str]) -> str:
    try:
        result=subprocess.run([cli]+args,shell=False,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except (OSError,subprocess.TimeoutExpired) as error:
        raise ValueError('KiCad command unavailable or timed out: '+str(error)[:300]) from error
    if result.returncode:
        raise ValueError('KiCad command failed: '+(result.stderr or result.stdout)[-500:])
    return result.stdout.strip()


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():raise ValueError('KiCad requires regular local files')
    with path.open('rb') as stream:data=stream.read(MAX_FILE+1)
    if not 1<=len(data)<=MAX_FILE:raise ValueError('KiCad file must contain1..16MiB')
    return data


def _snapshot(source: Path, directory: Path) -> tuple[Path,tuple[tuple[Path,bytes],...]]:
    rows=[]
    for path in (source,source.with_suffix('.kicad_pro'),source.with_suffix('.kicad_dru')):
        if path==source or path.exists():
            data=_read(path);(directory/path.name).write_bytes(data);rows.append((path,data))
    return directory/source.name,tuple(rows)


def _fresh(rows: tuple[tuple[Path,bytes],...]) -> None:
    if any(_read(path)!=data for path,data in rows):raise ValueError('KiCad source changed during export. Send again.')


def _outputs(directory: Path) -> tuple[tuple[TransferFile,...],tuple[bytes,...],tuple[str,...]]:
    records=[];contents=[];empty=[]
    suffixes={'-F_Cu.gbr':('gerber','F.Cu'),'-B_Cu.gbr':('gerber','B.Cu'),'-Edge_Cuts.gbr':('gerber','Edge.Cuts'),'-PTH.drl':('excellon','PTH'),'-NPTH.drl':('excellon','NPTH')}
    for path in sorted(directory.iterdir()):
        pair=next((v for k,v in suffixes.items() if path.name.endswith(k)),None)
        if pair is None:continue
        data=_read(path);kind,role=pair
        material=bool(re.search(rb'(?:^|\*)[^*%]*D0?[13]\*',data)) if kind=='gerber' else bool(re.search(rb'(?m)^[XY][+-]?\d',data))
        if not material:
            if role=='Edge.Cuts':raise ValueError('KiCad board needs nonempty Edge.Cuts')
            empty.append(path.name);continue
        records.append(TransferFile(path.name,kind,role,sha256(data).hexdigest(),len(data)));contents.append(data)
    expected=set(suffixes)
    present={key for key in suffixes if any(p.name.endswith(key) for p in directory.iterdir())}
    if present!=expected:raise ValueError('KiCad output missing a selected production file')
    roles={r.role for r in records}
    if 'Edge.Cuts' not in roles or not roles&{'F.Cu','B.Cu'}:raise ValueError('KiCad output missing copper or outline')
    return tuple(records),tuple(contents),tuple(empty)


def export_board(board: Path, output: Path, *, kicad_cli: str | None = None) -> Path:
    source=Path(board).resolve();destination=Path(output).resolve()
    if source.suffix.lower()!='.kicad_pcb' or destination.suffix.lower()!='.mcam-transfer' or destination==source:raise ValueError('Select a KiCad PCB and separate transfer destination')
    cli=discover_cli(kicad_cli);version=_run(cli,['version'])
    if re.fullmatch(r'10\.0\.\d+(?:[-+][\w.]+)?',version) is None:raise ValueError('Supported KiCad CLI version is10.0.x')
    with tempfile.TemporaryDirectory(prefix='mikrocam-kicad-') as temp:
        root=Path(temp);snapshot,originals=_snapshot(source,root)
        drc=root/'drc.json';plots=root/'plots';plots.mkdir()
        _run(cli,['pcb','drc','--format','json','--refill-zones','--save-board','--output',str(drc),str(snapshot)])
        raw_drc=_read(drc);counts=drc_counts(raw_drc);_fresh(originals)
        _run(cli,['pcb','export','gerbers','--layers','F.Cu,B.Cu,Edge.Cuts','--no-protel-ext','--output',str(plots)+os.sep,str(snapshot)])
        _run(cli,['pcb','export','drill','--format','excellon','--drill-origin','absolute','--excellon-units','mm','--excellon-zeros-format','decimal','--excellon-separate-th','--output',str(plots)+os.sep,str(snapshot)])
        rows,contents,empty=_outputs(plots);_fresh(originals)
        manifest=TransferManifest(source.name,sha256(originals[0][1]).hexdigest(),version,rows,empty,sha256(raw_drc).hexdigest(),*counts)
        write_package(destination,TransferPackage(manifest,raw_drc,contents))
    return destination
