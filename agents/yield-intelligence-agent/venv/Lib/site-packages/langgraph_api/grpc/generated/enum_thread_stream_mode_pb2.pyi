from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class ThreadStreamMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    unknown: _ClassVar[ThreadStreamMode]
    lifecycle: _ClassVar[ThreadStreamMode]
    run_modes: _ClassVar[ThreadStreamMode]
    state_update: _ClassVar[ThreadStreamMode]
unknown: ThreadStreamMode
lifecycle: ThreadStreamMode
run_modes: ThreadStreamMode
state_update: ThreadStreamMode
