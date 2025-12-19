from google.protobuf import wrappers_pb2 as _wrappers_pb2
from google.protobuf import empty_pb2 as _empty_pb2
from . import errors_pb2 as _errors_pb2
from . import enum_durability_pb2 as _enum_durability_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ChannelValue(_message.Message):
    __slots__ = ("serialized_value", "sends", "missing")
    SERIALIZED_VALUE_FIELD_NUMBER: _ClassVar[int]
    SENDS_FIELD_NUMBER: _ClassVar[int]
    MISSING_FIELD_NUMBER: _ClassVar[int]
    serialized_value: SerializedValue
    sends: Sends
    missing: _empty_pb2.Empty
    def __init__(self, serialized_value: _Optional[_Union[SerializedValue, _Mapping]] = ..., sends: _Optional[_Union[Sends, _Mapping]] = ..., missing: _Optional[_Union[_empty_pb2.Empty, _Mapping]] = ...) -> None: ...

class SerializedValue(_message.Message):
    __slots__ = ("encoding", "value")
    ENCODING_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    encoding: str
    value: bytes
    def __init__(self, encoding: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...

class ResponseChunk(_message.Message):
    __slots__ = ("namespaces", "mode", "payload")
    NAMESPACES_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    namespaces: _containers.RepeatedScalarFieldContainer[str]
    mode: str
    payload: SerializedValue
    def __init__(self, namespaces: _Optional[_Iterable[str]] = ..., mode: _Optional[str] = ..., payload: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...

class ResponseChunkList(_message.Message):
    __slots__ = ("responses",)
    RESPONSES_FIELD_NUMBER: _ClassVar[int]
    responses: _containers.RepeatedCompositeFieldContainer[ResponseChunk]
    def __init__(self, responses: _Optional[_Iterable[_Union[ResponseChunk, _Mapping]]] = ...) -> None: ...

class MessageIds(_message.Message):
    __slots__ = ("message_ids",)
    MESSAGE_IDS_FIELD_NUMBER: _ClassVar[int]
    message_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, message_ids: _Optional[_Iterable[str]] = ...) -> None: ...

class Channels(_message.Message):
    __slots__ = ("channels",)
    class ChannelsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: Channel
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[Channel, _Mapping]] = ...) -> None: ...
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    channels: _containers.MessageMap[str, Channel]
    def __init__(self, channels: _Optional[_Mapping[str, Channel]] = ...) -> None: ...

class Channel(_message.Message):
    __slots__ = ("get_result", "is_available_result", "checkpoint_result")
    GET_RESULT_FIELD_NUMBER: _ClassVar[int]
    IS_AVAILABLE_RESULT_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_RESULT_FIELD_NUMBER: _ClassVar[int]
    get_result: ChannelValue
    is_available_result: bool
    checkpoint_result: ChannelValue
    def __init__(self, get_result: _Optional[_Union[ChannelValue, _Mapping]] = ..., is_available_result: bool = ..., checkpoint_result: _Optional[_Union[ChannelValue, _Mapping]] = ...) -> None: ...

class Sends(_message.Message):
    __slots__ = ("sends",)
    SENDS_FIELD_NUMBER: _ClassVar[int]
    sends: _containers.RepeatedCompositeFieldContainer[Send]
    def __init__(self, sends: _Optional[_Iterable[_Union[Send, _Mapping]]] = ...) -> None: ...

class Send(_message.Message):
    __slots__ = ("node", "arg")
    NODE_FIELD_NUMBER: _ClassVar[int]
    ARG_FIELD_NUMBER: _ClassVar[int]
    node: str
    arg: SerializedValue
    def __init__(self, node: _Optional[str] = ..., arg: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("graph", "update", "resume", "gotos")
    class UpdateEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: SerializedValue
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...
    GRAPH_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FIELD_NUMBER: _ClassVar[int]
    RESUME_FIELD_NUMBER: _ClassVar[int]
    GOTOS_FIELD_NUMBER: _ClassVar[int]
    graph: str
    update: _containers.MessageMap[str, SerializedValue]
    resume: Resume
    gotos: _containers.RepeatedCompositeFieldContainer[Goto]
    def __init__(self, graph: _Optional[str] = ..., update: _Optional[_Mapping[str, SerializedValue]] = ..., resume: _Optional[_Union[Resume, _Mapping]] = ..., gotos: _Optional[_Iterable[_Union[Goto, _Mapping]]] = ...) -> None: ...

class Resume(_message.Message):
    __slots__ = ("value", "values")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    value: SerializedValue
    values: InterruptValues
    def __init__(self, value: _Optional[_Union[SerializedValue, _Mapping]] = ..., values: _Optional[_Union[InterruptValues, _Mapping]] = ...) -> None: ...

class InterruptValues(_message.Message):
    __slots__ = ("values",)
    class ValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: SerializedValue
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.MessageMap[str, SerializedValue]
    def __init__(self, values: _Optional[_Mapping[str, SerializedValue]] = ...) -> None: ...

class Goto(_message.Message):
    __slots__ = ("node_name", "send")
    NODE_NAME_FIELD_NUMBER: _ClassVar[int]
    SEND_FIELD_NUMBER: _ClassVar[int]
    node_name: str
    send: Send
    def __init__(self, node_name: _Optional[str] = ..., send: _Optional[_Union[Send, _Mapping]] = ...) -> None: ...

class GraphBubbleUp(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GraphInterrupt(_message.Message):
    __slots__ = ("interrupts",)
    INTERRUPTS_FIELD_NUMBER: _ClassVar[int]
    interrupts: _containers.RepeatedCompositeFieldContainer[Interrupt]
    def __init__(self, interrupts: _Optional[_Iterable[_Union[Interrupt, _Mapping]]] = ...) -> None: ...

class Interrupt(_message.Message):
    __slots__ = ("value", "id")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    value: SerializedValue
    id: str
    def __init__(self, value: _Optional[_Union[SerializedValue, _Mapping]] = ..., id: _Optional[str] = ...) -> None: ...

class WrappedInterrupts(_message.Message):
    __slots__ = ("interrupts", "serialized_interrupts")
    INTERRUPTS_FIELD_NUMBER: _ClassVar[int]
    SERIALIZED_INTERRUPTS_FIELD_NUMBER: _ClassVar[int]
    interrupts: _containers.RepeatedCompositeFieldContainer[Interrupt]
    serialized_interrupts: SerializedValue
    def __init__(self, interrupts: _Optional[_Iterable[_Union[Interrupt, _Mapping]]] = ..., serialized_interrupts: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...

class Write(_message.Message):
    __slots__ = ("channel", "value")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    channel: str
    value: ChannelValue
    def __init__(self, channel: _Optional[str] = ..., value: _Optional[_Union[ChannelValue, _Mapping]] = ...) -> None: ...

class PendingWrite(_message.Message):
    __slots__ = ("task_id", "channel", "value")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    channel: str
    value: ChannelValue
    def __init__(self, task_id: _Optional[str] = ..., channel: _Optional[str] = ..., value: _Optional[_Union[ChannelValue, _Mapping]] = ...) -> None: ...

class ChannelVersions(_message.Message):
    __slots__ = ("channel_versions",)
    class ChannelVersionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CHANNEL_VERSIONS_FIELD_NUMBER: _ClassVar[int]
    channel_versions: _containers.ScalarMap[str, str]
    def __init__(self, channel_versions: _Optional[_Mapping[str, str]] = ...) -> None: ...

class EngineRunnableConfig(_message.Message):
    __slots__ = ("tags", "metadata_json", "run_name", "max_concurrency", "recursion_limit", "run_id", "extra_configurable_json", "extra_json", "runtime", "resuming", "task_id", "thread_id", "checkpoint_map", "checkpoint_id", "checkpoint_ns", "durability", "resume_map", "graph_id", "stream", "run_attempt", "server_run_id")
    class MetadataJsonEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    class ExtraConfigurableJsonEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    class ExtraJsonEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    class CheckpointMapEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class ResumeMapEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: SerializedValue
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...
    TAGS_FIELD_NUMBER: _ClassVar[int]
    METADATA_JSON_FIELD_NUMBER: _ClassVar[int]
    RUN_NAME_FIELD_NUMBER: _ClassVar[int]
    MAX_CONCURRENCY_FIELD_NUMBER: _ClassVar[int]
    RECURSION_LIMIT_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    EXTRA_CONFIGURABLE_JSON_FIELD_NUMBER: _ClassVar[int]
    EXTRA_JSON_FIELD_NUMBER: _ClassVar[int]
    RUNTIME_FIELD_NUMBER: _ClassVar[int]
    RESUMING_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    THREAD_ID_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_MAP_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_ID_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_NS_FIELD_NUMBER: _ClassVar[int]
    DURABILITY_FIELD_NUMBER: _ClassVar[int]
    RESUME_MAP_FIELD_NUMBER: _ClassVar[int]
    GRAPH_ID_FIELD_NUMBER: _ClassVar[int]
    STREAM_FIELD_NUMBER: _ClassVar[int]
    RUN_ATTEMPT_FIELD_NUMBER: _ClassVar[int]
    SERVER_RUN_ID_FIELD_NUMBER: _ClassVar[int]
    tags: _containers.RepeatedScalarFieldContainer[str]
    metadata_json: _containers.ScalarMap[str, bytes]
    run_name: str
    max_concurrency: int
    recursion_limit: int
    run_id: str
    extra_configurable_json: _containers.ScalarMap[str, bytes]
    extra_json: _containers.ScalarMap[str, bytes]
    runtime: Runtime
    resuming: bool
    task_id: str
    thread_id: str
    checkpoint_map: _containers.ScalarMap[str, str]
    checkpoint_id: str
    checkpoint_ns: str
    durability: _enum_durability_pb2.Durability
    resume_map: _containers.MessageMap[str, SerializedValue]
    graph_id: str
    stream: bool
    run_attempt: int
    server_run_id: str
    def __init__(self, tags: _Optional[_Iterable[str]] = ..., metadata_json: _Optional[_Mapping[str, bytes]] = ..., run_name: _Optional[str] = ..., max_concurrency: _Optional[int] = ..., recursion_limit: _Optional[int] = ..., run_id: _Optional[str] = ..., extra_configurable_json: _Optional[_Mapping[str, bytes]] = ..., extra_json: _Optional[_Mapping[str, bytes]] = ..., runtime: _Optional[_Union[Runtime, _Mapping]] = ..., resuming: bool = ..., task_id: _Optional[str] = ..., thread_id: _Optional[str] = ..., checkpoint_map: _Optional[_Mapping[str, str]] = ..., checkpoint_id: _Optional[str] = ..., checkpoint_ns: _Optional[str] = ..., durability: _Optional[_Union[_enum_durability_pb2.Durability, str]] = ..., resume_map: _Optional[_Mapping[str, SerializedValue]] = ..., graph_id: _Optional[str] = ..., stream: bool = ..., run_attempt: _Optional[int] = ..., server_run_id: _Optional[str] = ...) -> None: ...

class Runtime(_message.Message):
    __slots__ = ("langgraph_context_json",)
    LANGGRAPH_CONTEXT_JSON_FIELD_NUMBER: _ClassVar[int]
    langgraph_context_json: bytes
    def __init__(self, langgraph_context_json: _Optional[bytes] = ...) -> None: ...

class Task(_message.Message):
    __slots__ = ("name", "writes", "config", "triggers", "id", "task_path", "pending_writes", "stream_subgraphs", "has_subgraphs")
    NAME_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    TRIGGERS_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    TASK_PATH_FIELD_NUMBER: _ClassVar[int]
    PENDING_WRITES_FIELD_NUMBER: _ClassVar[int]
    STREAM_SUBGRAPHS_FIELD_NUMBER: _ClassVar[int]
    HAS_SUBGRAPHS_FIELD_NUMBER: _ClassVar[int]
    name: str
    writes: _containers.RepeatedCompositeFieldContainer[Write]
    config: EngineRunnableConfig
    triggers: _containers.RepeatedScalarFieldContainer[str]
    id: str
    task_path: _containers.RepeatedCompositeFieldContainer[PathSegment]
    pending_writes: _containers.RepeatedCompositeFieldContainer[PendingWrite]
    stream_subgraphs: bool
    has_subgraphs: bool
    def __init__(self, name: _Optional[str] = ..., writes: _Optional[_Iterable[_Union[Write, _Mapping]]] = ..., config: _Optional[_Union[EngineRunnableConfig, _Mapping]] = ..., triggers: _Optional[_Iterable[str]] = ..., id: _Optional[str] = ..., task_path: _Optional[_Iterable[_Union[PathSegment, _Mapping]]] = ..., pending_writes: _Optional[_Iterable[_Union[PendingWrite, _Mapping]]] = ..., stream_subgraphs: bool = ..., has_subgraphs: bool = ...) -> None: ...

class TaskResult(_message.Message):
    __slots__ = ("user_error", "interrupts", "bubble_up", "writes")
    USER_ERROR_FIELD_NUMBER: _ClassVar[int]
    INTERRUPTS_FIELD_NUMBER: _ClassVar[int]
    BUBBLE_UP_FIELD_NUMBER: _ClassVar[int]
    WRITES_FIELD_NUMBER: _ClassVar[int]
    user_error: _errors_pb2.UserCodeExecutionError
    interrupts: WrappedInterrupts
    bubble_up: GraphBubbleUp
    writes: _containers.RepeatedCompositeFieldContainer[Write]
    def __init__(self, user_error: _Optional[_Union[_errors_pb2.UserCodeExecutionError, _Mapping]] = ..., interrupts: _Optional[_Union[WrappedInterrupts, _Mapping]] = ..., bubble_up: _Optional[_Union[GraphBubbleUp, _Mapping]] = ..., writes: _Optional[_Iterable[_Union[Write, _Mapping]]] = ...) -> None: ...

class TaskStateSnapshot(_message.Message):
    __slots__ = ("checkpoint_id", "thread_id", "checkpoint_ns", "checkpoint_map")
    class CheckpointMapEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    CHECKPOINT_ID_FIELD_NUMBER: _ClassVar[int]
    THREAD_ID_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_NS_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_MAP_FIELD_NUMBER: _ClassVar[int]
    checkpoint_id: str
    thread_id: str
    checkpoint_ns: str
    checkpoint_map: _containers.ScalarMap[str, str]
    def __init__(self, checkpoint_id: _Optional[str] = ..., thread_id: _Optional[str] = ..., checkpoint_ns: _Optional[str] = ..., checkpoint_map: _Optional[_Mapping[str, str]] = ...) -> None: ...

class PregelTaskSnapshot(_message.Message):
    __slots__ = ("id", "name", "path", "interrupts", "state", "result_json", "error")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    INTERRUPTS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    RESULT_JSON_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    path: _containers.RepeatedCompositeFieldContainer[PathSegment]
    interrupts: _containers.RepeatedCompositeFieldContainer[Interrupt]
    state: TaskStateSnapshot
    result_json: bytes
    error: SerializedValue
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., path: _Optional[_Iterable[_Union[PathSegment, _Mapping]]] = ..., interrupts: _Optional[_Iterable[_Union[Interrupt, _Mapping]]] = ..., state: _Optional[_Union[TaskStateSnapshot, _Mapping]] = ..., result_json: _Optional[bytes] = ..., error: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...

class Checkpoint(_message.Message):
    __slots__ = ("v", "id", "channel_values", "channel_versions", "versions_seen", "ts", "updated_channels")
    class ChannelValuesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ChannelValue
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ChannelValue, _Mapping]] = ...) -> None: ...
    class ChannelVersionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    class VersionsSeenEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ChannelVersions
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ChannelVersions, _Mapping]] = ...) -> None: ...
    V_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_VALUES_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_VERSIONS_FIELD_NUMBER: _ClassVar[int]
    VERSIONS_SEEN_FIELD_NUMBER: _ClassVar[int]
    TS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    v: int
    id: str
    channel_values: _containers.MessageMap[str, ChannelValue]
    channel_versions: _containers.ScalarMap[str, str]
    versions_seen: _containers.MessageMap[str, ChannelVersions]
    ts: str
    updated_channels: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, v: _Optional[int] = ..., id: _Optional[str] = ..., channel_values: _Optional[_Mapping[str, ChannelValue]] = ..., channel_versions: _Optional[_Mapping[str, str]] = ..., versions_seen: _Optional[_Mapping[str, ChannelVersions]] = ..., ts: _Optional[str] = ..., updated_channels: _Optional[_Iterable[str]] = ...) -> None: ...

class CheckpointMetadata(_message.Message):
    __slots__ = ("source", "step", "parents", "run_id")
    class CheckpointSource(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        unknown: _ClassVar[CheckpointMetadata.CheckpointSource]
        loop: _ClassVar[CheckpointMetadata.CheckpointSource]
        input: _ClassVar[CheckpointMetadata.CheckpointSource]
        update: _ClassVar[CheckpointMetadata.CheckpointSource]
        fork: _ClassVar[CheckpointMetadata.CheckpointSource]
    unknown: CheckpointMetadata.CheckpointSource
    loop: CheckpointMetadata.CheckpointSource
    input: CheckpointMetadata.CheckpointSource
    update: CheckpointMetadata.CheckpointSource
    fork: CheckpointMetadata.CheckpointSource
    class ParentsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    PARENTS_FIELD_NUMBER: _ClassVar[int]
    RUN_ID_FIELD_NUMBER: _ClassVar[int]
    source: CheckpointMetadata.CheckpointSource
    step: int
    parents: _containers.ScalarMap[str, str]
    run_id: str
    def __init__(self, source: _Optional[_Union[CheckpointMetadata.CheckpointSource, str]] = ..., step: _Optional[int] = ..., parents: _Optional[_Mapping[str, str]] = ..., run_id: _Optional[str] = ...) -> None: ...

class CheckpointTuple(_message.Message):
    __slots__ = ("config", "checkpoint", "metadata", "parent_config", "pending_writes")
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    CHECKPOINT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    PARENT_CONFIG_FIELD_NUMBER: _ClassVar[int]
    PENDING_WRITES_FIELD_NUMBER: _ClassVar[int]
    config: EngineRunnableConfig
    checkpoint: Checkpoint
    metadata: CheckpointMetadata
    parent_config: EngineRunnableConfig
    pending_writes: _containers.RepeatedCompositeFieldContainer[PendingWrite]
    def __init__(self, config: _Optional[_Union[EngineRunnableConfig, _Mapping]] = ..., checkpoint: _Optional[_Union[Checkpoint, _Mapping]] = ..., metadata: _Optional[_Union[CheckpointMetadata, _Mapping]] = ..., parent_config: _Optional[_Union[EngineRunnableConfig, _Mapping]] = ..., pending_writes: _Optional[_Iterable[_Union[PendingWrite, _Mapping]]] = ...) -> None: ...

class Updates(_message.Message):
    __slots__ = ("checkpoint", "channels", "updated_channels")
    CHECKPOINT_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_CHANNELS_FIELD_NUMBER: _ClassVar[int]
    checkpoint: Checkpoint
    channels: Channels
    updated_channels: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, checkpoint: _Optional[_Union[Checkpoint, _Mapping]] = ..., channels: _Optional[_Union[Channels, _Mapping]] = ..., updated_channels: _Optional[_Iterable[str]] = ...) -> None: ...

class ToolCall(_message.Message):
    __slots__ = ("name", "args_json", "id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGS_JSON_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    args_json: bytes
    id: _wrappers_pb2.StringValue
    def __init__(self, name: _Optional[str] = ..., args_json: _Optional[bytes] = ..., id: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ...) -> None: ...

class ToolCallChunk(_message.Message):
    __slots__ = ("name", "args_json", "id", "index")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGS_JSON_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    name: _wrappers_pb2.StringValue
    args_json: _wrappers_pb2.StringValue
    id: _wrappers_pb2.StringValue
    index: _wrappers_pb2.Int32Value
    def __init__(self, name: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., args_json: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., id: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., index: _Optional[_Union[_wrappers_pb2.Int32Value, _Mapping]] = ...) -> None: ...

class InvalidToolCall(_message.Message):
    __slots__ = ("name", "args", "id", "error")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGS_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    name: _wrappers_pb2.StringValue
    args: _wrappers_pb2.StringValue
    id: _wrappers_pb2.StringValue
    error: _wrappers_pb2.StringValue
    def __init__(self, name: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., args: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., id: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., error: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ...) -> None: ...

class InputTokenDetails(_message.Message):
    __slots__ = ("audio", "cache_creation", "cache_read")
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    CACHE_CREATION_FIELD_NUMBER: _ClassVar[int]
    CACHE_READ_FIELD_NUMBER: _ClassVar[int]
    audio: _wrappers_pb2.Int64Value
    cache_creation: _wrappers_pb2.Int64Value
    cache_read: _wrappers_pb2.Int64Value
    def __init__(self, audio: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ..., cache_creation: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ..., cache_read: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ...) -> None: ...

class OutputTokenDetails(_message.Message):
    __slots__ = ("audio", "reasoning")
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    REASONING_FIELD_NUMBER: _ClassVar[int]
    audio: _wrappers_pb2.Int64Value
    reasoning: _wrappers_pb2.Int64Value
    def __init__(self, audio: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ..., reasoning: _Optional[_Union[_wrappers_pb2.Int64Value, _Mapping]] = ...) -> None: ...

class UsageMetadata(_message.Message):
    __slots__ = ("input_tokens", "output_tokens", "total_tokens", "input_token_details", "output_token_details")
    INPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_TOKENS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TOKENS_FIELD_NUMBER: _ClassVar[int]
    INPUT_TOKEN_DETAILS_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_TOKEN_DETAILS_FIELD_NUMBER: _ClassVar[int]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_token_details: InputTokenDetails
    output_token_details: OutputTokenDetails
    def __init__(self, input_tokens: _Optional[int] = ..., output_tokens: _Optional[int] = ..., total_tokens: _Optional[int] = ..., input_token_details: _Optional[_Union[InputTokenDetails, _Mapping]] = ..., output_token_details: _Optional[_Union[OutputTokenDetails, _Mapping]] = ...) -> None: ...

class ResponseMetadata(_message.Message):
    __slots__ = ("data",)
    class DataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    DATA_FIELD_NUMBER: _ClassVar[int]
    data: _containers.ScalarMap[str, bytes]
    def __init__(self, data: _Optional[_Mapping[str, bytes]] = ...) -> None: ...

class AIFields(_message.Message):
    __slots__ = ("usage_metadata", "response_metadata", "tool_calls", "tool_call_chunks", "invalid_tool_calls", "chunk_position", "reasoning_content")
    USAGE_METADATA_FIELD_NUMBER: _ClassVar[int]
    RESPONSE_METADATA_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALLS_FIELD_NUMBER: _ClassVar[int]
    TOOL_CALL_CHUNKS_FIELD_NUMBER: _ClassVar[int]
    INVALID_TOOL_CALLS_FIELD_NUMBER: _ClassVar[int]
    CHUNK_POSITION_FIELD_NUMBER: _ClassVar[int]
    REASONING_CONTENT_FIELD_NUMBER: _ClassVar[int]
    usage_metadata: UsageMetadata
    response_metadata: ResponseMetadata
    tool_calls: _containers.RepeatedCompositeFieldContainer[ToolCall]
    tool_call_chunks: _containers.RepeatedCompositeFieldContainer[ToolCallChunk]
    invalid_tool_calls: _containers.RepeatedCompositeFieldContainer[InvalidToolCall]
    chunk_position: str
    reasoning_content: _wrappers_pb2.StringValue
    def __init__(self, usage_metadata: _Optional[_Union[UsageMetadata, _Mapping]] = ..., response_metadata: _Optional[_Union[ResponseMetadata, _Mapping]] = ..., tool_calls: _Optional[_Iterable[_Union[ToolCall, _Mapping]]] = ..., tool_call_chunks: _Optional[_Iterable[_Union[ToolCallChunk, _Mapping]]] = ..., invalid_tool_calls: _Optional[_Iterable[_Union[InvalidToolCall, _Mapping]]] = ..., chunk_position: _Optional[str] = ..., reasoning_content: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ...) -> None: ...

class ToolFields(_message.Message):
    __slots__ = ("tool_call_id", "status", "artifact")
    TOOL_CALL_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_FIELD_NUMBER: _ClassVar[int]
    tool_call_id: _wrappers_pb2.StringValue
    status: str
    artifact: SerializedValue
    def __init__(self, tool_call_id: _Optional[_Union[_wrappers_pb2.StringValue, _Mapping]] = ..., status: _Optional[str] = ..., artifact: _Optional[_Union[SerializedValue, _Mapping]] = ...) -> None: ...

class HumanFields(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Content(_message.Message):
    __slots__ = ("text", "blocks")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    text: str
    blocks: ContentBlocks
    def __init__(self, text: _Optional[str] = ..., blocks: _Optional[_Union[ContentBlocks, _Mapping]] = ...) -> None: ...

class ContentBlocks(_message.Message):
    __slots__ = ("items",)
    ITEMS_FIELD_NUMBER: _ClassVar[int]
    items: _containers.RepeatedCompositeFieldContainer[ContentBlock]
    def __init__(self, items: _Optional[_Iterable[_Union[ContentBlock, _Mapping]]] = ...) -> None: ...

class ContentBlock(_message.Message):
    __slots__ = ("text", "structured")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    STRUCTURED_FIELD_NUMBER: _ClassVar[int]
    text: str
    structured: StructuredBlock
    def __init__(self, text: _Optional[str] = ..., structured: _Optional[_Union[StructuredBlock, _Mapping]] = ...) -> None: ...

class StructuredBlock(_message.Message):
    __slots__ = ("index", "type", "data_json")
    INDEX_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_JSON_FIELD_NUMBER: _ClassVar[int]
    index: int
    type: str
    data_json: bytes
    def __init__(self, index: _Optional[int] = ..., type: _Optional[str] = ..., data_json: _Optional[bytes] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("id", "name", "type", "content", "additional_kwargs", "ai", "tool", "human", "extensions")
    class AdditionalKwargsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    class ExtensionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_KWARGS_FIELD_NUMBER: _ClassVar[int]
    AI_FIELD_NUMBER: _ClassVar[int]
    TOOL_FIELD_NUMBER: _ClassVar[int]
    HUMAN_FIELD_NUMBER: _ClassVar[int]
    EXTENSIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    type: str
    content: Content
    additional_kwargs: _containers.ScalarMap[str, bytes]
    ai: AIFields
    tool: ToolFields
    human: HumanFields
    extensions: _containers.ScalarMap[str, bytes]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., type: _Optional[str] = ..., content: _Optional[_Union[Content, _Mapping]] = ..., additional_kwargs: _Optional[_Mapping[str, bytes]] = ..., ai: _Optional[_Union[AIFields, _Mapping]] = ..., tool: _Optional[_Union[ToolFields, _Mapping]] = ..., human: _Optional[_Union[HumanFields, _Mapping]] = ..., extensions: _Optional[_Mapping[str, bytes]] = ...) -> None: ...

class ChatMessageEnvelope(_message.Message):
    __slots__ = ("is_streaming_chunk", "namespace", "message", "metadata")
    IS_STREAMING_CHUNK_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    is_streaming_chunk: bool
    namespace: _containers.RepeatedScalarFieldContainer[str]
    message: ChatMessage
    metadata: bytes
    def __init__(self, is_streaming_chunk: bool = ..., namespace: _Optional[_Iterable[str]] = ..., message: _Optional[_Union[ChatMessage, _Mapping]] = ..., metadata: _Optional[bytes] = ...) -> None: ...

class StateSnapshot(_message.Message):
    __slots__ = ("values_json", "next", "config", "metadata", "created_at", "parent_config", "tasks", "interrupts")
    VALUES_JSON_FIELD_NUMBER: _ClassVar[int]
    NEXT_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    PARENT_CONFIG_FIELD_NUMBER: _ClassVar[int]
    TASKS_FIELD_NUMBER: _ClassVar[int]
    INTERRUPTS_FIELD_NUMBER: _ClassVar[int]
    values_json: bytes
    next: _containers.RepeatedScalarFieldContainer[str]
    config: EngineRunnableConfig
    metadata: CheckpointMetadata
    created_at: str
    parent_config: EngineRunnableConfig
    tasks: _containers.RepeatedCompositeFieldContainer[PregelTaskSnapshot]
    interrupts: _containers.RepeatedCompositeFieldContainer[Interrupt]
    def __init__(self, values_json: _Optional[bytes] = ..., next: _Optional[_Iterable[str]] = ..., config: _Optional[_Union[EngineRunnableConfig, _Mapping]] = ..., metadata: _Optional[_Union[CheckpointMetadata, _Mapping]] = ..., created_at: _Optional[str] = ..., parent_config: _Optional[_Union[EngineRunnableConfig, _Mapping]] = ..., tasks: _Optional[_Iterable[_Union[PregelTaskSnapshot, _Mapping]]] = ..., interrupts: _Optional[_Iterable[_Union[Interrupt, _Mapping]]] = ...) -> None: ...

class StateUpdate(_message.Message):
    __slots__ = ("values", "as_node", "task_id")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    AS_NODE_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    values: SerializedValue
    as_node: str
    task_id: str
    def __init__(self, values: _Optional[_Union[SerializedValue, _Mapping]] = ..., as_node: _Optional[str] = ..., task_id: _Optional[str] = ...) -> None: ...

class SuperstepUpdates(_message.Message):
    __slots__ = ("updates",)
    UPDATES_FIELD_NUMBER: _ClassVar[int]
    updates: _containers.RepeatedCompositeFieldContainer[StateUpdate]
    def __init__(self, updates: _Optional[_Iterable[_Union[StateUpdate, _Mapping]]] = ...) -> None: ...

class StringOrSlice(_message.Message):
    __slots__ = ("values", "is_string")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    IS_STRING_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    is_string: bool
    def __init__(self, values: _Optional[_Iterable[str]] = ..., is_string: bool = ...) -> None: ...

class PathSegment(_message.Message):
    __slots__ = ("string_value", "int_value", "bool_value")
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
    string_value: str
    int_value: int
    bool_value: bool
    def __init__(self, string_value: _Optional[str] = ..., int_value: _Optional[int] = ..., bool_value: bool = ...) -> None: ...

class StaticInterruptConfig(_message.Message):
    __slots__ = ("all", "node_names")
    class NodeNames(_message.Message):
        __slots__ = ("names",)
        NAMES_FIELD_NUMBER: _ClassVar[int]
        names: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, names: _Optional[_Iterable[str]] = ...) -> None: ...
    ALL_FIELD_NUMBER: _ClassVar[int]
    NODE_NAMES_FIELD_NUMBER: _ClassVar[int]
    all: bool
    node_names: StaticInterruptConfig.NodeNames
    def __init__(self, all: bool = ..., node_names: _Optional[_Union[StaticInterruptConfig.NodeNames, _Mapping]] = ...) -> None: ...
