# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
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
# Empirical Challenge Verification Suite for Milestone 1 (EDI, SEDI, Pipeline).
# Author: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# Compliance: .agents/rules/e2s-014-scientific-integrity.mdc

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import numpy as np
import pytest
import torch

from earth2studio.statistics.edi import (
    compute_contingency_table,
    compute_edi,
    compute_rates,
    compute_sedi,
)
from od_experiments.ensemble.verification import EnsembleVerificationPipeline
from od_experiments.scientific_study.metrics_engine import (
    extreme_dependency_index,
    symmetric_extremal_dependence_index,
)
from od_experiments.tests.test_metrics_operational import MockGroundTruthSource

# =====================================================================
# 1. Base-Rate Invariance vs ETS/HSS Collapse
# =====================================================================


def compute_ets_hss(a: float, b: float, c: float, d: float) -> tuple[float, float]:
    """Compute Equitable Threat Score (ETS) and Heidke Skill Score (HSS)."""
    N = a + b + c + d
    if N <= 0:
        return 0.0, 0.0
    a_r = ((a + b) * (a + c)) / N
    den_ets = a + b + c - a_r
    ets = (a - a_r) / den_ets if den_ets > 0 else 0.0

    num_hss = 2.0 * (a * d - b * c)
    den_hss = (a + c) * (c + d) + (a + b) * (b + d)
    hss = num_hss / den_hss if den_hss > 0 else 0.0
    return float(ets), float(hss)


def test_base_rate_invariance_and_ets_hss_collapse():
    """Verify base-rate invariance of EDI/SEDI while demonstrating ETS/HSS collapse."""
    H = 0.80  # 80% hit rate
    F = 0.05  # 5% false alarm rate
    base_rates = [0.5, 0.05, 0.005, 0.0005]

    edi_vals_pt = []
    sedi_vals_pt = []
    edi_vals_np = []
    sedi_vals_np = []
    ets_vals = []
    hss_vals = []

    for p in base_rates:
        # Scale contingency table counts
        N_events = 20000.0
        ac = N_events
        a = round(H * ac)
        c = round((1.0 - H) * ac)
        bd = round(ac * (1.0 - p) / p)
        b = round(F * bd)
        d = bd - b

        # 1. PyTorch computation
        H_pt = torch.tensor(a / (a + c), dtype=torch.float32)
        F_pt = torch.tensor(b / (b + d), dtype=torch.float32)
        log_H = torch.log(H_pt)
        log_F = torch.log(F_pt)
        edi_pt = (log_F - log_H) / (log_F + log_H)

        num_sedi = log_F - log_H - torch.log(1.0 - F_pt) + torch.log(1.0 - H_pt)
        den_sedi = log_F + log_H + torch.log(1.0 - F_pt) + torch.log(1.0 - H_pt)
        sedi_pt = num_sedi / den_sedi

        edi_vals_pt.append(float(edi_pt))
        sedi_vals_pt.append(float(sedi_pt))

        # 2. NumPy / metrics_engine computation
        fc_binary = np.concatenate(
            [np.ones(int(a)), np.ones(int(b)), np.zeros(int(c)), np.zeros(int(d))]
        )
        tr_binary = np.concatenate(
            [np.ones(int(a)), np.zeros(int(b)), np.ones(int(c)), np.zeros(int(d))]
        )
        edi_res = extreme_dependency_index(fc_binary, tr_binary, threshold=0.5)
        sedi_res = symmetric_extremal_dependence_index(
            fc_binary, tr_binary, threshold=0.5
        )
        edi_vals_np.append(edi_res["edi"])
        sedi_vals_np.append(sedi_res["sedi"])

        # 3. ETS and HSS
        ets_val, hss_val = compute_ets_hss(a, b, c, d)
        ets_vals.append(ets_val)
        hss_vals.append(hss_val)

    # Invariance check: EDI and SEDI must have zero drift across orders of magnitude of p
    edi_drift_pt = max(edi_vals_pt) - min(edi_vals_pt)
    sedi_drift_pt = max(sedi_vals_pt) - min(sedi_vals_pt)
    edi_drift_np = max(edi_vals_np) - min(edi_vals_np)
    sedi_drift_np = max(sedi_vals_np) - min(sedi_vals_np)

    assert edi_drift_pt < 1e-4, f"EDI drifted in PyTorch: {edi_vals_pt}"
    assert sedi_drift_pt < 1e-4, f"SEDI drifted in PyTorch: {sedi_vals_pt}"
    assert edi_drift_np < 1e-4, f"EDI drifted in NumPy: {edi_vals_np}"
    assert sedi_drift_np < 1e-4, f"SEDI drifted in NumPy: {sedi_vals_np}"

    # Collapse check: ETS and HSS must strictly monotonically decrease towards zero
    for i in range(len(base_rates) - 1):
        assert ets_vals[i] > ets_vals[i + 1], f"ETS failed to decrease: {ets_vals}"
        assert hss_vals[i] > hss_vals[i + 1], f"HSS failed to decrease: {hss_vals}"

    # At p=0.0005, ETS and HSS should have collapsed (< 0.05) despite H=0.80, F=0.05
    assert ets_vals[-1] < 0.05, f"ETS did not collapse for rare events: {ets_vals[-1]}"
    assert hss_vals[-1] < 0.05, f"HSS did not collapse for rare events: {hss_vals[-1]}"

    # EDI and SEDI stay robust and high (~0.85 and ~0.84)
    assert edi_vals_pt[-1] > 0.80, f"EDI unexpectedly low: {edi_vals_pt[-1]}"
    assert sedi_vals_pt[-1] > 0.80, f"SEDI unexpectedly low: {sedi_vals_pt[-1]}"


# =====================================================================
# 2. Exact Boundary Assertions
# =====================================================================


def test_boundary_perfect_forecast():
    """Verify perfect forecast yields EDI = 1.0, SEDI = 1.0."""
    truth = torch.tensor([[10.0, 30.0], [5.0, 25.0]])
    fc = truth.clone()
    edi_val = compute_edi(fc, truth, threshold=20.0, reduction_dims=[0, 1])
    sedi_val = compute_sedi(fc, truth, threshold=20.0, reduction_dims=[0, 1])

    assert torch.isclose(edi_val, torch.tensor(1.0), atol=1e-3), (
        f"Expected EDI=1.0, got {edi_val}"
    )
    assert torch.isclose(sedi_val, torch.tensor(1.0), atol=1e-3), (
        f"Expected SEDI=1.0, got {sedi_val}"
    )

    # Verify via metrics_engine as well
    res_edi = extreme_dependency_index(fc.numpy(), truth.numpy(), threshold=20.0)
    res_sedi = symmetric_extremal_dependence_index(
        fc.numpy(), truth.numpy(), threshold=20.0
    )
    assert np.isclose(res_edi["edi"], 1.0, atol=1e-3), (
        f"Expected np EDI=1.0, got {res_edi['edi']}"
    )
    assert np.isclose(res_sedi["sedi"], 1.0, atol=1e-3), (
        f"Expected np SEDI=1.0, got {res_sedi['sedi']}"
    )


def test_boundary_random_forecast():
    """Verify random forecast (H = F) yields EDI = 0.0, SEDI = 0.0."""
    a = 300
    c = 700
    b = 300
    d = 700
    fc = np.concatenate([np.ones(a), np.ones(b), np.zeros(c), np.zeros(d)])
    tr = np.concatenate([np.ones(a), np.zeros(b), np.ones(c), np.zeros(d)])

    res_edi = extreme_dependency_index(fc, tr, threshold=0.5)
    res_sedi = symmetric_extremal_dependence_index(fc, tr, threshold=0.5)

    assert abs(res_edi["edi"]) < 1e-4, f"Expected EDI=0.0 for H=F, got {res_edi['edi']}"
    assert abs(res_sedi["sedi"]) < 1e-4, (
        f"Expected SEDI=0.0 for H=F, got {res_sedi['sedi']}"
    )

    fc_t = torch.from_numpy(fc)
    tr_t = torch.from_numpy(tr)
    edi_t = compute_edi(fc_t, tr_t, threshold=0.5, reduction_dims=[0])
    sedi_t = compute_sedi(fc_t, tr_t, threshold=0.5, reduction_dims=[0])

    assert abs(float(edi_t)) < 1e-4, f"Expected PyTorch EDI=0.0 for H=F, got {edi_t}"
    assert abs(float(sedi_t)) < 1e-4, f"Expected PyTorch SEDI=0.0 for H=F, got {sedi_t}"


def test_boundary_inverted_forecast():
    """Verify inverted forecast (H = 0, F = 1) yields EDI = -1.0, SEDI = -1.0."""
    truth = torch.tensor([[25.0, 25.0], [5.0, 5.0]])
    fc = torch.tensor([[5.0, 5.0], [25.0, 25.0]])

    edi_val = compute_edi(fc, truth, threshold=20.0, reduction_dims=[0, 1])
    sedi_val = compute_sedi(fc, truth, threshold=20.0, reduction_dims=[0, 1])

    assert torch.isclose(edi_val, torch.tensor(-1.0), atol=1e-3), (
        f"Expected EDI=-1.0, got {edi_val}"
    )
    assert torch.isclose(sedi_val, torch.tensor(-1.0), atol=1e-3), (
        f"Expected SEDI=-1.0, got {sedi_val}"
    )

    res_edi = extreme_dependency_index(fc.numpy(), truth.numpy(), threshold=20.0)
    res_sedi = symmetric_extremal_dependence_index(
        fc.numpy(), truth.numpy(), threshold=20.0
    )
    assert np.isclose(res_edi["edi"], -1.0, atol=1e-3), (
        f"Expected np EDI=-1.0, got {res_edi['edi']}"
    )
    assert np.isclose(res_sedi["sedi"], -1.0, atol=1e-3), (
        f"Expected np SEDI=-1.0, got {res_sedi['sedi']}"
    )


# =====================================================================
# 3. Contingency Table Singularities & Regularization Analysis
# =====================================================================


def test_singularity_empty_event_space():
    """Test behavior when no events occur in observation domain (a + c = 0)."""
    truth = np.full((10, 10), 5.0, dtype=np.float32)
    fc_clean = np.full((10, 10), 5.0, dtype=np.float32)
    fc_with_fa = np.full((10, 10), 5.0, dtype=np.float32)
    fc_with_fa[0, 0] = 25.0

    # 1. metrics_engine handling
    res_clean = extreme_dependency_index(fc_clean, truth, threshold=20.0)
    assert not np.isnan(res_clean["edi"]), (
        "metrics_engine EDI produced NaN on clean empty event space"
    )
    assert not np.isnan(res_clean["hit_rate"]), "metrics_engine hit_rate produced NaN"
    assert res_clean["base_rate"] == 0.0

    res_fa = extreme_dependency_index(fc_with_fa, truth, threshold=20.0)
    assert not np.isnan(res_fa["edi"]), (
        "metrics_engine EDI produced NaN on empty event space with FA"
    )

    # 2. PyTorch compute_rates / compute_edi analysis
    fc_t = torch.from_numpy(fc_clean)
    tr_t = torch.from_numpy(truth)
    a, b, c, d = compute_contingency_table(
        fc_t, tr_t, threshold=20.0, reduction_dims=[0, 1]
    )
    compute_rates(a, b, c, d)

    edi_pt = compute_edi(fc_t, tr_t, threshold=20.0, reduction_dims=[0, 1])
    is_pt_nan = torch.isnan(edi_pt).item()
    print(
        f"[Singularity Test] PyTorch EDI on empty event space returns NaN: {is_pt_nan} (value={edi_pt})"
    )


def test_singularity_full_event_space():
    """Test behavior when entire domain exceeds threshold (b + d = 0)."""
    truth = np.full((10, 10), 25.0, dtype=np.float32)
    fc_perfect = np.full((10, 10), 25.0, dtype=np.float32)

    res = extreme_dependency_index(fc_perfect, truth, threshold=20.0)
    assert not np.isnan(res["edi"]), (
        "metrics_engine EDI produced NaN on full event space"
    )
    assert res["base_rate"] == 1.0


def test_singularity_zero_hits_with_events():
    """Test zero hits (a = 0) when events do occur (c > 0)."""
    truth = np.array([[25.0, 25.0], [5.0, 5.0]], dtype=np.float32)
    fc = np.array([[5.0, 5.0], [5.0, 5.0]], dtype=np.float32)

    res_edi = extreme_dependency_index(fc, truth, threshold=20.0)
    res_sedi = symmetric_extremal_dependence_index(fc, truth, threshold=20.0)

    assert not np.isnan(res_edi["edi"]), "EDI is NaN on zero hits"
    assert not np.isnan(res_sedi["sedi"]), "SEDI is NaN on zero hits"
    assert res_edi["hits"] == 0.0
    assert res_edi["misses"] == 2.0


def test_singularity_zero_false_alarms():
    """Test zero false alarms (b = 0) when non-events occur (d > 0)."""
    truth = np.array([[25.0, 5.0], [5.0, 5.0]], dtype=np.float32)
    fc = np.array([[25.0, 5.0], [5.0, 5.0]], dtype=np.float32)

    res_edi = extreme_dependency_index(fc, truth, threshold=20.0)
    assert not np.isnan(res_edi["edi"]), "EDI is NaN on zero false alarms"
    assert res_edi["false_alarms"] == 0.0


# =====================================================================
# 4. Latitude Weighting (Spherical Attenuation)
# =====================================================================


def test_latitude_weighting_cosine_attenuation():
    """Verify polar pixels are cosine-attenuated relative to equatorial pixels."""
    lats = np.array([0.0, 60.0, 85.0], dtype=np.float32)

    # Test 1: Hit at equator only
    tr_eq = torch.tensor([[25.0], [5.0], [5.0]])
    fc_eq = torch.tensor([[25.0], [5.0], [5.0]])

    # Test 2: Hit at near-pole only (lat = 85)
    tr_pol = torch.tensor([[5.0], [5.0], [25.0]])
    fc_pol = torch.tensor([[5.0], [5.0], [25.0]])

    rad = np.deg2rad(lats)
    cos_w = torch.tensor(np.cos(rad), dtype=torch.float32).unsqueeze(-1)

    a_eq, _, _, _ = compute_contingency_table(
        fc_eq, tr_eq, threshold=20.0, reduction_dims=[0, 1], weights=cos_w
    )
    a_pol, _, _, _ = compute_contingency_table(
        fc_pol, tr_pol, threshold=20.0, reduction_dims=[0, 1], weights=cos_w
    )

    ratio = float(a_pol / a_eq)
    expected_ratio = np.cos(np.deg2rad(85.0)) / np.cos(np.deg2rad(0.0))

    assert np.isclose(ratio, expected_ratio, atol=1e-4), (
        f"Expected polar hit weight ratio {expected_ratio}, got {ratio}"
    )


def test_latitude_grid_direction_validation():
    """Verify ascending latitude vectors trigger warning and reversal per e2s-014."""
    ascending_lats = np.linspace(-90, 90, 181)
    pipeline = EnsembleVerificationPipeline(target_lats=ascending_lats)

    assert pipeline.target_lats[0] == 90.0, (
        f"First lat must be +90, got {pipeline.target_lats[0]}"
    )
    assert pipeline.target_lats[-1] == -90.0, (
        f"Last lat must be -90, got {pipeline.target_lats[-1]}"
    )


# =====================================================================
# 5. Verification Pipeline Stress Test
# =====================================================================


def test_pipeline_lead_time_synchronization():
    """Stress test valid time synchronization across lead intervals and formats."""
    pipeline = EnsembleVerificationPipeline()

    init_iso = "2024-06-01T12:00:00"
    init_dt = datetime(2024, 6, 1, 12, 0, 0)
    init_np = np.datetime64("2024-06-01T12:00:00")

    leads = [0, 6, 18, 24, 72, 168, 240]

    for lead in leads:
        expected_valid = init_dt + timedelta(hours=lead)
        v1 = pipeline.synchronize_valid_time(init_iso, lead)
        v2 = pipeline.synchronize_valid_time(init_dt, lead)
        v3 = pipeline.synchronize_valid_time(init_np, lead)

        assert v1 == expected_valid
        assert v2 == expected_valid
        assert v3 == expected_valid


def test_pipeline_sha256_cryptographic_verification(tmp_path):
    """Stress test pipeline JSON generation and independently verify SHA-256 seal."""
    lats = np.linspace(90, -90, 19)
    lons = np.linspace(0, 350, 36)
    mock_source = MockGroundTruthSource(lats, lons, seed=99)

    pipeline = EnsembleVerificationPipeline(
        ground_truth_source=mock_source,
        source_name="mock_gfs",
        target_lats=lats,
    )

    lead_steps = [0, 6, 12]
    rng = np.random.default_rng(42)
    forecast_data = {
        "w10m": [
            rng.exponential(6.0, (4, 19, 36)).astype(np.float32) for _ in lead_steps
        ],
        "msl": [
            rng.uniform(98000.0, 102000.0, (4, 19, 36)).astype(np.float32)
            for _ in lead_steps
        ],
    }

    pipeline.verify_forecast_dataset(
        forecast_dataset=forecast_data,
        init_time="2024-03-15T00:00:00",
        lead_steps_hours=lead_steps,
        output_dir=tmp_path,
    )

    report_path = tmp_path / "verification_report.json"
    assert report_path.exists(), "verification_report.json was not written"

    with open(report_path, "r", encoding="utf-8") as f:
        loaded_report = json.load(f)

    # 1. Integrity seal existence
    assert "sha256_integrity_seal" in loaded_report, "Missing sha256_integrity_seal"
    seal_in_file = loaded_report.pop("sha256_integrity_seal")
    assert len(seal_in_file) == 64

    # 2. Independent cryptographic re-calculation
    canonical_json_str = json.dumps(loaded_report, indent=2)
    recalculated_sha256 = hashlib.sha256(canonical_json_str.encode("utf-8")).hexdigest()

    assert seal_in_file == recalculated_sha256, (
        f"Cryptographic integrity mismatch! Expected {recalculated_sha256}, got {seal_in_file}"
    )

    # 3. Bit-tamper test
    tampered_report = loaded_report.copy()
    tampered_report["variables"]["w10m"]["lead_trajectory"][0]["deterministic_metrics"][
        "rmse"
    ] = 999.99
    tampered_json_str = json.dumps(tampered_report, indent=2)
    tampered_sha256 = hashlib.sha256(tampered_json_str.encode("utf-8")).hexdigest()

    assert tampered_sha256 != seal_in_file, (
        "Tamper detection failed! Modified payload produced identical hash."
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
