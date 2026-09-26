"""Explicit-source, bounded-process capture CLI; never updates existing goldens."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from threading import Thread


BASELINES = {'legacy8994': '6ba378bca139aa306f8c94f09461a98f95d3c75b',
             'evo': 'd0a86cf4f1ac41a206b20f316d4a29f28a93bbff'}
MAX_CHILD_BYTES = 128 * 1024 * 1024
MAX_TIMEOUT_SECONDS = 3600


class CaptureFailure(ValueError):
    """A child did not return a bounded usable capture; do not claim CAM success."""


def _git(source: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(source), *args], capture_output=True,
                            text=True, timeout=30)
    if result.returncode:
        raise ValueError(f'Cannot verify source Git history: {result.stderr.strip()}')
    return result.stdout.strip()


def verify_source(source: Path, engine: str, revision: str | None) -> str:
    """Require a full clean revision and prevent relabelling arbitrary source as baseline."""
    source = Path(source).resolve(strict=True)
    if engine not in (*BASELINES, 'current'):
        raise ValueError('Unknown capture engine')
    expected = BASELINES.get(engine)
    if expected is not None and revision is not None and revision != expected:
        raise ValueError('Declared baseline revision differs from its pinned source')
    revision = expected if expected is not None else revision
    if not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision):
        raise ValueError('Current capture requires an explicit full 40-character revision')
    if _git(source, 'rev-parse', '--show-toplevel') != str(source):
        # Git uses forward slashes on Windows; compare resolved paths.
        if Path(_git(source, 'rev-parse', '--show-toplevel')).resolve() != source:
            raise ValueError('Source must be the declared checkout root')
    if _git(source, 'rev-parse', 'HEAD') != revision:
        raise ValueError('Source HEAD does not match the required revision')
    if _git(source, 'status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Dirty source: capture requires a clean checkout')
    return revision


def _timeout(value: float) -> None:
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or not 0 < value <= MAX_TIMEOUT_SECONDS):
        raise ValueError(f'Timeout must be positive and at most {MAX_TIMEOUT_SECONDS} seconds')


def _read_pipe(pipe, output: bytearray, failures: list[str], process: subprocess.Popen) -> None:
    try:
        while chunk := pipe.read(8192):
            if len(output) + len(chunk) > MAX_CHILD_BYTES:
                failures.append('Child exceeded output limit')
                process.kill()
                break
            output.extend(chunk)
    finally:
        pipe.close()


def run_worker(command: list[str], cwd: Path, timeout: float) -> dict:
    """Drain bounded pipes concurrently, kill/reap only this owned child on timeout."""
    _timeout(timeout)
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr, failures = bytearray(), bytearray(), []
    readers = [Thread(target=_read_pipe, args=(pipe, buffer, failures, process), daemon=True)
               for pipe, buffer in ((process.stdout, stdout), (process.stderr, stderr))]
    for reader in readers:
        reader.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        failures.append(f'Child timed out after {timeout} seconds')
        process.kill()
        process.wait()
    finally:
        for reader in readers:
            reader.join()
    if failures or process.returncode:
        detail = stderr.decode('utf-8', errors='replace')[-4000:]
        raise CaptureFailure('; '.join(failures) or f'Child failed ({process.returncode}): {detail}')
    try:
        data = json.loads(stdout.decode('utf-8'))
        if not isinstance(data, dict):
            raise ValueError('Child result must be an object')
        return data
    except (UnicodeError, ValueError) as error:
        raise CaptureFailure(f'Child returned invalid JSON: {error}') from error


def _source_files(source: Path) -> list[dict]:
    files = []
    for relative in _git(source, 'ls-files', '*.py').splitlines():
        if relative.startswith('tests/'):
            continue
        path = (source / relative).resolve(strict=True)
        if not path.is_relative_to(source):
            raise ValueError('Tracked source file escapes checkout')
        files.append({'path': relative, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    if not files:
        raise ValueError('Source contains no tracked application Python files')
    return sorted(files, key=lambda item: item['path'])


def _harness_hash() -> str:
    digest = hashlib.sha256()
    for name in ('capture.py', 'capture_worker.py', 'baseline_host.py', 'reference_data.py',
                 'reference_capture_data.py', '../qt_settings_sandbox.py'):
        digest.update(name.encode('utf-8') + b'\0')
        digest.update((Path(__file__).parent / name).read_bytes())
    return digest.hexdigest()


def _artifact(board: dict, engine: str, source: dict, runtime: dict, config: dict,
              config_hash: str, stages: list[dict]) -> dict:
    return {'kind': 'mikrocam.reference-capture', 'schema_version': 1, 'board_id': board['id'],
            'engine': engine, 'source': source, 'runtime': runtime,
            'inputs': [{'path': item['path'], 'sha256': item['sha256']} for item in board['files']],
            'configuration': {'sha256': config_hash, 'requested': config,
                              'effective_optimization': 'RTree' if engine == 'legacy8994' else 'N'},
            'stages': stages}


def _failed_stages(board: dict, config: dict, diagnostic: str) -> list[dict]:
    return [{'input_path': item['path'], 'stage': stage, 'status': 'error', 'units': 'mm',
             'source_units': None, 'tools': [], 'geometry_wkb': [], 'paths': [],
             'gcode': None, 'diagnostic': diagnostic}
            for item in board['files'] for stage in config['stages'][item['role']]]


def capture_dataset(engine: str, source: Path, python: Path | str, manifest: Path,
                     config_path: Path, output: Path, revision: str | None,
                     timeout: float, board_id: str | None = None) -> list[dict]:
    """Validate provenance first and write complete per-board records to a new directory."""
    output, source = Path(output).resolve(), Path(source).resolve()
    if output.exists():
        raise ValueError('Capture output directory already exists; never overwrite records')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from reference.reference_data import load_manifest, load_config, config_to_json, validate_capture, write_capture
    _timeout(timeout)
    revision = verify_source(source, engine, revision)
    python = Path(python).resolve(strict=True)
    corpus, config = load_manifest(manifest), load_config(config_path)
    boards = [board for board in corpus['boards'] if board_id is None or board['id'] == board_id]
    if not boards:
        raise ValueError('Requested board is not in manifest')
    worker = Path(__file__).with_name('capture_worker.py').resolve()
    runtime = run_worker([str(python), '-I', str(worker), '--runtime'], source, timeout)
    runtime['harness_sha256'] = _harness_hash()
    source_info = {'revision': revision, 'files': _source_files(source)}
    config_hash = hashlib.sha256(config_to_json(config).encode('utf-8')).hexdigest()
    records = []
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='mikrocam-capture-request-') as temp:
        for board in boards:
            request = Path(temp) / 'request.json'
            request.write_text(json.dumps({'source': str(source), 'root': str(Path(manifest).resolve().parent),
                                           'board': board, 'config': config}), encoding='utf-8')
            try:
                result = run_worker([str(python), '-I', str(worker), '--request', str(request)], source, timeout)
                stages = result['stages']
            except (CaptureFailure, KeyError) as error:
                stages = _failed_stages(board, config, f'{board["id"]}: worker failed: {error}')
            verify_source(source, engine, revision)
            if _source_files(source) != source_info['files']:
                raise ValueError('Source file hashes changed during actual capture')
            if _harness_hash() != runtime['harness_sha256']:
                raise ValueError('Capture harness changed during actual capture')
            if load_manifest(manifest) != corpus or load_config(config_path) != config:
                raise ValueError('Corpus or configuration changed during actual capture')
            data = _artifact(board, engine, source_info, runtime, config, config_hash, stages)
            validate_capture(data, manifest=corpus, config=config, expected_engine=engine,
                             expected_board=board['id'])
            write_capture(output / f'{board["id"]}.json.gz', data)
            records.append({'board_id': board['id'],
                            'non_success_stages': sum(stage['status'] != 'ok' for stage in stages)})
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', choices=(*BASELINES, 'current'), required=True)
    for name in ('source', 'python', 'manifest', 'config', 'output'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    parser.add_argument('--revision')
    parser.add_argument('--timeout-seconds', type=float, default=120)
    parser.add_argument('--board')
    args = parser.parse_args(argv)
    try:
        records = capture_dataset(args.engine, args.source, args.python, args.manifest, args.config,
                                  args.output, args.revision, args.timeout_seconds, args.board)
        errors = sum(record['non_success_stages'] for record in records)
        print(f'Capture complete: {len(records)} boards; {errors} non-success CAM stages')
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f'Capture failed: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
