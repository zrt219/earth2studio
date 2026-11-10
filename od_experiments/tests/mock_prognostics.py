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

"""Deterministic CPU Mock Prognostic Models and Fixtures.

Provides zero-dependency, zero-network CPU mocks for:
1. GraphCast (2-step history [-6h, 0h], 6h step, optional tp06)
2. FourCastNet v2 / SFNO (1-step history [0h], 6h step)
3. Pangu-Weather (1-step history [0h], 6h step)
4. ClimaX (1-step history [0h], 6h step)
5. Persistence Baseline (identity operator, 6h step)

Scientific Integrity:
Adheres strictly to .agents/rules/e2s-014-scientific-integrity.mdc:
Zero synthetic pseudo-random noise; pure deterministic physical evolution
(zonal advection, Rossby wave phase dispersion, and physical momentum tendencies).
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest
import torch

from earth2studio.models.batch import batch_coords, batch_func
from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.utils import PrognosticMixin
from earth2studio.utils.type import CoordSystem

DEFAULT_EVAL_VARS = ["t2m", "u10m", "v10m", "z500", "t850", "msl"]


class MockPrognosticBase(torch.nn.Module, PrognosticMixin):
    """Base class for lightweight protocol-compliant CPU mock models.

    Parameters
    ----------
    variables : list[str] | None, optional
        Variables predicted by the model, by default DEFAULT_EVAL_VARS.
    domain_coords : CoordSystem | None, optional
        Domain coordinates containing 'lat' and 'lon'.
    lat_size : int, optional
        Number of latitude points if domain_coords is None, by default 32.
    lon_size : int, optional
        Number of longitude points if domain_coords is None, by default 64.
    history : int, optional
        Number of history steps required in input, by default 1.
    time_step : np.timedelta64, optional
        Time-step size of prognostic model, by default np.timedelta64(6, 'h').
    """

    def __init__(
        self,
        variables: list[str] | None = None,
        domain_coords: CoordSystem | None = None,
        lat_size: int = 32,
        lon_size: int = 64,
        history: int = 1,
        time_step: np.timedelta64 = np.timedelta64(6, "h"),
    ) -> None:
        super().__init__()
        self.variables = np.array(
            variables if variables is not None else DEFAULT_EVAL_VARS
        )
        if domain_coords is not None:
            self.lat = np.asarray(domain_coords["lat"])
            self.lon = np.asarray(domain_coords["lon"])
        else:
            self.lat = np.linspace(90.0, -90.0, lat_size)
            self.lon = np.linspace(0.0, 360.0, lon_size, endpoint=False)

        self._history = history
        self._time_step = time_step
        self.register_buffer("device_buffer", torch.empty(0))

    def input_coords(self) -> CoordSystem:
        """Input coordinate system with batch as first key."""
        return OrderedDict(
            {
                "batch": np.empty(0),
                "lead_time": np.array(
                    [
                        np.timedelta64(-self._time_step * i, "h")
                        for i in reversed(range(self._history))
                    ]
                ),
                "variable": self.variables,
                "lat": self.lat,
                "lon": self.lon,
            }
        )

    @batch_coords()
    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        """Output coordinate system advanced by one time-step."""
        out = input_coords.copy()
        out["lead_time"] = input_coords["lead_time"][-1:] + np.array([self._time_step])
        out["variable"] = self.variables
        return out

    def to(self, device: Any) -> PrognosticModel:
        """Move model to device."""
        super().to(device)
        return self


class MockPersistence(MockPrognosticBase):
    """Persistence baseline model applying identity operator with dt increment."""

    @batch_func()
    def __call__(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> tuple[torch.Tensor, CoordSystem]:
        return x[:, -1:], self.output_coords(coords)

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: CoordSystem):
        coords_out = coords.copy()
        coords_out["lead_time"] = coords["lead_time"][-1:]
        yield x[:, -1:], coords_out

        curr_x = x
        while True:
            curr_x, coords = self.front_hook(curr_x, coords)
            nxt, coords = self(curr_x, coords)
            nxt, coords = self.rear_hook(nxt, coords)
            if self._history > 1:
                curr_x = torch.cat([curr_x[:, 1:], nxt], dim=1)
            else:
                curr_x = nxt
            yield nxt, coords.copy()

    def create_iterator(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        yield from self._default_generator(x, coords)


class MockGraphCast(MockPrognosticBase):
    """GraphCast mock requiring 2-step history [-6h, 0h]."""

    def __init__(
        self,
        variables: list[str] | None = None,
        domain_coords: CoordSystem | None = None,
        lat_size: int = 32,
        lon_size: int = 64,
        time_step: np.timedelta64 = np.timedelta64(6, "h"),
        add_tp06: bool = False,
        advection_shift: int = 1,
        tendency_scale: float = 0.1,
    ) -> None:
        super().__init__(
            variables=variables,
            domain_coords=domain_coords,
            lat_size=lat_size,
            lon_size=lon_size,
            history=2,
            time_step=time_step,
        )
        self.add_tp06 = add_tp06
        self.advection_shift = advection_shift
        self.tendency_scale = tendency_scale
        if add_tp06:
            self._out_variables = np.array(list(self.variables) + ["tp06"])
        else:
            self._out_variables = self.variables

    @batch_coords()
    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        out = input_coords.copy()
        out["lead_time"] = input_coords["lead_time"][-1:] + np.array([self._time_step])
        out["variable"] = self._out_variables
        return out

    @batch_func()
    def __call__(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> tuple[torch.Tensor, CoordSystem]:
        x_prev = x[:, 0]
        x_curr = x[:, 1]
        tendency = x_curr - x_prev
        advected = (
            torch.roll(x_curr, shifts=self.advection_shift, dims=-1)
            + self.tendency_scale * tendency
        )
        if self.add_tp06:
            tp06 = 0.05 * torch.abs(x_curr[:, :1] - 273.15)
            out = torch.cat([advected, tp06], dim=1)
        else:
            out = advected
        return out.unsqueeze(1), self.output_coords(coords)

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: CoordSystem):
        coords_out = coords.copy()
        coords_out["lead_time"] = coords["lead_time"][-1:]
        coords_out["variable"] = self._out_variables
        if self.add_tp06:
            tp06_init = torch.zeros_like(x[:, -1:, :1])
            init_val = torch.cat([x[:, -1:], tp06_init], dim=2)
        else:
            init_val = x[:, -1:]
        yield init_val, coords_out

        curr_x = x
        while True:
            curr_x, coords = self.front_hook(curr_x, coords)
            nxt, coords = self(curr_x, coords)
            nxt, coords = self.rear_hook(nxt, coords)
            if self.add_tp06:
                curr_x = torch.cat([curr_x[:, 1:], nxt[:, :, :-1]], dim=1)
            else:
                curr_x = torch.cat([curr_x[:, 1:], nxt], dim=1)
            yield nxt, coords.copy()

    def create_iterator(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        yield from self._default_generator(x, coords)


class MockSFNO(MockPrognosticBase):
    """SFNO mock simulating spherical harmonic wave advection."""

    def __init__(
        self,
        variables: list[str] | None = None,
        domain_coords: CoordSystem | None = None,
        lat_size: int = 32,
        lon_size: int = 64,
        time_step: np.timedelta64 = np.timedelta64(6, "h"),
        advection_shift: int = 2,
        damping: float = 0.998,
    ) -> None:
        super().__init__(
            variables=variables,
            domain_coords=domain_coords,
            lat_size=lat_size,
            lon_size=lon_size,
            history=1,
            time_step=time_step,
        )
        self.advection_shift = advection_shift
        self.damping = damping

    @batch_func()
    def __call__(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> tuple[torch.Tensor, CoordSystem]:
        x_curr = x[:, -1:]
        out = self.damping * torch.roll(x_curr, shifts=self.advection_shift, dims=-1)
        return out, self.output_coords(coords)

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: CoordSystem):
        coords_out = coords.copy()
        coords_out["lead_time"] = coords["lead_time"][-1:]
        yield x[:, -1:], coords_out

        curr_x = x
        while True:
            curr_x, coords = self.front_hook(curr_x, coords)
            nxt, coords = self(curr_x, coords)
            nxt, coords = self.rear_hook(nxt, coords)
            curr_x = nxt
            yield nxt, coords.copy()

    def create_iterator(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        yield from self._default_generator(x, coords)


class MockPangu(MockPrognosticBase):
    """Pangu-Weather mock simulating 3D Swin transformer with Rossby wave dynamics."""

    def __init__(
        self,
        variables: list[str] | None = None,
        domain_coords: CoordSystem | None = None,
        lat_size: int = 32,
        lon_size: int = 64,
        time_step: np.timedelta64 = np.timedelta64(6, "h"),
        advection_shift: int = 1,
        damping: float = 0.997,
        rossby_scale: float = 0.002,
    ) -> None:
        super().__init__(
            variables=variables,
            domain_coords=domain_coords,
            lat_size=lat_size,
            lon_size=lon_size,
            history=1,
            time_step=time_step,
        )
        self.advection_shift = advection_shift
        self.damping = damping
        self.rossby_scale = rossby_scale

        lat_rad = torch.deg2rad(torch.tensor(self.lat, dtype=torch.float32)).view(
            1, 1, 1, -1, 1
        )
        self.register_buffer("lat_cos", torch.cos(lat_rad))

    @batch_func()
    def __call__(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> tuple[torch.Tensor, CoordSystem]:
        x_curr = x[:, -1:]
        out = (
            self.damping * torch.roll(x_curr, shifts=self.advection_shift, dims=-1)
            - self.rossby_scale * self.lat_cos * x_curr
        )
        return out, self.output_coords(coords)

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: CoordSystem):
        coords_out = coords.copy()
        coords_out["lead_time"] = coords["lead_time"][-1:]
        yield x[:, -1:], coords_out

        curr_x = x
        while True:
            curr_x, coords = self.front_hook(curr_x, coords)
            nxt, coords = self(curr_x, coords)
            nxt, coords = self.rear_hook(nxt, coords)
            curr_x = nxt
            yield nxt, coords.copy()

    def create_iterator(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        yield from self._default_generator(x, coords)


class MockClimaX(MockPrognosticBase):
    """ClimaX mock simulating Vision Transformer patch-tokenized weather evolution."""

    def __init__(
        self,
        variables: list[str] | None = None,
        domain_coords: CoordSystem | None = None,
        lat_size: int = 32,
        lon_size: int = 64,
        time_step: np.timedelta64 = np.timedelta64(6, "h"),
        advection_shift: int = 2,
        damping: float = 0.995,
        meridional_blend: float = 0.005,
    ) -> None:
        super().__init__(
            variables=variables,
            domain_coords=domain_coords,
            lat_size=lat_size,
            lon_size=lon_size,
            history=1,
            time_step=time_step,
        )
        self.advection_shift = advection_shift
        self.damping = damping
        self.meridional_blend = meridional_blend

    @batch_func()
    def __call__(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> tuple[torch.Tensor, CoordSystem]:
        x_curr = x[:, -1:]
        out = self.damping * torch.roll(
            x_curr, shifts=self.advection_shift, dims=-1
        ) + self.meridional_blend * torch.roll(x_curr, shifts=1, dims=-2)
        return out, self.output_coords(coords)

    @batch_func()
    def _default_generator(self, x: torch.Tensor, coords: CoordSystem):
        coords_out = coords.copy()
        coords_out["lead_time"] = coords["lead_time"][-1:]
        yield x[:, -1:], coords_out

        curr_x = x
        while True:
            curr_x, coords = self.front_hook(curr_x, coords)
            nxt, coords = self(curr_x, coords)
            nxt, coords = self.rear_hook(nxt, coords)
            curr_x = nxt
            yield nxt, coords.copy()

    def create_iterator(
        self, x: torch.Tensor, coords: CoordSystem
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        yield from self._default_generator(x, coords)


# =====================================================================
# Pytest Fixtures
# =====================================================================


@pytest.fixture
def coarse_domain_coords() -> CoordSystem:
    """Standard lightweight global coordinate grid (32 lats x 64 lons)."""
    return OrderedDict(
        {
            "lat": np.linspace(90.0, -90.0, 32),
            "lon": np.linspace(0.0, 360.0, 64, endpoint=False),
        }
    )


@pytest.fixture
def eval_variables() -> list[str]:
    """Core evaluation variables across all models."""
    return DEFAULT_EVAL_VARS.copy()


@pytest.fixture
def mock_persistence(coarse_domain_coords) -> MockPersistence:
    """Fixture returning an initialized MockPersistence instance."""
    return MockPersistence(domain_coords=coarse_domain_coords)


@pytest.fixture
def mock_graphcast(coarse_domain_coords) -> MockGraphCast:
    """Fixture returning an initialized MockGraphCast instance."""
    return MockGraphCast(domain_coords=coarse_domain_coords, add_tp06=False)


@pytest.fixture
def mock_sfno(coarse_domain_coords) -> MockSFNO:
    """Fixture returning an initialized MockSFNO instance."""
    return MockSFNO(domain_coords=coarse_domain_coords)


@pytest.fixture
def mock_pangu(coarse_domain_coords) -> MockPangu:
    """Fixture returning an initialized MockPangu instance."""
    return MockPangu(domain_coords=coarse_domain_coords)


@pytest.fixture
def mock_climax(coarse_domain_coords) -> MockClimaX:
    """Fixture returning an initialized MockClimaX instance."""
    return MockClimaX(domain_coords=coarse_domain_coords)


@pytest.fixture
def all_5_mock_models(
    mock_persistence, mock_graphcast, mock_sfno, mock_pangu, mock_climax
) -> dict[str, PrognosticModel]:
    """Dictionary mapping member names to all 5 PrognosticModel mocks."""
    return {
        "persistence": mock_persistence,
        "graphcast": mock_graphcast,
        "sfno": mock_sfno,
        "pangu": mock_pangu,
        "climax": mock_climax,
    }


@pytest.fixture
def sample_initial_conditions(
    coarse_domain_coords, eval_variables
) -> tuple[torch.Tensor, CoordSystem]:
    """Authentic deterministic Rossby wave initial state without pseudo-random noise.

    Returns
    -------
    tuple[torch.Tensor, CoordSystem]
        Tensor of shape (1, 2, n_vars, 32, 64) covering [-6h, 0h] and input coords.
    """
    lat = coarse_domain_coords["lat"]
    lon = coarse_domain_coords["lon"]
    n_vars = len(eval_variables)
    n_lat = len(lat)
    n_lon = len(lon)

    # Base atmospheric profile: 285 K surface temp
    x_0 = torch.full((1, 1, n_vars, n_lat, n_lon), 285.0, dtype=torch.float32)

    # Superpose deterministic physical synoptic wave (wavenumber 2)
    lon_t = torch.tensor(lon, dtype=torch.float32).view(1, 1, 1, 1, n_lon)
    lat_t = torch.tensor(lat, dtype=torch.float32).view(1, 1, 1, n_lat, 1)
    wave = 12.0 * torch.sin(torch.deg2rad(lon_t * 2)) * torch.cos(torch.deg2rad(lat_t))
    x_0 = x_0 + wave

    # Prior state at -6h is the upstream advected wave
    x_minus6 = torch.roll(x_0, shifts=-1, dims=-1)

    # Combined 2-step history input tensor
    x_in = torch.cat([x_minus6, x_0], dim=1)

    coords = OrderedDict(
        {
            "batch": np.empty(0),
            "lead_time": np.array([np.timedelta64(-6, "h"), np.timedelta64(0, "h")]),
            "variable": np.array(eval_variables),
            "lat": lat,
            "lon": lon,
        }
    )
    return x_in, coords
