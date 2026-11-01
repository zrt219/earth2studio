# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Runtime compatibility bootstrap for Earth2Studio in Python 3.10 and Zarr 2.x environments.

Provides lightweight stubs for Zarr 3.x store abstractions, tomllib fallback,
and isolates package namespaces to prevent eager cascade import crashes.
"""

from __future__ import annotations

import pathlib
import sys
import types
from typing import Any


def bootstrap_environment() -> None:
    """Initialize compatibility stubs before importing Earth2Studio modules."""
    # 1. Python < 3.11 tomllib fallback
    if "tomllib" not in sys.modules:
        try:
            import tomllib  # type: ignore
        except ModuleNotFoundError:
            try:
                import tomli as tomllib  # type: ignore

                sys.modules["tomllib"] = tomllib
            except ImportError:
                pass

    # 2. Zarr 2.x -> Zarr 3.x store compatibility stubs
    try:
        import zarr

        # In Zarr 2.x, zarr.abc is aliased to numcodecs.abc; replace with store-capable module
        zarr_store = types.ModuleType("zarr.abc.store")
        zarr_store.Store = type("Store", (object,), {})  # type: ignore
        zarr_store.ByteRequest = type("ByteRequest", (object,), {})  # type: ignore

        zarr.abc = types.ModuleType("zarr.abc")
        zarr.abc.store = zarr_store  # type: ignore
        sys.modules["zarr.abc"] = zarr.abc
        sys.modules["zarr.abc.store"] = zarr_store

        # Buffer stubs
        zarr_core_buffer = types.ModuleType("zarr.core.buffer")
        zarr_core_buffer.Buffer = type("Buffer", (object,), {})  # type: ignore
        zarr_core_buffer.BufferPrototype = type("BufferPrototype", (object,), {})  # type: ignore
        sys.modules["zarr.core.buffer"] = zarr_core_buffer
        if hasattr(zarr, "core"):
            zarr.core.buffer = zarr_core_buffer  # type: ignore

        # Storage wrapper stubs
        import zarr.storage

        if not hasattr(zarr.storage, "WrapperStore"):
            zarr.storage.WrapperStore = type("WrapperStore", (object,), {})  # type: ignore
        if not hasattr(zarr.storage, "LocalStore"):
            zarr.storage.LocalStore = type("LocalStore", (object,), {})  # type: ignore
        if not hasattr(zarr.storage, "ObjectStore"):
            zarr.storage.ObjectStore = type("ObjectStore", (object,), {})  # type: ignore
    except ImportError:
        pass


def get_persistence_model_class() -> Any:
    """Cleanly import Persistence without triggering cascading package imports."""
    bootstrap_environment()
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent

    # Isolate earth2studio.models.px if not already loaded
    if "earth2studio.models.px" not in sys.modules:
        px_mod = types.ModuleType("earth2studio.models.px")
        px_mod.__path__ = [str(repo_root / "earth2studio" / "models" / "px")]
        px_mod.__file__ = str(
            repo_root / "earth2studio" / "models" / "px" / "__init__.py"
        )
        sys.modules["earth2studio.models.px"] = px_mod

    import earth2studio.models.px.persistence as persistence_mod

    return persistence_mod.Persistence


def get_gfs_data_source_class() -> Any:
    """Cleanly import GFS data source without triggering cascading package imports."""
    bootstrap_environment()
    repo_root = pathlib.Path(__file__).resolve().parent.parent.parent.parent

    # Isolate earth2studio.data if not already loaded
    if "earth2studio.data" not in sys.modules:
        data_mod = types.ModuleType("earth2studio.data")
        data_mod.__path__ = [str(repo_root / "earth2studio" / "data")]
        data_mod.__file__ = str(repo_root / "earth2studio" / "data" / "__init__.py")
        sys.modules["earth2studio.data"] = data_mod

    import earth2studio.data.gfs as gfs_mod

    return gfs_mod.GFS
