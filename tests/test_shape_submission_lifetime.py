"""A render submission completing after removal cannot resurrect object shapes."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('method,collection_name', [('add_shape', 'shapes'),
    ('add_shapes_batch', 'shapes'), ('add_mark_shape', 'mark_shapes')])
def test_submission_already_in_progress_is_discarded_after_removal(method, collection_name):
    from appObjects.AppObjectTemplate import FlatCAMObj, ObjectDeleted
    entered, release = Event(), Event()
    rendered = []
    def submit(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        rendered.append('late shape')
        return [1] if method == 'add_shapes_batch' else 1
    collection = SimpleNamespace(add=submit, add_batch=submit, clear=lambda **kwargs: rendered.clear())
    other = SimpleNamespace(clear=lambda **kwargs: pytest.fail('Cleared an unrelated shape collection'))
    collections = {'shapes': other, 'mark_shapes': other, collection_name: collection}
    obj = SimpleNamespace(deleted=False, drawing_tolerance=.01, **collections)
    function = getattr(FlatCAMObj, method)
    args = ([{'shape': object()}],) if method == 'add_shapes_batch' else ()
    with ThreadPoolExecutor(max_workers=1) as worker:
        future = worker.submit(function, obj, *args)
        try:
            assert entered.wait(5)
            obj.deleted = True
            collection.clear(update=True)
        finally:
            release.set()
        with pytest.raises(ObjectDeleted):
            future.result(timeout=5)
    assert not rendered


@pytest.mark.parametrize('remove_all', [False, True])
def test_collection_marks_objects_deleted_before_clearing_shapes(remove_all):
    from appObjects.ObjectCollection import TreeItem
    observed = []
    obj = SimpleNamespace(deleted=False)
    obj.delete = lambda: setattr(obj, 'deleted', True)
    obj.clear = lambda *args: observed.append(obj.deleted)
    item = SimpleNamespace(obj=obj)
    parent = SimpleNamespace(child_items=[item])
    if remove_all:
        TreeItem.remove_children(parent)
    else:
        TreeItem.remove_child(parent, item)
    assert observed == [True]
    assert not parent.child_items
