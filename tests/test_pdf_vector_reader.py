"""Authored PDF object streams exercise strict selected-page reader boundaries."""
from hashlib import sha256
from io import BytesIO
import subprocess
import sys

import pytest
from pypdf import PdfWriter, get_configuration
from pypdf.generic import (ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject,
                           NameObject, NumberObject, RectangleObject, TextStringObject)

import mikrocam.bridge.pdf_reader as reader


def pdf(contents=(b'0 0 10 5 re f\n',), *, mutate=None, compressed=False, encrypt=False):
    writer = PdfWriter()
    for content in contents:
        page = writer.add_blank_page(100, 100)
        chunks = content if isinstance(content, tuple) else (content,)
        streams = []
        for chunk in chunks:
            stream = DecodedStreamObject()
            stream.set_data(chunk)
            streams.append(writer._add_object(stream.flate_encode() if compressed else stream))
        page[NameObject('/Contents')] = streams[0] if len(streams) == 1 else ArrayObject(streams)
    if mutate:
        mutate(writer)
    if encrypt:
        writer.encrypt('private')
    result = BytesIO()
    writer.write(result)
    return result.getvalue()


@pytest.mark.parametrize('suffix', [b'1 2', b'(trailing)', b'[]', b'/Name'])
def test_trailing_operands_are_not_silently_discarded(suffix):
    with pytest.raises(ValueError, match='operand'):
        reader.read_pdf_page(pdf((b'0 0 10 5 re f ' + suffix,)), 'tail.pdf', 0)


def test_comments_after_last_command_and_empty_commented_page_are_valid():
    assert len(reader.read_pdf_page(pdf((b'0 0 1 1 re f % final comment',)), 'comment.pdf', 0).commands) == 2
    assert reader.read_pdf_page(pdf((b'% comment only',)), 'empty.pdf', 0).commands == ()


def test_operator_limit_stops_parser_before_later_operations_are_materialized(monkeypatch):
    monkeypatch.setattr(reader, 'MAX_PDF_OPERATORS', 3)
    calls = []
    original = reader._OperationList.append

    def append(instance, operation):
        calls.append(operation[1])
        return original(instance, operation)

    monkeypatch.setattr(reader._OperationList, 'append', append)
    with pytest.raises(ValueError, match='operator'):
        reader.read_pdf_page(pdf((b'q Q ' * 1000,)), 'many.pdf', 0)
    assert calls == [b'q', b'Q', b'q', b'Q']


def test_exact_source_identity_and_distinct_selected_page_commands():
    data = pdf((b'0 0 10 5 re f\n', b'20 30 m 40 50 l S\n'))
    info = reader.inspect_pdf_bytes(data, 'two.pdf')
    assert info.source_name == 'two.pdf' and info.source_sha256 == sha256(data).hexdigest()
    assert tuple(p.index for p in info.pages) == (0, 1)
    first = reader.read_pdf_page(data, 'two.pdf', 0)
    second = reader.read_pdf_page(data, 'two.pdf', 1)
    assert first.document == second.document == info
    assert [(c.operator, c.operands) for c in first.commands] == [('re', (0, 0, 10, 5)), ('f', ())]
    assert [c.operator for c in second.commands] == ['m', 'l', 'S']


@pytest.mark.parametrize('compressed', [False, True])
def test_joint_content_arrays_preserve_command_order(compressed):
    program = reader.read_pdf_page(pdf(((b'q\n', b'1 0 0 1 10 20 cm\n', b'0 0 4 5 re f Q\n'),),
                                       compressed=compressed), 'array.pdf', 0)
    assert [c.operator for c in program.commands] == ['q', 'cm', 're', 'f', 'Q']


def test_inherited_boxes_rotation_userunit_and_crop_intersection():
    def mutate(writer):
        page = writer.pages[0]
        del page['/MediaBox']
        parent = writer._pages.get_object()
        parent[NameObject('/MediaBox')] = RectangleObject((10, 20, 110, 120))
        parent[NameObject('/CropBox')] = RectangleObject((0, 30, 100, 150))
        parent[NameObject('/Rotate')] = NumberObject(-90)
        page[NameObject('/UserUnit')] = FloatObject(2)
    page = reader.inspect_pdf_bytes(pdf(mutate=mutate), 'inherited.pdf').pages[0]
    assert page.media_box == (10, 20, 110, 120)
    assert page.crop_box == (10, 30, 100, 120)
    assert page.rotation == 270 and page.user_unit == 2


@pytest.mark.parametrize(('key', 'value'), [
    ('/MediaBox', RectangleObject((0, 0, 0, 100))),
    ('/CropBox', RectangleObject((200, 200, 300, 300))),
    ('/Rotate', NumberObject(45)), ('/Rotate', FloatObject(90.5)),
    ('/UserUnit', NumberObject(0)), ('/UserUnit', NumberObject(75001)),
    ('/UserUnit', TextStringObject('1')),
])
def test_invalid_page_facts_reject_whole_inspection(key, value):
    def mutate(writer):
        writer.pages[0][NameObject(key)] = value
    with pytest.raises(ValueError):
        reader.inspect_pdf_bytes(pdf(mutate=mutate), 'invalid-page.pdf')


def test_only_selected_page_content_is_decoded_and_checked(monkeypatch):
    monkeypatch.setattr(reader, 'MAX_PDF_STREAM_BYTES', 64)
    data = pdf((b'0 0 4 5 re f\n', b' ' * 1024 + b'/Bad Do\n'), compressed=True)
    assert len(reader.inspect_pdf_bytes(data, 'selection.pdf').pages) == 2
    assert reader.read_pdf_page(data, 'selection.pdf', 0).commands
    with pytest.raises(ValueError):
        reader.read_pdf_page(data, 'selection.pdf', 1)


@pytest.mark.parametrize('content', [b'/X Do', b'/G gs', b'/S sh', b'/Pattern cs', b'(visible) Tj',
                                    b'[(visible)] TJ', b'(visible)\x27', b'1 2 (visible)"',
                                    b'/OC /Layer BDC', b'/Layer BMC', b'EMC', b'unknown',
                                    b'BI /W 1 /H 1 /BPC 8 /CS /G ID X EI'])
def test_visible_or_unknown_unsupported_operators_are_not_silently_dropped(content):
    with pytest.raises(ValueError, match='PDF|unsupported|Unsupported'):
        reader.read_pdf_page(pdf((b'0 0 4 5 re f\n' + content,)), 'unsupported.pdf', 0)


def test_numeric_arrays_names_and_empty_text_setup_translate_without_paint_guess():
    content = b'[] 0 d BT /F1 12 Tf 1 0 0 1 0 0 Tm ET /RelativeColorimetric ri\n'
    program = reader.read_pdf_page(pdf((content,)), 'setup.pdf', 0)
    assert program.commands[0].operands == ((), 0)
    assert program.commands[2].operands == ('/F1', 12)
    assert program.commands[-1].operands == ('/RelativeColorimetric',)


@pytest.mark.parametrize('content', [b'<< /A 1 >> q', b'[[1]] 0 d', b'[' + b'1 ' * 65 + b'] 0 d',
                                    b'/' + b'A' * 129 + b' 12 Tf', b'1 2 3 4 5 6 7 8 9 cm',
                                    b'1000000001 w'])
def test_complex_or_oversized_operand_records_reject(content):
    with pytest.raises(ValueError):
        reader.read_pdf_page(pdf((content,)), 'operands.pdf', 0)


@pytest.mark.parametrize('compressed', [False, True])
def test_selected_stream_decoded_limit_rejects_before_commands(compressed, monkeypatch):
    monkeypatch.setattr(reader, 'MAX_PDF_STREAM_BYTES', 64)
    with pytest.raises(ValueError, match='limit|length|budget|bytes'):
        reader.read_pdf_page(pdf((b' ' * 65,), compressed=compressed), 'large.pdf', 0)


def test_contents_array_joint_limit_includes_inserted_separators(monkeypatch):
    monkeypatch.setattr(reader, 'MAX_PDF_STREAM_BYTES', 64)
    with pytest.raises(ValueError, match='limit|length|budget|bytes'):
        reader.read_pdf_page(pdf(((b' ' * 32, b' ' * 32),)), 'joint.pdf', 0)


def test_operator_cap_stops_collection_at_limit_and_resets_configuration(monkeypatch):
    monkeypatch.setattr(reader, 'MAX_PDF_OPERATORS', 3)
    before = get_configuration()
    assert len(reader.read_pdf_page(pdf((b'q Q q',)), 'cap.pdf', 0).commands) == 3
    with pytest.raises(ValueError, match='operator|limit'):
        reader.read_pdf_page(pdf((b'q Q q Q q Q',)), 'over-cap.pdf', 0)
    assert get_configuration() is before


def test_annotations_and_group_rejection_apply_to_selected_page_only():
    def mutate(writer):
        writer.pages[1][NameObject('/Annots')] = ArrayObject([DictionaryObject()])
        writer.pages[1][NameObject('/Group')] = DictionaryObject({NameObject('/S'): NameObject('/Transparency')})
    data = pdf((b'0 0 5 5 re f', b'0 0 5 5 re f'), mutate=mutate)
    assert reader.read_pdf_page(data, 'annotations.pdf', 0).commands
    with pytest.raises(ValueError):
        reader.read_pdf_page(data, 'annotations.pdf', 1)


@pytest.mark.parametrize('value', [DictionaryObject(), NumberObject(0)])
def test_falsey_malformed_annotation_containers_are_rejected(value):
    def mutate(writer):
        writer.pages[0][NameObject('/Annots')] = value
    with pytest.raises(ValueError, match='annotation|Annots'):
        reader.read_pdf_page(pdf(mutate=mutate), 'bad-annots.pdf', 0)


def test_indirect_empty_annotation_array_is_valid():
    def mutate(writer):
        writer.pages[0][NameObject('/Annots')] = writer._add_object(ArrayObject())
    assert reader.read_pdf_page(pdf(mutate=mutate), 'empty-annots.pdf', 0).commands


def test_unused_external_actions_and_resources_are_not_executed_or_decoded():
    def mutate(writer):
        bomb = DecodedStreamObject()
        bomb.set_data(b' ' * 100000)
        image = writer._add_object(bomb.flate_encode())
        writer.pages[0][NameObject('/Resources')] = DictionaryObject({
            NameObject('/XObject'): DictionaryObject({NameObject('/Unused'): image})})
        writer.root_object[NameObject('/OpenAction')] = DictionaryObject({
            NameObject('/S'): NameObject('/JavaScript'),
            NameObject('/JS'): TextStringObject('app.alert("not executed")')})
    assert reader.read_pdf_page(pdf(mutate=mutate), 'unused.pdf', 0).commands


@pytest.mark.parametrize('index', [True, -1, 1, '0'])
def test_selected_index_is_exact_and_within_actual_pages(index):
    with pytest.raises(ValueError):
        reader.read_pdf_page(pdf(), 'one.pdf', index)


@pytest.mark.parametrize(('data', 'name'), [(b'', 'x'), (b'%PDF-9.9\n', 'x'), (b'not pdf', 'x'),
                                           ('%PDF-1.7', 'x'), (b'%PDF-1.7\n', ''),
                                           (b'%PDF-1.7\n', 'é' * 129)])
def test_invalid_source_arguments_fail(data, name):
    with pytest.raises(ValueError):
        reader.inspect_pdf_bytes(data, name)


def test_encrypted_and_excessive_pages_reject_inspection():
    with pytest.raises(ValueError, match='encrypt|Encrypted'):
        reader.inspect_pdf_bytes(pdf(encrypt=True), 'secret.pdf')
    with pytest.raises(ValueError, match='page|Page'):
        reader.inspect_pdf_bytes(pdf(tuple(b'' for _ in range(129))), 'many.pdf')


def test_malformed_page_tree_kids_and_count_are_not_silently_skipped():
    def bad_child(writer):
        writer._pages.get_object()['/Kids'].append(NumberObject(7))
    def bad_count(writer):
        writer._pages.get_object()[NameObject('/Count')] = NumberObject(2)
    for mutate in (bad_child, bad_count):
        with pytest.raises(ValueError, match='tree|Tree|page|Page|Count'):
            reader.inspect_pdf_bytes(pdf(mutate=mutate), 'broken-tree.pdf')


def test_source_size_and_tree_entry_caps(monkeypatch):
    monkeypatch.setattr(reader, 'MAX_PDF_BYTES', 32)
    with pytest.raises(ValueError, match='limit|bytes'):
        reader.inspect_pdf_bytes(pdf(), 'large-source.pdf')
    monkeypatch.setattr(reader, 'MAX_PDF_BYTES', 16777216)
    monkeypatch.setattr(reader, 'MAX_PAGE_TREE_ENTRIES', 1)
    with pytest.raises(ValueError, match='tree|Tree|limit'):
        reader.inspect_pdf_bytes(pdf((b'', b'')), 'tree-cap.pdf')


def test_reader_module_import_does_not_load_optional_pypdf():
    script = 'import sys; import mikrocam.bridge.pdf_reader; assert "pypdf" not in sys.modules'
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr


def test_bridge_and_ui_import_without_pypdf_and_invocation_is_actionable():
    script = '''
import builtins
original = builtins.__import__
def unavailable(name, *args, **kwargs):
    if name == 'pypdf' or name.startswith('pypdf.'):
        raise ImportError('deliberately unavailable')
    return original(name, *args, **kwargs)
builtins.__import__ = unavailable
import mikrocam.bridge.pdf_import
import mikrocam.ui.pdf_import
from mikrocam.bridge.pdf_reader import inspect_pdf_bytes
try:
    inspect_pdf_bytes(b'%PDF-1.7\\n', 'missing.pdf')
except ValueError as error:
    assert 'pypdf==6.19.0' in str(error), str(error)
else:
    raise AssertionError('Missing parser should be actionable')
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
