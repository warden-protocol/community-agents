from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class RunStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    pending: _ClassVar[RunStatus]
    running: _ClassVar[RunStatus]
    error: _ClassVar[RunStatus]
    success: _ClassVar[RunStatus]
    timeout: _ClassVar[RunStatus]
    interrupted: _ClassVar[RunStatus]
    rollback: _ClassVar[RunStatus]
pending: RunStatus
running: RunStatus
error: RunStatus
success: RunStatus
timeout: RunStatus
interrupted: RunStatus
rollback: RunStatus
