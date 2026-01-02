import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

logger = logging.getLogger(__name__)


def _ensure_uuid(id: str | UUID) -> UUID:
    return UUID(id) if isinstance(id, str) else id


def _generate_ms_seq_id() -> str:
    """Generate a Redis-like millisecond-sequence ID (e.g., '1234567890123-0')"""
    # Get current time in milliseconds
    ms = int(time.time() * 1000)
    # For simplicity, always use sequence 0 since we're not handling high throughput
    return f"{ms}-0"


@dataclass
class Message:
    topic: bytes
    data: bytes
    id: bytes | None = None


class ContextQueue(asyncio.Queue):
    """Queue that supports async context manager protocol"""

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        # Clear the queue
        while not self.empty():
            try:
                self.get_nowait()
            except asyncio.QueueEmpty:
                break


THREADLESS_KEY = "no-thread"


class StreamManager:
    def __init__(self):
        self.queues = defaultdict(
            lambda: defaultdict(list)
        )  # Dict[str, List[asyncio.Queue]]
        self.control_keys = defaultdict(lambda: defaultdict())
        self.control_queues = defaultdict(lambda: defaultdict(list))
        self.thread_streams = defaultdict(list)

        self.message_stores = defaultdict(
            lambda: defaultdict(list[Message])
        )  # Dict[str, List[Message]]

    def get_queues(
        self, run_id: UUID | str, thread_id: UUID | str | None
    ) -> list[asyncio.Queue]:
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        return self.queues[thread_id][run_id]

    def get_control_queues(
        self, run_id: UUID | str, thread_id: UUID | str | None
    ) -> list[asyncio.Queue]:
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        return self.control_queues[thread_id][run_id]

    def get_control_key(
        self, run_id: UUID | str, thread_id: UUID | str | None
    ) -> Message | None:
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        return self.control_keys.get(thread_id, {}).get(run_id)

    async def put(
        self,
        run_id: UUID | str | None,
        thread_id: UUID | str | None,
        message: Message,
        resumable: bool = False,
    ) -> None:
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)

        message.id = _generate_ms_seq_id().encode()
        # For resumable run streams, embed the generated message ID into the frame
        topic = message.topic.decode()
        if resumable:
            self.message_stores[thread_id][run_id].append(message)
        if "control" in topic:
            self.control_keys[thread_id][run_id] = message
            queues = self.control_queues[thread_id][run_id]
        else:
            queues = self.queues[thread_id][run_id]
        coros = [queue.put(message) for queue in queues]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.exception(f"Failed to put message in queue: {result}")

    async def put_thread(
        self,
        thread_id: UUID | str,
        message: Message,
    ) -> None:
        thread_id = _ensure_uuid(thread_id)
        message.id = _generate_ms_seq_id().encode()
        queues = self.thread_streams[thread_id]
        coros = [queue.put(message) for queue in queues]
        results = await asyncio.gather(*coros, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.exception(f"Failed to put message in queue: {result}")

    async def add_queue(
        self, run_id: UUID | str, thread_id: UUID | str | None
    ) -> asyncio.Queue:
        run_id = _ensure_uuid(run_id)
        queue = ContextQueue()
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        self.queues[thread_id][run_id].append(queue)
        return queue

    async def add_control_queue(
        self, run_id: UUID | str, thread_id: UUID | str | None
    ) -> asyncio.Queue:
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        queue = ContextQueue()
        self.control_queues[thread_id][run_id].append(queue)
        return queue

    async def add_thread_stream(self, thread_id: UUID | str) -> asyncio.Queue:
        thread_id = _ensure_uuid(thread_id)
        queue = ContextQueue()
        self.thread_streams[thread_id].append(queue)
        return queue

    async def remove_queue(
        self, run_id: UUID | str, thread_id: UUID | str | None, queue: asyncio.Queue
    ):
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        if thread_id in self.queues and run_id in self.queues[thread_id]:
            self.queues[thread_id][run_id].remove(queue)
            if not self.queues[thread_id][run_id]:
                del self.queues[thread_id][run_id]

    async def remove_control_queue(
        self, run_id: UUID | str, thread_id: UUID | str | None, queue: asyncio.Queue
    ):
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        if (
            thread_id in self.control_queues
            and run_id in self.control_queues[thread_id]
        ):
            self.control_queues[thread_id][run_id].remove(queue)
            if not self.control_queues[thread_id][run_id]:
                del self.control_queues[thread_id][run_id]

    def restore_messages(
        self, run_id: UUID | str, thread_id: UUID | str | None, message_id: str | None
    ) -> Iterator[Message]:
        """Get a stored message by ID for resumable streams."""
        run_id = _ensure_uuid(run_id)
        if thread_id is None:
            thread_id = THREADLESS_KEY
        else:
            thread_id = _ensure_uuid(thread_id)
        if message_id is None:
            return
        try:
            # Handle ms-seq format (e.g., "1234567890123-0")
            if thread_id in self.message_stores:
                for message in self.message_stores[thread_id][run_id]:
                    if message.id.decode() > message_id:
                        yield message
        except TypeError:
            # Try integer format if ms-seq fails
            message_idx = int(message_id) + 1
            if run_id in self.message_stores:
                yield from self.message_stores[thread_id][run_id][message_idx:]

    def get_queues_by_thread_id(self, thread_id: UUID | str) -> list[asyncio.Queue]:
        """Get all queues for a specific thread_id across all runs."""
        all_queues = []
        # Search through all stored queue keys for ones ending with the thread_id
        thread_id = _ensure_uuid(thread_id)
        if thread_id in self.queues:
            for run_id in self.queues[thread_id]:
                all_queues.extend(self.queues[thread_id][run_id])

        return all_queues


# Global instance
stream_manager = StreamManager()


async def start_stream() -> None:
    """Initialize the queue system.
    In this in-memory implementation, we just need to ensure we have a clean StreamManager instance.
    """
    global stream_manager
    stream_manager = StreamManager()


async def stop_stream() -> None:
    """Clean up the queue system.
    Clear all queues and stored control messages."""
    global stream_manager

    # Send 'done' message to all active queues before clearing
    for run_id in list(stream_manager.queues.keys()):
        control_message = Message(topic=f"run:{run_id}:control".encode(), data=b"done")

        for queue in stream_manager.queues[run_id]:
            try:
                await queue.put(control_message)
            except (Exception, RuntimeError):
                pass  # Ignore errors during shutdown

    # Clear all stored data
    stream_manager.queues.clear()
    stream_manager.control_queues.clear()
    stream_manager.message_stores.clear()


def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance."""
    return stream_manager
