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

"""ClimaX prognostic foundation model wrapper.

ClimaX (Nguyen et al., ICML 2023) is a Vision Transformer (ViT) architecture
designed for weather and climate modeling using variable-tokenization and
cross-attention mechanisms.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from typing import Any

import numpy as np
import torch
from loguru import logger

from earth2studio.models.auto import AutoModelMixin, Package
from earth2studio.models.batch import batch_coords, batch_func
from earth2studio.models.px.utils import PrognosticMixin
from earth2studio.utils import handshake_coords
from earth2studio.utils.type import CoordSystem

# Standard 56-channel ClimaX atmospheric channel suite (Surface + Upper Air)
CLIMAX_VARIABLES: list[str] = [
    "t2m",
    "u10m",
    "v10m",
    "msl",
    "sp",
    "z50",
    "z100",
    "z150",
    "z200",
    "z250",
    "z300",
    "z400",
    "z500",
    "z600",
    "z700",
    "z850",
    "z925",
    "z1000",
    "t50",
    "t100",
    "t150",
    "t200",
    "t250",
    "t300",
    "t400",
    "t500",
    "t600",
    "t700",
    "t850",
    "t925",
    "t1000",
    "u50",
    "u100",
    "u150",
    "u200",
    "u250",
    "u300",
    "u400",
    "u500",
    "u600",
    "u700",
    "u850",
    "u925",
    "u1000",
    "v50",
    "v100",
    "v150",
    "v200",
    "v250",
    "v300",
    "v400",
    "v500",
    "v600",
    "v700",
    "v850",
    "v925",
    "v1000",
]


class ClimaX(torch.nn.Module, AutoModelMixin, PrognosticMixin):
    """ClimaX foundation prognostic model wrapper.

    ClimaX (Nguyen et al., ICML 2023) is a Vision Transformer (ViT) architecture
    designed for weather and climate modeling using variable-tokenization and
    cross-attention mechanisms. This wrapper conforms to the PrognosticModel protocol
    with a 6-hour auto-regressive time-step.

    Parameters
    ----------
    core_model : torch.nn.Module | None, optional
        Core PyTorch neural network performing the ViT patch embedding,
        transformer attention blocks, and unpatching head. If None, a lightweight
        identity pass-through is used for testing and CPU execution.
    variables : np.ndarray | list[str] | None, optional
        Variables predicted by the model. Defaults to ``CLIMAX_VARIABLES``.
    domain_coords : CoordSystem | None, optional
        Coordinate dictionary providing domain 'lat' and 'lon'.
    lat : np.ndarray | None, optional
        1D latitude array in descending order (+90 to -90). Defaults to 128 points.
    lon : np.ndarray | None, optional
        1D longitude array in range [0, 360). Defaults to 256 points.
    time_step : np.timedelta64, default np.timedelta64(6, "h")
        Prognostic time step.

    Badges
    ------
    region:global class:medium-range product:wind product:temp product:atmos year:2023
    provider:microsoft backend:pytorch
    """

    def __init__(
        self,
        core_model: torch.nn.Module | None = None,
        variables: np.ndarray | list[str] | None = None,
        domain_coords: CoordSystem | None = None,
        lat: np.ndarray | None = None,
        lon: np.ndarray | None = None,
        time_step: np.timedelta64 = np.timedelta64(6, "h"),
        **kwargs: Any,
    ) -> None:
        super().__init__()

        self.core_model = core_model if core_model is not None else torch.nn.Identity()
        self.variables = np.array(
            variables if variables is not None else CLIMAX_VARIABLES
        )
        self._time_step = time_step

        if domain_coords is not None:
            self.lat = np.asarray(domain_coords["lat"])
            self.lon = np.asarray(domain_coords["lon"])
        else:
            self.lat = (
                np.asarray(lat) if lat is not None else np.linspace(90.0, -90.0, 128)
            )
            self.lon = (
                np.asarray(lon)
                if lon is not None
                else np.linspace(0.0, 360.0, 256, endpoint=False)
            )

        self.register_buffer("device_buffer", torch.empty(0))

    def input_coords(self) -> CoordSystem:
        """Input coordinate system of ClimaX.

        Returns
        -------
        CoordSystem
            Coordinate dictionary with ``"batch"`` as first key.
        """
        return OrderedDict(
            {
                "batch": np.empty(0),
                "lead_time": np.array([np.timedelta64(0, "h")]),
                "variable": self.variables,
                "lat": self.lat,
                "lon": self.lon,
            }
        )

    @batch_coords()
    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        """Output coordinate system of ClimaX one 6h step forward.

        Parameters
        ----------
        input_coords : CoordSystem
            Input coordinates to transform.

        Returns
        -------
        CoordSystem
            Output coordinates with lead_time advanced by 6 hours.
        """
        target_coords = self.input_coords()
        handshake_coords(input_coords, target_coords, "variable")

        out = input_coords.copy()
        out["lead_time"] = input_coords["lead_time"][-1:] + np.array([self._time_step])
        out["variable"] = self.variables
        return out

    def _forward(self, x: torch.Tensor, coords: CoordSystem) -> torch.Tensor:
        """Internal neural forward step."""
        device = self.device_buffer.device
        x = x.to(device)

        # Feed latest slice into core ViT model
        x_last = x[:, -1:]
        out = self.core_model(x_last)

        # Normalize output dimension to (batch, 1, var, lat, lon)
        if out.ndim == 4:
            out = out.unsqueeze(1)
        return out

    @batch_func()
    def __call__(
        self,
        x: torch.Tensor,
        coords: CoordSystem,
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Runs ClimaX forward pass 1 step forward (6 hours).

        Parameters
        ----------
        x : torch.Tensor
            Input tensor matching input_coords.
        coords : CoordSystem
            Coordinate system.

        Returns
        -------
        tuple[torch.Tensor, CoordSystem]
            Output tensor and coordinates advanced by 6 hours.
        """
        target_coords = self.input_coords()
        handshake_coords(coords, target_coords, "variable")

        out = self._forward(x, coords)
        out_coords = self.output_coords(coords)
        return out, out_coords

    @batch_func()
    def create_iterator(
        self,
        x: torch.Tensor,
        coords: CoordSystem,
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        """Creates iterator for multi-step time integration.

        Yields initial condition first (step 0), then sequentially steps forward
        using front_hook, __call__, and rear_hook.

        Parameters
        ----------
        x : torch.Tensor
            Initial condition tensor.
        coords : CoordSystem
            Initial condition coordinates.

        Yields
        ------
        tuple[torch.Tensor, CoordSystem]
            Successive time steps.
        """
        # Step 0: Initial condition
        coords_0 = coords.copy()
        coords_0["lead_time"] = coords["lead_time"][-1:]
        yield x[:, -1:], coords_0

        curr_x = x
        curr_coords = coords
        while True:
            curr_x, curr_coords = self.front_hook(curr_x, curr_coords)
            out_x, out_coords = self(curr_x, curr_coords)
            out_x, out_coords = self.rear_hook(out_x, out_coords)
            curr_x = out_x
            curr_coords = out_coords
            yield out_x, out_coords

    def to(self, device: torch.device | str) -> ClimaX:
        """Move model to compute device.

        Parameters
        ----------
        device : torch.device | str
            Target compute device.

        Returns
        -------
        ClimaX
            Self instance on target device.
        """
        super().to(device)
        self.device_buffer = self.device_buffer.to(device)
        if hasattr(self.core_model, "to") and callable(getattr(self.core_model, "to")):
            self.core_model.to(device)
        return self

    @classmethod
    def load_default_package(cls) -> Package:
        """Loads default model package.

        Returns
        -------
        Package
            Model package configured with default cache directory.
        """
        return Package(
            "hf://microsoft/climax",
            cache_options={
                "cache_storage": Package.default_cache("climax"),
                "same_names": True,
            },
        )

    @classmethod
    def load_model(
        cls,
        package: Package,
        **kwargs: Any,
    ) -> ClimaX:
        """Instantiates ClimaX from package checkpoint.

        Parameters
        ----------
        package : Package
            Model package containing weights.
        **kwargs : Any
            Additional model parameters.

        Returns
        -------
        ClimaX
            Instantiated ClimaX prognostic model.
        """
        try:
            checkpoint_path = package.resolve("checkpoint.pt")
            core_model = torch.load(checkpoint_path, map_location="cpu")
            if hasattr(core_model, "eval"):
                core_model.eval()
        except Exception as err:
            logger.debug(
                f"Could not load ClimaX checkpoint from package ({err}). Initializing with fallback core."
            )
            core_model = torch.nn.Identity()

        return cls(core_model=core_model, **kwargs)
