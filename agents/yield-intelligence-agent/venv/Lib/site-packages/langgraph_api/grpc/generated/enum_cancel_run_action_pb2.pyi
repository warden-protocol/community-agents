from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class CancelRunAction(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    interrupt: _ClassVar[CancelRunAction]
    rollback: _ClassVar[CancelRunAction]
interrupt: CancelRunAction
rollback: CancelRunAction
