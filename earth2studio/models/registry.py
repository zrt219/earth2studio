# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# Compliance: .agents/rules/e2s-009-prognostic-models.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

"""Unified model registry for Earth2Studio prognostic models.

Provides model discovery, case-insensitive alias normalization, metadata inspection,
and decoupled lazy loading without eager imports of optional dependencies or heavy libraries.
"""

from __future__ import annotations

import difflib
import importlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# Core evaluation variable subset
CORE_EVAL_VARIABLES: list[str] = [
    "t2m",
    "u10m",
    "v10m",
    "z500",
    "t850",
    "msl",
]


@runtime_checkable
class PrognosticModelProtocol(Protocol):
    """Protocol matching earth2studio.models.px.base.PrognosticModel."""

    def __call__(self, x: Any, coords: Any) -> tuple[Any, Any]: ...
    def create_iterator(self, x: Any, coords: Any) -> Any: ...
    def input_coords(self) -> Any: ...
    def output_coords(self, input_coords: Any) -> Any: ...


@dataclass(frozen=True)
class ModelInfo:
    """Standardized metadata representation for registered prognostic models.

    Parameters
    ----------
    name : str
        Canonical model identifier.
    family : str
        Model architecture family (e.g. 'sfno', 'gnn', 'transformer_3d', 'vit', 'baseline', 'ensemble').
    resolution : float | tuple[float, float] | str
        Nominal spatial resolution (degrees or 'domain_adaptive').
    variables : list[str]
        List of nominal variables predicted by the model.
    history_steps : int
        Number of historical lead-time steps required in input.
    timestep : float | str
        Nominal time-step increment in hours.
    description : str
        Human-readable summary of the model.
    license : str
        License string (e.g. 'Apache-2.0', 'CC-BY-4.0').
    checkpoint_source : str
        Pre-trained checkpoint URI or model card provenance (NGC, HuggingFace, etc.).
    aliases : tuple[str, ...]
        Registered alternate lookup aliases.
    provider : str
        Creating organization or project.
    backend : str
        Computational backend framework ('pytorch', 'jax', 'onnx', 'composite').
    grid_shape : tuple[int, int] | str
        Nominal grid shape (lat, lon) or descriptor.
    extra_metadata : dict[str, Any]
        Additional architecture flags or domain-specific attributes.
    """

    name: str
    family: str
    resolution: float | tuple[float, float] | str
    variables: list[str]
    history_steps: int
    timestep: float | str
    description: str
    license: str
    checkpoint_source: str
    aliases: tuple[str, ...] = field(default_factory=tuple)
    provider: str = ""
    backend: str = "pytorch"
    grid_shape: tuple[int, int] | str = "domain_adaptive"
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def nominal_resolution(self) -> float | tuple[float, float] | str:
        """Alias for resolution property."""
        return self.resolution

    @property
    def time_step_hours(self) -> float:
        """Nominal time-step increment in hours."""
        if isinstance(self.timestep, (int, float)):
            return float(self.timestep)
        try:
            return float(self.timestep)
        except (ValueError, TypeError):
            return 6.0

    @property
    def checkpoint_provenance(self) -> str:
        """Alias for checkpoint_source property."""
        return self.checkpoint_source

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary."""
        return {
            "name": self.name,
            "family": self.family,
            "resolution": self.resolution,
            "nominal_resolution": self.nominal_resolution,
            "grid_shape": self.grid_shape,
            "variables": list(self.variables),
            "num_variables": len(self.variables),
            "history_steps": self.history_steps,
            "timestep": self.timestep,
            "time_step_hours": self.time_step_hours,
            "description": self.description,
            "license": self.license,
            "checkpoint_source": self.checkpoint_source,
            "checkpoint_provenance": self.checkpoint_provenance,
            "aliases": list(self.aliases),
            "provider": self.provider,
            "backend": self.backend,
            "extra_metadata": dict(self.extra_metadata),
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def __contains__(self, key: str) -> bool:
        return key in self.to_dict()

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


@dataclass
class _ModelEntry:
    info: ModelInfo
    module_path: str = ""
    class_name: str = ""
    model_cls: type[Any] | None = None
    loader: Callable[..., Any] | None = None


# Internal registry tables
_REGISTRY: dict[str, _ModelEntry] = {}
_ALIAS_MAP: dict[str, str] = {}


def _normalize(name: str) -> str:
    """Normalize model identifier: lowercase, whitespace stripped, hyphens replaced."""
    return re.sub(r"[-\s]+", "_", name.strip().lower())


def register_model(
    name: str,
    module_path: str | None = None,
    class_name: str | None = None,
    info: ModelInfo | None = None,
    aliases: list[str] | tuple[str, ...] | None = None,
    loader: Callable[..., Any] | None = None,
    override: bool = False,
) -> Callable[[Any], Any] | None:
    """Register a prognostic model in the central registry.

    Can be called directly as a function or used as a class decorator.

    Parameters
    ----------
    name : str
        Canonical model name.
    module_path : str | None, optional
        Import path for the module containing the class.
    class_name : str | None, optional
        Class name within the module.
    info : ModelInfo | None, optional
        Metadata describing the model.
    aliases : list[str] | tuple[str, ...] | None, optional
        Alternative lookup aliases.
    loader : Callable[..., Any] | None, optional
        Custom loader function for instantiating the model.
    override : bool, default False
        Whether to overwrite an existing registration.
    """
    canonical = _normalize(name)
    if canonical in _REGISTRY and not override:
        raise ValueError(
            f"Model '{name}' is already registered. Set override=True to overwrite."
        )

    alias_tuple = tuple(_normalize(a) for a in (aliases or ()))

    def decorator(cls: Any) -> Any:
        entry_info = info
        if entry_info is None:
            entry_info = ModelInfo(
                name=canonical,
                family=getattr(cls, "FAMILY", "unknown"),
                resolution=getattr(cls, "NOMINAL_RESOLUTION", "domain_adaptive"),
                variables=getattr(cls, "VARIABLES", CORE_EVAL_VARIABLES),
                history_steps=getattr(cls, "HISTORY_STEPS", 1),
                timestep=getattr(cls, "TIME_STEP_HOURS", 6.0),
                description=cls.__doc__ or f"Prognostic model {cls.__name__}",
                license=getattr(cls, "LICENSE", "Apache-2.0"),
                checkpoint_source=getattr(cls, "CHECKPOINT_PROVENANCE", "custom"),
                aliases=alias_tuple,
                provider=getattr(cls, "PROVIDER", "custom"),
                backend=getattr(cls, "BACKEND", "pytorch"),
                grid_shape=getattr(cls, "GRID_SHAPE", "domain_adaptive"),
            )
        entry = _ModelEntry(
            info=entry_info,
            module_path=getattr(cls, "__module__", ""),
            class_name=getattr(cls, "__name__", ""),
            model_cls=cls,
            loader=loader,
        )
        _REGISTRY[canonical] = entry
        for alias in alias_tuple:
            _ALIAS_MAP[alias] = canonical
        return cls

    if module_path is not None and class_name is not None and info is not None:
        entry = _ModelEntry(
            info=info,
            module_path=module_path,
            class_name=class_name,
            loader=loader,
        )
        _REGISTRY[canonical] = entry
        for alias in alias_tuple:
            _ALIAS_MAP[alias] = canonical
        return None

    return decorator


def resolve_model_name(name: str) -> str:
    """Resolve user-supplied name or alias to canonical model identifier.

    Parameters
    ----------
    name : str
        Model name or registered alias.

    Returns
    -------
    str
        Canonical model name.

    Raises
    ------
    KeyError
        If model name is not recognized, includes fuzzy "Did you mean?" suggestion.
    """
    norm = _normalize(name)
    if norm in _REGISTRY:
        return norm
    if norm in _ALIAS_MAP:
        return _ALIAS_MAP[norm]

    # Ultra-tolerant alphanumeric match (ignoring underscores)
    compact_norm = norm.replace("_", "")
    for k in _REGISTRY:
        if k.replace("_", "") == compact_norm:
            return k
    for alias, canonical in _ALIAS_MAP.items():
        if alias.replace("_", "") == compact_norm:
            return canonical

    # Fuzzy suggestion
    all_known = sorted(list(_REGISTRY.keys()) + list(_ALIAS_MAP.keys()))
    matches = difflib.get_close_matches(norm, all_known, n=3, cutoff=0.5)
    hint = f" Did you mean '{matches[0]}'?" if matches else ""
    available = sorted(list(_REGISTRY.keys()))
    raise KeyError(
        f"Model '{name}' not found in registry.{hint} Available models: {available}"
    )


def list_models(include_aliases: bool = False) -> list[str]:
    """List registered prognostic models.

    Parameters
    ----------
    include_aliases : bool, default False
        Whether to include alternate aliases in the returned list.

    Returns
    -------
    list[str]
        Alphabetically sorted model identifiers.
    """
    if not include_aliases:
        return sorted(list(_REGISTRY.keys()))
    return sorted(list(set(list(_REGISTRY.keys()) + list(_ALIAS_MAP.keys()))))


def get_model_info(name: str) -> ModelInfo:
    """Retrieve metadata ModelInfo for a model by name or alias.

    Parameters
    ----------
    name : str
        Model name or alias.

    Returns
    -------
    ModelInfo
        Frozen dataclass containing model metadata.
    """
    canonical = resolve_model_name(name)
    return _REGISTRY[canonical].info


def get_model(
    name: str,
    pretrained: bool = True,
    pretrained_path: str | None = None,
    **kwargs: Any,
) -> Any:
    """Retrieve and instantiate a prognostic model by registered name or alias.

    Performs dynamic lazy loading via ``importlib.import_module()`` so that
    importing the registry does not trigger optional dependencies or heavy imports.

    Parameters
    ----------
    name : str
        Model name or registered alias (case-insensitive).
    pretrained : bool, default True
        Whether to load pre-trained weights if supported by model.
    pretrained_path : str, optional
        Custom checkpoint path or URI.
    **kwargs : Any
        Additional keyword arguments passed to model constructor or loader.

    Returns
    -------
    PrognosticModel
        Instantiated prognostic model.
    """
    canonical = resolve_model_name(name)
    entry = _REGISTRY[canonical]

    # If custom loader registered
    if entry.loader is not None:
        return entry.loader(
            pretrained=pretrained, pretrained_path=pretrained_path, **kwargs
        )

    # Dynamic lazy import or direct class
    if entry.model_cls is not None:
        cls = entry.model_cls
    else:
        try:
            mod = importlib.import_module(entry.module_path)
            cls = getattr(mod, entry.class_name)
        except (ImportError, AttributeError) as err:
            raise ImportError(
                f"Failed to import model class '{entry.class_name}' from '{entry.module_path}' "
                f"for model '{canonical}'. Required dependencies may be missing. Original error: {err}"
            ) from err

    # Check for AutoModelMixin compatibility
    is_auto_model = hasattr(cls, "from_pretrained") and callable(
        getattr(cls, "from_pretrained")
    )

    if pretrained and is_auto_model and "domain_coords" not in kwargs:
        try:
            return cls.from_pretrained(pretrained_path, **kwargs)
        except Exception:
            # Fall back to standard constructor if offline or checkpoint resolution fails
            return cls(**kwargs)

    return cls(**kwargs)


class AutoPrognostic:
    """High-level auto factory for prognostic models."""

    @classmethod
    def from_pretrained(
        cls,
        pretrained_model_name_or_path: str,
        **kwargs: Any,
    ) -> Any:
        """Instantiate a pre-trained prognostic model from name or path."""
        pretrained = kwargs.pop("pretrained", True)
        return get_model(pretrained_model_name_or_path, pretrained=pretrained, **kwargs)


# ==============================================================================
# Built-In Canonical Model Registrations
# ==============================================================================


def _init_catalog() -> None:
    """Initialize canonical models into the registry."""

    # 1. SFNO (FourCastNet v2)
    register_model(
        name="sfno",
        module_path="earth2studio.models.px.sfno",
        class_name="SFNO",
        aliases=[
            "fcnv2",
            "fourcastnetv2",
            "fourcastnet_v2",
            "fcn_v2",
            "sfno_73ch",
            "sfno_73ch_small",
            "fourcastnet2",
        ],
        info=ModelInfo(
            name="sfno",
            family="sfno",
            resolution=0.25,
            variables=CORE_EVAL_VARIABLES + ["sp", "tcwv", "u100m", "v100m"],
            history_steps=1,
            timestep=6.0,
            description="NVIDIA FourCastNet v2 Spherical Fourier Neural Operator (SFNO)",
            license="Apache-2.0",
            checkpoint_source="ngc://models/nvidia/modulus/sfno_73ch_small@0.1.0",
            aliases=(
                "fcnv2",
                "fourcastnetv2",
                "fourcastnet_v2",
                "sfno_73ch",
            ),
            provider="NVIDIA",
            backend="pytorch",
            grid_shape=(721, 1440),
            extra_metadata={"so3_equivariant": True, "channels": 73},
        ),
    )

    # 2. GraphCast
    register_model(
        name="graphcast",
        module_path="earth2studio.models.px.graphcast_operational",
        class_name="GraphCastOperational",
        aliases=[
            "graphcast_operational",
            "graphcast-operational",
            "graphcast_small",
            "weathernext_graph",
            "graphcast_025",
        ],
        info=ModelInfo(
            name="graphcast",
            family="gnn",
            resolution=0.25,
            variables=CORE_EVAL_VARIABLES + ["tp06"],
            history_steps=2,
            timestep=6.0,
            description="Google DeepMind GraphCast multi-mesh message passing graph neural network",
            license="Apache-2.0",
            checkpoint_source="https://storage.googleapis.com/dm_graphcast/params/GraphCast_operational",
            aliases=("graphcast_operational", "weathernext_graph"),
            provider="Google DeepMind",
            backend="jax",
            grid_shape=(721, 1440),
            extra_metadata={"requires_two_step_history": True, "has_tp06": True},
        ),
    )

    # 3. Pangu-Weather
    register_model(
        name="pangu",
        module_path="earth2studio.models.px.pangu",
        class_name="Pangu6",
        aliases=[
            "panguweather",
            "pangu_weather",
            "pangu6",
            "pangu-6",
            "pangu24",
            "pangu3",
        ],
        info=ModelInfo(
            name="pangu",
            family="transformer_3d",
            resolution=0.25,
            variables=CORE_EVAL_VARIABLES,
            history_steps=1,
            timestep=6.0,
            description="Huawei Pangu-Weather 3D Earth-Specific Swin Transformer",
            license="Apache-2.0",
            checkpoint_source="hf://NickGeneva/earth_ai/pangu",
            aliases=("panguweather", "pangu_weather", "pangu6"),
            provider="Huawei",
            backend="onnx",
            grid_shape=(721, 1440),
            extra_metadata={"interweaved_ar": True, "channels": 69},
        ),
    )

    # 4. ClimaX
    register_model(
        name="climax",
        module_path="earth2studio.models.px.climax",
        class_name="ClimaX",
        aliases=[
            "climax_vit",
            "climax-vit",
            "climax_era5",
            "climax_foundation",
        ],
        info=ModelInfo(
            name="climax",
            family="vit",
            resolution=1.40625,
            variables=CORE_EVAL_VARIABLES,
            history_steps=1,
            timestep=6.0,
            description="Microsoft ClimaX foundation model for weather and climate with cross-channel attention",
            license="Apache-2.0",
            checkpoint_source="hf://microsoft/climax",
            aliases=("climax_vit", "climax_era5"),
            provider="Microsoft Research",
            backend="pytorch",
            grid_shape=(128, 256),
            extra_metadata={"patch_size": (16, 16), "variable_tokenization": True},
        ),
    )

    # 5. Persistence
    register_model(
        name="persistence",
        module_path="earth2studio.models.px.persistence",
        class_name="Persistence",
        aliases=[
            "baseline_persistence",
            "identity",
            "persist",
            "persistence_baseline",
        ],
        info=ModelInfo(
            name="persistence",
            family="baseline",
            resolution="domain_adaptive",
            variables=CORE_EVAL_VARIABLES,
            history_steps=1,
            timestep=6.0,
            description="Persistence physical identity baseline: forecast state equals initialization state",
            license="Apache-2.0",
            checkpoint_source="none://analytical_baseline",
            aliases=("identity", "persist", "baseline_persistence"),
            provider="Origin Datum / NVIDIA",
            backend="pytorch",
            grid_shape="domain_adaptive",
            extra_metadata={"analytical": True, "skill_score_baseline": True},
        ),
    )

    # 6. Multi-Model Ensemble
    register_model(
        name="multimodel",
        module_path="earth2studio.models.px.multi_model",
        class_name="MultiModelEnsemble",
        aliases=[
            "multi_model_ensemble",
            "mme",
            "ensemble",
            "multi_model",
            "multimodelensemble",
        ],
        info=ModelInfo(
            name="multimodel",
            family="ensemble",
            resolution="target_coords_adaptive",
            variables=CORE_EVAL_VARIABLES,
            history_steps=1,
            timestep=6.0,
            description="Multi-Model Prognostic Ensemble combining GraphCast, SFNO, Pangu, ClimaX, and Persistence",
            license="Apache-2.0",
            checkpoint_source="composite://multi_model",
            aliases=(
                "multi_model_ensemble",
                "mme",
                "ensemble",
                "multi_model",
            ),
            provider="Origin Datum",
            backend="pytorch",
            grid_shape="target_coords_adaptive",
            extra_metadata={"member_count": 5, "supports_weighting": True},
        ),
    )


_init_catalog()
