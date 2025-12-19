from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class ThreadStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    idle: _ClassVar[ThreadStatus]
    busy: _ClassVar[ThreadStatus]
    interrupted: _ClassVar[ThreadStatus]
    error: _ClassVar[ThreadStatus]
idle: ThreadStatus
busy: ThreadStatus
interrupted: ThreadStatus
error: ThreadStatus
