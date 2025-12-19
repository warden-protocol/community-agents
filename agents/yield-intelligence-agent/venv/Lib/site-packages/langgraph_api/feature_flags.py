import os

from langgraph.version import __version__

# Only gate features on the major.minor version; Lets you ignore the rc/alpha/etc. releases anyway
LANGGRAPH_PY_MINOR = tuple(map(int, __version__.split(".")[:2]))

OMIT_PENDING_SENDS = LANGGRAPH_PY_MINOR >= (0, 5)
USE_RUNTIME_CONTEXT_API = LANGGRAPH_PY_MINOR >= (0, 6)
USE_NEW_INTERRUPTS = LANGGRAPH_PY_MINOR >= (0, 6)
USE_DURABILITY = LANGGRAPH_PY_MINOR >= (0, 6)

# Feature flag for new gRPC-based persistence layer
FF_USE_CORE_API = os.getenv("FF_USE_CORE_API", "false").lower() in (
    "true",
    "1",
    "yes",
)
# Feature flag for using the JS native API
FF_USE_JS_API = os.getenv("FF_USE_JS_API", "false").lower() in (
    "true",
    "1",
    "yes",
)

# In langgraph <= 1.0.3, we automatically subscribed to updates stream events to surface interrupts. In langgraph 1.0.4 we include interrupts in values events (which we are automatically subscribed to), so we no longer need to implicitly subscribe to updates stream events
# If the version is not valid, e.g. rc/alpha/etc., we default to 0.0.0
try:
    LANGGRAPH_PY_PATCH = tuple(map(int, __version__.split(".")[:3]))
except ValueError:
    LANGGRAPH_PY_PATCH = (0, 0, 0)
UPDATES_NEEDED_FOR_INTERRUPTS = LANGGRAPH_PY_PATCH <= (1, 0, 3)
