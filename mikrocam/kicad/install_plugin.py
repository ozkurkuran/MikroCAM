"""Targeted, backed-up KiCad IPC plugin installation without CAM dependencies."""
import argparse
import ctypes
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]


def documents_path() -> Path:
    if os.name!='nt':return Path.home()/'Documents'
    from ctypes import wintypes
    class Guid(ctypes.Structure):
        _fields_=[('Data1',wintypes.DWORD),('Data2',wintypes.WORD),('Data3',wintypes.WORD),('Data4',ctypes.c_ubyte*8)]
    guid=Guid.from_buffer_copy(uuid.UUID('fdd39ad0-238f-46af-adb4-6c85480369c7').bytes_le)
    value=ctypes.c_wchar_p()
    result=ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid),0,None,ctypes.byref(value))
    if result:raise OSError('Cannot resolve Windows Documents folder')
    try:return Path(value.value)
    finally:ctypes.windll.ole32.CoTaskMemFree(value)


def _publish(path: Path,data: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.mikrocam-install-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(data)
        os.replace(name,path)
    finally:Path(name).unlink(missing_ok=True)


def _settings(path: Path) -> dict:
    if not path.exists():return {}
    try:
        if path.stat().st_size>1024*1024:raise ValueError('KiCad settings exceed1MiB')
        value=json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,UnicodeError) as error:raise ValueError('KiCad settings invalid; installation stopped without changing them') from error
    if type(value) is not dict or 'api' in value and type(value['api']) is not dict:
        raise ValueError('Invalid KiCad API settings')
    return value


def install_plugin(plugins: Path,settings: Path,python: Path,transfers: Path) -> Path:
    plugins=Path(plugins).resolve();settings=Path(settings).resolve();python=Path(python).resolve();transfers=Path(transfers).resolve()
    if not python.is_file() or not (ROOT/'flatcam.py').is_file():raise ValueError('CAM Python/checkout unavailable')
    current=_settings(settings)
    source=ROOT/'integrations/kicad'
    names=('plugin.json','bridge.py','requirements.txt','icons/app32.png','icons/app64.png')
    data={n:(source/n).read_bytes() for n in names}
    config={'schema':1,'repo_root':str(ROOT),'python_executable':str(python),'transfer_directory':str(transfers)}
    data['config.json']=(json.dumps(config,indent=2)+'\n').encode('utf-8')
    target=plugins/'org.mikrocam.bridge'
    if target.is_symlink():raise ValueError('Refusing symbolic plugin directory')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
    for name in data:
        old=target/name
        for candidate in (old,old.parent,target):
            if candidate.is_symlink() or candidate.is_junction():raise ValueError('Refusing symbolic plugin file/directory')
    backup=plugins.parent/'mikrocam-bridge-backups'/stamp
    for name in data:
        old=target/name
        if old.is_file():
            copy=backup/name;copy.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(old,copy)
    for name,content in data.items():_publish(target/name,content)
    api=dict(current.get('api',{}))
    if api.get('enable_server') is not True:
        if settings.is_file():shutil.copy2(settings,settings.with_name(settings.name+'.mikrocam-backup-'+stamp))
        api['enable_server']=True;current['api']=api
        _publish(settings,(json.dumps(current,indent=2)+'\n').encode('utf-8'))
    transfers.mkdir(parents=True,exist_ok=True)
    return target


def main() -> int:
    parser=argparse.ArgumentParser(description='Install MikroCAM Bridge into KiCad10 PCB Editor')
    parser.add_argument('--plugins',type=Path)
    parser.add_argument('--settings',type=Path)
    parser.add_argument('--python',type=Path,default=Path(sys.executable))
    parser.add_argument('--transfers',type=Path,default=ROOT/'.venv/kicad-transfers')
    args=parser.parse_args()
    plugins=args.plugins or documents_path()/'KiCad/10.0/plugins'
    settings=args.settings or (Path(os.environ['APPDATA'])/'kicad/10.0/kicad_common.json' if os.name=='nt' else Path.home()/'.config/kicad/10.0/kicad_common.json')
    try:print(install_plugin(plugins,settings,args.python,args.transfers))
    except (OSError,ValueError) as error:parser.exit(2,str(error)+'\n')
    return 0


if __name__=='__main__':raise SystemExit(main())
