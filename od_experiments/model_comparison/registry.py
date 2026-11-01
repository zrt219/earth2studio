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

"""Operational model comparison registry for cross-model comparative evaluation.

Integrates the core Earth2Studio model catalog with deterministic CPU mock models,
empirical benchmark metadata, and multi-model evaluation suites.
"""

from __future__ import annotations

from typing import Any

from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.registry import (
    ModelInfo,
    list_models,
    register_model,
    resolve_model_name,
)
from earth2studio.models.registry import (
    get_model as _core_get_model,
)
from earth2studio.models.registry import (
    get_model_info as _core_get_model_info,
)
from od_experiments.tests.mock_prognostics import (
    MockClimaX,
    MockGraphCast,
    MockPangu,
    MockPersistence,
    MockSFNO,
)

# Reference benchmark profiles matching studyData.js and empirical proxy disclosures
BENCHMARK_PROFILES: dict[str, dict[str, Any]] = {
    "persistence": {
        "display_name": "Persistence Baseline",
        "reference_rmse_t2m_k": 1.7629,
        "nominal_tac": 0.0000,
        "skill_score_pct": 0.0,
        "param_count_m": 0.0,
        "latency_ms_cpu": 0.5,
        "empirical_proxy": False,
    },
    "sfno": {
        "display_name": "FourCastNet v2 (SFNO)",
        "reference_rmse_t2m_k": 0.4231,
        "nominal_tac": 1.0000,
        "skill_score_pct": 76.0,
        "param_count_m": 73.0,
        "latency_ms_cpu": 2.1,
        "empirical_proxy": True,
    },
    "pangu": {
        "display_name": "Pangu-Weather",
        "reference_rmse_t2m_k": 0.3812,
        "nominal_tac": 1.0000,
        "skill_score_pct": 78.4,
        "param_count_m": 64.0,
        "latency_ms_cpu": 1.9,
        "empirical_proxy": True,
    },
    "graphcast": {
        "display_name": "GraphCast (GNN)",
        "reference_rmse_t2m_k": 0.3526,
        "nominal_tac": 1.0000,
        "skill_score_pct": 80.0,
        "param_count_m": 36.7,
        "latency_ms_cpu": 3.2,
        "empirical_proxy": True,
    },
    "climax": {
        "display_name": "ClimaX (ViT)",
        "reference_rmse_t2m_k": 0.4910,
        "nominal_tac": 1.0000,
        "skill_score_pct": 72.1,
        "param_count_m": 107.0,
        "latency_ms_cpu": 2.8,
        "empirical_proxy": True,
    },
    "multimodel": {
        "display_name": "Multi-Model Ensemble",
        "reference_rmse_t2m_k": 0.2985,
        "nominal_tac": 1.0000,
        "skill_score_pct": 83.1,
        "param_count_m": 280.7,
        "latency_ms_cpu": 8.5,
        "empirical_proxy": False,
    },
    "multi_model_ensemble": {
        "display_name": "Multi-Model Ensemble",
        "reference_rmse_t2m_k": 0.2985,
        "nominal_tac": 1.0000,
        "skill_score_pct": 83.1,
        "param_count_m": 280.7,
        "latency_ms_cpu": 8.5,
        "empirical_proxy": False,
    },
}


def get_benchmark_model(
    name: str,
    mock: bool = False,
    domain_coords: Any = None,
    lat_size: int = 32,
    lon_size: int = 64,
    **kwargs: Any,
) -> PrognosticModel:
    """Instantiate a model for benchmarking, with seamless CPU mock support.

    Parameters
    ----------
    name : str
        Model identifier or registered alias.
    mock : bool, default False
        If True, returns a deterministic lightweight CPU mock model.
    domain_coords : CoordSystem | None, optional
        Domain coordinates for mock model.
    lat_size : int, default 32
        Latitude grid dimension for mock model if domain_coords is None.
    lon_size : int, default 64
        Longitude grid dimension for mock model if domain_coords is None.
    **kwargs : Any
        Passed to core ``get_model()`` when ``mock=False``.

    Returns
    -------
    PrognosticModel
        Instantiated prognostic model (either real checkpoint or CPU mock).
    """
    canonical = resolve_model_name(name)

    if mock:
        if canonical in ("multimodel", "multi_model_ensemble"):
            from earth2studio.models.px.multi_model import MultiModelEnsemble

            members = {
                m: get_benchmark_model(
                    m,
                    mock=True,
                    domain_coords=domain_coords,
                    lat_size=lat_size,
                    lon_size=lon_size,
                )
                for m in ["graphcast", "sfno", "pangu", "climax", "persistence"]
            }
            return MultiModelEnsemble(
                models=members,
                reduction=kwargs.get("reduction", "stack"),
                weights=kwargs.get("weights", None),
                target_coords=domain_coords,
            )

        if canonical == "persistence":
            return MockPersistence(
                domain_coords=domain_coords,
                lat_size=lat_size,
                lon_size=lon_size,
            )
        if canonical == "graphcast":
            return MockGraphCast(
                domain_coords=domain_coords,
                lat_size=lat_size,
                lon_size=lon_size,
            )
        if canonical == "sfno":
            return MockSFNO(
                domain_coords=domain_coords,
                lat_size=lat_size,
                lon_size=lon_size,
            )
        if canonical == "pangu":
            return MockPangu(
                domain_coords=domain_coords,
                lat_size=lat_size,
                lon_size=lon_size,
            )
        if canonical == "climax":
            return MockClimaX(
                domain_coords=domain_coords,
                lat_size=lat_size,
                lon_size=lon_size,
            )

    return _core_get_model(canonical, **kwargs)


def get_benchmark_info(name: str) -> dict[str, Any]:
    """Retrieve combined core metadata and benchmark profile data for a model.

    Parameters
    ----------
    name : str
        Model identifier or registered alias.

    Returns
    -------
    dict[str, Any]
        Dictionary merging core model info and benchmark profile.
    """
    canonical = resolve_model_name(name)
    core_info = _core_get_model_info(canonical).to_dict()
    profile = BENCHMARK_PROFILES.get(canonical, {})
    return {**core_info, **profile}


def get_5model_benchmark_suite(
    mock: bool = True,
    domain_coords: Any = None,
    lat_size: int = 32,
    lon_size: int = 64,
    **kwargs: Any,
) -> dict[str, PrognosticModel]:
    """Instantiate the complete 5-model evaluation suite.

    Parameters
    ----------
    mock : bool, default True
        Whether to instantiate CPU mock models.
    domain_coords : CoordSystem | None, optional
        Domain coordinates.
    lat_size : int, default 32
        Latitude grid dimension.
    lon_size : int, default 64
        Longitude grid dimension.
    **kwargs : Any
        Additional keyword arguments.

    Returns
    -------
    dict[str, PrognosticModel]
        Dictionary mapping model names to instantiated models:
        ``{"graphcast": ..., "sfno": ..., "pangu": ..., "climax": ..., "persistence": ...}``.
    """
    models = ["graphcast", "sfno", "pangu", "climax", "persistence"]
    return {
        m: get_benchmark_model(
            m,
            mock=mock,
            domain_coords=domain_coords,
            lat_size=lat_size,
            lon_size=lon_size,
            **kwargs,
        )
        for m in models
    }


# Re-export core registry items for unified access
get_model = _core_get_model
get_model_info = _core_get_model_info

__all__ = [
    "BENCHMARK_PROFILES",
    "ModelInfo",
    "get_5model_benchmark_suite",
    "get_benchmark_info",
    "get_benchmark_model",
    "get_model",
    "get_model_info",
    "list_models",
    "register_model",
    "resolve_model_name",
]
