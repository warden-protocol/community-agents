"""gRPC client wrapper for LangGraph persistence services."""

import asyncio
import os

import structlog
from grpc import aio  # type: ignore[import]

from langgraph_api import config

from .generated.core_api_pb2_grpc import AdminStub, AssistantsStub, ThreadsStub

logger = structlog.stdlib.get_logger(__name__)


# Shared global client pool
_client_pool: "GrpcClientPool | None" = None


class GrpcClient:
    """gRPC client for LangGraph persistence services."""

    def __init__(
        self,
        server_address: str | None = None,
    ):
        """Initialize the gRPC client.

        Args:
            server_address: The gRPC server address (default: localhost:50051)
        """
        self.server_address = server_address or os.getenv(
            "GRPC_SERVER_ADDRESS", "localhost:50051"
        )
        self._channel: aio.Channel | None = None
        self._assistants_stub: AssistantsStub | None = None
        self._threads_stub: ThreadsStub | None = None
        self._admin_stub: AdminStub | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def connect(self):
        """Connect to the gRPC server."""
        if self._channel is not None:
            return

        options = [
            ("grpc.max_receive_message_length", config.GRPC_CLIENT_MAX_RECV_MSG_BYTES),
            ("grpc.max_send_message_length", config.GRPC_CLIENT_MAX_SEND_MSG_BYTES),
        ]

        self._channel = aio.insecure_channel(self.server_address, options=options)

        self._assistants_stub = AssistantsStub(self._channel)
        self._threads_stub = ThreadsStub(self._channel)
        self._admin_stub = AdminStub(self._channel)

        await logger.adebug(
            "Connected to gRPC server", server_address=self.server_address
        )

    async def close(self):
        """Close the gRPC connection."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._assistants_stub = None
            self._threads_stub = None
            self._admin_stub = None
            await logger.adebug("Closed gRPC connection")

    @property
    def assistants(self) -> AssistantsStub:
        """Get the assistants service stub."""
        if self._assistants_stub is None:
            raise RuntimeError(
                "Client not connected. Use async context manager or call connect() first."
            )
        return self._assistants_stub

    @property
    def threads(self) -> ThreadsStub:
        """Get the threads service stub."""
        if self._threads_stub is None:
            raise RuntimeError(
                "Client not connected. Use async context manager or call connect() first."
            )
        return self._threads_stub

    @property
    def admin(self) -> AdminStub:
        """Get the admin service stub."""
        if self._admin_stub is None:
            raise RuntimeError(
                "Client not connected. Use async context manager or call connect() first."
            )
        return self._admin_stub


class GrpcClientPool:
    """Pool of gRPC clients for load distribution."""

    def __init__(self, pool_size: int = 5, server_address: str | None = None):
        self.pool_size = pool_size
        self.server_address = server_address
        self.clients: list[GrpcClient] = []
        self._current_index = 0
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _initialize(self):
        """Initialize the pool of clients."""
        async with self._init_lock:
            if self._initialized:
                return

            await logger.ainfo(
                "Initializing gRPC client pool",
                pool_size=self.pool_size,
                server_address=self.server_address,
            )

            for _ in range(self.pool_size):
                client = GrpcClient(server_address=self.server_address)
                await client.connect()
                self.clients.append(client)

            self._initialized = True
            await logger.ainfo(
                f"gRPC client pool initialized with {self.pool_size} clients"
            )

    async def get_client(self) -> GrpcClient:
        """Get next client using round-robin selection.

        Round-robin without strict locking - slight races are acceptable
        and result in good enough distribution under high load.
        """
        if not self._initialized:
            await self._initialize()

        idx = self._current_index % self.pool_size
        self._current_index = idx + 1
        return self.clients[idx]

    async def close(self):
        """Close all clients in the pool."""
        if self._initialized:
            await logger.ainfo(f"Closing gRPC client pool ({self.pool_size} clients)")
            for client in self.clients:
                await client.close()
            self.clients.clear()
            self._initialized = False


async def get_shared_client() -> GrpcClient:
    """Get a gRPC client from the shared pool.

    Uses a pool of channels for better performance under high concurrency.
    Each channel is a separate TCP connection that can handle ~100-200
    concurrent streams effectively.

    Returns:
        A GrpcClient instance from the pool
    """
    global _client_pool
    if _client_pool is None:
        from langgraph_api import config

        _client_pool = GrpcClientPool(
            pool_size=config.GRPC_CLIENT_POOL_SIZE,
            server_address=os.getenv("GRPC_SERVER_ADDRESS"),
        )

    return await _client_pool.get_client()


async def close_shared_client():
    """Close the shared gRPC client pool."""
    global _client_pool
    if _client_pool is not None:
        await _client_pool.close()
        _client_pool = None
