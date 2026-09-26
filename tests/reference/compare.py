"""Offline, read-only comparison against an explicitly selected frozen baseline."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mikrocam.core.reference_compare import (
    ReferencePath, ReferenceTool, _tolerance, compare_geometry_sets, compare_paths, compare_tools,
)
from mikrocam.core.reference_gcode import compare_gcode
from reference.reference_data import load_capture, load_config, load_manifest


def _tool(value: dict) -> ReferenceTool:
    return ReferenceTool(value['id'], value['diameter_mm'], tuple(tuple(p) for p in value['drills']),
                         tuple(tuple(tuple(p) for p in slot) for slot in value['slots']))


def _outcome(board_id: str, stage: dict, outcome: str, diagnostic: str | None,
             metrics: dict | None = None) -> dict:
    return dict(board_id=board_id, input_path=stage.get('input_path'), stage=stage.get('stage', 'capture'),
                outcome=outcome, diagnostic=diagnostic, metrics=metrics or {})


def compare_stage(board_id: str, expected: dict, actual: dict, *, distance_mm: float,
                  area_mm2: float) -> dict:
    """Compare a validated stage, retaining failed/unsupported evidence as indeterminate."""
    if expected['status'] != 'ok' or actual['status'] != 'ok':
        diagnostic = (f"Baseline {expected['status']}: {expected['diagnostic']}; "
                      f"candidate {actual['status']}: {actual['diagnostic']}")
        return _outcome(board_id, expected, 'indeterminate', diagnostic)
    metrics, matches = {}, expected['source_units'] == actual['source_units']
    try:
        first, second = expected['geometry_wkb'], actual['geometry_wkb']
        metrics['geometry_counts'] = [len(first), len(second)]
        if first or second:
            geometry = compare_geometry_sets(first, second, distance_mm=distance_mm, area_mm2=area_mm2)
            metrics['geometry'] = [asdict(geometry)]
            matches = matches and geometry.matches
        if expected['stage'] == 'cnc':
            paths = compare_paths([ReferencePath(tuple(p['kind']), p['wkb_hex']) for p in expected['paths']],
                                  [ReferencePath(tuple(p['kind']), p['wkb_hex']) for p in actual['paths']],
                                  distance_mm=distance_mm)
            words = compare_gcode(expected['gcode'], actual['gcode'], distance_mm=distance_mm)
            metrics.update(paths=asdict(paths), gcode=asdict(words))
            matches = matches and paths.matches and words.matches
        if expected['stage'] == 'excellon':
            tools = compare_tools([_tool(value) for value in expected['tools']],
                                  [_tool(value) for value in actual['tools']], distance_mm=distance_mm)
            metrics['tools'] = asdict(tools)
            matches = matches and tools.matches
    except (ValueError, TypeError) as error:
        return _outcome(board_id, expected, 'indeterminate', str(error), metrics)
    diagnostic = None if matches else 'Captured geometry, ordering, units or emitted instructions differ'
    return _outcome(board_id, expected, 'match' if matches else 'difference', diagnostic, metrics)


def _compatible(expected: dict, actual: dict) -> None:
    if expected['configuration']['requested'] != actual['configuration']['requested']:
        raise ValueError('Requested capture configurations differ')
    for key in ('python', 'architecture', 'dependencies', 'harness_sha256'):
        if expected['runtime'][key] != actual['runtime'][key]:
            raise ValueError(f'Runtime evidence differs: {key}; use the same capture environment/harness')


def _load_board(path: Path, engine: str, board: dict, manifest: dict,
                config: dict, results: list) -> dict | None:
    identifier = board['id']
    try:
        return load_capture(path, manifest=manifest, config=config,
                            expected_engine=engine, expected_board=identifier)
    except (ValueError, OSError, KeyError) as error:
        results.append(_outcome(identifier, {}, 'indeterminate', str(error)))
    # Only structurally valid evidence can supply additional missing-stage context.
    try:
        data = load_capture(path, config=config, expected_engine=engine, expected_board=identifier)
        required = {(file['path'], stage) for file in board['files']
                    for stage in config['stages'][file['role']]}
        captured = {(stage['input_path'], stage['stage']) for stage in data['stages']}
        side = 'candidate' if engine == 'current' else 'baseline'
        for input_path, stage in sorted(required - captured):
            results.append(_outcome(identifier, dict(input_path=input_path, stage=stage),
                                    'indeterminate', f'Missing requested {side} stage'))
    except (ValueError, OSError, KeyError):
        pass  # The primary validation failure remains in the report.
    return None


def compare_directories(*, baseline: str, goldens: Path, candidate: Path, manifest_path: Path,
                        config_path: Path, distance_mm: float, area_mm2: float) -> dict:
    """Validate every admitted board's artifacts and preserve complete contextual results."""
    distance, area = _tolerance(distance_mm, 'distance_mm'), _tolerance(area_mm2, 'area_mm2')
    manifest, config = load_manifest(manifest_path), load_config(config_path)
    results, source, candidate_identity = [], None, None
    for board in manifest['boards']:
        identifier = board['id']
        try:
            expected = _load_board(goldens / f'{identifier}.json.gz', baseline, board, manifest, config, results)
            actual = _load_board(candidate / f'{identifier}.json.gz', 'current', board, manifest, config, results)
            if expected is None or actual is None:
                continue
            _compatible(expected, actual)
            identity = (actual['engine'], actual['source'], actual['runtime'])
            if candidate_identity is not None and identity != candidate_identity:
                raise ValueError('Candidate directory mixes source revisions, source hashes or runtime evidence')
            candidate_identity, source = identity, actual['source']
            stages = {(stage['input_path'], stage['stage']): stage for stage in actual['stages']}
            for stage in expected['stages']:
                other = stages[(stage['input_path'], stage['stage'])]
                results.append(compare_stage(identifier, stage, other, distance_mm=distance, area_mm2=area))
        except (ValueError, OSError, KeyError) as error:
            results.append(_outcome(identifier, {}, 'indeterminate', str(error)))
    statuses = {value['outcome'] for value in results}
    outcome = ('indeterminate' if not results or 'indeterminate' in statuses
               else 'difference' if 'difference' in statuses else 'match')
    return dict(kind='mikrocam.reference-report', schema_version=1, baseline=baseline,
                candidate_source=source, tolerances=dict(distance_mm=distance, area_mm2=area),
                results=results, outcome=outcome)


def _publish(path: Path, report: dict) -> None:
    data = (json.dumps(report, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.reference-report-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)  # Exclusive publication: never replace a user's existing file.
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', choices=('legacy8994', 'evo'), required=True)
    for name in ('goldens', 'candidate', 'manifest', 'config', 'report'):
        parser.add_argument(f'--{name}', type=Path, required=True)
    parser.add_argument('--distance-mm', type=float, required=True)
    parser.add_argument('--area-mm2', type=float, required=True)
    args = parser.parse_args(argv)
    try:
        target = args.report.resolve()
        protected = (args.goldens.resolve(), args.candidate.resolve(), args.manifest.resolve().parent)
        if any(target.is_relative_to(root) for root in protected):
            raise ValueError('Report must be outside golden, candidate and corpus directories')
        if target.exists():
            raise FileExistsError(f'Report already exists: {target}')
        report = compare_directories(baseline=args.baseline, goldens=args.goldens, candidate=args.candidate,
                                     manifest_path=args.manifest, config_path=args.config,
                                     distance_mm=args.distance_mm, area_mm2=args.area_mm2)
        _publish(target, report)
    except (ValueError, OSError) as error:
        print(f'Comparison unavailable: {error}', file=sys.stderr)
        return 2
    counts = {status: sum(item['outcome'] == status for item in report['results'])
              for status in ('match', 'difference', 'indeterminate')}
    print(f"{report['outcome']}: {counts}; report={target}")
    return {'match': 0, 'difference': 1, 'indeterminate': 2}[report['outcome']]


if __name__ == '__main__':
    raise SystemExit(main())
