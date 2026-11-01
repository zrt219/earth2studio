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

"""Unit tests for ClimaX prognostic model wrapper.

Validates:
- PrognosticModel protocol conformance.
- Coordinate system requirements (batch first, lead time, variables, lat/lon).
- Forward step (__call__) and iterator time series (create_iterator).
- Batch dimension management via @batch_func and @batch_coords.
- Device placement (.to) and package loading.
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import torch

from earth2studio.models.auto import AutoModelMixin, Package
from earth2studio.models.px import ClimaX
from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.climax import CLIMAX_VARIABLES
from earth2studio.models.px.utils import PrognosticMixin


def test_climax_protocol_conformance():
    """Verify ClimaX inherits required mixins and satisfies PrognosticModel protocol."""
    model = ClimaX()
    assert isinstance(model, PrognosticModel)
    assert isinstance(model, AutoModelMixin)
    assert isinstance(model, PrognosticMixin)
    assert isinstance(model, torch.nn.Module)


def test_climax_input_and_output_coords():
    """Verify ClimaX coordinate structure conforms to rule e2s-009."""
    lat = np.linspace(90.0, -90.0, 32)
    lon = np.linspace(0.0, 360.0, 64, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    in_coords = model.input_coords()
    assert isinstance(in_coords, OrderedDict)
    assert list(in_coords.keys())[0] == "batch"
    assert in_coords["lead_time"] == np.array([np.timedelta64(0, "h")])
    assert len(in_coords["variable"]) == len(CLIMAX_VARIABLES)
    assert np.array_equal(in_coords["lat"], lat)
    assert np.array_equal(in_coords["lon"], lon)

    out_coords = model.output_coords(in_coords)
    assert isinstance(out_coords, OrderedDict)
    assert list(out_coords.keys())[0] == "batch"
    assert out_coords["lead_time"] == np.array([np.timedelta64(6, "h")])
    assert np.array_equal(out_coords["variable"], in_coords["variable"])


def test_climax_forward_call():
    """Verify single time-step forward pass."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    x = torch.ones((1, 1, len(CLIMAX_VARIABLES), 16, 32), dtype=torch.float32)
    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(CLIMAX_VARIABLES),
            "lat": lat,
            "lon": lon,
        }
    )

    out, out_coords = model(x, coords)
    assert out.shape == (1, 1, len(CLIMAX_VARIABLES), 16, 32)
    assert out_coords["lead_time"][0] == np.timedelta64(6, "h")
    # Using identity core model
    assert torch.allclose(out, x)


def test_climax_create_iterator():
    """Verify create_iterator yields step 0 first, then steps 1..3 at 6h increments."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    x = torch.ones((1, 1, len(CLIMAX_VARIABLES), 16, 32), dtype=torch.float32) * 280.0
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

    # Step 0: initial condition
    s0, c0 = next(it)
    assert c0["lead_time"][0] == np.timedelta64(0, "h")
    assert torch.allclose(s0, x)

    # Step 1: 6h
    s1, c1 = next(it)
    assert c1["lead_time"][0] == np.timedelta64(6, "h")
    assert torch.allclose(s1, x)

    # Step 2: 12h
    s2, c2 = next(it)
    assert c2["lead_time"][0] == np.timedelta64(12, "h")


def test_climax_multi_batch_handling():
    """Verify @batch_func compresses and decompresses leading dimensions."""
    lat = np.linspace(90.0, -90.0, 16)
    lon = np.linspace(0.0, 360.0, 32, endpoint=False)
    model = ClimaX(lat=lat, lon=lon)

    # (ensemble=3, time=2, lead_time=1, var, lat, lon)
    x = torch.ones((3, 2, 1, len(CLIMAX_VARIABLES), 16, 32), dtype=torch.float32)
    coords = OrderedDict(
        {
            "ensemble": np.array(["e1", "e2", "e3"]),
            "time": np.array(
                [np.datetime64("2026-10-20"), np.datetime64("2026-10-21")]
            ),
            "lead_time": np.array([np.timedelta64(0, "h")]),
            "variable": np.array(CLIMAX_VARIABLES),
            "lat": lat,
            "lon": lon,
        }
    )

    out, out_coords = model(x, coords)
    assert out.shape == (3, 2, 1, len(CLIMAX_VARIABLES), 16, 32)
    assert list(out_coords.keys())[:2] == ["ensemble", "time"]
    assert out_coords["lead_time"][0] == np.timedelta64(6, "h")


def test_climax_to_device():
    """Verify device placement."""
    model = ClimaX()
    ret = model.to("cpu")
    assert ret is model


def test_climax_package_methods(tmp_path):
    """Verify load_default_package and load_model fallback."""
    pkg = ClimaX.load_default_package()
    assert isinstance(pkg, Package)

    # Instantiate from empty package directory via fallback
    dummy_pkg = Package(str(tmp_path))
    model = ClimaX.load_model(dummy_pkg)
    assert isinstance(model, ClimaX)
