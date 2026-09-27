"""Separate job wire grammar; manual operations retain their narrow allowlist."""
from mikrocam.core.cnc_job import validate_job_block


def validate_job_command(data: bytes) -> None:
    """Accept a reviewed-source block or the two owner-controlled hold/resume bytes."""
    if type(data) is bytes and data in (b'!', b'~'):
        return
    validate_job_block(data)
