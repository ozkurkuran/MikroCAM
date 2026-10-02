"""MikroCAM Bridge: standalone official IPC client; exports a live board copy."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


def configuration(path: Path) -> dict:
    try:config=json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError) as error:raise ValueError('MikroCAM Bridge is not configured. Run its installer.') from error
    required={'schema','repo_root','python_executable','transfer_directory'}
    if type(config) is not dict or set(config)!=required or type(config['schema']) is not int or config['schema']!=1:
        raise ValueError('Unsupported MikroCAM Bridge configuration')
    for key in required-{'schema'}:
        if type(config[key]) is not str or not config[key] or not Path(config[key]).is_absolute():raise ValueError('Bridge paths must be absolute')
    if not (Path(config['repo_root'])/'flatcam.py').is_file() or not Path(config['python_executable']).is_file():
        raise ValueError('Configured MikroCAM checkout/Python is unavailable. Run installer again.')
    return config


def transfer(client: object,config: dict) -> Path:
    repo=Path(config['repo_root']);python=Path(config['python_executable'])
    if not repo.is_absolute() or not (repo/'flatcam.py').is_file() or not python.is_file():raise ValueError('MikroCAM checkout/Python unavailable')
    version=client.get_version()
    if version.major!=10 or version.minor!=0:raise ValueError('MikroCAM Bridge currently supports KiCad10.0.x')
    board=client.get_board();name=board.name
    if type(name) is not str or not name or not name.isprintable() or '..' in Path(name).parts or Path(name).suffix.lower()!='.kicad_pcb':
        raise ValueError('Save the named PCB once before sending it to MikroCAM.')
    name=Path(name).name
    if len(name.encode('utf-8'))>256:raise ValueError('PCB filename exceeds supported length')
    cli=client.get_kicad_binary_path('kicad-cli')
    output_dir=Path(config['transfer_directory'])
    if not output_dir.is_absolute():raise ValueError('Transfer directory must be absolute')
    output_dir.mkdir(parents=True,exist_ok=True)
    package=output_dir/(Path(name).stem+'-'+uuid.uuid4().hex+'.mcam-transfer')
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    with tempfile.TemporaryDirectory(prefix='mikrocam-live-board-') as temp:
        copy=Path(temp)/name
        board.save_as(str(copy),overwrite=False,include_project=True)
        if not copy.is_file():raise ValueError('KiCad did not produce a board copy')
        args=[str(python),'-m','mikrocam.kicad',str(copy),'--output',str(package),'--kicad-cli',str(cli)]
        try:result=subprocess.run(args,cwd=repo,shell=False,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=330,creationflags=flags)
        except (OSError,subprocess.TimeoutExpired) as error:raise ValueError('KiCad transfer export failed or timed out') from error
        if result.returncode or not package.is_file():raise ValueError('KiCad production export failed: '+(result.stderr or result.stdout)[-500:])
    try:subprocess.Popen([str(python),str(repo/'flatcam.py'),str(package)],cwd=repo,shell=False,creationflags=flags)
    except OSError as error:raise ValueError('Export completed, but MikroCAM could not start. Open '+str(package)) from error
    return package


def main() -> int:
    try:
        config=configuration(Path(__file__).with_name('config.json'))
        if not os.environ.get('KICAD_API_SOCKET'):raise ValueError('Launch MikroCAM Bridge from the KiCad PCB toolbar with IPC API enabled.')
        from kipy import KiCad
        client=KiCad(client_name='org.mikrocam.bridge',timeout_ms=15000)
        package=transfer(client,config)
        # kicad-python0.8 exposes no public close method; this action process owns its connection.
        print('MikroCAM production transfer: '+str(package))
        return 0
    except Exception as error:
        print('MikroCAM Bridge: '+str(error)[:700],file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
