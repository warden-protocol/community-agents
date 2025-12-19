from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class StreamMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    unknown: _ClassVar[StreamMode]
    values: _ClassVar[StreamMode]
    updates: _ClassVar[StreamMode]
    checkpoints: _ClassVar[StreamMode]
    tasks: _ClassVar[StreamMode]
    debug: _ClassVar[StreamMode]
    messages: _ClassVar[StreamMode]
    custom: _ClassVar[StreamMode]
    events: _ClassVar[StreamMode]
    messages_tuple: _ClassVar[StreamMode]
unknown: StreamMode
values: StreamMode
updates: StreamMode
checkpoints: StreamMode
tasks: StreamMode
debug: StreamMode
messages: StreamMode
custom: StreamMode
events: StreamMode
messages_tuple: StreamMode
