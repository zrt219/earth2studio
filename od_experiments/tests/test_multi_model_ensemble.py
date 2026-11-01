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

"""Unit tests for MultiModelEnsemble prognostic framework.

Validates:
- 5 mock model ensemble across 4 lead-time steps.
- Reduction modes: stack, mean, weighted_mean.
- Multi-horizon history slicing: GraphCast (2-step) + 1-step models.
- Spatial bilinear regridding.
- Direct feeding into CRPS and SSR metrics.
- Error handling and boundary conditions.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pytest
import torch

from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.multi_model import CORE_EVAL_VARIABLES, MultiModelEnsemble
from earth2studio.statistics import crps, spread_skill_ratio
from od_experiments.tests.mock_prognostics import (
    MockClimaX,
    MockGraphCast,
    MockPangu,
    MockPersistence,
    MockSFNO,
)

pytest_plugins = ("od_experiments.tests.mock_prognostics",)


def test_ensemble_protocol_and_input_coords(all_5_mock_models):
    """Verify MultiModelEnsemble conforms to PrognosticModel protocol and coordinates."""
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="stack")
    assert isinstance(mme, PrognosticModel)

    in_coords = mme.input_coords()
    assert list(in_coords.keys())[0] == "batch"
    assert len(in_coords["lead_time"]) == 2  # GraphCast requires 2 steps
    assert in_coords["lead_time"][0] == np.timedelta64(-6, "h")
    assert in_coords["lead_time"][1] == np.timedelta64(0, "h")
    assert list(in_coords["variable"]) == CORE_EVAL_VARIABLES

    out_coords = mme.output_coords(in_coords)
    assert list(out_coords.keys())[0] == "batch"
    assert "ensemble" in out_coords
    assert list(out_coords["ensemble"]) == list(all_5_mock_models.keys())
    assert out_coords["lead_time"][0] == np.timedelta64(6, "h")


def test_ensemble_stack_reduction(all_5_mock_models, sample_initial_conditions):
    """Verify reduction='stack' produces tensor with ensemble dimension."""
    x_in, coords_in = sample_initial_conditions
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="stack")

    out, out_coords = mme(x_in, coords_in)
    assert out.shape == (1, 5, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert "ensemble" in out_coords
    assert list(out_coords["ensemble"]) == list(all_5_mock_models.keys())
    assert out_coords["lead_time"][0] == np.timedelta64(6, "h")


def test_ensemble_mean_reduction(all_5_mock_models, sample_initial_conditions):
    """Verify reduction='mean' computes unweighted arithmetic mean across members."""
    x_in, coords_in = sample_initial_conditions
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="mean")

    out, out_coords = mme(x_in, coords_in)
    assert out.shape == (1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert "ensemble" not in out_coords

    # Compare with manual member forward outputs
    member_outputs = []
    for model in all_5_mock_models.values():
        if model._history == 2:
            m_x, m_c = x_in, coords_in
        else:
            m_x = x_in[:, -1:]
            m_c = coords_in.copy()
            m_c["lead_time"] = coords_in["lead_time"][-1:]
        m_out, _ = model(m_x, m_c)
        member_outputs.append(m_out)

    expected_mean = torch.stack(member_outputs, dim=0).mean(dim=0)
    assert torch.allclose(out, expected_mean, atol=1e-5)


def test_ensemble_weighted_mean_reduction(all_5_mock_models, sample_initial_conditions):
    """Verify reduction='weighted_mean' correctly weights member forecasts."""
    x_in, coords_in = sample_initial_conditions
    weights = {
        "persistence": 0.1,
        "graphcast": 0.3,
        "sfno": 0.25,
        "pangu": 0.2,
        "climax": 0.15,
    }
    mme = MultiModelEnsemble(
        models=all_5_mock_models, weights=weights, reduction="weighted_mean"
    )

    out, out_coords = mme(x_in, coords_in)
    assert out.shape == (1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert "ensemble" not in out_coords

    # Manual convex combination calculation
    member_outputs = []
    for name, model in all_5_mock_models.items():
        if model._history == 2:
            m_x, m_c = x_in, coords_in
        else:
            m_x = x_in[:, -1:]
            m_c = coords_in.copy()
            m_c["lead_time"] = coords_in["lead_time"][-1:]
        m_out, _ = model(m_x, m_c)
        member_outputs.append(m_out * weights[name])

    expected_weighted = sum(member_outputs)
    assert torch.allclose(out, expected_weighted, atol=1e-5)


def test_ensemble_weight_normalization():
    """Verify unnormalized positive weights are automatically normalized to sum to 1."""
    weights = {
        "persistence": 2.0,
        "graphcast": 6.0,
        "sfno": 5.0,
        "pangu": 4.0,
        "climax": 3.0,
    }
    # Total sum is 20.0, persistence should become 0.1, graphcast 0.3
    mock_models = {
        "persistence": MockPersistence(),
        "graphcast": MockGraphCast(),
        "sfno": MockSFNO(),
        "pangu": MockPangu(),
        "climax": MockClimaX(),
    }
    mme = MultiModelEnsemble(
        models=mock_models, weights=weights, reduction="weighted_mean"
    )
    assert pytest.approx(mme.weights["persistence"]) == 0.1
    assert pytest.approx(mme.weights["graphcast"]) == 0.3
    assert pytest.approx(sum(mme.weights.values())) == 1.0


def test_ensemble_autonomous_rollout_iterator(
    all_5_mock_models, sample_initial_conditions
):
    """Verify create_iterator yields step 0 first, then steps 1..4 at 6h intervals."""
    x_in, coords_in = sample_initial_conditions
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="stack")

    it = mme.create_iterator(x_in, coords_in)

    # Step 0: Initial condition
    s0, c0 = next(it)
    assert c0["lead_time"][0] == np.timedelta64(0, "h")
    assert s0.shape == (1, 5, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    # Check that member fields match initial wave
    for m in range(5):
        assert torch.allclose(s0[:, m], x_in[:, -1:])

    # Steps 1 to 4
    for k in range(1, 5):
        sk, ck = next(it)
        assert ck["lead_time"][0] == np.timedelta64(6 * k, "h")
        assert sk.shape == (1, 5, 1, len(CORE_EVAL_VARIABLES), 32, 64)


def test_ensemble_multi_horizon_history_slicing(sample_initial_conditions):
    """Verify GraphCast receives 2 history slices while 1-step models receive 1 slice."""
    x_in, coords_in = sample_initial_conditions

    # Create an ensemble with GraphCast (history=2) and SFNO (history=1)
    models = {
        "graphcast": MockGraphCast(),
        "sfno": MockSFNO(),
    }
    mme = MultiModelEnsemble(models=models, reduction="stack")

    out, out_coords = mme(x_in, coords_in)
    assert out.shape == (1, 2, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert list(out_coords["ensemble"]) == ["graphcast", "sfno"]


def test_ensemble_spatial_regridding():
    """Verify bilinear interpolation regrids disparate model resolutions to target grid."""
    # Member 1 on 16x32 grid, Member 2 on 32x64 grid
    m1 = MockSFNO(lat_size=16, lon_size=32)
    m2 = MockSFNO(lat_size=32, lon_size=64)

    # Target grid is 32x64
    target_dc = OrderedDict(
        {
            "lat": np.linspace(90.0, -90.0, 32),
            "lon": np.linspace(0.0, 360.0, 64, endpoint=False),
        }
    )

    mme = MultiModelEnsemble(
        models={"sfno_16x32": m1, "sfno_32x64": m2},
        target_coords=target_dc,
        reduction="stack",
    )

    # Input on 32x64
    x = torch.ones((1, 1, len(CORE_EVAL_VARIABLES), 32, 64), dtype=torch.float32)
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(CORE_EVAL_VARIABLES),
            "lat": target_dc["lat"],
            "lon": target_dc["lon"],
        }
    )

    out, out_coords = mme(x, coords)
    assert out.shape == (1, 2, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert len(out_coords["lat"]) == 32
    assert len(out_coords["lon"]) == 64
    # Constant field remains constant after bilinear interpolation
    assert torch.allclose(out, torch.ones_like(out) * 0.998, atol=1e-4)


def test_ensemble_feed_into_crps_and_ssr(all_5_mock_models, sample_initial_conditions):
    """Verify stacked ensemble output directly evaluates CRPS and SSR metrics."""
    x_in, coords_in = sample_initial_conditions
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="stack")

    out, out_coords = mme(x_in, coords_in)
    # out shape: (1, 5, 1, 6, 32, 64)
    y_obs = x_in[:, -1:]  # (1, 1, 6, 32, 64)
    obs_coords = OrderedDict(
        {
            "batch": np.array([0]),
            "lead_time": out_coords["lead_time"],
            "variable": out_coords["variable"],
            "lat": out_coords["lat"],
            "lon": out_coords["lon"],
        }
    )

    # 1. CRPS evaluation
    crps_val, crps_coords = crps(out, out_coords, y_obs, obs_coords, dim="ensemble")
    assert crps_val.shape == (1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert torch.all(crps_val >= 0.0)

    # 2. SSR evaluation
    ssr_metric = spread_skill_ratio(
        ensemble_dimension="ensemble",
        reduction_dimensions=["lat", "lon"],
        correct_finite=True,
    )
    ssr_val, ssr_coords = ssr_metric(out, out_coords, y_obs, obs_coords)
    assert ssr_val.shape == (1, 1, len(CORE_EVAL_VARIABLES))
    assert torch.all(ssr_val > 0.0)


def test_ensemble_error_handling(all_5_mock_models):
    """Verify appropriate exceptions for invalid configurations."""
    # 1. Invalid reduction
    with pytest.raises(ValueError, match="Invalid reduction"):
        MultiModelEnsemble(models=all_5_mock_models, reduction="unsupported")

    # 2. Negative weight
    with pytest.raises(ValueError, match="strictly positive"):
        MultiModelEnsemble(
            models=all_5_mock_models,
            weights={
                "persistence": -0.1,
                "graphcast": 0.4,
                "sfno": 0.3,
                "pangu": 0.2,
                "climax": 0.2,
            },
            reduction="weighted_mean",
        )

    # 3. Missing weight for member
    with pytest.raises(KeyError, match="missing from provided weights"):
        MultiModelEnsemble(
            models=all_5_mock_models,
            weights={"persistence": 0.5, "graphcast": 0.5},
            reduction="weighted_mean",
        )
