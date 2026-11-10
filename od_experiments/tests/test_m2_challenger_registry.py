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

"""Adversarial challenger test suite for Milestone 2.

Focus Areas:
1. Model Registry Stress:
   - Extreme alias resolution (leading/trailing/interspersed whitespace, mixed casing, hyphens, underscores).
   - Unknown models & typos: KeyError verification with difflib fuzzy suggestions.
   - Dynamic registration concurrency & duplicate registration guards.
   - Lazy loading isolation: verifying model discovery/metadata never triggers heavy optional imports.
   - AutoPrognostic.from_pretrained resilience with valid, aliased, and invalid identifiers.
2. ClimaX Prognostic Wrapper Stress:
   - Coordinate mismatch handling in ClimaX forward pass (missing variables, wrong order, wrong shapes).
   - Arbitrary lead times and multi-step rollouts (monotonic time evolution, tensor shape integrity).
   - Multi-batch dimension preservation and device placement (.to('cpu')).
   - Coordinate systems contract verification (batch-first, descending latitude, longitude bounds).
3. Execution Latency & Memory:
   - 5-model mock instantiation and multi-step rollout benchmark on CPU (< 1.0s target).
   - Memory stability over 20 iterations.
"""

from __future__ import annotations

import concurrent.futures
import gc
import subprocess
import sys
import time
from collections import OrderedDict

import numpy as np
import pytest
import torch

from earth2studio.models.batch import batch_coords, batch_func
from earth2studio.models.px import ClimaX, Persistence
from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.climax import CLIMAX_VARIABLES
from earth2studio.models.px.utils import PrognosticMixin
from earth2studio.models.registry import (
    AutoPrognostic,
    ModelInfo,
    get_model,
    get_model_info,
    list_models,
    register_model,
    resolve_model_name,
)
from earth2studio.utils.type import CoordSystem
from od_experiments.model_comparison.registry import (
    get_5model_benchmark_suite,
    get_benchmark_info,
    get_benchmark_model,
)
from od_experiments.tests.mock_prognostics import DEFAULT_EVAL_VARS

# ==============================================================================
# SECTION 1: Model Registry Adversarial Stress Tests
# ==============================================================================


@pytest.mark.parametrize(
    "extreme_alias,expected_canonical",
    [
        ("  sfno  ", "sfno"),
        ("\t\n SFNO \r\n", "sfno"),
        ("--sfno--", "sfno"),
        ("___sfno___", "sfno"),
        ("-f-c-n-v-2-", "sfno"),
        ("  FCN_V2  ", "sfno"),
        ("fourcastnet--v2", "sfno"),
        ("FourCastNetV2", "sfno"),
        ("  pangu_weather  ", "pangu"),
        ("PANGU---6", "pangu"),
        ("___panguweather___", "pangu"),
        ("  climax-vit  ", "climax"),
        ("clima-x", "climax"),
        ("CLIMAX_ERA5", "climax"),
        ("  graphcast_operational  ", "graphcast"),
        ("GRAPHCAST---OPERATIONAL", "graphcast"),
        ("  persistence_baseline  ", "persistence"),
        ("BASELINE-PERSISTENCE", "persistence"),
        ("  multi-model-ensemble  ", "multimodel"),
        ("MME", "multimodel"),
    ],
)
def test_registry_extreme_alias_resolution(extreme_alias, expected_canonical):
    """Stress-test alias resolution under extreme whitespace, mixed cases, hyphens, and underscores."""
    resolved = resolve_model_name(extreme_alias)
    assert resolved == expected_canonical, (
        f"Failed to resolve extreme alias '{extreme_alias}' -> got '{resolved}', expected '{expected_canonical}'"
    )


@pytest.mark.parametrize(
    "bogus_input",
    [
        "",
        "   ",
        "\t\n  \r\n",
        "---",
        "___",
        "---___---",
        "totally_unknown_atmospheric_neural_network_xyz",
        "1234567890",
        "!@#$%^&*()",
    ],
)
def test_registry_unknown_model_raises_keyerror(bogus_input):
    """Verify bogus inputs cleanly raise KeyError without crashing with unhandled exceptions."""
    with pytest.raises(KeyError) as exc_info:
        resolve_model_name(bogus_input)
    assert "not found in registry" in str(exc_info.value)
    assert "Available models" in str(exc_info.value)


@pytest.mark.parametrize(
    "typo_input,expected_suggestion",
    [
        ("sfnoo", "sfno"),
        ("fcnv3", "fcnv2"),
        ("pangoo", "pangu"),
        ("climaz", "climax"),
        ("graphcastt", "graphcast"),
        ("persistenc", "persistence"),
        ("multimodell", "multimodel"),
    ],
)
def test_registry_fuzzy_suggestions(typo_input, expected_suggestion):
    """Verify close typos trigger helpful fuzzy suggestions via difflib."""
    with pytest.raises(KeyError) as exc_info:
        resolve_model_name(typo_input)
    msg = str(exc_info.value)
    assert "Did you mean" in msg, (
        f"Expected fuzzy suggestion for '{typo_input}', got: {msg}"
    )
    assert expected_suggestion in msg, (
        f"Expected suggestion '{expected_suggestion}' in message, got: {msg}"
    )


def test_registry_duplicate_registration_guard():
    """Verify re-registering an existing canonical model without override=True raises ValueError."""
    with pytest.raises(ValueError, match="already registered"):
        register_model(name="sfno", override=False)(None)

    with pytest.raises(ValueError, match="already registered"):
        register_model(name="graphcast", override=False)(None)


def test_registry_dynamic_registration_and_overwrite():
    """Verify registering a custom model with override=True works, and get_model retrieves it."""
    test_model_name = "test_adversarial_custom_net"

    @register_model(
        name=test_model_name,
        aliases=["adv_net_1", "adv_net_2"],
        override=True,
    )
    class CustomAdversarialModel(torch.nn.Module, PrognosticMixin):
        def __init__(self, multiplier: float = 2.0):
            super().__init__()
            self.multiplier = multiplier

        def input_coords(self) -> CoordSystem:
            return OrderedDict({"batch": np.empty(0)})

        @batch_coords()
        def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
            return input_coords

        @batch_func()
        def __call__(self, x: torch.Tensor, coords: CoordSystem):
            return x * self.multiplier, coords

        def create_iterator(self, x: torch.Tensor, coords: CoordSystem):
            yield x, coords

    assert test_model_name in list_models()
    assert resolve_model_name("adv_net_1") == test_model_name
    assert resolve_model_name("adv_net_2") == test_model_name

    inst = get_model(test_model_name, pretrained=False, multiplier=3.5)
    assert isinstance(inst, CustomAdversarialModel)
    assert inst.multiplier == 3.5

    # Test override
    @register_model(
        name=test_model_name,
        override=True,
    )
    class OverwrittenCustomModel(torch.nn.Module, PrognosticMixin):
        def __init__(self):
            super().__init__()
            self.version = 2

        def input_coords(self) -> CoordSystem:
            return OrderedDict({"batch": np.empty(0)})

        @batch_coords()
        def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
            return input_coords

        @batch_func()
        def __call__(self, x: torch.Tensor, coords: CoordSystem):
            return x, coords

        def create_iterator(self, x: torch.Tensor, coords: CoordSystem):
            yield x, coords

    inst2 = get_model(test_model_name, pretrained=False)
    assert isinstance(inst2, OverwrittenCustomModel)
    assert inst2.version == 2

    info = get_model_info(test_model_name)
    assert isinstance(info, ModelInfo)


def test_registry_concurrent_dynamic_registration():
    """Verify thread-safety of register_model under concurrent multi-threaded execution."""

    def register_worker(worker_id: int):
        model_name = f"concurrent_model_{worker_id}"

        class DummyModel(torch.nn.Module, PrognosticMixin):
            def input_coords(self):
                return OrderedDict({"batch": np.empty(0)})

            @batch_coords()
            def output_coords(self, coords):
                return coords

            @batch_func()
            def __call__(self, x, c):
                return x, c

            def create_iterator(self, x, c):
                yield x, c

        register_model(
            name=model_name, aliases=[f"c_alias_{worker_id}"], override=True
        )(DummyModel)
        resolved = resolve_model_name(f"c_alias_{worker_id}")
        return resolved == model_name

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(register_worker, i) for i in range(16)]
        results = [f.result() for f in futures]

    assert all(results), (
        "Concurrent model registration encountered race conditions or corruption"
    )


def test_registry_lazy_loading_isolation():
    """Verify that importing registry and inspecting metadata NEVER imports heavy model modules.

    Executes an isolated python subprocess to inspect sys.modules cleanly.
    """
    code = """
import sys
from earth2studio.models.registry import list_models, get_model_info, resolve_model_name

# Perform metadata queries
models = list_models(include_aliases=True)
sfno_info = get_model_info("sfno")
gc_info = get_model_info("graphcast")
pangu_info = get_model_info("pangu")
climax_info = get_model_info("climax")
res = resolve_model_name("fourcastnetv2")

# Check sys.modules
imported_modules = set(sys.modules.keys())

forbidden_modules = [
    "earth2studio.models.px.sfno",
    "earth2studio.models.px.graphcast_operational",
    "earth2studio.models.px.pangu",
    "jax",
    "onnxruntime",
]

for forbidden in forbidden_modules:
    if forbidden in imported_modules:
        print(f"VIOLATION: Forbidden module '{forbidden}' was eagerly imported!")
        sys.exit(1)

print("SUCCESS: Lazy loading isolation strictly preserved.")
sys.exit(0)
"""
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Lazy loading isolation failed: {result.stdout}\n{result.stderr}"
    )
    assert "SUCCESS: Lazy loading isolation strictly preserved." in result.stdout


def test_auto_prognostic_from_pretrained():
    """Verify AutoPrognostic.from_pretrained behavior with canonical, aliased, and invalid names."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)

    # Valid canonical
    m1 = AutoPrognostic.from_pretrained("climax", lat=lat, lon=lon, pretrained=False)
    assert isinstance(m1, ClimaX)

    # Valid alias
    m2 = AutoPrognostic.from_pretrained(
        "climax_vit", lat=lat, lon=lon, pretrained=False
    )
    assert isinstance(m2, ClimaX)

    # Persistence baseline
    dc = OrderedDict({"lat": lat, "lon": lon})
    m3 = AutoPrognostic.from_pretrained(
        "persistence", variable=["t2m"], domain_coords=dc, pretrained=False
    )
    assert isinstance(m3, Persistence)

    # Invalid name raises KeyError
    with pytest.raises(KeyError, match="not found in registry"):
        AutoPrognostic.from_pretrained("non_existent_climate_model_12345")


# ==============================================================================
# SECTION 2: ClimaX Prognostic Wrapper Adversarial Stress Tests
# ==============================================================================


def test_climax_coordinate_mismatch_variable_missing():
    """Verify ClimaX catches missing 'variable' dimension via batch_func or handshake_coords."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    # Case A: 5D tensor provided with 4D coords (missing 'variable') -> batch_func catches rank mismatch
    x5d = torch.zeros((1, 1, len(CLIMAX_VARIABLES), 16, 32))
    coords_missing_var = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "lat": lat,
            "lon": lon,
        }
    )
    with pytest.raises(
        ValueError, match="Input tensor shape does not match the provided coordinates"
    ):
        model(x5d, coords_missing_var)

    # Case B: 4D tensor provided matching 4D coords -> handshake_coords catches missing 'variable'
    x4d = torch.zeros((1, 1, 16, 32))
    with pytest.raises(
        KeyError, match="Required dimension variable not found in input coordinates"
    ):
        model(x4d, coords_missing_var)


def test_climax_coordinate_mismatch_wrong_variables():
    """Verify ClimaX.__call__ raises ValueError when variables don't match CLIMAX_VARIABLES."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    x = torch.zeros((1, 1, 3, 16, 32))
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(["t2m", "u10m", "v10m"]),
            "lat": lat,
            "lon": lon,
        }
    )
    with pytest.raises(
        ValueError,
        match="Coordinate systems for required dim variable are not the same",
    ):
        model(x, coords)


def test_climax_coordinate_mismatch_inverted_variables():
    """Verify ClimaX raises ValueError when variables are permuted / inverted."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    inverted_vars = np.array(CLIMAX_VARIABLES[::-1])
    x = torch.zeros((1, 1, 56, 16, 32))
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": inverted_vars,
            "lat": lat,
            "lon": lon,
        }
    )
    with pytest.raises(
        ValueError,
        match="Coordinate systems for required dim variable are not the same",
    ):
        model(x, coords)


def test_climax_arbitrary_initial_lead_time():
    """Verify ClimaX correctly steps forward from non-zero initial lead times (e.g. 18h -> 24h)."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    init_lead = np.array([np.timedelta64(18, "h")])
    x = torch.ones((1, 1, len(CLIMAX_VARIABLES), 16, 32)) * 290.0
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": init_lead,
            "variable": np.array(CLIMAX_VARIABLES),
            "lat": lat,
            "lon": lon,
        }
    )

    out, out_coords = model(x, coords)
    assert out_coords["lead_time"][0] == np.timedelta64(24, "h")
    assert torch.allclose(out, x)


def test_climax_multi_step_rollout_monotonicity():
    """Verify multi-step rollout iterator yields monotonic lead times and stable shapes over 10 steps."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    x = torch.ones((1, 1, len(CLIMAX_VARIABLES), 16, 32)) * 285.0
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(CLIMAX_VARIABLES),
            "lat": lat,
            "lon": lon,
        }
    )

    it = model.create_iterator(x, coords)

    expected_lead_times_hours = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60]
    for step, exp_h in enumerate(expected_lead_times_hours):
        out_x, out_c = next(it)
        assert out_x.shape == (1, 1, len(CLIMAX_VARIABLES), 16, 32), (
            f"Step {step} shape mismatch"
        )
        assert out_c["lead_time"][0] == np.timedelta64(exp_h, "h"), (
            f"Step {step} lead time mismatch: got {out_c['lead_time'][0]}, expected {exp_h}h"
        )
        assert torch.isfinite(out_x).all(), f"Step {step} contains NaN or Inf values"


def test_climax_complex_multi_batch_dimensions():
    """Verify ClimaX handles 3-level hierarchical batch dimensions (e.g. ensemble, member, scenario)."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    # 3 leading batch dims: (2, 3, 2, 1, 56, 16, 32)
    x = torch.ones((2, 3, 2, 1, len(CLIMAX_VARIABLES), 16, 32))
    coords = OrderedDict(
        {
            "scenario": np.array(["s1", "s2"]),
            "ensemble": np.array(["e1", "e2", "e3"]),
            "member": np.array(["m1", "m2"]),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(CLIMAX_VARIABLES),
            "lat": lat,
            "lon": lon,
        }
    )

    out, out_coords = model(x, coords)
    assert out.shape == (2, 3, 2, 1, len(CLIMAX_VARIABLES), 16, 32)
    assert list(out_coords.keys())[:3] == ["scenario", "ensemble", "member"]
    assert np.array_equal(out_coords["scenario"], np.array(["s1", "s2"]))
    assert np.array_equal(out_coords["ensemble"], np.array(["e1", "e2", "e3"]))
    assert np.array_equal(out_coords["member"], np.array(["m1", "m2"]))
    assert out_coords["lead_time"][0] == np.timedelta64(6, "h")


def test_climax_device_transfer_cpu():
    """Verify .to('cpu') and .to(torch.device('cpu')) return self and maintain buffer placement."""
    model = ClimaX()
    m_cpu_str = model.to("cpu")
    assert m_cpu_str is model
    assert model.device_buffer.device.type == "cpu"

    m_cpu_dev = model.to(torch.device("cpu"))
    assert m_cpu_dev is model
    assert model.device_buffer.device.type == "cpu"


def test_climax_coordinate_systems_contract():
    """Verify ClimaX input_coords conforms to e2s-009 and e2s-014 rules."""
    model = ClimaX()
    in_coords = model.input_coords()

    # Rule e2s-009: batch must be first key
    keys = list(in_coords.keys())
    assert keys[0] == "batch", f"First key must be 'batch', got '{keys[0]}'"

    # Rule e2s-014: Descending latitudes (+90 to -90)
    lat = in_coords["lat"]
    assert lat[0] > lat[-1], (
        f"Latitudes must be descending (+90 to -90), got {lat[0]} to {lat[-1]}"
    )
    assert np.isclose(lat[0], 90.0)
    assert np.isclose(lat[-1], -90.0)

    # Longitudes in [0, 360)
    lon = in_coords["lon"]
    assert lon[0] >= 0.0
    assert lon[-1] < 360.0

    # Variables must match 57-channel CLIMAX_VARIABLES
    assert len(in_coords["variable"]) == 57
    assert len(CLIMAX_VARIABLES) == 57
    assert np.array_equal(in_coords["variable"], np.array(CLIMAX_VARIABLES))


# ==============================================================================
# SECTION 3: Execution Latency & Memory Verification on CPU
# ==============================================================================


def test_5model_mock_instantiation_latency():
    """Verify instant instantiation of the complete 5-model suite on CPU (< 0.1s target, prompt < 1.0s)."""
    t0 = time.perf_counter()
    suite = get_5model_benchmark_suite(mock=True, lat_size=16, lon_size=32)
    instantiation_elapsed = time.perf_counter() - t0

    assert len(suite) == 5
    assert instantiation_elapsed < 0.2, (
        f"5-model mock instantiation took {instantiation_elapsed:.4f}s, expected < 0.2s"
    )

    # Verify individual benchmark model and info retrieval
    p_model = get_benchmark_model("persistence", mock=True)
    assert isinstance(p_model, PrognosticModel)
    b_info = get_benchmark_info("graphcast")
    assert b_info["name"] == "graphcast"


def test_5model_mock_forward_latency_and_memory():
    """Verify 5-model mock forward pass execution is < 1.0s and memory remains stable over 20 iterations."""
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

    gc.collect()
    t0 = time.perf_counter()

    # Perform 20 rollout loops across all 5 models
    for _ in range(20):
        for model in suite.values():
            if model._history == 2:
                m_x, m_c = x, coords
            else:
                m_x = x[:, -1:]
                m_c = coords.copy()
                m_c["lead_time"] = coords["lead_time"][-1:]

            out, out_coords = model(m_x, m_c)
            assert out.shape[-3:] == (len(DEFAULT_EVAL_VARS), 16, 32)
            assert torch.isfinite(out).all()

    total_elapsed = time.perf_counter() - t0

    # Prompt requirement: Must be < 1.0s for 5 models
    assert total_elapsed < 1.0, (
        f"20 steps x 5 models forward pass took {total_elapsed:.4f}s on CPU (target < 1.0s)"
    )
