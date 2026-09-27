"""Immutable layer and clip scopes from source XML without geometry/Qt dependencies."""
import pytest

from mikrocam.importers.svg_document import parse_svg_document


def doc(body):
    return parse_svg_document(('<svg width="20mm" height="10mm" viewBox="0 0 20 10">'+body+'</svg>').encode(),'a.svg')


def test_group_clip_scope_is_shared_and_source_shapes_keep_local_definitions():
    result=doc('<defs><clipPath id="clip" transform="translate(1 2)"><rect id="r" width="3" height="4"/></clipPath></defs>'
               '<g id="Copper" transform="translate(5 0)" clip-path="url(#clip)">'
               '<circle cx="2" cy="2" r="1"/><rect width="2" height="2"/></g>')
    first,second=result.elements
    assert first.layer_path == second.layer_path == ('Copper',)
    assert first.clips == second.clips and len(first.clips)==1
    clip=first.clips[0]
    assert clip.matrix == pytest.approx((1.,0.,0.,1.,5.,0.))
    assert clip.elements[0].matrix == (1.,0.,0.,1.,1.,2.)
    assert dict(clip.elements[0].attributes)['width']=='3'
    assert len(result.elements)==2


def test_definition_clip_rule_inherits_its_own_ancestors_not_target():
    result=doc('<defs clip-rule="evenodd"><clipPath id="c"><path d="M0 0H3V3H0Z"/></clipPath></defs>'
               '<rect width="5" height="5" clip-rule="nonzero" clip-path="url(#c)"/>')
    assert result.elements[0].clips[0].elements[0].paint.fill_rule=='evenodd'


def test_hidden_layers_and_child_visibility_override_with_css():
    result=doc('<style>.hide{display:none} .gone{visibility:hidden}</style>'
               '<g id="Hidden" class="hide"><rect width="1" height="1"/></g>'
               '<g id="Parent" class="gone"><rect id="a" width="1" height="1"/>'
               '<rect id="b" width="2" height="2" visibility="visible"/></g>')
    assert len(result.elements)==1 and result.elements[0].layer_path==('Parent',)
    assert dict(result.elements[0].attributes)['id']=='b'


@pytest.mark.parametrize('body',[
    '<rect width="1" height="1" clip-path="url(#missing)"/>',
    '<defs><g id="c"/></defs><rect width="1" height="1" clip-path="url(#c)"/>',
    '<defs><clipPath id="c"><g><rect width="1" height="1"/></g></clipPath></defs><rect width="1" height="1" clip-path="url(#c)"/>',
    '<defs><clipPath id="c" clip-path="url(#c)"><rect width="1" height="1"/></clipPath></defs><rect width="1" height="1" clip-path="url(#c)"/>',
])
def test_invalid_clip_definition_fails_explicitly(body):
    with pytest.raises(ValueError,match='clip|Clip'):
        doc(body)
