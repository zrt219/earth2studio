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

"""Extreme Dependency Index (EDI) and Symmetric Extremal Dependence Index (SEDI).

Author: Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
References:
    Stephenson, D. B., et al. (2008). Extreme Dependence Index.
    Ferro, C. A., & Stephenson, D. B. (2011). Extremal Dependence Indices.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
import torch

from earth2studio.statistics.utils import _broadcast_weights
from earth2studio.utils.coords import handshake_dim
from earth2studio.utils.type import CoordSystem


def compute_contingency_table(
    forecast: torch.Tensor,
    observation: torch.Tensor,
    threshold: float,
    reduction_dims: list[int],
    weights: torch.Tensor | None = None,
    is_upper: bool = True,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Compute area-weighted 2x2 contingency table for extreme events.

    Parameters
    ----------
    forecast : torch.Tensor
        Forecast tensor.
    observation : torch.Tensor
        Verifying observation tensor.
    threshold : float
        Physical threshold value.
    reduction_dims : list[int]
        Axes over which to accumulate contingency counts.
    weights : torch.Tensor | None, default None
        Broadcasting area weights matching reduction dimensions.
    is_upper : bool, default True
        If True, event is x >= threshold (wind, precip); if False, x <= threshold (MSLP depression).

    Returns
    -------
    tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]
        Hits (a), False Alarms (b), Misses (c), Correct Negatives (d).
    """
    if is_upper:
        f_event = (forecast >= threshold).to(torch.float32)
        o_event = (observation >= threshold).to(torch.float32)
    else:
        f_event = (forecast <= threshold).to(torch.float32)
        o_event = (observation <= threshold).to(torch.float32)

    hits_mask = f_event * o_event
    fa_mask = f_event * (1.0 - o_event)
    miss_mask = (1.0 - f_event) * o_event
    cn_mask = (1.0 - f_event) * (1.0 - o_event)

    if weights is not None:
        hits_mask = hits_mask * weights
        fa_mask = fa_mask * weights
        miss_mask = miss_mask * weights
        cn_mask = cn_mask * weights

    if reduction_dims:
        a = torch.sum(hits_mask, dim=reduction_dims)
        b = torch.sum(fa_mask, dim=reduction_dims)
        c = torch.sum(miss_mask, dim=reduction_dims)
        d = torch.sum(cn_mask, dim=reduction_dims)
    else:
        a = hits_mask
        b = fa_mask
        c = miss_mask
        d = cn_mask

    return a, b, c, d


def compute_rates(
    a: torch.Tensor,
    b: torch.Tensor,
    c: torch.Tensor,
    d: torch.Tensor,
    epsilon: float = 1e-7,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Calculate clamped Hit Rate (H) and False Alarm Rate (F) from contingency table."""
    event_total = a + c
    nonevent_total = b + d

    # Handle domain with 0 events or 0 non-events
    h_raw = torch.where(
        event_total > 0, a / torch.clamp(event_total, min=1e-12), float("nan")
    )
    f_raw = torch.where(
        nonevent_total > 0, b / torch.clamp(nonevent_total, min=1e-12), float("nan")
    )

    H = torch.clamp(h_raw, min=epsilon, max=1.0 - epsilon)
    F = torch.clamp(f_raw, min=epsilon, max=1.0 - epsilon)
    return H, F


def compute_edi(
    forecast: torch.Tensor,
    observation: torch.Tensor,
    threshold: float,
    reduction_dims: list[int] | None = None,
    weights: torch.Tensor | None = None,
    is_upper: bool = True,
    epsilon: float = 1e-7,
) -> torch.Tensor:
    """Compute Extreme Dependency Index (EDI).

    EDI = (log F - log H) / (log F + log H)
    """
    dims = reduction_dims if reduction_dims is not None else []
    a, b, c, d = compute_contingency_table(
        forecast, observation, threshold, dims, weights=weights, is_upper=is_upper
    )
    H, F = compute_rates(a, b, c, d, epsilon=epsilon)

    log_H = torch.log(H)
    log_F = torch.log(F)
    edi_val = (log_F - log_H) / (log_F + log_H)
    # Perfect forecast H=1, F=0 -> EDI=1.0; random H=F -> EDI=0.0; inverse H=0, F=1 -> EDI=-1.0
    return torch.clamp(edi_val, min=-1.0, max=1.0)


def compute_sedi(
    forecast: torch.Tensor,
    observation: torch.Tensor,
    threshold: float,
    reduction_dims: list[int] | None = None,
    weights: torch.Tensor | None = None,
    is_upper: bool = True,
    epsilon: float = 1e-7,
) -> torch.Tensor:
    """Compute Symmetric Extremal Dependence Index (SEDI).

    SEDI = (log F - log H - log(1-F) + log(1-H)) / (log F + log H + log(1-F) + log(1-H))
    """
    dims = reduction_dims if reduction_dims is not None else []
    a, b, c, d = compute_contingency_table(
        forecast, observation, threshold, dims, weights=weights, is_upper=is_upper
    )
    H, F = compute_rates(a, b, c, d, epsilon=epsilon)

    log_H = torch.log(H)
    log_F = torch.log(F)
    log_1_H = torch.log(1.0 - H)
    log_1_F = torch.log(1.0 - F)

    num = log_F - log_H - log_1_F + log_1_H
    den = log_F + log_H + log_1_F + log_1_H
    sedi_val = torch.where(den != 0, num / den, torch.zeros_like(num))
    return torch.clamp(sedi_val, min=-1.0, max=1.0)


class edi:
    """Extreme Dependency Index (EDI) for rare event threshold verification.

    EDI provides a base-rate invariant verification metric that does not degenerate to 0
    as the event frequency approaches 0:
        EDI = (ln F - ln H) / (ln F + ln H)

    Parameters
    ----------
    thresholds : float | Sequence[float]
        Physical threshold value(s) (e.g. 20.0 for wind > 20 m/s).
    reduction_dimensions : list[str] | None, default ['lat', 'lon']
        Spatial dimensions over which to accumulate contingency table.
    weights : torch.Tensor | None, default None
        Area weights matching reduction dimensions.
    ensemble_dimension : str | None, default None
        If provided, computes ensemble exceedance probability before thresholding.
    probability_threshold : float, default 0.5
        Decision cutoff probability when evaluating ensemble forecasts.
    tail : str, default "upper"
        Threshold direction: "upper" (>= threshold) or "lower" (<= threshold).
    epsilon : float, default 1e-7
        Clamping epsilon for numerical stability of logarithms.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        """Route to functional execution if first argument is a torch.Tensor."""
        if args and isinstance(args[0], torch.Tensor):
            x = args[0]
            if len(args) > 1 and isinstance(args[1], torch.Tensor):
                y = args[1]
                x_coords = kwargs.get("x_coords")
                y_coords = kwargs.get("y_coords")
            elif len(args) > 2 and isinstance(args[2], torch.Tensor):
                x_coords = args[1]
                y = args[2]
                y_coords = args[3] if len(args) > 3 else kwargs.get("y_coords")
            else:
                x_coords = args[1] if len(args) > 1 else kwargs.get("x_coords")
                y = args[2] if len(args) > 2 else kwargs.get("y")
                y_coords = args[3] if len(args) > 3 else kwargs.get("y_coords")
            threshold = kwargs.get("threshold", kwargs.get("thresholds", 20.0))
            is_upper = kwargs.get("tail", "upper").lower() == "upper"
            red_dims = kwargs.get("reduction_dimensions", ["lat", "lon"])
            weights = kwargs.get("weights", None)

            if isinstance(threshold, (list, tuple, np.ndarray)):
                threshold = float(threshold[0])
            else:
                threshold = float(threshold)

            dims = []
            if x_coords is not None and red_dims is not None:
                dims.extend(
                    list(x_coords).index(rd) for rd in red_dims if rd in x_coords
                )

            res = compute_edi(
                x,
                y,
                threshold=threshold,
                reduction_dims=dims,
                weights=weights,
                is_upper=is_upper,
            )
            out_coords = y_coords.copy() if y_coords is not None else {}
            if red_dims:
                for rd in red_dims:
                    out_coords.pop(rd, None)
            return res, out_coords

        return super().__new__(cls)

    def __init__(
        self,
        thresholds: float | Sequence[float] | None = None,
        reduction_dimensions: list[str] | None = None,
        weights: torch.Tensor | None = None,
        ensemble_dimension: str | None = None,
        probability_threshold: float = 0.5,
        tail: str = "upper",
        epsilon: float = 1e-7,
        threshold: float | Sequence[float] | None = None,
    ):
        raw_thresh = threshold if threshold is not None else thresholds
        if raw_thresh is None:
            raw_thresh = 20.0

        if isinstance(raw_thresh, (int, float)):
            self.thresholds = [float(raw_thresh)]
        else:
            self.thresholds = [float(t) for t in raw_thresh]

        self._reduction_dimensions = (
            reduction_dimensions if reduction_dimensions is not None else ["lat", "lon"]
        )
        self.weights = weights
        self.ensemble_dimension = ensemble_dimension
        self.probability_threshold = probability_threshold
        self.tail = tail.lower()
        if self.tail not in ["upper", "lower"]:
            raise ValueError(f"tail must be 'upper' or 'lower', got {tail}")
        self.epsilon = epsilon

    def __str__(self) -> str:
        return "_".join(self.reduction_dimensions + ["edi"])

    @property
    def reduction_dimensions(self) -> list[str]:
        return self._reduction_dimensions

    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        """Output coordinate system with reduced dimensions removed and thresholds coordinate added."""
        output_coords = input_coords.copy()
        if self.ensemble_dimension and self.ensemble_dimension in output_coords:
            output_coords.pop(self.ensemble_dimension)

        for dimension in self.reduction_dimensions:
            handshake_dim(input_coords, dimension)
            output_coords.pop(dimension)

        if len(self.thresholds) > 1:
            output_coords["threshold"] = np.asarray(self.thresholds, dtype=np.float32)

        return output_coords

    def _get_reduction_dims_and_weights(
        self, coords: CoordSystem, device: torch.device | None = None
    ) -> tuple[list[int], torch.Tensor | None]:
        """Compute reduction dimension indices and broadcast weights matching coords."""
        dims = [list(coords).index(rd) for rd in self._reduction_dimensions]
        w = None
        if self.weights is not None:
            w = _broadcast_weights(self.weights, self._reduction_dimensions, coords)
            if device is not None:
                w = w.to(device)
        return dims, w

    def ensemble_metric(
        self,
        x: torch.Tensor,
        coords: CoordSystem,
        threshold: float | None = None,
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Compute binary exceedance event indicator from ensemble forecast."""
        if not self.ensemble_dimension or self.ensemble_dimension not in coords:
            return x, coords
        t = threshold if threshold is not None else self.thresholds[0]
        ens_dim = list(coords).index(self.ensemble_dimension)
        if self.tail == "upper":
            prob = torch.mean((x >= t).to(torch.float32), dim=ens_dim)
        else:
            prob = torch.mean((x <= t).to(torch.float32), dim=ens_dim)
        target_x = (prob >= self.probability_threshold).to(torch.float32)
        curr_coords = coords.copy()
        curr_coords.pop(self.ensemble_dimension)
        return target_x, curr_coords

    def _evaluate_threshold(
        self,
        x: torch.Tensor,
        x_coords: CoordSystem,
        y: torch.Tensor,
        y_coords: CoordSystem,
        threshold: float,
        metric_func: Any,
    ) -> torch.Tensor:
        """Evaluate single threshold."""
        target_x = x
        curr_coords = x_coords.copy()
        if self.ensemble_dimension and self.ensemble_dimension in curr_coords:
            target_x, curr_coords = self.ensemble_metric(
                target_x, curr_coords, threshold=threshold
            )
            eff_thresh = 0.5
            eff_upper = True
        else:
            eff_thresh = threshold
            eff_upper = self.tail == "upper"

        dims, w = self._get_reduction_dims_and_weights(curr_coords, device=x.device)

        return metric_func(
            target_x,
            y,
            threshold=eff_thresh,
            reduction_dims=dims,
            weights=w,
            is_upper=eff_upper,
            epsilon=self.epsilon,
        )

    def __call__(
        self,
        x: torch.Tensor,
        x_coords: CoordSystem,
        y: torch.Tensor,
        y_coords: CoordSystem,
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Apply EDI metric to data x and y."""
        for rd in self._reduction_dimensions:
            handshake_dim(x_coords, rd)
            handshake_dim(y_coords, rd)

        output_coords = self.output_coords(x_coords)

        res_list = [
            self._evaluate_threshold(x, x_coords, y, y_coords, t, compute_edi)
            for t in self.thresholds
        ]

        if len(self.thresholds) == 1:
            return res_list[0], output_coords
        else:
            return torch.stack(res_list, dim=-1), output_coords


class sedi(edi):
    """Symmetric Extremal Dependence Index (SEDI) for rare event threshold verification.

    SEDI provides reflection symmetry with respect to event/non-event transposition:
        SEDI = (ln F - ln H - ln(1-F) + ln(1-H)) / (ln F + ln H + ln(1-F) + ln(1-H))
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        """Route to functional execution if first argument is a torch.Tensor."""
        if args and isinstance(args[0], torch.Tensor):
            x = args[0]
            if len(args) > 1 and isinstance(args[1], torch.Tensor):
                y = args[1]
                x_coords = kwargs.get("x_coords")
                y_coords = kwargs.get("y_coords")
            elif len(args) > 2 and isinstance(args[2], torch.Tensor):
                x_coords = args[1]
                y = args[2]
                y_coords = args[3] if len(args) > 3 else kwargs.get("y_coords")
            else:
                x_coords = args[1] if len(args) > 1 else kwargs.get("x_coords")
                y = args[2] if len(args) > 2 else kwargs.get("y")
                y_coords = args[3] if len(args) > 3 else kwargs.get("y_coords")
            threshold = kwargs.get("threshold", kwargs.get("thresholds", 20.0))
            is_upper = kwargs.get("tail", "upper").lower() == "upper"
            red_dims = kwargs.get("reduction_dimensions", ["lat", "lon"])
            weights = kwargs.get("weights", None)

            if isinstance(threshold, (list, tuple, np.ndarray)):
                threshold = float(threshold[0])
            else:
                threshold = float(threshold)

            dims = []
            if x_coords is not None and red_dims is not None:
                dims.extend(
                    list(x_coords).index(rd) for rd in red_dims if rd in x_coords
                )

            res = compute_sedi(
                x,
                y,
                threshold=threshold,
                reduction_dims=dims,
                weights=weights,
                is_upper=is_upper,
            )
            out_coords = y_coords.copy() if y_coords is not None else {}
            if red_dims:
                for rd in red_dims:
                    out_coords.pop(rd, None)
            return res, out_coords

        return super().__new__(cls)

    def __str__(self) -> str:
        return "_".join(self.reduction_dimensions + ["sedi"])

    def __call__(
        self,
        x: torch.Tensor,
        x_coords: CoordSystem,
        y: torch.Tensor,
        y_coords: CoordSystem,
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Apply SEDI metric to data x and y."""
        for rd in self._reduction_dimensions:
            handshake_dim(x_coords, rd)
            handshake_dim(y_coords, rd)

        output_coords = self.output_coords(x_coords)

        res_list = [
            self._evaluate_threshold(x, x_coords, y, y_coords, t, compute_sedi)
            for t in self.thresholds
        ]

        if len(self.thresholds) == 1:
            return res_list[0], output_coords
        else:
            return torch.stack(res_list, dim=-1), output_coords
