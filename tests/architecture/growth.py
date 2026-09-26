"""Git-aware signed growth budget for the ten largest baseline legacy modules."""

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


class GrowthError(ValueError):
    """An invalid baseline, unavailable history or exceeded growth budget."""


def _git(repo, *args, input=None):
    try:
        result = subprocess.run(
            ['git', *args], cwd=repo, input=input, capture_output=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, 'stderr', b'').decode('utf-8', errors='replace').strip()
        raise GrowthError(
            f"Git history unavailable for {' '.join(args)}: {detail or error}. "
            'Run git fetch origin main and git fetch --unshallow if this checkout is shallow; '
            'set MIKROCAM_BASE_REF to the available feature base commit.'
        ) from error
    return result.stdout


def _application_path(path):
    parts = PurePosixPath(path).parts
    if not parts or path != '/'.join(parts) or '\\' in path or ':' in path:
        return False
    if path.startswith('/') or any(part in ('.', '..') for part in parts):
        return False
    if not path.endswith('.py'):
        return False
    return len(parts) == 1 or parts[0].startswith('app') or parts[0] in {
        'Utils', 'services', 'preprocessors', 'tclCommands',
    }


def _revision_counts(repo, revision, paths=None):
    """Read Git blobs in one batch; platform checkout newline conversion is irrelevant."""
    entries = _git(repo, 'ls-tree', '-rz', revision).split(b'\0')
    selected = []
    for entry in entries:
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        _, kind, oid = metadata.split()
        path = raw_path.decode('utf-8')
        if kind == b'blob' and (path in paths if paths is not None else _application_path(path)):
            selected.append((path, oid))
    if not selected:
        return {}
    output = _git(repo, 'cat-file', '--batch', input=b'\n'.join(oid for _, oid in selected) + b'\n')
    counts, offset = {}, 0
    for path, _ in selected:
        end = output.index(b'\n', offset)
        size = int(output[offset:end].split()[-1])
        content = output[end + 1:end + 1 + size]
        counts[path] = len(content.splitlines())
        offset = end + size + 2
    return counts


def load_baseline(repo, manifest):
    try:
        record = json.loads(Path(manifest).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise GrowthError(f'Cannot read legacy baseline {manifest}: {error}. Restore the reviewed record.') from error
    if not isinstance(record, dict) or set(record) != {'schema_version', 'revision', 'budget', 'files'}:
        raise GrowthError('Malformed legacy baseline: expected schema_version, revision, budget and files.')
    if type(record['schema_version']) is not int or record['schema_version'] != 1:
        raise GrowthError('Unsupported legacy baseline schema_version; require schema 1.')
    if type(record['budget']) is not int or record['budget'] != 50:
        raise GrowthError('Invalid legacy baseline budget: the constitutional limit is 50.')
    revision, files = record['revision'], record['files']
    if not isinstance(revision, str) or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', revision):
        raise GrowthError('Invalid legacy baseline revision: require an immutable full commit hash.')
    if not isinstance(files, dict) or len(files) != 10 or any(
        not _application_path(path) or type(count) is not int or count < 0 for path, count in files.items()
    ):
        raise GrowthError('Malformed legacy baseline files: require ten application Python paths with nonnegative counts.')
    resolved = _git(repo, 'rev-parse', '--verify', f'{revision}^{{commit}}').decode().strip()
    if resolved != revision:
        raise GrowthError('Invalid legacy baseline revision: require the commit hash, not a tag object.')
    counts = _revision_counts(repo, revision)
    expected = dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10])
    if files != expected:
        raise GrowthError('Legacy baseline counts or top-ten selection do not match its immutable revision. Restore the reviewed record.')
    return record


def select_base(repo, base_ref=None):
    explicit = base_ref if base_ref is not None else os.environ.get('MIKROCAM_BASE_REF')
    if explicit is not None:
        if not explicit.strip():
            raise GrowthError('Empty MIKROCAM_BASE_REF: set it to the available feature base commit.')
        return _git(repo, 'rev-parse', '--verify', f'{explicit}^{{commit}}').decode().strip()
    base = _git(repo, 'merge-base', 'HEAD', 'origin/main').decode().strip()
    head = _git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    if base == head:
        base = _git(repo, 'rev-parse', '--verify', 'HEAD^').decode().strip()
    return base


def _follow_moves(repo, paths, before, after=None, cached=False):
    args = ['diff', '--name-status', '-z', '--find-renames', '--find-copies-harder', '--diff-filter=RC', before]
    if cached:
        args.insert(1, '--cached')
    if after is not None:
        args.append(after)
    fields = _git(repo, *args).split(b'\0')
    moves = []
    while fields and fields[0]:
        _, source, target, *fields = fields
        moves.append((source.decode('utf-8'), target.decode('utf-8')))
    result = set(paths)
    while True:
        additions = {target for source, target in moves if source in result}
        updated = result | additions
        if updated == result:
            return result
        result = updated


def _follow_history(repo, paths, before, after):
    """Follow intermediate moves even if later edits erase endpoint similarity."""
    result = _follow_moves(repo, paths, before, after)
    commits = _git(repo, 'rev-list', '--reverse', '--topo-order', f'{before}..{after}').decode().splitlines()
    for commit in commits:
        parents = _git(repo, 'rev-list', '--parents', '-n', '1', commit).decode().split()[1:]
        for parent in parents:
            result = _follow_moves(repo, result, parent, commit)
    return result


def _current_counts(repo, paths):
    counts = {}
    for path in sorted(paths):
        target = Path(repo) / path
        if target.is_symlink():
            content = os.readlink(target).encode('utf-8')
        elif target.is_file():
            content = target.read_bytes()
        else:
            content = b''
        counts[path] = len(content.splitlines())
    return counts


def check_growth(repo, manifest, base_ref=None):
    """Validate the record, then enforce the feature's signed combined growth."""
    repo = Path(repo).resolve()
    record = load_baseline(repo, manifest)
    base = select_base(repo, base_ref)
    paths = _follow_history(repo, record['files'], record['revision'], base)
    head = _git(repo, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
    paths = _follow_history(repo, paths, base, head)
    paths = _follow_moves(repo, paths, 'HEAD', cached=True)
    paths = _follow_moves(repo, paths, base)
    before = _revision_counts(repo, base, paths)
    after = _current_counts(repo, paths)
    files = {path: {'before': before.get(path, 0), 'after': count,
                    'delta': count - before.get(path, 0)} for path, count in after.items()}
    total = sum(value['delta'] for value in files.values())
    if total > record['budget']:
        detail = ', '.join(f"{path}: {value['delta']:+d}" for path, value in files.items() if value['delta'])
        raise GrowthError(
            f"Legacy growth {total:+d} exceeds budget {record['budget']} relative to {base}: {detail}. "
            'Reduce legacy growth or document and review a narrowly scoped constitutional exception.'
        )
    return {'base': base, 'budget': record['budget'], 'files': files, 'total': total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('legacy-baseline.json'))
    parser.add_argument('--base', help='feature base revision (otherwise MIKROCAM_BASE_REF or origin/main)')
    args = parser.parse_args()
    try:
        result = check_growth(args.repo, args.manifest, args.base)
    except GrowthError as error:
        parser.exit(1, f'{error}\n')
    print(f"Legacy growth {result['total']:+d}/{result['budget']} relative to {result['base']}")


if __name__ == '__main__':
    main()
