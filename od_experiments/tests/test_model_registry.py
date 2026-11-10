# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
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
# Author: Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
# Compliance: .agents/rules/e2s-009-prognostic-models.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

"""Unit tests for operational experiment model comparison registry.

Validates:
- Instantiation of CPU mock models with mock=True.
- Verification of empirical benchmark metadata matching studyData.js.
- Multi-model 5-suite generation and fast CPU execution.
- MultiModelEnsemble mock instantiation and rollout.
"""

from __future__ import annotations

import time
from collections import OrderedDict

import numpy as np
import pytest
import torch

from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.multi_model import MultiModelEnsemble
from od_experiments.model_comparison.registry import (
    get_5model_benchmark_suite,
    get_benchmark_info,
    get_benchmark_model,
)
from od_experiments.tests.mock_prognostics import (
    DEFAULT_EVAL_VARS,
    MockClimaX,
    MockGraphCast,
    MockPangu,
    MockPersistence,
    MockSFNO,
)


@pytest.mark.parametrize(
    "model_name,expected_cls",
    [
        ("persistence", MockPersistence),
        ("graphcast", MockGraphCast),
        ("sfno", MockSFNO),
        ("pangu", MockPangu),
        ("climax", MockClimaX),
    ],
)
def test_benchmark_model_mock_mode(model_name, expected_cls):
    """Verify get_benchmark_model with mock=True returns lightweight mock instance."""
    model = get_benchmark_model(model_name, mock=True, lat_size=16, lon_size=32)
    assert isinstance(model, expected_cls)
    assert isinstance(model, PrognosticModel)

    in_coords = model.input_coords()
    assert list(in_coords.keys())[0] == "batch"
    assert len(in_coords["lat"]) == 16
    assert len(in_coords["lon"]) == 32


def test_benchmark_multimodel_mock_mode():
    """Verify get_benchmark_model('multimodel', mock=True) returns MultiModelEnsemble."""
    mme = get_benchmark_model(
        "multimodel", mock=True, lat_size=16, lon_size=32, reduction="stack"
    )
    assert isinstance(mme, MultiModelEnsemble)
    assert len(mme.member_names) == 5

    x = torch.zeros((1, 2, len(DEFAULT_EVAL_VARS), 16, 32))
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(-6, "h"), np.timedelta64(0, "h")]),
            "variable": np.array(DEFAULT_EVAL_VARS),
            "lat": np.linspace(90, -90, 16),
            "lon": np.linspace(0, 360, 32, endpoint=False),
        }
    )
    out, out_coords = mme(x, coords)
    assert out.shape == (1, 5, 1, len(DEFAULT_EVAL_VARS), 16, 32)
    assert "ensemble" in out_coords


def test_5model_benchmark_suite_mock():
    """Verify get_5model_benchmark_suite generates complete 5-model evaluation suite."""
    suite = get_5model_benchmark_suite(mock=True, lat_size=16, lon_size=32)
    assert len(suite) == 5
    expected_keys = ["graphcast", "sfno", "pangu", "climax", "persistence"]
    for k in expected_keys:
        assert k in suite
        assert isinstance(suite[k], PrognosticModel)


def test_benchmark_metadata_integration():
    """Verify get_benchmark_info returns combined core metadata and benchmark profile."""
    # GraphCast
    gc_info = get_benchmark_info("graphcast")
    assert gc_info["name"] == "graphcast"
    assert gc_info["family"] == "gnn"
    assert gc_info["reference_rmse_t2m_k"] == 0.3526
    assert gc_info["skill_score_pct"] == 80.0
    assert gc_info["empirical_proxy"] is True

    # Persistence
    pers_info = get_benchmark_info("persistence")
    assert pers_info["reference_rmse_t2m_k"] == 1.7629
    assert pers_info["nominal_tac"] == 0.0000
    assert pers_info["skill_score_pct"] == 0.0
    assert pers_info["empirical_proxy"] is False

    # Multi-Model Ensemble
    mme_info = get_benchmark_info("multimodel")
    assert mme_info["reference_rmse_t2m_k"] == 0.2985
    assert mme_info["skill_score_pct"] == 83.1


def test_5model_cpu_latency():
    """Verify 5-model mock suite executes 4 steps on CPU well within 1.5 seconds."""
    suite = get_5model_benchmark_suite(mock=True, lat_size=16, lon_size=32)

    lat = np.linspace(90, -90, 16)
    lon = np.linspace(0, 360, 32, endpoint=False)
    x = torch.zeros((1, 2, len(DEFAULT_EVAL_VARS), 16, 32))
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(-6, "h"), np.timedelta64(0, "h")]),
            "variable": np.array(DEFAULT_EVAL_VARS),
            "lat": lat,
            "lon": lon,
        }
    )

    t0 = time.perf_counter()
    for model in suite.values():
        if model._history == 2:
            m_x, m_c = x, coords
        else:
            m_x = x[:, -1:]
            m_c = coords.copy()
            m_c["lead_time"] = coords["lead_time"][-1:]

        it = model.create_iterator(m_x, m_c)
        next(it)  # step 0
        for _ in range(4):
            next(it)

    elapsed = time.perf_counter() - t0
    # Must complete in < 1.0 second on CPU
    assert elapsed < 1.0, f"Suite execution took {elapsed:.3f}s"
