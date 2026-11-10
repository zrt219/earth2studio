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

"""Multi-Model Prognostic Ensemble framework.

Combines heterogeneous AI-NWP architectures (e.g. GraphCast, FourCastNet v2 / SFNO,
Pangu-Weather, ClimaX, and Persistence) into a synchronized ensemble.
Maintains decoupled, autonomous trajectory evolution for each member to prevent
dynamical shock from cross-model state averaging, and projects fields onto
common evaluation coordinates and reduction modes (stack, mean, weighted_mean).
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterator
from typing import Literal

import numpy as np
import torch
import torch.nn.functional as F

from earth2studio.models.batch import batch_coords, batch_func
from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.utils import PrognosticMixin
from earth2studio.utils.type import CoordSystem

CORE_EVAL_VARIABLES: list[str] = [
    "t2m",
    "u10m",
    "v10m",
    "z500",
    "t850",
    "msl",
]


class MultiModelEnsemble(torch.nn.Module, PrognosticMixin):
    """Multi-Model Prognostic Ensemble framework combining heterogeneous NWP architectures.

    Orchestrates autonomous, decoupled auto-regressive trajectory evolution across
    diverse weather models (e.g. GraphCast, FourCastNet v2 / SFNO, Pangu-Weather,
    ClimaX, and Persistence). Each member integrates forward in its native latent
    manifold on a synchronized 6-hour time-step, avoiding dynamical shock from
    cross-model state averaging. Output slices are projected onto common target
    coordinates (variables and spatial grid) and reduced via stacking or weighting.

    Parameters
    ----------
    models : dict[str, PrognosticModel]
        Dictionary mapping member identifiers to PrognosticModel instances.
        Example: ``{"graphcast": m1, "sfno": m2, "pangu": m3, "climax": m4, "persistence": m5}``.
    weights : dict[str, float] | None, optional
        Ensemble member weights for ``reduction="weighted_mean"``. If None, uniform
        weights are used. If weights are provided, they are normalized to sum to 1.0.
    reduction : Literal["stack", "mean", "weighted_mean"], default "stack"
        Reduction mode:
        - ``"stack"``: stacks member forecasts along a new ``"ensemble"`` coordinate dimension.
        - ``"mean"``: computes the unweighted arithmetic ensemble mean across members.
        - ``"weighted_mean"``: computes the convex weighted combination of member forecasts.
    target_coords : CoordSystem | None, optional
        Target evaluation coordinates defining variable channels, latitude, and longitude.
        If None, variables default to ``CORE_EVAL_VARIABLES`` and spatial coordinates are
        derived from member models or set to a global 0.25-degree grid.
    regrid_method : Literal["bilinear", "nearest"], default "bilinear"
        Spatial interpolation method when regridding member outputs to target grid.

    Badges
    ------
    region:global class:medium-range product:ensemble product:atmos provider:zhane-daye backend:pytorch
    """

    def __init__(
        self,
        models: dict[str, PrognosticModel],
        weights: dict[str, float] | None = None,
        reduction: Literal["stack", "mean", "weighted_mean"] = "stack",
        target_coords: CoordSystem | None = None,
        regrid_method: Literal["bilinear", "nearest"] = "bilinear",
    ) -> None:
        super().__init__()

        if not models:
            raise ValueError("models dictionary cannot be empty.")

        if reduction not in ("stack", "mean", "weighted_mean"):
            raise ValueError(
                f"Invalid reduction '{reduction}'. Expected 'stack', 'mean', or 'weighted_mean'."
            )

        self.member_names = list(models.keys())
        if all(isinstance(m, torch.nn.Module) for m in models.values()):
            self.models: dict[str, PrognosticModel] = torch.nn.ModuleDict(models)  # type: ignore[assignment]
        else:
            self.models = models

        self.reduction = reduction
        self.regrid_method = regrid_method
        self._time_step = np.timedelta64(6, "h")

        # Determine target coordinates (variables, lat, lon)
        if target_coords is not None:
            if "variable" in target_coords:
                self._target_variables = np.asarray(target_coords["variable"])
            else:
                self._target_variables = np.array(CORE_EVAL_VARIABLES)

            if "lat" in target_coords and "lon" in target_coords:
                self._target_lat = np.asarray(target_coords["lat"])
                self._target_lon = np.asarray(target_coords["lon"])
            else:
                # Fall back to first model grid if present
                first_model = next(iter(models.values()))
                first_coords = first_model.input_coords()
                if "lat" in first_coords and "lon" in first_coords:
                    self._target_lat = np.asarray(first_coords["lat"])
                    self._target_lon = np.asarray(first_coords["lon"])
                else:
                    self._target_lat = np.linspace(90.0, -90.0, 721)
                    self._target_lon = np.linspace(0.0, 360.0, 1440, endpoint=False)
        else:
            self._target_variables = np.array(CORE_EVAL_VARIABLES)
            first_model = next(iter(models.values()))
            first_coords = first_model.input_coords()
            if "lat" in first_coords and "lon" in first_coords:
                self._target_lat = np.asarray(first_coords["lat"])
                self._target_lon = np.asarray(first_coords["lon"])
            else:
                self._target_lat = np.linspace(90.0, -90.0, 721)
                self._target_lon = np.linspace(0.0, 360.0, 1440, endpoint=False)

        # Accommodate maximum history across member models (e.g. 2 for GraphCast, 1 for others)
        self._max_history = max(
            len(m.input_coords()["lead_time"]) for m in models.values()
        )
        self._input_lead_times = np.array(
            [np.timedelta64(-6 * i, "h") for i in reversed(range(self._max_history))]
        )

        # Process and normalize weights
        self.weights = self._normalize_weights(weights)

    def _normalize_weights(self, weights: dict[str, float] | None) -> dict[str, float]:
        """Normalize ensemble weights into a convex combination summing to 1.0."""
        n_members = len(self.member_names)
        if weights is None:
            return {name: 1.0 / n_members for name in self.member_names}

        # Validate provided weights
        for name in self.member_names:
            if name not in weights:
                raise KeyError(
                    f"Weight for ensemble member '{name}' missing from provided weights."
                )

        raw_weights = [weights[name] for name in self.member_names]
        if any(w <= 0.0 for w in raw_weights):
            raise ValueError("Ensemble weights must be strictly positive scalars.")

        total_weight = sum(raw_weights)
        if total_weight <= 0.0:
            raise ValueError("Sum of ensemble weights must be strictly positive.")

        norm_weights = {
            name: float(weights[name]) / total_weight for name in self.member_names
        }
        return norm_weights

    def input_coords(self) -> CoordSystem:
        """Input coordinate system required by the ensemble.

        Returns
        -------
        CoordSystem
            Coordinate system dictionary with ``"batch"`` as first dimension.
        """
        return OrderedDict(
            {
                "batch": np.empty(0),
                "lead_time": self._input_lead_times,
                "variable": self._target_variables,
                "lat": self._target_lat,
                "lon": self._target_lon,
            }
        )

    @batch_coords()
    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        """Output coordinate system produced by the ensemble.

        Parameters
        ----------
        input_coords : CoordSystem
            Input coordinate system to transform.

        Returns
        -------
        CoordSystem
            Output coordinate system. If ``reduction="stack"``, includes the ``"ensemble"``
            coordinate dimension. If ``reduction="mean"`` or ``"weighted_mean"``, the ensemble
            dimension is reduced.
        """
        out = OrderedDict()
        out["batch"] = input_coords["batch"]
        if self.reduction == "stack":
            out["ensemble"] = np.array(self.member_names)
        out["lead_time"] = input_coords["lead_time"][-1:] + np.array([self._time_step])
        out["variable"] = self._target_variables
        out["lat"] = self._target_lat
        out["lon"] = self._target_lon
        return out

    def _prepare_member_input(
        self, x: torch.Tensor, coords: CoordSystem, member: PrognosticModel
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Slice appropriate history horizon and adapt coordinates for an ensemble member."""
        m_in_coords = member.input_coords()
        m_history = len(m_in_coords["lead_time"])

        # History slicing: accommodate 1-step vs 2-step history
        if x.shape[1] < m_history:
            raise ValueError(
                f"Model requires {m_history} lead-time slices, but input only has {x.shape[1]}."
            )

        m_x = x[:, -m_history:]
        m_coords = coords.copy()
        m_coords["lead_time"] = coords["lead_time"][-m_history:]

        # Variable alignment: if member expects specific variables available in coords
        m_vars = list(m_in_coords["variable"])
        curr_vars = list(coords["variable"])
        if m_vars != curr_vars and all(v in curr_vars for v in m_vars):
            var_idx = [curr_vars.index(v) for v in m_vars]
            m_x = m_x[:, :, var_idx]
            m_coords["variable"] = np.array(m_vars)

        # Spatial grid adaptation if member native grid differs from input
        if "lat" in m_in_coords and "lon" in m_in_coords:
            m_lat = np.asarray(m_in_coords["lat"])
            m_lon = np.asarray(m_in_coords["lon"])
            c_lat = np.asarray(coords["lat"])
            c_lon = np.asarray(coords["lon"])
            if (
                len(c_lat) != len(m_lat)
                or len(c_lon) != len(m_lon)
                or not (np.allclose(c_lat, m_lat) and np.allclose(c_lon, m_lon))
            ):
                m_x = self._regrid_spatial(m_x, c_lat, c_lon, m_lat, m_lon)
                m_coords["lat"] = m_lat
                m_coords["lon"] = m_lon

        return m_x, m_coords

    def _project_member_output(
        self,
        y: torch.Tensor,
        coords: CoordSystem,
        member_name: str,
    ) -> torch.Tensor:
        """Project member output tensor onto target variables and spatial grid."""
        # 1. Variable gathering to target evaluation channels
        y_vars = list(coords["variable"])
        for req_var in self._target_variables:
            if req_var not in y_vars:
                raise KeyError(
                    f"Member '{member_name}' does not provide required target variable '{req_var}'. "
                    f"Available variables: {y_vars}"
                )

        target_idx = [y_vars.index(v) for v in self._target_variables]
        y_proj = y[:, :, target_idx]

        # 2. Spatial bilinear regridding if member grid differs from target grid
        m_lat = np.asarray(coords["lat"])
        m_lon = np.asarray(coords["lon"])
        if (
            len(m_lat) != len(self._target_lat)
            or len(m_lon) != len(self._target_lon)
            or not (
                np.allclose(m_lat, self._target_lat)
                and np.allclose(m_lon, self._target_lon)
            )
        ):
            y_proj = self._regrid_spatial(
                y_proj, m_lat, m_lon, self._target_lat, self._target_lon
            )

        return y_proj

    def _regrid_spatial(
        self,
        tensor: torch.Tensor,
        src_lat: np.ndarray,
        src_lon: np.ndarray,
        tgt_lat: np.ndarray,
        tgt_lon: np.ndarray,
    ) -> torch.Tensor:
        """Bilinear spatial interpolation preserving latitude orientation."""
        # Check if latitudes are ascending; if so, invert to descending atmospheric convention
        val = tensor
        if src_lat[0] < src_lat[-1]:
            val = torch.flip(val, dims=[-2])

        orig_shape = val.shape
        # Flatten leading dimensions into single batch dimension: (N, 1, H, W)
        flat = val.reshape(-1, 1, orig_shape[-2], orig_shape[-1])
        regridded = F.interpolate(
            flat,
            size=(len(tgt_lat), len(tgt_lon)),
            mode="bilinear" if self.regrid_method == "bilinear" else "nearest",
            align_corners=True if self.regrid_method == "bilinear" else None,
        )
        out = regridded.reshape(*orig_shape[:-2], len(tgt_lat), len(tgt_lon))

        # If target latitude was ascending, adjust orientation
        if tgt_lat[0] < tgt_lat[-1]:
            out = torch.flip(out, dims=[-2])

        return out

    def _apply_reduction(self, member_outputs: list[torch.Tensor]) -> torch.Tensor:
        """Apply ensemble reduction across member output tensors."""
        if self.reduction == "stack":
            # Stack along ensemble dimension: (batch, ensemble, lead_time, var, lat, lon)
            return torch.stack(member_outputs, dim=1)

        if self.reduction == "mean":
            # Arithmetic mean across members: (batch, lead_time, var, lat, lon)
            stacked = torch.stack(member_outputs, dim=0)
            return torch.mean(stacked, dim=0)

        if self.reduction == "weighted_mean":
            # Convex weighted sum across members: (batch, lead_time, var, lat, lon)
            weights_list = [self.weights[name] for name in self.member_names]
            w_tensor = torch.tensor(
                weights_list,
                dtype=member_outputs[0].dtype,
                device=member_outputs[0].device,
            ).view(-1, 1, 1, 1, 1, 1)
            stacked = torch.stack(
                member_outputs, dim=0
            )  # (M, batch, lead_time, var, lat, lon)
            return torch.sum(w_tensor * stacked, dim=0)

        raise ValueError(f"Unsupported reduction '{self.reduction}'.")

    @batch_func()
    def __call__(
        self,
        x: torch.Tensor,
        coords: CoordSystem,
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Runs all ensemble members 1 step forward in time and applies the reduction.

        Parameters
        ----------
        x : torch.Tensor
            Input tensor matching ensemble input coordinates.
        coords : CoordSystem
            Input coordinate system.

        Returns
        -------
        tuple[torch.Tensor, CoordSystem]
            Reduced ensemble output tensor and coordinates advanced by 6 hours.
        """
        projected_outputs: list[torch.Tensor] = []
        for name in self.member_names:
            model = self.models[name]
            m_x, m_coords = self._prepare_member_input(x, coords, model)
            out_m, coords_m = model(m_x, m_coords)
            proj_m = self._project_member_output(out_m, coords_m, name)
            projected_outputs.append(proj_m)

        reduced = self._apply_reduction(projected_outputs)
        out_coords = self.output_coords(coords)
        return reduced, out_coords

    @batch_func()
    def create_iterator(
        self,
        x: torch.Tensor,
        coords: CoordSystem,
    ) -> Iterator[tuple[torch.Tensor, CoordSystem]]:
        """Creates an iterator performing multi-model time integration.

        Each member model executes its own autonomous auto-regressive trajectory
        via its native ``create_iterator``, preventing cross-model covariate shock.
        At each lead-time step, outputs are gathered, projected to target coordinates,
        and reduced.

        Parameters
        ----------
        x : torch.Tensor
            Initial condition tensor (step 0).
        coords : CoordSystem
            Initial condition coordinates.

        Yields
        ------
        tuple[torch.Tensor, CoordSystem]
            Successive forecast lead times from step 0 (initial condition) onward.
        """
        # 1. Instantiate native iterators for each member model
        member_iterators: dict[str, Iterator[tuple[torch.Tensor, CoordSystem]]] = {}
        for name in self.member_names:
            model = self.models[name]
            m_x, m_coords = self._prepare_member_input(x, coords, model)
            member_iterators[name] = model.create_iterator(m_x, m_coords)

        # 2. Step 0: Initial condition projection and yield
        step0_outputs: list[torch.Tensor] = []
        for name in self.member_names:
            s0_raw, c0_raw = next(member_iterators[name])
            s0_proj = self._project_member_output(s0_raw, c0_raw, name)
            step0_outputs.append(s0_proj)

        step0_reduced = self._apply_reduction(step0_outputs)

        # Build step 0 coordinates
        step0_coords = OrderedDict()
        step0_coords["batch"] = coords["batch"]
        if self.reduction == "stack":
            step0_coords["ensemble"] = np.array(self.member_names)
        step0_coords["lead_time"] = coords["lead_time"][-1:]
        step0_coords["variable"] = self._target_variables
        step0_coords["lat"] = self._target_lat
        step0_coords["lon"] = self._target_lon

        yield step0_reduced, step0_coords

        # 3. Successive auto-regressive forecast lead-times (6h, 12h, 18h, ...)
        while True:
            step_k_outputs: list[torch.Tensor] = []
            lead_time_k: np.ndarray | None = None

            for name in self.member_names:
                sk_raw, ck_raw = next(member_iterators[name])
                sk_proj = self._project_member_output(sk_raw, ck_raw, name)
                step_k_outputs.append(sk_proj)
                if lead_time_k is None:
                    lead_time_k = ck_raw["lead_time"]

            step_k_reduced = self._apply_reduction(step_k_outputs)

            coords_k = OrderedDict()
            coords_k["batch"] = coords["batch"]
            if self.reduction == "stack":
                coords_k["ensemble"] = np.array(self.member_names)
            coords_k["lead_time"] = (
                lead_time_k
                if lead_time_k is not None
                else coords["lead_time"][-1:] + np.array([self._time_step])
            )
            coords_k["variable"] = self._target_variables
            coords_k["lat"] = self._target_lat
            coords_k["lon"] = self._target_lon

            yield step_k_reduced, coords_k

    def to(self, device: torch.device | str) -> MultiModelEnsemble:
        """Moves all member models to the target compute device.

        Parameters
        ----------
        device : torch.device | str
            Target compute device.

        Returns
        -------
        MultiModelEnsemble
            Self instance on target device.
        """
        super().to(device)
        for model in self.models.values():
            if hasattr(model, "to") and callable(getattr(model, "to")):
                model.to(device)
        return self
