import asyncio
import functools
import glob
import importlib.util
import inspect
import os
import sys
import warnings
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from itertools import filterfalse
from typing import TYPE_CHECKING, Any, NamedTuple, TypeGuard, cast
from uuid import UUID, uuid5

import orjson
import structlog
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.constants import CONFIG_KEY_CHECKPOINTER
from langgraph.graph import StateGraph
from langgraph.pregel import Pregel
from langgraph.store.base import BaseStore
from starlette.exceptions import HTTPException

from langgraph_api import config as lg_api_config
from langgraph_api import timing
from langgraph_api.feature_flags import FF_USE_CORE_API, USE_RUNTIME_CONTEXT_API
from langgraph_api.js.base import BaseRemotePregel, is_js_path
from langgraph_api.schema import Config
from langgraph_api.timing import profiled_import
from langgraph_api.utils.config import run_in_executor, var_child_runnable_config
from langgraph_api.utils.errors import GraphLoadError

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

logger = structlog.stdlib.get_logger(__name__)

GraphFactoryFromConfig = Callable[[Config], Pregel | StateGraph]
GraphFactory = Callable[[], Pregel | StateGraph]
GraphValue = Pregel | GraphFactory | GraphFactoryFromConfig


GRAPHS: dict[str, GraphValue] = {}
NAMESPACE_GRAPH = UUID("6ba7b821-9dad-11d1-80b4-00c04fd430c8")
FACTORY_ACCEPTS_CONFIG: dict[str, bool] = {}


async def register_graph(
    graph_id: str,
    graph: GraphValue,
    config: dict | None,
    *,
    description: str | None = None,
) -> None:
    """Register a graph."""
    from langgraph_api.grpc.ops import Assistants as AssistantsGrpc
    from langgraph_runtime.database import connect
    from langgraph_runtime.ops import Assistants as AssistantsRuntime

    Assistants = AssistantsGrpc if FF_USE_CORE_API else AssistantsRuntime

    GRAPHS[graph_id] = graph
    if callable(graph):
        FACTORY_ACCEPTS_CONFIG[graph_id] = len(inspect.signature(graph).parameters) > 0

    from langgraph_runtime.retry import retry_db

    @retry_db
    async def register_graph_db():
        async with connect() as conn:
            graph_name = (
                getattr(graph, "name", None) if isinstance(graph, Pregel) else None
            )
            assistant_name = (
                graph_name
                if graph_name is not None and graph_name != "LangGraph"
                else graph_id
            )
            await Assistants.put(
                conn,
                str(uuid5(NAMESPACE_GRAPH, graph_id)),
                graph_id=graph_id,
                metadata={"created_by": "system"},
                config=config or {},
                context={},
                if_exists="do_nothing",
                name=assistant_name,
                description=description,
            )

    if not lg_api_config.IS_EXECUTOR_ENTRYPOINT:
        await register_graph_db()


@asynccontextmanager
async def _generate_graph(value: Any) -> AsyncIterator[Any]:
    """Yield a graph object regardless of its type."""
    if isinstance(value, Pregel | BaseRemotePregel):
        yield value
    elif hasattr(value, "__aenter__") and hasattr(value, "__aexit__"):
        async with value as ctx_value:
            yield ctx_value
    elif hasattr(value, "__enter__") and hasattr(value, "__exit__"):
        with value as ctx_value:
            yield ctx_value
    elif asyncio.iscoroutine(value):
        yield await value
    else:
        yield value


def is_js_graph(graph_id: str) -> TypeGuard[BaseRemotePregel]:
    """Return whether a graph is a JS graph."""
    return graph_id in GRAPHS and isinstance(GRAPHS[graph_id], BaseRemotePregel)


def is_factory(
    value: GraphValue, graph_id: str
) -> TypeGuard[GraphFactoryFromConfig | GraphFactory]:
    return graph_id in FACTORY_ACCEPTS_CONFIG


def factory_accepts_config(
    value: GraphValue, graph_id: str
) -> TypeGuard[GraphFactoryFromConfig]:
    return FACTORY_ACCEPTS_CONFIG.get(graph_id, False)


@asynccontextmanager
async def get_graph(
    graph_id: str,
    config: Config,
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    store: BaseStore | None = None,
) -> AsyncIterator[Pregel]:
    """Return the runnable."""
    from langgraph_api.utils import config as lg_config

    assert_graph_exists(graph_id)
    value = GRAPHS[graph_id]
    if is_factory(value, graph_id):
        config = lg_config.ensure_config(config)

        if store is not None:
            if USE_RUNTIME_CONTEXT_API:
                from langgraph._internal._constants import CONFIG_KEY_RUNTIME
                from langgraph.runtime import Runtime

                runtime = config["configurable"].get(CONFIG_KEY_RUNTIME)
                if runtime is None:
                    patched_runtime = Runtime(store=store)
                elif isinstance(runtime, dict):
                    patched_runtime = Runtime(**(runtime | {"store": store}))
                elif runtime.store is None:
                    patched_runtime = cast("Runtime", runtime).override(store=store)
                else:
                    patched_runtime = runtime

                config["configurable"][CONFIG_KEY_RUNTIME] = patched_runtime
            else:
                from langgraph.constants import CONFIG_KEY_STORE

                if not config["configurable"].get(CONFIG_KEY_STORE):
                    config["configurable"][CONFIG_KEY_STORE] = store

        if checkpointer is not None and not config["configurable"].get(
            CONFIG_KEY_CHECKPOINTER
        ):
            config["configurable"][CONFIG_KEY_CHECKPOINTER] = checkpointer
        var_child_runnable_config.set(config)
        value = value(config) if factory_accepts_config(value, graph_id) else value()
    try:
        async with _generate_graph(value) as graph_obj:
            if isinstance(graph_obj, StateGraph):
                graph_obj = graph_obj.compile()
            if not isinstance(graph_obj, Pregel | BaseRemotePregel):
                raise HTTPException(
                    status_code=424,
                    detail=f"Graph '{graph_id}' is not valid. Review graph registration.",
                )
            update = {
                "checkpointer": checkpointer,
                "store": store,
            }
            if graph_obj.name == "LangGraph":
                update["name"] = graph_id
            if isinstance(graph_obj, BaseRemotePregel):
                update["config"] = config
            yield graph_obj.copy(update=update)
    finally:
        var_child_runnable_config.set(None)


def graph_exists(graph_id: str) -> bool:
    """Return whether a graph exists."""
    return graph_id in GRAPHS


def assert_graph_exists(graph_id: str) -> None:
    """Assert that a graph exists."""
    if not graph_exists(graph_id):
        raise HTTPException(
            status_code=404,
            detail=f"Graph '{graph_id}' not found. Expected one of: {sorted(GRAPHS.keys())}",
        )


def get_assistant_id(assistant_id: str) -> str:
    """Check if assistant_id is a valid graph_id. If so, retrieve the
    assistant_id from the graph_id. Otherwise, return the assistant_id
    as is.

    This method is used where the API allows passing both assistant_id
    and graph_id interchangeably.
    """
    if assistant_id in GRAPHS:
        assistant_id = str(uuid5(NAMESPACE_GRAPH, assistant_id))
    return assistant_id


class GraphSpec(NamedTuple):
    """A graph specification.

    This is a definition of the graph that can be used to load the graph
    from a file or module.
    """

    id: str
    """The ID of the graph."""
    path: str | None = None
    module: str | None = None
    variable: str | None = None
    config: dict | None = None
    """The configuration for the graph.
    
    Contains information such as: tags, recursion_limit and configurable.
    
    Configurable is a dict containing user defined values for the graph.
    """
    description: str | None = None
    """A description of the graph"""


js_bg_tasks: set[asyncio.Task] = set()


def _load_graph_config_from_env() -> dict | None:
    """Return graph config from env."""
    config_str = os.getenv("LANGGRAPH_CONFIG")
    if not config_str:
        return None
    try:
        config_per_id = orjson.loads(config_str)
    except orjson.JSONDecodeError as e:
        raise ValueError(
            "Provided environment variable LANGGRAPH_CONFIG must be a valid JSON object"
            f"\nFound: {config_str}"
        ) from e

    if not isinstance(config_per_id, dict):
        raise ValueError(
            "Provided environment variable LANGGRAPH_CONFIG must be a JSON object"
            f"\nFound: {config_str}"
        )

    return config_per_id


async def collect_graphs_from_env(register: bool = False) -> None:
    """Return graphs from env."""

    paths_str = os.getenv("LANGSERVE_GRAPHS")
    config_per_graph = _load_graph_config_from_env() or {}

    if paths_str:
        specs = []
        # graphs-config can be either a mapping from graph id to path where the graph
        # is defined or graph id to a dictionary containing information about the graph.
        try:
            graphs_config = orjson.loads(paths_str)
        except orjson.JSONDecodeError as e:
            raise ValueError(
                "LANGSERVE_GRAPHS must be a valid JSON object."
                f"\nFound: {paths_str}"
                "\n The LANGSERVE_GRAPHS environment variable is typically set"
                'from the "graphs" field in your configuration (langgraph.json) file.'
            ) from e

        for key, value in graphs_config.items():
            if isinstance(value, dict) and "path" in value:
                source = value["path"]
            elif isinstance(value, str):
                source = value
            else:
                msg = (
                    f"Invalid value '{value}' for graph '{key}'. "
                    "Expected a string or a dictionary. "
                    "If a string, it should be the path to the graph definition. "
                    "For example: '/path/to/graph.py:graph_variable' "
                    "or 'my.module:graph_variable'. "
                    "If a dictionary, then it needs to contains a `path` key with the "
                    "path to the graph definition."
                    "It can also contains additional configuration for the graph; "
                    "e.g., `description`."
                    "For example: {'path': '/path/to/graph.py:graph_variable', "
                    "'description': 'My graph'}"
                )
                raise TypeError(msg)

            try:
                path_or_module, variable = source.rsplit(":", maxsplit=1)
            except ValueError as e:
                raise ValueError(
                    f"Invalid path '{value}' for graph '{key}'."
                    " Did you miss a variable name?\n"
                    " Expected one of the following formats:"
                    " 'my.module:variable_name' or '/path/to/file.py:variable_name'"
                ) from e

            graph_config = config_per_graph.get(key, {})
            description = (
                value.get("description", None) if isinstance(value, dict) else None
            )

            # Module syntax uses `.` instead of `/` to separate directories
            if "/" in path_or_module:
                path = path_or_module
                module_ = None
            else:
                path = None
                module_ = path_or_module

            specs.append(
                GraphSpec(
                    key,
                    module=module_,
                    path=path,
                    variable=variable,
                    config=graph_config,
                    description=description,
                )
            )
    else:
        specs = [
            GraphSpec(
                id=graph_path.split("/")[-1].replace(".py", ""),
                path=graph_path,
                config=config_per_graph.get(
                    graph_path.split("/")[-1].replace(".py", "")
                ),
            )
            for graph_path in glob.glob("/graphs/*.py")
        ]

    def is_js_spec(x: GraphSpec) -> bool:
        return is_js_path(x.path)

    js_specs = list(filter(is_js_spec, specs))
    py_specs = list(filterfalse(is_js_spec, specs))

    if js_specs:
        if lg_api_config.API_VARIANT == "local_dev":
            raise NotImplementedError(
                "LangGraph.JS graphs are not yet supported in local development mode. "
                "To run your JS graphs, either use the LangGraph Studio application "
                "or run `langgraph up` to start the server in a Docker container."
            )
        import sys

        from langgraph_api.js.remote import (
            RemotePregel,
            run_js_http_process,
            run_js_process,
            run_remote_checkpointer,
            wait_until_js_ready,
        )

        js_bg_tasks.add(
            asyncio.create_task(
                run_remote_checkpointer(),
                name="remote-socket-poller",
            )
        )
        js_bg_tasks.add(
            asyncio.create_task(
                run_js_process(paths_str, watch="--reload" in sys.argv[1:]),
                name="remote-graphs",
            )
        )

        if (
            lg_api_config.HTTP_CONFIG
            and (js_app := lg_api_config.HTTP_CONFIG.get("app"))
            and is_js_path(js_app.split(":")[0])
        ):
            js_bg_tasks.add(
                asyncio.create_task(
                    run_js_http_process(
                        paths_str,
                        lg_api_config.HTTP_CONFIG or {},
                        watch="--reload" in sys.argv[1:],
                    ),
                )
            )

        for task in js_bg_tasks:
            task.add_done_callback(_handle_exception)

        await wait_until_js_ready()

        for spec in js_specs:
            graph = RemotePregel(graph_id=spec.id)
            if register:
                await register_graph(
                    spec.id, graph, spec.config, description=spec.description
                )

    for spec in py_specs:
        try:
            graph = await run_in_executor(None, _graph_from_spec, spec)
        except Exception as exc:
            raise GraphLoadError(spec, exc) from exc
        if register:
            await register_graph(
                spec.id, graph, spec.config, description=spec.description
            )


def _handle_exception(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception("Task failed", exc_info=e)
    finally:
        # if the task died either with exception or not, we should exit
        sys.exit(1)


async def stop_remote_graphs() -> None:
    logger.info("Shutting down remote graphs")
    for task in js_bg_tasks:
        task.cancel("Stopping remote graphs.")


def verify_graphs() -> None:
    asyncio.run(collect_graphs_from_env())


def _metadata_fn(spec: GraphSpec) -> dict[str, Any]:
    return {"graph_id": spec.id, "module": spec.module, "path": spec.path}


@timing.timer(
    message="Importing graph with id {graph_id}",
    metadata_fn=_metadata_fn,
    warn_threshold_secs=3,
    warn_message=(
        "Import for graph {graph_id} exceeded the expected startup time. "
        "Slow initialization (often due to work executed at import time) can delay readiness, "
        "reduce scale-out capacity, and may cause deployments to be marked unhealthy."
    ),
    error_threshold_secs=30,
)
def _graph_from_spec(spec: GraphSpec) -> GraphValue:
    """Return a graph from a spec."""
    # import the graph module
    import_path = f"{spec.module or spec.path}:{spec.variable or '<auto>'}"
    with profiled_import(import_path):
        if spec.module:
            module = importlib.import_module(spec.module)
        elif spec.path:
            try:
                modname = (
                    spec.path.replace("/", "__")
                    .replace(".py", "")
                    .replace(" ", "_")
                    .lstrip(".")
                )
                modspec = importlib.util.spec_from_file_location(modname, spec.path)
                if modspec is None:
                    raise ValueError(f"Could not find python file for graph: {spec}")
                module = importlib.util.module_from_spec(modspec)
                sys.modules[modname] = module
                modspec.loader.exec_module(module)  # type: ignore[possibly-unbound-attribute]
            except ImportError as e:
                e.add_note(f"Could not import python module for graph:\n{spec}")
                if lg_api_config.API_VARIANT == "local_dev":
                    e.add_note(
                        "This error likely means you haven't installed your project and its dependencies yet. Before running the server, install your project:\n\n"
                        "If you are using requirements.txt:\n"
                        "python -m pip install -r requirements.txt\n\n"
                        "If you are using pyproject.toml or setuptools:\n"
                        "python -m pip install -e .\n\n"
                        "Make sure to run this command from your project's root directory (where your setup.py or pyproject.toml is located)"
                    )
                raise
            except FileNotFoundError as e:
                e.add_note(f"Could not find python file for graph: {spec}")
                raise
        else:
            raise ValueError("Graph specification must have a path or module")

    if spec.variable:
        try:
            graph: GraphValue = module.__dict__[spec.variable]
        except KeyError as e:
            available = [k for k in module.__dict__ if not k.startswith("__")]
            suggestion = ""
            if available:
                likely = [
                    k
                    for k in available
                    if isinstance(module.__dict__[k], StateGraph | Pregel)
                ]
                if likely:
                    prefix = spec.module or spec.path
                    likely_ = "\n".join(
                        [f"\t- {prefix}:{k}" if prefix else k for k in likely]
                    )
                    suggestion = (
                        f"\nDid you mean to use one of the following?\n{likely_}"
                    )
                elif available:
                    suggestion = (
                        f"\nFound the following exports: {', '.join(available)}"
                    )

            raise ValueError(
                f"Could not find graph '{spec.variable}' in '{spec.path}'. "
                f"Please check that:\n"
                f"1. The file exports a variable named '{spec.variable}'\n"
                f"2. The variable name in your config matches the export name{suggestion}"
            ) from e
        if callable(graph):
            sig = inspect.signature(graph)
            if not sig.parameters:
                pass
            elif len(sig.parameters) != 1:
                raise ValueError(
                    f"Graph factory function '{spec.variable}' in module '{spec.path}' must take exactly one argument, a RunnableConfig"
                )
        elif isinstance(graph, StateGraph):
            graph = graph.compile()
        elif isinstance(graph, Pregel):
            # We don't want to fail real deployments, but this will help folks catch unnecessary custom components
            # before they deploy
            if lg_api_config.API_VARIANT == "local_dev":
                has_checkpointer = isinstance(graph.checkpointer, BaseCheckpointSaver)
                has_store = isinstance(graph.store, BaseStore)
                if has_checkpointer or has_store:
                    components = []
                    if has_checkpointer:
                        components.append(
                            f"checkpointer (type {type(graph.checkpointer)})"
                        )
                    if has_store:
                        components.append(f"store (type {type(graph.store)})")
                    component_list = " and ".join(components)

                    raise ValueError(
                        f"Heads up! Your graph '{spec.variable}' from '{spec.path}' includes a custom {component_list}. "
                        f"With LangGraph API, persistence is handled automatically by the platform, "
                        f"so providing a custom {component_list} here isn't necessary and will be ignored when deployed.\n\n"
                        f"To simplify your setup and use the built-in persistence, please remove the custom {component_list} "
                        f"from your graph definition. If you are looking to customize which postgres database to connect to,"
                        " please set the `POSTGRES_URI` environment variable."
                        " See https://langchain-ai.github.io/langgraph/cloud/reference/env_var/#postgres_uri_custom for more details."
                    )

        else:
            raise ValueError(
                f"Variable '{spec.variable}' in module '{spec.path}' is not a Graph or Graph factory function"
            )
    else:
        # find the graph in the module
        # - first look for a compiled graph (Pregel)
        # - if not found, look for a Graph and compile it
        for _, member in inspect.getmembers(module):
            if isinstance(member, Pregel):
                graph = member
                break
        else:
            for _, member in inspect.getmembers(module):
                if isinstance(member, StateGraph):
                    graph = member.compile()
                    break
            else:
                raise ValueError(
                    f"Could not find a Graph in module at path: {spec.path}"
                )

    return graph


@functools.lru_cache(maxsize=1)
def _get_init_embeddings() -> Callable[[str, ...], "Embeddings"] | None:
    try:
        from langchain.embeddings import (  # type: ignore[unresolved-import]
            init_embeddings,
        )

        return init_embeddings
    except ImportError:
        return None


@timing.timer(
    message="Loading embeddings {embeddings_path}",
    metadata_fn=lambda index_config: {"embeddings_path": index_config.get("embed")},
    warn_threshold_secs=5,
    warn_message="Loading embeddings '{embeddings_path}' took longer than expected",
    error_threshold_secs=10,
)
def resolve_embeddings(index_config: dict) -> "Embeddings":
    """Return embeddings from config.

    Args:
        index_config: Configuration for the vector store index
            Must contain an "embed" key specifying either:
            - A path to a Python file and function (e.g. "./embeddings.py:get_embeddings")
            - A LangChain embeddings identifier (e.g. "openai:text-embedding-3-small")

    Returns:
        Embeddings: A LangChain embeddings instance

    Raises:
        ValueError: If embeddings cannot be loaded from the config
    """
    from langchain_core.embeddings import Embeddings
    from langgraph.store.base import ensure_embeddings

    embed: str = index_config["embed"]
    if ".py:" in embed:
        module_name, function = embed.rsplit(":", 1)
        module_name = module_name.rstrip(":")

        try:
            with profiled_import(embed):
                if "/" in module_name:
                    # Load from file path
                    modname = (
                        module_name.replace("/", "__")
                        .replace(".py", "")
                        .replace(" ", "_")
                    )
                    modspec = importlib.util.spec_from_file_location(
                        modname, module_name
                    )
                    if modspec is None:
                        raise ValueError(
                            f"Could not find embeddings file: {module_name}"
                        )
                    module = importlib.util.module_from_spec(modspec)
                    sys.modules[modname] = module
                    modspec.loader.exec_module(module)  # type: ignore[possibly-unbound-attribute]
                else:
                    # Load from Python module
                    module = importlib.import_module(module_name)

            embedding_fn = getattr(module, function, None)
            if embedding_fn is None:
                raise ValueError(
                    f"Could not find embeddings function '{function}' in module: {module_name}"
                )

            if isinstance(embedding_fn, Embeddings):
                return embedding_fn
            elif not callable(embedding_fn):
                raise ValueError(
                    f"Embeddings function '{function}' in module: {module_name} is not callable"
                )

            return ensure_embeddings(embedding_fn)

        except ImportError as e:
            e.add_note(f"Could not import embeddings module:\n{module_name}\n\n")
            if lg_api_config.API_VARIANT == "local_dev":
                e.add_note(
                    "If you're in development mode, make sure you've installed your project "
                    "and its dependencies:\n"
                    "- For requirements.txt: pip install -r requirements.txt\n"
                    "- For pyproject.toml: pip install -e .\n"
                )
            raise
        except FileNotFoundError as e:
            raise ValueError(f"Could not find embeddings file: {module_name}") from e

    else:
        # Load from LangChain embeddings
        init_embeddings = _get_init_embeddings()
        if init_embeddings is None:
            raise ValueError(
                f"Could not load LangChain embeddings '{embed}'. "
                "Loading embeddings by provider:identifier requires the langchain package (>=0.3.9). "
                "Install it with: pip install 'langchain>=0.3.9'"
                " or specify 'embed' as a path to a "
                "variable in a Python file instead."
            )
        # Capture warnings
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=("The function `init_embeddings` is in beta."),
            )
            return init_embeddings(embed)
