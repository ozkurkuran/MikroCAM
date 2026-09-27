"""Construct the concrete read-only serial controller without opening a port."""
from mikrocam.machine.controller import MachineController
from .serial_transport import SerialIO


def make_controller(port: str) -> MachineController:
    """Create owned serial I/O; the communication worker performs the explicit connect."""
    return MachineController(SerialIO(port))
