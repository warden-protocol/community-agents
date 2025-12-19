"""Custom encryption loading for LangGraph API.

This module provides functions to load and access custom encryption
instances defined by users in their langgraph.json configuration.
"""

from __future__ import annotations

import functools
import importlib.util
import sys
from typing import TYPE_CHECKING, Literal, get_args

import structlog

from langgraph_api import timing
from langgraph_api.config import LANGGRAPH_ENCRYPTION
from langgraph_api.timing import profiled_import

if TYPE_CHECKING:
    from langgraph_sdk import Encryption

ModelType = Literal["run", "thread", "assistant", "cron", "checkpoint"]
SUPPORTED_ENCRYPTION_MODELS: frozenset[str] = frozenset(get_args(ModelType))

logger = structlog.stdlib.get_logger(__name__)


@functools.lru_cache(maxsize=1)
def get_encryption_instance() -> Encryption | None:
    """Get the custom encryption instance if configured.

    Returns:
        The Encryption instance if configured, or None if no encryption is configured.
    """
    if not LANGGRAPH_ENCRYPTION:
        return None
    logger.info(
        f"Getting encryption instance: {LANGGRAPH_ENCRYPTION}",
        langgraph_encryption=str(LANGGRAPH_ENCRYPTION),
    )
    path = LANGGRAPH_ENCRYPTION.get("path")
    if path is None:
        return None
    return _get_encryption_instance(path)


def _get_encryption_instance(path: str) -> Encryption:
    """Load the encryption instance from a path.

    Args:
        path: Module path in format "./path/to/file.py:name" or "module:name"

    Returns:
        The Encryption instance.

    Raises:
        ValueError: If the path is invalid or the encryption instance is not found.
    """
    encryption_instance = _load_encryption_obj(path)
    logger.info(f"Loaded encryption instance from path {path}: {encryption_instance}")
    return encryption_instance


@timing.timer(
    message="Loading custom encryption {encryption_path}",
    metadata_fn=lambda encryption_path: {"encryption_path": encryption_path},
    warn_threshold_secs=5,
    warn_message="Loading custom encryption '{encryption_path}' took longer than expected",
    error_threshold_secs=10,
)
def _load_encryption_obj(path: str) -> Encryption:
    """Load an Encryption object from a path string.

    Args:
        path: Module path in format "./path/to/file.py:name" or "module:name"

    Returns:
        The Encryption instance.

    Raises:
        ValueError: If the path is invalid or the encryption instance is not found.
        ImportError: If the module cannot be imported.
        FileNotFoundError: If the file cannot be found.
    """
    if ":" not in path:
        raise ValueError(
            f"Invalid encryption path format: {path}. "
            "Must be in format: './path/to/file.py:name' or 'module:name'"
        )

    module_name, callable_name = path.rsplit(":", 1)
    module_name = module_name.rstrip(":")

    if module_name.endswith(".js") or module_name.endswith(".mjs"):
        raise ValueError(
            f"JavaScript encryption is not supported. "
            f"Please use a Python module instead: {module_name}"
        )

    try:
        with profiled_import(path):
            if "/" in module_name or ".py" in module_name:
                modname = f"dynamic_module_{hash(module_name)}"
                modspec = importlib.util.spec_from_file_location(modname, module_name)
                if modspec is None or modspec.loader is None:
                    raise ValueError(f"Could not load file: {module_name}")
                module = importlib.util.module_from_spec(modspec)
                sys.modules[modname] = module
                modspec.loader.exec_module(module)
            else:
                module = importlib.import_module(module_name)

        loaded_encrypt = getattr(module, callable_name, None)
        if loaded_encrypt is None:
            raise ValueError(
                f"Could not find encrypt '{callable_name}' in module: {module_name}"
            )
        # Import Encryption at runtime only when needed (avoids requiring SDK 0.2.14)
        from langgraph_sdk import Encryption as EncryptionClass

        if not isinstance(loaded_encrypt, EncryptionClass):
            raise ValueError(
                f"Expected an Encryption instance, got {type(loaded_encrypt)}"
            )

        _validate_encryption_models(loaded_encrypt)
        return loaded_encrypt

    except ImportError as e:
        e.add_note(f"Could not import module:\n{module_name}\n\n")
        raise
    except FileNotFoundError as e:
        raise ValueError(f"Could not find file: {module_name}") from e


def _validate_encryption_models(encryption_instance: Encryption) -> None:
    """Validate that all registered model-specific handlers use supported models.

    Args:
        encryption_instance: The loaded Encryption instance to validate.

    Raises:
        ValueError: If any registered model names are not in SUPPORTED_ENCRYPTION_MODELS.
    """
    registered_encryptor_models = set(encryption_instance._json_encryptors.keys())
    registered_decryptor_models = set(encryption_instance._json_decryptors.keys())

    invalid_encryptor_models = registered_encryptor_models - SUPPORTED_ENCRYPTION_MODELS
    invalid_decryptor_models = registered_decryptor_models - SUPPORTED_ENCRYPTION_MODELS

    invalid_models = invalid_encryptor_models | invalid_decryptor_models
    if invalid_models:
        raise ValueError(
            f"Invalid encryption model(s) configured: {sorted(invalid_models)}. "
            f"Supported models are: {sorted(SUPPORTED_ENCRYPTION_MODELS)}"
        )
