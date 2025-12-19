from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class Durability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[Durability]
    ASYNC: _ClassVar[Durability]
    SYNC: _ClassVar[Durability]
    EXIT: _ClassVar[Durability]
UNKNOWN: Durability
ASYNC: Durability
SYNC: Durability
EXIT: Durability
