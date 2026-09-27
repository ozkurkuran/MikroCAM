"""Bounded files, duplicate canonical paths and explicit failed inspection rows."""
from dataclasses import replace
import pytest
from mikrocam.bridge.manufacturing_import import inspect_manufacturing_files, review_manufacturing_files
from mikrocam.core.manufacturing_models import ManufacturingAssignment

GERBER = b'%FSLAX24Y24*%%MOMM*%%ADD10C,1*%D10*X10000Y20000D03*M02*'
DRILL = b'M48\nMETRIC,TZ\nT1C1.0\n%\nT1\nX1.0Y2.0\nM30\n'


def sources(tmp_path):
    paths = [tmp_path / 'board-F_Cu.gbr', tmp_path / 'board-PTH.drl']
    for path, data in zip(paths, (GERBER, DRILL)):
        path.write_bytes(data)
    return tuple(str(path) for path in paths)


def test_inspect_distinct_rows_and_duplicate_paths_without_mutation(tmp_path):
    paths = sources(tmp_path)
    files = inspect_manufacturing_files((*paths, paths[0]))
    assert len(files) == 2 and all(not file.error for file in files)
    assert tuple(file.source_bytes for file in files) == (GERBER, DRILL)
    assert files[0].inspection.format_hint == 'gerber'
    assert files[1].inspection.role_hint == 'PTH'


def test_same_name_and_content_in_different_directories_are_retained(tmp_path):
    paths = []
    for subdir in ('first', 'second'):
        folder = tmp_path / subdir
        folder.mkdir()
        path = folder / 'board-F_Cu.gbr'
        path.write_bytes(GERBER)
        paths.append(str(path))
    files = inspect_manufacturing_files(tuple(paths))
    assert len(files) == 2 and files[0].path != files[1].path
    assert files[0].inspection == files[1].inspection


def test_missing_directory_and_empty_inputs_become_failed_rows(tmp_path):
    empty = tmp_path / 'empty.gbr'
    empty.write_bytes(b'')
    files = inspect_manufacturing_files((str(tmp_path / 'missing.gbr'), str(tmp_path), str(empty)))
    assert len(files) == 3
    assert all(file.inspection is None and file.source_bytes == b'' and file.error for file in files)


@pytest.mark.parametrize('paths', [(), ['a'], ('a',)*65, (None,), ('',)])
def test_invalid_input_path_list_rejects(paths):
    with pytest.raises(ValueError):
        inspect_manufacturing_files(paths)


def test_per_file_and_total_size_bounds(tmp_path, monkeypatch):
    import mikrocam.bridge.manufacturing_import as module
    paths = sources(tmp_path)
    monkeypatch.setattr(module, 'MAX_MANUFACTURING_BYTES', 10)
    assert all(file.error for file in inspect_manufacturing_files(paths))
    monkeypatch.setattr(module, 'MAX_MANUFACTURING_BYTES', 16777216)
    monkeypatch.setattr(module, 'MAX_MANUFACTURING_TOTAL_BYTES', 10)
    with pytest.raises(ValueError, match='total|set'):
        inspect_manufacturing_files(paths)


def test_review_rereads_and_rejects_source_mutation_and_forged_facts(tmp_path):
    paths = sources(tmp_path)
    files = inspect_manufacturing_files(paths)
    assignments = (ManufacturingAssignment(0, 'gerber', 'F.Cu', 'top'),)
    review = review_manufacturing_files(files, assignments)
    assert review.assignments == assignments
    forged = replace(files[0], inspection=replace(files[0].inspection, role_hint='B.Cu'))
    with pytest.raises(ValueError, match='[Ii]nspect|[Rr]eview'):
        review_manufacturing_files((forged, files[1]), assignments)
    from pathlib import Path
    Path(paths[0]).write_bytes(GERBER + b'\nG04 changed*')
    with pytest.raises(ValueError, match='[Ii]nspect|[Rr]eview'):
        review_manufacturing_files(files, assignments)
