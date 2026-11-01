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

"""Unit tests for the core Earth2Studio model registry.

Validates:
- Canonical model cataloging and alias listing.
- Case-insensitive and punctuation-agnostic alias normalization.
- Metadata inspection (ModelInfo schema and values).
- Fuzzy "Did you mean?" suggestions for unknown model names.
- Dynamic runtime model registration and overwrite protection.
- Model instantiation via get_model and AutoPrognostic.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pytest
import torch

from earth2studio.models.batch import batch_coords, batch_func
from earth2studio.models.px import ClimaX, Persistence
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


def test_list_models_canonical():
    """Verify canonical model listing contains required models."""
    models = list_models(include_aliases=False)
    assert isinstance(models, list)
    expected_models = [
        "climax",
        "graphcast",
        "pangu",
        "persistence",
        "sfno",
    ]
    for exp in expected_models:
        assert exp in models, f"Expected canonical model '{exp}' missing from list"

    # Multimodel or multi_model_ensemble must also be present
    assert any("multi" in m for m in models)


def test_list_models_include_aliases():
    """Verify list_models(include_aliases=True) includes registered aliases."""
    all_names = list_models(include_aliases=True)
    canonical_names = list_models(include_aliases=False)
    assert len(all_names) > len(canonical_names)

    expected_aliases = [
        "fcnv2",
        "fourcastnetv2",
        "panguweather",
        "persist",
        "climax_vit",
    ]
    for alias in expected_aliases:
        assert alias in all_names, f"Expected alias '{alias}' missing from list"


def test_alias_resolution():
    """Verify canonical resolution of various aliases."""
    assert resolve_model_name("fcnv2") == "sfno"
    assert resolve_model_name("fourcastnetv2") == "sfno"
    assert resolve_model_name("fourcastnet_v2") == "sfno"
    assert resolve_model_name("panguweather") == "pangu"
    assert resolve_model_name("pangu_weather") == "pangu"
    assert resolve_model_name("pangu6") == "pangu"
    assert resolve_model_name("climax_vit") == "climax"
    assert resolve_model_name("persist") == "persistence"
    assert resolve_model_name("identity") == "persistence"
    assert resolve_model_name("graphcast_operational") == "graphcast"


def test_case_insensitivity_and_punctuation():
    """Verify case, hyphen, and underscore tolerance."""
    assert resolve_model_name("SFNO") == "sfno"
    assert resolve_model_name("SfNo") == "sfno"
    assert resolve_model_name("FCN-V2") == "sfno"
    assert resolve_model_name("fourcastnet-v2") == "sfno"
    assert resolve_model_name("PANGU-WEATHER") == "pangu"
    assert resolve_model_name("ClimaX-ViT") == "climax"
    assert resolve_model_name("GraphCast-Operational") == "graphcast"


def test_unknown_model_raises_key_error():
    """Verify unknown model raises KeyError containing available models."""
    with pytest.raises(KeyError) as exc_info:
        resolve_model_name("completely_unknown_network_xyz")
    assert "Available models" in str(exc_info.value)


def test_fuzzy_suggestion_in_error():
    """Verify closest match recommendation on typos."""
    with pytest.raises(KeyError) as exc_info:
        resolve_model_name("sfnoo")
    assert "Did you mean 'sfno'?" in str(exc_info.value)

    with pytest.raises(KeyError) as exc_info:
        resolve_model_name("panguw")
    assert "Did you mean" in str(exc_info.value)


def test_get_model_info_schema():
    """Verify get_model_info returns ModelInfo with all required fields."""
    info = get_model_info("sfno")
    assert isinstance(info, ModelInfo)
    assert info.name == "sfno"
    assert info.family == "sfno"
    assert info.resolution == 0.25
    assert info.history_steps == 1
    assert info.timestep == 6.0
    assert info.license == "Apache-2.0"
    assert "ngc://" in info.checkpoint_source

    # Dict-like access
    assert info["name"] == "sfno"
    assert "variables" in info
    assert info.get("family") == "sfno"


def test_model_metadata_values():
    """Verify specific architecture characteristics."""
    gc_info = get_model_info("graphcast")
    assert gc_info.history_steps == 2
    assert gc_info.resolution == 0.25
    assert gc_info.family == "gnn"

    pers_info = get_model_info("persistence")
    assert pers_info.family == "baseline"
    assert pers_info.resolution == "domain_adaptive"

    climax_info = get_model_info("climax")
    assert climax_info.family == "vit"
    assert climax_info.resolution == 1.40625


def test_dynamic_registration():
    """Verify runtime model registration via decorator."""

    @register_model(
        name="custom_toy_model",
        aliases=["toy_model", "toy_net"],
        override=True,
    )
    class CustomToyModel(torch.nn.Module, PrognosticMixin):
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

    assert "custom_toy_model" in list_models()
    assert resolve_model_name("toy_model") == "custom_toy_model"
    assert resolve_model_name("toy_net") == "custom_toy_model"

    inst = get_model("custom_toy_model", pretrained=False)
    assert isinstance(inst, CustomToyModel)


def test_duplicate_registration_guards():
    """Verify re-registering without override=True raises ValueError."""
    with pytest.raises(ValueError, match="already registered"):
        register_model(name="sfno", override=False)(None)


def test_persistence_instantiation():
    """Verify get_model instantiates Persistence baseline."""
    dc = OrderedDict(
        {
            "lat": np.linspace(90.0, -90.0, 32),
            "lon": np.linspace(0.0, 360.0, 64, endpoint=False),
        }
    )
    model = get_model("persistence", variable=["t2m"], domain_coords=dc)
    assert isinstance(model, Persistence)

    x = torch.zeros((1, 1, 1, 32, 64))
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(["t2m"]),
            "lat": dc["lat"],
            "lon": dc["lon"],
        }
    )
    out, out_coords = model(x, coords)
    assert out.shape == x.shape
    assert out_coords["lead_time"][0] == np.timedelta64(6, "h")


def test_climax_instantiation():
    """Verify get_model instantiates ClimaX wrapper."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = get_model("climax", lat=lat, lon=lon, pretrained=False)
    assert isinstance(model, ClimaX)


def test_auto_prognostic_bridge():
    """Verify AutoPrognostic delegates cleanly to get_model."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = AutoPrognostic.from_pretrained("climax", lat=lat, lon=lon, pretrained=False)
    assert isinstance(model, ClimaX)
