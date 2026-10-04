"""Smoke-test the built Windows artifacts without hardware.

    python release/windows/smoke_binary.py --dist DIR [--native] [--installer] [--report FILE]

1. Extracts the portable ZIP below a path with spaces and Turkish characters.
2. Runs the shipped MikroCAM.exe twice through a Tcl startup script: bundled Gerber/Excellon →
   isolation → CNC job → G-code + project; then reopen the project and write the G-code again.
3. Runs MikroCAMSmoke.exe (same PYZ, not shipped) inside the extracted bundle: frozen-only
   modules, optional dependencies absent, bitmap/SVG/PDF visual jobs and project roundtrip.
4. --native repeats 2-3 on the real desktop (OpenGL render required for the smoke executable).
5. --installer installs setup.exe silently into a temporary per-user folder, checks the
   Start Menu shortcut and HKCU uninstall entry, runs the installed exe, then uninstalls.

Safety: refuses to start while another MikroCAM owns the default IPC pipe or when a MikroCAM
uninstall entry already exists; backs up and restores HKCU\\Software\\Open Source\\FlatCAM_EVO;
redirects APPDATA to a temporary directory. No serial port, camera or machine is opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import release_layout as layout  # noqa: E402
from mikrocam.core import identity  # noqa: E402

SETTINGS_KEY = r'HKCU\Software\Open Source\FlatCAM_EVO'
UNINSTALL_KEY = 'HKCU\\' + layout.nsis_defines(identity, Path(), Path(), Path(), Path(), Path())['REG_KEY']
PIPE_DIR = '\\\\.\\pipe\\'
# flatcam.py reads --shellfile with the ANSI code page (open(..., 'r')), not UTF-8.
SCRIPT_ENCODING = locale.getencoding()
START_MENU = Path(os.environ['APPDATA']) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs'
TCL_WAIT = '''proc wait_for {name} {
  for {set i 0} {$i < 400} {incr i} {
    if {[lsearch -exact [split [get_names] "\\n"] $name] >= 0} { return }
    plot_all
  }
  error "MIKROCAM_SMOKE timeout waiting for $name"
}
proc wait_file {path} {
  for {set i 0} {$i < 400} {incr i} {
    if {[file exists $path] && [file size $path] > 0} { plot_all; plot_all; return }
    plot_all
  }
  error "MIKROCAM_SMOKE timeout waiting for $path"
}
'''


def local_name(preferred: str, fallback: str) -> str:
    """Use non-ASCII directory names that the ANSI code page (and thus Tcl scripts) can carry."""
    try:
        preferred.encode(SCRIPT_ENCODING)
        return preferred
    except UnicodeEncodeError:
        return fallback


def tcl_path(path: Path) -> str:
    return '{' + str(path).replace('\\', '/') + '}'


def guarded(body: str) -> str:
    """Always reach quit_app; a failed step leaves its output missing instead of a hung app."""
    return TCL_WAIT + 'if {[catch {\n' + body + '} err]} { puts "MIKROCAM_SMOKE_ERROR $err" }\nquit_app\n'


def first_script(bundle: Path, out: Path) -> str:
    samples = bundle / '_internal' / 'assets' / 'examples' / 'files'
    return guarded(f'''open_gerber {tcl_path(samples / 'test.gbr')} -outname g
wait_for g
open_excellon {tcl_path(samples / 'test.txt')} -outname d
wait_for d
isolate g -dia 0.2 -passes 1 -combine 1 -outname iso
wait_for iso
cncjob iso -dia 0.2 -z_cut -0.1 -z_move 2 -feedrate 120 -outname cnc
wait_for cnc
write_gcode cnc {tcl_path(out / 'first.nc')}
wait_file {tcl_path(out / 'first.nc')}
save_project {tcl_path(out / 'smoke.FlatPrj')}
wait_file {tcl_path(out / 'smoke.FlatPrj')}
''')


def second_script(out: Path) -> str:
    return guarded(f'''open_project {tcl_path(out / 'smoke.FlatPrj')}
wait_for cnc
write_gcode cnc {tcl_path(out / 'reopened.nc')}
wait_file {tcl_path(out / 'reopened.nc')}
''')


def run(command: list[str] | str, env: dict, log: Path, timeout: int = 300) -> int:
    started = time.monotonic()
    with open(log, 'w', encoding='utf-8', errors='replace') as handle:
        process = subprocess.Popen(command, env=env, stdout=handle, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(process.pid)], capture_output=True)
            raise AssertionError(f'{log.stem} timed out after {timeout}s; see {log}')
    print(f'{log.stem} exit {code} in {time.monotonic() - started:.1f}s', flush=True)
    return code


def leftover_processes(directory: Path) -> list[str]:
    query = ("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -like '%s*' } | "
             "ForEach-Object { $_.ProcessId }") % str(directory).replace("'", "''")
    result = subprocess.run(['powershell', '-NoProfile', '-Command', query], capture_output=True, text=True,
                            errors='replace')
    return result.stdout.split()


def stop_leftovers(directory: Path) -> None:
    """After a failed run, end only processes started from this temporary bundle."""
    for pid in leftover_processes(directory):
        subprocess.run(['taskkill', '/T', '/F', '/PID', pid], capture_output=True)
    deadline = time.monotonic() + 10
    while leftover_processes(directory) and time.monotonic() < deadline:
        time.sleep(0.5)


def gcode_body(path: Path) -> list[str]:
    return [line for line in path.read_text(encoding='utf-8').splitlines() if not line.startswith('(Created on')]


def tcl_journey(exe: Path, env: dict, out: Path, label: str) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for name, text in (('first', first_script(exe.parent, out)), ('second', second_script(out))):
        script = out / f'{name}.tcl'
        script.write_text(text, encoding=SCRIPT_ENCODING)
        code = run([str(exe), f'--shellfile={script}'], env, out / f'{label}-{name}.log')
        assert code == 0, f'{label} {name} exited {code}'
        assert not leftover_processes(exe.parent), f'{label} {name} left MikroCAM processes running'
    first, reopened = gcode_body(out / 'first.nc'), gcode_body(out / 'reopened.nc')
    assert first and first == reopened, f'{label}: reopened project G-code differs'
    return {'gcode_lines': len(first), 'project_bytes': (out / 'smoke.FlatPrj').stat().st_size}


def frozen_smoke(bundle: Path, smoke_exe: Path, env: dict, out: Path, native: bool, label: str) -> dict:
    target = bundle / layout.SMOKE_EXE
    shutil.copyfile(smoke_exe, target)
    try:
        command = [str(target), '--out', str(out)] + (['--native'] if native else [])
        code = run(command, env, out.parent / f'{label}-frozen-smoke.log', timeout=300)
        text = (out.parent / f'{label}-frozen-smoke.log').read_text(encoding='utf-8', errors='replace')
        assert code == 0 and 'FROZEN_SMOKE_PASS' in text, f'{label} frozen smoke failed; see log'
        assert not leftover_processes(bundle), f'{label} frozen smoke left child processes running'
    finally:
        stop_leftovers(bundle)
        target.unlink(missing_ok=True)
    return {'markers': [line.split()[0] for line in text.splitlines() if line.endswith('_OK') or '_OK ' in line]}


def environment(appdata: Path, native: bool) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in {'QT_QPA_PLATFORM', 'PYTHONPATH', 'PYTHONHOME', 'PYTHONUTF8'}}
    env['APPDATA'] = str(appdata)
    appdata.mkdir(parents=True, exist_ok=True)
    if not native:
        env['QT_QPA_PLATFORM'] = 'offscreen'
    return env


def reg(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['reg', *args], capture_output=True, text=True, encoding='oem', errors='replace')


def installer_journey(setup: Path, work: Path, native: bool) -> dict:
    target = work / local_name('Kurulum Dizini ğüş', 'Install Dir ü')
    # NSIS requires /D=path last and unquoted, so the command line is passed verbatim.
    code = run(f'"{setup}" /S /D={target}', dict(os.environ), work / 'setup.log', timeout=600)
    assert code == 0 and (target / layout.APP_EXE).is_file(), 'silent install failed'
    shortcut = START_MENU / f'{identity.NAME}.lnk'
    assert shortcut.is_file(), 'Start Menu shortcut missing'
    query = reg('query', UNINSTALL_KEY)
    assert query.returncode == 0 and identity.VERSION in query.stdout and str(target) in query.stdout
    assert (target / 'config' / 'configuration.txt').read_text() == layout.configuration_text(False)
    appdata = work / 'installed-appdata'
    result = tcl_journey(target / layout.APP_EXE, environment(appdata, native), work / 'installed', 'installed')
    assert (appdata / 'FlatCAM').is_dir(), 'installed app did not use APPDATA\\FlatCAM'
    run([str(target / layout.UNINSTALLER_EXE), '/S'], dict(os.environ), work / 'uninstall.log')
    deadline = time.monotonic() + 120
    while target.exists() and time.monotonic() < deadline:
        time.sleep(0.5)
    assert not target.exists(), f'uninstall left files: {list(target.rglob("*"))[:5]}'
    assert not shortcut.exists(), 'uninstall left the Start Menu shortcut'
    assert reg('query', UNINSTALL_KEY).returncode != 0, 'uninstall left the registry entry'
    assert (appdata / 'FlatCAM').is_dir(), 'uninstall must keep user data'
    return dict(result, installed_to=str(target), user_data_kept=True)


def guards(installer: bool) -> None:
    assert 'NPtest' not in os.listdir(PIPE_DIR), 'A MikroCAM/FlatCAM instance owns the default IPC pipe'
    if installer:
        assert reg('query', UNINSTALL_KEY).returncode != 0, 'MikroCAM is already installed for this user'
        assert not (START_MENU / f'{identity.NAME}.lnk').exists(), 'A MikroCAM shortcut already exists'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable_journeys(dist: Path, names: dict, work: Path, native: bool) -> dict:
    extract = work / local_name('Taşınabilir ğüş paket', 'Portable ü package')
    with zipfile.ZipFile(dist / names['zip']) as archive:
        archive.extractall(extract)
    bundle = extract / names['folder']
    exe = bundle / layout.APP_EXE
    digest = sha256(exe)
    assert (bundle / 'config' / 'configuration.txt').read_text() == layout.configuration_text(True)
    smoke_exe = dist / 'pyinstaller' / names['folder'] / layout.SMOKE_EXE
    results = {}
    for mode in ['offscreen'] + (['native'] if native else []):
        live = mode == 'native'
        env = environment(work / f'{mode}-appdata', live)
        results[f'portable-{mode}'] = tcl_journey(exe, env, work / f'portable-{mode}', f'portable-{mode}')
        results[f'frozen-smoke-{mode}'] = frozen_smoke(bundle, smoke_exe, env, work / f'frozen-{mode}', live,
                                                       f'portable-{mode}')
    assert exe.is_file() and sha256(exe) == digest, 'MikroCAM.exe vanished or changed (antivirus?)'
    results['portable-exe-sha256'] = digest
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--dist', type=Path, required=True)
    parser.add_argument('--native', action='store_true')
    parser.add_argument('--installer', action='store_true')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--keep', action='store_true', help='keep the temporary work directory')
    args = parser.parse_args(argv)
    dist = args.dist.resolve()
    names = layout.artifact_names(identity.NAME, identity.VERSION)
    guards(args.installer)
    work = Path(tempfile.mkdtemp(prefix='mikrocam-binary-smoke-'))
    backup = work / 'settings-backup.reg'
    had_settings = reg('export', SETTINGS_KEY, str(backup), '/y').returncode == 0
    report = {'version': identity.VERSION, 'work': str(work), 'status': 'FAIL'}
    try:
        report.update(portable_journeys(dist, names, work, args.native))
        if args.installer:
            report['installer'] = installer_journey(dist / names['setup'], work, args.native)
        report['status'] = 'PASS'
    finally:
        stop_leftovers(work)
        reg('delete', SETTINGS_KEY, '/f')
        if had_settings:
            restored = reg('import', str(backup))
            assert restored.returncode == 0, restored.stderr
        report['settings_restored'] = had_settings
        text = json.dumps(report, indent=1, ensure_ascii=False)
        print(text)
        if args.report:
            args.report.write_text(text + '\n', encoding='utf-8')
        if report['status'] == 'PASS' and not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
