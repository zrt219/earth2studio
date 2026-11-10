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

"""Adversarial stress test suite for MultiModelEnsemble (Milestone 2 Challenge).

Evaluates empirical robustness across 4 adversarial attack vectors:
1. Reduction Edge Cases:
   - Single-model ensemble in stack, mean, and weighted_mean modes.
   - Non-uniform weights with extreme dynamic range [1e6, 1.0, 1e-6].
   - Zero, negative, and invalid weights handling.
   - Mismatched and partial variable sets across member models.
2. Tensor Shape and Batching Stress:
   - Arbitrary multi-dimensional batch shapes (e.g. (2, 3)).
   - Edge batch sizes: batch size 1, batch size 0, and unbatched (0D) inputs.
   - Long auto-regressive rollouts (12+ lead steps / 72h) testing numerical stability.
3. Multi-Horizon History and Spatial Orientation Stress:
   - Mixed-history models (2-step GraphCast vs 1-step models).
   - Non-destructive slicing verification (ensuring input coords remain uncorrupted).
   - Insufficient history slice rejection.
   - Inverted latitude grid handling (ascending vs descending orientation).
4. Pillar A Metric Interoperability:
   - Stacked ensemble feeding into standard and fair CRPS.
   - Stacked ensemble feeding into Spread-Skill Ratio with finite-size calibration.
   - Single-member and multi-batch propagation through CRPS and SSR.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pytest
import torch

from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.multi_model import CORE_EVAL_VARIABLES, MultiModelEnsemble
from earth2studio.statistics import crps, rmse, spread_skill_ratio
from od_experiments.tests.mock_prognostics import (
    MockGraphCast,
    MockPangu,
    MockPersistence,
    MockSFNO,
)

pytest_plugins = ("od_experiments.tests.mock_prognostics",)


# ==============================================================================
# Vector 1: Reduction Edge Cases
# ==============================================================================


@pytest.mark.parametrize("reduction", ["stack", "mean", "weighted_mean"])
def test_adversarial_single_model_ensemble_reductions(reduction: str):
    """Verify single-model ensemble behaves consistently across all reduction modes."""
    model = MockPersistence()
    mme = MultiModelEnsemble(
        models={"solo": model},
        weights={"solo": 42.0} if reduction == "weighted_mean" else None,
        reduction=reduction,
    )
    assert isinstance(mme, PrognosticModel)

    # Weights for single model must normalize to 1.0
    assert pytest.approx(mme.weights["solo"]) == 1.0

    x = torch.ones((1, 1, len(CORE_EVAL_VARIABLES), 32, 64), dtype=torch.float32)
    coords = mme.input_coords()
    coords["batch"] = np.array([0])

    out, out_coords = mme(x, coords)

    if reduction == "stack":
        assert out.shape == (1, 1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
        assert "ensemble" in out_coords
        assert list(out_coords["ensemble"]) == ["solo"]
    else:
        assert out.shape == (1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
        assert "ensemble" not in out_coords

    # For a persistence model, single model output must equal identity input (at t+dt)
    if reduction == "stack":
        assert torch.allclose(out.squeeze(1), x)
    else:
        assert torch.allclose(out, x)


def test_adversarial_weights_large_dynamic_range():
    """Verify weights with extreme dynamic range [1e6, 1.0, 1e-6] normalize stably."""
    models = {
        "dominant": MockPersistence(),
        "median": MockSFNO(),
        "trace": MockPangu(),
    }
    weights = {
        "dominant": 1e6,
        "median": 1.0,
        "trace": 1e-6,
    }
    mme = MultiModelEnsemble(models=models, weights=weights, reduction="weighted_mean")

    # Check normalization precision
    norm_w = mme.weights
    assert pytest.approx(sum(norm_w.values()), rel=1e-12) == 1.0
    assert norm_w["dominant"] > 0.99999
    assert norm_w["trace"] < 1e-11

    # Verify forward pass does not underflow or produce NaN/Inf
    x = torch.randn((1, 1, len(CORE_EVAL_VARIABLES), 32, 64)).abs() + 1.0
    coords = mme.input_coords()
    coords["batch"] = np.array([0])

    out, _ = mme(x, coords)
    assert not torch.isnan(out).any().item()
    assert not torch.isinf(out).any().item()

    # Dominant model output should account for virtually all signal
    out_dominant, _ = models["dominant"](x, coords)
    assert torch.allclose(out, out_dominant, atol=1e-4)


@pytest.mark.parametrize(
    "invalid_weights, expected_exc, match_msg",
    [
        (
            {"p": 0.0, "s": 1.0},
            ValueError,
            "strictly positive scalars",
        ),
        (
            {"p": -2.5, "s": 3.0},
            ValueError,
            "strictly positive scalars",
        ),
        (
            {"p": 1.0},
            KeyError,
            "missing from provided weights",
        ),
    ],
)
def test_adversarial_invalid_weights_rejection(
    invalid_weights: dict[str, float],
    expected_exc: type[Exception],
    match_msg: str,
):
    """Verify strict validation and rejection of non-positive or incomplete weights."""
    models = {"p": MockPersistence(), "s": MockSFNO()}
    with pytest.raises(expected_exc, match=match_msg):
        MultiModelEnsemble(
            models=models, weights=invalid_weights, reduction="weighted_mean"
        )


def test_adversarial_empty_models_rejection():
    """Verify passing an empty models dict raises ValueError."""
    with pytest.raises(ValueError, match="models dictionary cannot be empty"):
        MultiModelEnsemble(models={})


def test_adversarial_mismatched_and_partial_variables():
    """Verify behavior when member models support differing variable subsets."""
    # Member mA only supports ['t2m', 'u10m']
    # Member mB only supports ['t2m', 'v10m']
    mA = MockPersistence(variables=["t2m", "u10m"])
    mB = MockSFNO(variables=["t2m", "v10m"])

    # 1. Default target_coords expects CORE_EVAL_VARIABLES (6 variables).
    # Since neither mA nor mB provides all 6, __call__ must raise KeyError identifying missing variable.
    mme_default = MultiModelEnsemble({"mA": mA, "mB": mB}, reduction="stack")
    x_full = torch.ones((1, 1, len(CORE_EVAL_VARIABLES), 32, 64))
    coords_full = mme_default.input_coords()
    coords_full["batch"] = np.array([0])

    with pytest.raises(KeyError, match="does not provide required target variable"):
        mme_default(x_full, coords_full)

    # 2. When target_coords explicitly requests the intersection ['t2m'],
    # and input tensor supplies union ['t2m', 'u10m', 'v10m'], both models must succeed.
    target_c = OrderedDict(
        [
            ("variable", ["t2m"]),
            ("lat", np.linspace(90.0, -90.0, 32)),
            ("lon", np.linspace(0.0, 360.0, 64, endpoint=False)),
        ]
    )
    mme_subset = MultiModelEnsemble(
        {"mA": mA, "mB": mB}, target_coords=target_c, reduction="stack"
    )

    x_union = torch.ones((1, 1, 3, 32, 64))
    coords_union = OrderedDict(
        [
            ("batch", np.array([0])),
            ("lead_time", np.array([np.timedelta64(0, "h")])),
            ("variable", np.array(["t2m", "u10m", "v10m"])),
            ("lat", target_c["lat"]),
            ("lon", target_c["lon"]),
        ]
    )

    out_subset, coords_out = mme_subset(x_union, coords_union)
    assert out_subset.shape == (1, 2, 1, 1, 32, 64)
    assert list(coords_out["variable"]) == ["t2m"]
    assert list(coords_out["ensemble"]) == ["mA", "mB"]


# ==============================================================================
# Vector 2: Tensor Shape and Batching Stress
# ==============================================================================


def test_adversarial_multidimensional_batch_shape():
    """Verify arbitrary multi-dimensional batch shapes (e.g. (2, 3)) are preserved."""
    models = {
        "persistence": MockPersistence(),
        "sfno": MockSFNO(),
        "graphcast": MockGraphCast(),
    }
    mme = MultiModelEnsemble(models=models, reduction="stack")

    # Construct input with 2D batch dimension (2, 3)
    x = torch.ones((2, 3, 2, len(CORE_EVAL_VARIABLES), 32, 64))
    coords = OrderedDict(
        [
            ("ensemble_run", np.arange(2)),
            ("init_date", np.arange(3)),
            ("lead_time", np.array([np.timedelta64(-6, "h"), np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )

    # 1. Forward step
    out, out_coords = mme(x, coords)
    assert out.shape == (2, 3, 3, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert list(out_coords.keys()) == [
        "ensemble_run",
        "init_date",
        "ensemble",
        "lead_time",
        "variable",
        "lat",
        "lon",
    ]

    # 2. Multi-step rollout iterator with (2, 3) batch
    it = mme.create_iterator(x, coords)
    for step in range(4):
        step_out, step_coords = next(it)
        assert step_out.shape == (2, 3, 3, 1, len(CORE_EVAL_VARIABLES), 32, 64)
        assert step_coords["lead_time"][0] == np.timedelta64(6 * step, "h")
        assert list(step_coords.keys())[:2] == ["ensemble_run", "init_date"]


def test_adversarial_edge_batch_sizes():
    """Verify edge batch shapes: batch size 1, batch size 0, and unbatched input."""
    models = {"persistence": MockPersistence(), "sfno": MockSFNO()}
    mme = MultiModelEnsemble(models=models, reduction="stack")

    # 1. Batch size 1
    x1 = torch.ones((1, 1, len(CORE_EVAL_VARIABLES), 32, 64))
    c1 = OrderedDict(
        [
            ("batch", np.array([0])),
            ("lead_time", np.array([np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )
    out1, c1_out = mme(x1, c1)
    assert out1.shape == (1, 2, 1, len(CORE_EVAL_VARIABLES), 32, 64)

    # 2. Batch size 0 (empty tensor along batch axis)
    x0 = torch.empty((0, 1, len(CORE_EVAL_VARIABLES), 32, 64))
    c0 = OrderedDict(
        [
            ("batch", np.empty(0)),
            ("lead_time", np.array([np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )
    out0, c0_out = mme(x0, c0)
    assert out0.shape == (0, 2, 1, len(CORE_EVAL_VARIABLES), 32, 64)

    # 3. Unbatched input (0D batch, dims start with lead_time)
    x_unbatched = torch.ones((1, len(CORE_EVAL_VARIABLES), 32, 64))
    c_unbatched = OrderedDict(
        [
            ("lead_time", np.array([np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )
    out_unb, c_unb_out = mme(x_unbatched, c_unb_out_coords := c_unbatched.copy())
    assert out_unb.shape == (2, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert "batch" not in c_unb_out
    assert list(c_unb_out.keys()) == ["ensemble", "lead_time", "variable", "lat", "lon"]


def test_adversarial_long_rollout_stability(all_5_mock_models):
    """Verify long 12-step (72h) auto-regressive trajectory evolution."""
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="mean")

    x = torch.ones((1, 2, len(CORE_EVAL_VARIABLES), 32, 64))
    coords = mme.input_coords()
    coords["batch"] = np.array([0])

    it = mme.create_iterator(x, coords)

    for step in range(13):  # Step 0 (initial) through Step 12 (72h)
        step_val, step_coords = next(it)
        assert step_val.shape == (1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
        assert step_coords["lead_time"][0] == np.timedelta64(6 * step, "h")
        assert not torch.isnan(step_val).any().item(), f"NaN detected at step {step}"
        assert not torch.isinf(step_val).any().item(), f"Inf detected at step {step}"


# ==============================================================================
# Vector 3: Multi-Horizon History and Spatial Orientation Stress
# ==============================================================================


def test_adversarial_mixed_history_slicing_and_coord_immutability():
    """Verify 2-step and 1-step models receive correct history without mutating input coords."""
    models = {
        "graphcast": MockGraphCast(),  # history = 2
        "sfno": MockSFNO(),  # history = 1
        "persistence": MockPersistence(),  # history = 1
    }
    mme = MultiModelEnsemble(models=models, reduction="stack")

    orig_lead_time = np.array([np.timedelta64(-6, "h"), np.timedelta64(0, "h")])
    coords = OrderedDict(
        [
            ("batch", np.array([0])),
            ("lead_time", orig_lead_time.copy()),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )
    x = torch.ones((1, 2, len(CORE_EVAL_VARIABLES), 32, 64))

    out, out_coords = mme(x, coords)
    assert out.shape == (1, 3, 1, len(CORE_EVAL_VARIABLES), 32, 64)

    # Invariant: input coordinates dictionary and arrays must NOT have been mutated in place
    assert np.array_equal(coords["lead_time"], orig_lead_time)
    assert len(coords["lead_time"]) == 2


def test_adversarial_insufficient_history_rejection():
    """Verify passing fewer history slices than required by member models raises ValueError."""
    mme = MultiModelEnsemble(
        models={"graphcast": MockGraphCast(), "sfno": MockSFNO()},
        reduction="stack",
    )
    # GraphCast requires 2 lead times, provide only 1
    x_under = torch.ones((1, 1, len(CORE_EVAL_VARIABLES), 32, 64))
    c_under = OrderedDict(
        [
            ("batch", np.array([0])),
            ("lead_time", np.array([np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )

    with pytest.raises(
        ValueError, match="requires 2 lead-time slices, but input only has 1"
    ):
        mme(x_under, c_under)


def test_adversarial_ascending_latitude_orientation_preservation():
    """Verify regridding preserves descending atmospheric latitude convention and values."""
    mme = MultiModelEnsemble({"p": MockPersistence()}, reduction="stack")

    # Feed input with inverted ascending latitudes (-90 to +90)
    asc_lat = np.linspace(-90.0, 90.0, 32)
    c_asc = OrderedDict(
        [
            ("batch", np.array([0])),
            ("lead_time", np.array([np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", asc_lat),
            ("lon", mme.input_coords()["lon"]),
        ]
    )

    # South pole (-90) = 0.0, North pole (+90) = 31.0
    x = (
        torch.arange(32, dtype=torch.float32)
        .view(1, 1, 1, 32, 1)
        .expand(1, 1, 6, 32, 64)
    )

    out, out_coords = mme(x, c_asc)

    # Output latitude must be in descending atmospheric order (+90 to -90)
    assert out_coords["lat"][0] == 90.0
    assert out_coords["lat"][-1] == -90.0

    # Physical values must align: North pole value at index 0 must be 31.0
    val_north = out[0, 0, 0, 0, 0, 0].item()
    val_south = out[0, 0, 0, 0, -1, 0].item()
    assert pytest.approx(val_north, abs=0.1) == 31.0
    assert pytest.approx(val_south, abs=0.1) == 0.0


# ==============================================================================
# Vector 4: Pillar A Metric Interoperability
# ==============================================================================


def test_adversarial_crps_and_ssr_interoperability_multi_batch(all_5_mock_models):
    """Verify stacked multi-model ensemble feeds cleanly into CRPS and SSR with multi-batch."""
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="stack")

    # 2D batch input (2, 3)
    x = torch.ones((2, 3, 2, len(CORE_EVAL_VARIABLES), 32, 64))
    coords = OrderedDict(
        [
            ("run_idx", np.arange(2)),
            ("init_idx", np.arange(3)),
            ("lead_time", np.array([np.timedelta64(-6, "h"), np.timedelta64(0, "h")])),
            ("variable", mme.input_coords()["variable"]),
            ("lat", mme.input_coords()["lat"]),
            ("lon", mme.input_coords()["lon"]),
        ]
    )

    out, out_coords = mme(x, coords)
    assert out.shape == (2, 3, 5, 1, len(CORE_EVAL_VARIABLES), 32, 64)

    y_obs = x[:, :, -1:].clone()
    obs_coords = OrderedDict(
        [
            ("run_idx", out_coords["run_idx"]),
            ("init_idx", out_coords["init_idx"]),
            ("lead_time", out_coords["lead_time"]),
            ("variable", out_coords["variable"]),
            ("lat", out_coords["lat"]),
            ("lon", out_coords["lon"]),
        ]
    )

    # 1. Vectorized CRPS (standard)
    crps_std, crps_std_coords = crps(out, out_coords, y_obs, obs_coords, dim="ensemble")
    assert crps_std.shape == (2, 3, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert torch.all(crps_std >= 0.0)
    assert list(crps_std_coords.keys()) == list(obs_coords.keys())

    # 2. Vectorized Fair CRPS
    crps_fair, _ = crps(out, out_coords, y_obs, obs_coords, dim="ensemble", fair=True)
    assert crps_fair.shape == (2, 3, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert torch.all(crps_fair >= 0.0)

    # 3. Spread-Skill Ratio with area reduction over lat, lon
    ssr_metric = spread_skill_ratio(
        ensemble_dimension="ensemble",
        reduction_dimensions=["lat", "lon"],
        correct_finite=True,
    )
    ssr_val, ssr_coords = ssr_metric(out, out_coords, y_obs, obs_coords)
    assert ssr_val.shape == (2, 3, 1, len(CORE_EVAL_VARIABLES))
    assert list(ssr_coords.keys()) == ["run_idx", "init_idx", "lead_time", "variable"]


def test_adversarial_single_model_pillar_a_boundaries():
    """Verify single-member ensemble boundaries against CRPS and SSR requirements."""
    mme = MultiModelEnsemble({"solo": MockPersistence()}, reduction="stack")
    x = torch.ones((1, 1, len(CORE_EVAL_VARIABLES), 32, 64))
    coords = mme.input_coords()
    coords["batch"] = np.array([0])

    out, out_coords = mme(x, coords)
    y_obs = x.clone()
    obs_coords = OrderedDict(
        [
            ("batch", out_coords["batch"]),
            ("lead_time", out_coords["lead_time"]),
            ("variable", out_coords["variable"]),
            ("lat", out_coords["lat"]),
            ("lon", out_coords["lon"]),
        ]
    )

    # 1. Standard CRPS with M=1 degenerates to Mean Absolute Error (MAE)
    crps_val, _ = crps(out, out_coords, y_obs, obs_coords, dim="ensemble", fair=False)
    assert crps_val.shape == (1, 1, len(CORE_EVAL_VARIABLES), 32, 64)
    assert torch.allclose(crps_val, torch.zeros_like(crps_val))

    # 2. Fair CRPS with M=1 must raise ValueError (requires M >= 2)
    with pytest.raises(ValueError, match="Fair CRPS requires at least M >= 2"):
        crps(out, out_coords, y_obs, obs_coords, dim="ensemble", fair=True)

    # 3. Spread-Skill Ratio with M=1 and correct_finite=True must raise ValueError (requires M >= 2)
    ssr_metric = spread_skill_ratio(
        ensemble_dimension="ensemble",
        reduction_dimensions=["lat", "lon"],
        correct_finite=True,
    )
    with pytest.raises(ValueError, match="Spread-skill ratio requires at least M >= 2"):
        ssr_metric(out, out_coords, y_obs, obs_coords)


def test_adversarial_mean_reduction_rmse_integration(all_5_mock_models):
    """Verify ensemble mean output integrates with standard RMSE statistic."""
    mme = MultiModelEnsemble(models=all_5_mock_models, reduction="mean")
    x = torch.ones((1, 2, len(CORE_EVAL_VARIABLES), 32, 64))
    coords = mme.input_coords()
    coords["batch"] = np.array([0])

    out, out_coords = mme(x, coords)
    assert "ensemble" not in out_coords

    y_obs = x[:, -1:].clone()
    obs_coords = OrderedDict(
        [
            ("batch", out_coords["batch"]),
            ("lead_time", out_coords["lead_time"]),
            ("variable", out_coords["variable"]),
            ("lat", out_coords["lat"]),
            ("lon", out_coords["lon"]),
        ]
    )

    rmse_metric = rmse(reduction_dimensions=["lat", "lon"])
    rmse_val, rmse_coords = rmse_metric(out, out_coords, y_obs, obs_coords)
    assert rmse_val.shape == (1, 1, len(CORE_EVAL_VARIABLES))
    assert list(rmse_coords.keys()) == ["batch", "lead_time", "variable"]
    assert torch.all(rmse_val >= 0.0)
