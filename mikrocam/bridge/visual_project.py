"""Visual payload carrier through existing host Geometry object options."""
from mikrocam.core.interlace_job import VisualInterlaceJob
from .visual_recipe import job_to_payload, job_from_payload

PAYLOAD_KEY = 'mikrocam_visual_interlace'


def attach_visual_job(owner: object, job: VisualInterlaceJob) -> None:
    owner.obj_options[PAYLOAD_KEY] = job_to_payload(job)


def read_visual_job(owner: object) -> VisualInterlaceJob | None:
    payload = owner.obj_options.get(PAYLOAD_KEY)
    return None if payload is None else job_from_payload(payload)
