"""Exercise the per-feature signed line budget without application imports."""

import json
from pathlib import Path
import subprocess

import pytest

from growth import GrowthError, check_growth


def git(repo, *args):
    result = subprocess.run(
        ['git', '-c', 'user.name=Growth Test', '-c', 'user.email=growth@example.invalid', *args],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def commit(repo):
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'fixture')
    return git(repo, 'rev-parse', 'HEAD')


def append(repo, path, count):
    with (repo / path).open('a', encoding='utf-8') as stream:
        stream.write('# addition\n' * count)


@pytest.fixture
def repository(tmp_path):
    repo = tmp_path / 'repository with spaces'
    repo.mkdir()
    git(repo, 'init', '-q')
    counts = {'appMain.py': 100}
    counts.update({f'appPlugins/Tool{i}.py': 90 - i for i in range(10)})
    for path, count in counts.items():
        target = repo / path
        target.parent.mkdir(exist_ok=True)
        target.write_text(''.join(f'value_{i} = {i}\n' for i in range(count)), encoding='utf-8')
    for path in ('tests/huge.py', 'assets/huge.py', 'vendor/huge.py', 'mikrocam/core/huge.py'):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('# excluded\n' * 200, encoding='utf-8')
    revision = commit(repo)
    files = dict(sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10])
    manifest = repo / 'legacy-baseline.json'
    manifest.write_text(json.dumps({
        'schema_version': 1, 'revision': revision, 'budget': 50, 'files': files,
    }), encoding='utf-8')
    return repo, manifest, revision


@pytest.mark.parametrize('growth', [0, 50])
def test_accepts_budget_boundary_and_worktree_changes(repository, growth):
    repo, manifest, base = repository
    append(repo, 'appMain.py', growth)
    result = check_growth(repo, manifest, base)
    assert result['total'] == growth
    assert result['base'] == base
    assert result['files']['appMain.py'] == {'before': 100, 'after': 100 + growth, 'delta': growth}


def test_rejects_51_lines(repository):
    repo, manifest, base = repository
    append(repo, 'appMain.py', 51)
    with pytest.raises(GrowthError, match=r'51.*50.*appMain.py'):
        check_growth(repo, manifest, base)


def test_signed_deletions_offset_additions(repository):
    repo, manifest, base = repository
    (repo / 'appPlugins/Tool0.py').unlink()
    append(repo, 'appMain.py', 140)
    result = check_growth(repo, manifest, base)
    assert result['total'] == 50
    assert result['files']['appPlugins/Tool0.py']['delta'] == -90


def test_renamed_modules_remain_in_budget(repository):
    repo, manifest, base = repository
    git(repo, 'mv', 'appMain.py', 'relocated.py')
    append(repo, 'relocated.py', 51)
    commit(repo)
    with pytest.raises(GrowthError, match='relocated.py'):
        check_growth(repo, manifest, base)


def test_recreation_at_original_path_does_not_hide_rename(repository):
    repo, manifest, base = repository
    git(repo, 'mv', 'appMain.py', 'relocated.py')
    append(repo, 'relocated.py', 51)
    (repo / 'appMain.py').write_text('replacement = True\n', encoding='utf-8')
    commit(repo)
    with pytest.raises(GrowthError, match='52'):
        check_growth(repo, manifest, base)


def test_rename_before_feature_base_is_followed(repository):
    repo, manifest, _ = repository
    git(repo, 'mv', 'appMain.py', 'relocated.py')
    base = commit(repo)
    append(repo, 'relocated.py', 50)
    assert check_growth(repo, manifest, base)['total'] == 50


def test_rename_then_large_edit_cannot_lose_identity(repository):
    repo, manifest, base = repository
    git(repo, 'mv', 'appMain.py', 'relocated.py')
    commit(repo)
    append(repo, 'relocated.py', 200)
    commit(repo)
    with pytest.raises(GrowthError, match='200'):
        check_growth(repo, manifest, base)


def test_staged_rename_is_counted_with_unstaged_growth(repository):
    repo, manifest, base = repository
    git(repo, 'mv', 'appMain.py', 'relocated.py')
    append(repo, 'relocated.py', 200)
    with pytest.raises(GrowthError, match='200'):
        check_growth(repo, manifest, base)


def test_budget_is_per_feature_not_since_manifest(repository):
    repo, manifest, _ = repository
    append(repo, 'appMain.py', 40)
    base = commit(repo)
    append(repo, 'appMain.py', 40)
    assert check_growth(repo, manifest, base)['total'] == 40


def test_explicit_environment_base_wins(repository, monkeypatch):
    repo, manifest, base = repository
    monkeypatch.setenv('MIKROCAM_BASE_REF', base)
    assert check_growth(repo, manifest)['base'] == base


def test_local_merge_base_and_latest_main_change(repository, monkeypatch):
    repo, manifest, base = repository
    monkeypatch.delenv('MIKROCAM_BASE_REF', raising=False)
    git(repo, 'update-ref', 'refs/remotes/origin/main', base)
    append(repo, 'appMain.py', 10)
    head = commit(repo)
    assert check_growth(repo, manifest)['base'] == base
    git(repo, 'update-ref', 'refs/remotes/origin/main', head)
    assert check_growth(repo, manifest)['base'] == base


def test_merge_commit_follows_feature_rename_without_false_growth(repository, monkeypatch):
    repo, manifest, _ = repository
    monkeypatch.delenv('MIKROCAM_BASE_REF', raising=False)
    main = git(repo, 'branch', '--show-current')
    git(repo, 'checkout', '-qb', 'feature')
    git(repo, 'mv', 'appMain.py', 'relocated.py')
    append(repo, 'relocated.py', 50)
    commit(repo)
    git(repo, 'checkout', '-q', main)
    append(repo, 'appPlugins/Tool0.py', 1)
    base = commit(repo)
    git(repo, 'merge', '--no-ff', '-qm', 'merge feature', 'feature')
    git(repo, 'update-ref', 'refs/remotes/origin/main', git(repo, 'rev-parse', 'HEAD'))
    result = check_growth(repo, manifest)
    assert result['base'] == base
    assert result['total'] == 50


@pytest.mark.parametrize('base', ['missing-revision', '0' * 40])
def test_missing_history_fails_with_recovery_guidance(repository, base):
    repo, manifest, _ = repository
    with pytest.raises(GrowthError, match=r'fetch.*MIKROCAM_BASE_REF'):
        check_growth(repo, manifest, base)


def test_missing_origin_main_does_not_disable_check(repository, monkeypatch):
    repo, manifest, _ = repository
    monkeypatch.delenv('MIKROCAM_BASE_REF', raising=False)
    with pytest.raises(GrowthError, match=r'origin/main.*fetch.*MIKROCAM_BASE_REF'):
        check_growth(repo, manifest)


@pytest.mark.parametrize('mutation', [
    lambda record: record.update(schema_version=2),
    lambda record: record.update(budget=51),
    lambda record: record.update(revision='HEAD'),
    lambda record: record['files'].update({'../escape.py': 1}),
    lambda record: record['files'].update({'tests/huge.py': 200}),
    lambda record: record['files'].update({'appMain.py': True}),
    lambda record: record['files'].update({'appMain.py': -1}),
    lambda record: record['files'].update({'appMain.py': 99}),
    lambda record: record['files'].pop('appMain.py'),
    lambda record: record['files'].update({'appPlugins/Tool9.py': 81}),
])
def test_malformed_or_falsified_manifest_fails(repository, mutation):
    repo, manifest, base = repository
    record = json.loads(manifest.read_text())
    mutation(record)
    manifest.write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(GrowthError, match='baseline'):
        check_growth(repo, manifest, base)


def test_missing_or_invalid_json_manifest_fails(repository):
    repo, manifest, base = repository
    manifest.write_text('{broken', encoding='utf-8')
    with pytest.raises(GrowthError, match='baseline'):
        check_growth(repo, manifest, base)
    manifest.unlink()
    with pytest.raises(GrowthError, match='baseline'):
        check_growth(repo, manifest, base)


def test_repository_legacy_growth():
    repo = Path(__file__).resolve().parents[2]
    result = check_growth(repo, Path(__file__).with_name('legacy-baseline.json'))
    assert result['total'] <= 50
