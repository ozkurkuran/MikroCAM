"""Atomic local package publication and bounded ZIP loading without extractall."""
import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile
from mikrocam.core.kicad_transfer import MAX_TOTAL,MAX_FILE,MAX_MANIFEST,TransferPackage,json_object,manifest_from_dict,manifest_to_dict


def write_package(path: Path, package: TransferPackage) -> None:
    if type(package) is not TransferPackage:raise ValueError('Validated transfer package required')
    destination=Path(path)
    destination.parent.mkdir(parents=True,exist_ok=True)
    descriptor,temporary=tempfile.mkstemp(prefix='.mcam-transfer-',suffix='.tmp',dir=destination.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',json.dumps(manifest_to_dict(package.manifest),ensure_ascii=False,separators=(',',':')).encode('utf-8'))
            archive.writestr('drc.json',package.drc_bytes)
            for row,data in zip(package.manifest.files,package.contents):archive.writestr('files/'+row.name,data)
        read_package(Path(temporary))
        os.replace(temporary,destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _bounded(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    if not 1<=info.file_size<=limit or info.flag_bits&1 or stat.S_IFMT(info.external_attr>>16) not in (0,stat.S_IFREG):
        raise ValueError('Invalid transfer archive member')
    if info.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):raise ValueError('Unsupported archive compression')
    with archive.open(info) as stream:data=stream.read(limit+1)
    if len(data)!=info.file_size or len(data)>limit:raise ValueError('Transfer member size exceeded')
    return data


def read_package(path: Path) -> TransferPackage:
    source=Path(path)
    if not source.is_file() or source.is_symlink() or source.stat().st_size>MAX_TOTAL+MAX_MANIFEST:
        raise ValueError('Transfer requires bounded local regular archive')
    try:
        with zipfile.ZipFile(source) as archive:
            members=archive.infolist();names=[i.filename for i in members]
            if not 3<=len(names)<=66 or len(set(names))!=len(names) or sum(i.file_size for i in members)>MAX_TOTAL+MAX_MANIFEST:
                raise ValueError('Transfer inventory/count/total exceeded')
            infos={i.filename:i for i in members}
            if 'manifest.json' not in infos or 'drc.json' not in infos:raise ValueError('Missing transfer manifest/DRC')
            manifest=manifest_from_dict(json_object(_bounded(archive,infos['manifest.json'],MAX_MANIFEST)))
            expected={'manifest.json','drc.json'}|{'files/'+f.name for f in manifest.files}
            if set(names)!=expected:raise ValueError('Transfer inventory mismatch')
            drc=_bounded(archive,infos['drc.json'],MAX_FILE)
            contents=tuple(_bounded(archive,infos['files/'+f.name],min(MAX_FILE,f.byte_count)) for f in manifest.files)
        return TransferPackage(manifest,drc,contents)
    except (zipfile.BadZipFile,KeyError,RuntimeError,EOFError,NotImplementedError) as error:
        raise ValueError('Invalid or corrupted transfer archive') from error
