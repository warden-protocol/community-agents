from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class UserCodeExecutionError(_message.Message):
    __slots__ = ("error_type", "error_message", "traceback")
    ERROR_TYPE_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TRACEBACK_FIELD_NUMBER: _ClassVar[int]
    error_type: str
    error_message: str
    traceback: str
    def __init__(self, error_type: _Optional[str] = ..., error_message: _Optional[str] = ..., traceback: _Optional[str] = ...) -> None: ...

class GraphRecursionLimitError(_message.Message):
    __slots__ = ("limit",)
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    limit: int
    def __init__(self, limit: _Optional[int] = ...) -> None: ...
