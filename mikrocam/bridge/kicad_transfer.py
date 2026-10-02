"""Validate every KiCad package member before preparing the existing import owner."""
from pathlib import Path
from mikrocam.core.kicad_transfer import TransferPackage,TransferManifest,manifest_to_dict,manifest_from_dict
from mikrocam.core.manufacturing_models import ManufacturingFile,ManufacturingAssignment,ManufacturingReview
from mikrocam.importers.manufacturing_classify import inspect_manufacturing_bytes
from mikrocam.bridge.manufacturing_import import review_manufacturing_files


def prepare_transfer(package: TransferPackage, directory: Path) -> ManufacturingReview:
    if type(package) is not TransferPackage:raise ValueError('Validated KiCad package required')
    inspected=[]
    for row,data in zip(package.manifest.files,package.contents):
        known=inspect_manufacturing_bytes(data,row.name)
        if known.format_hint!=row.kind or known.units_hint!='MM' or known.role_hint not in (row.role,'unknown'):
            raise ValueError('KiCad member format/role/units contradicts its production metadata: '+row.name)
        inspected.append(known)
    root=Path(directory);root.mkdir(exist_ok=True,parents=True)
    files=[];assignments=[]
    for i,(row,data,known) in enumerate(zip(package.manifest.files,package.contents,inspected)):
        path=root/row.name
        with path.open('xb') as stream:stream.write(data)
        files.append(ManufacturingFile(str(path),data,known))
        assignments.append(ManufacturingAssignment(i,row.kind,row.role,Path(row.name).stem))
    return review_manufacturing_files(tuple(files),tuple(assignments))


def attach_transfer_metadata(owner: object,manifest: TransferManifest) -> None:
    """Persist bounded board/DRC/member provenance through existing object options."""
    owner.obj_options['kicad_transfer']=manifest_to_dict(manifest)


def read_transfer_metadata(owner: object) -> TransferManifest | None:
    value=owner.obj_options.get('kicad_transfer')
    return None if value is None else manifest_from_dict(value)
