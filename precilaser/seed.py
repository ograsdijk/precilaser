from abc import ABC
from enums import Enum
from dataclasses import dataclass
import pyvisa

from .device import AbstractPrecilaserDevice


class Seed(AbstractPrecilaserDevice):
    def __init__(
        self,
        resource_name: str,
        header: bytes = b"P",
        terminator=b"\r\n",
        check_start=1,
    ):
        super().__init__(resource_name, header, terminator, check_start)
