from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class MultitaskStrategy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    reject: _ClassVar[MultitaskStrategy]
    rollback: _ClassVar[MultitaskStrategy]
    interrupt: _ClassVar[MultitaskStrategy]
    enqueue: _ClassVar[MultitaskStrategy]
reject: MultitaskStrategy
rollback: MultitaskStrategy
interrupt: MultitaskStrategy
enqueue: MultitaskStrategy
