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

"""Continuous Ranked Probability Score (CRPS).

Author: Zhane Daye (SAR & Earth System Engineering; zhanedaye@umattr.ca)
Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
"""

from __future__ import annotations

from typing import Any

import torch

from earth2studio.statistics.moments import mean
from earth2studio.utils import handshake_coords, handshake_dim
from earth2studio.utils.type import CoordSystem


def compute_crps(
    ensemble: torch.Tensor,
    observation: torch.Tensor,
    dim: int = 0,
    fair: bool = False,
) -> torch.Tensor:
    """Compute exact Continuous Ranked Probability Score (CRPS) in O(M log M) time.

    Uses the kernel/energy representation via sorted order statistics:
        CRPS(F, y) = E|X - y| - 0.5 * E|X - X'|

    Where the pairwise difference term is evaluated exactly in linear time over sorted members:
        sum_{i,j} |x_i - x_j| = 2 * sum_{k=0}^{M-1} (2*k + 1 - M) * x_{(k)}

    Parameters
    ----------
    ensemble : torch.Tensor
        Ensemble prediction tensor with shape (..., M, ...).
    observation : torch.Tensor
        Observation tensor matching ensemble shape without dimension dim.
    dim : int, default 0
        Dimension corresponding to ensemble members.
    fair : bool, default False
        Whether to compute the fair (unbiased for finite ensemble size) CRPS
        using factor 1 / (2*M*(M-1)) (Ferro et al. 2008).

    Returns
    -------
    torch.Tensor
        Tensor of CRPS scores with dimension dim reduced.
    """
    M = ensemble.shape[dim]

    if fair and M < 2:
        raise ValueError(
            f"Fair CRPS requires at least M >= 2 ensemble members, got {M}."
        )

    # Term 1: E|X - y|
    obs_expanded = observation.unsqueeze(dim)
    term1 = torch.mean(torch.abs(ensemble - obs_expanded), dim=dim)

    if M == 1:
        return term1

    # Term 2: 0.5 * E|X - X'| via sorted order statistics
    sorted_ens, _ = torch.sort(ensemble, dim=dim)

    # w_k = 2*k + 1 - M for k in 0..M-1
    indices = torch.arange(M, dtype=ensemble.dtype, device=ensemble.device)
    weights = 2.0 * indices + 1.0 - float(M)

    shape = [1] * ensemble.ndim
    shape[dim] = M
    weights = weights.view(shape)

    pairwise_sum = 2.0 * torch.sum(weights * sorted_ens, dim=dim)

    if fair:
        term2 = pairwise_sum / (2.0 * float(M) * float(M - 1))
    else:
        term2 = pairwise_sum / (2.0 * float(M) * float(M))

    return term1 - term2


def _crps_from_empirical_cdf(
    ensemble: torch.Tensor, truth: torch.Tensor, dim: int = 0
) -> torch.Tensor:
    """Compute exact CRPS using the vectorized order-statistics method.

    Maintained for API backwards-compatibility with test harnesses.
    """
    return compute_crps(ensemble, truth, dim=dim, fair=False)


class crps:
    """Continuous Ranked Probability Score (CRPS).

    Computes CRPS using the kernel representation via vectorized order statistics in O(M log M) time:
        CRPS(F, y) = E|X - y| - 0.5 * E|X - X'|

    Supports both standard CRPS and fair (unbiased finite-ensemble) CRPS.
    Operates either as an instantiated Metric or as a direct functional call.

    Parameters
    ----------
    ensemble_dimension : str, default "ensemble"
        Name of coordinate dimension corresponding to ensemble members.
    reduction_dimensions : list[str] | None, default None
        Optional dimensions (e.g. ['lat', 'lon']) over which to average CRPS.
    weights : torch.Tensor | None, default None
        Optional weights tensor assigned to reduction dimensions (e.g. cosine latitude weights).
    fair : bool, default False
        If True, applies finite-ensemble unbiased correction factor 1 / (2*M*(M-1)).
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

            dim = kwargs.get("dim", kwargs.get("ensemble_dimension", "ensemble"))
            fair = kwargs.get("fair", False)

            if isinstance(dim, str):
                if x_coords is None or dim not in x_coords:
                    dim_idx = 0
                else:
                    dim_idx = list(x_coords).index(dim)
            else:
                dim_idx = int(dim)

            if y is None:
                raise ValueError("Target observation 'y' must be provided.")

            res = compute_crps(x, y, dim=dim_idx, fair=fair)
            out_coords = y_coords.copy() if y_coords is not None else {}
            return res, out_coords

        return super().__new__(cls)

    def __init__(
        self,
        ensemble_dimension: str = "ensemble",
        reduction_dimensions: list[str] | None = None,
        weights: torch.Tensor | None = None,
        fair: bool = False,
    ):
        if not isinstance(ensemble_dimension, str):
            raise ValueError(
                "Error! CRPS currently assumes reduction over a single dimension."
            )

        self.ensemble_dimension = ensemble_dimension
        self._reduction_dimensions = reduction_dimensions
        if reduction_dimensions is not None:
            self.mean = mean(reduction_dimensions, weights=weights, batch_update=False)
        self.fair = fair
        self.weights = weights

    def __str__(self) -> str:
        return "_".join(self.reduction_dimensions + ["crps"])

    @property
    def reduction_dimensions(self) -> list[str]:
        return (
            [self.ensemble_dimension]
            if self._reduction_dimensions is None
            else [self.ensemble_dimension] + self._reduction_dimensions
        )

    def output_coords(self, input_coords: CoordSystem) -> CoordSystem:
        """Output coordinate system of the computed statistic, corresponding to the given input coordinates

        Parameters
        ----------
        input_coords : CoordSystem
            Input coordinate system to transform into output_coords

        Returns
        -------
        CoordSystem
            Coordinate system dictionary
        """
        output_coords = input_coords.copy()
        for dimension in self.reduction_dimensions:
            handshake_dim(input_coords, dimension)
            output_coords.pop(dimension)

        return output_coords

    def __call__(
        self,
        x: torch.Tensor,
        x_coords: CoordSystem,
        y: torch.Tensor,
        y_coords: CoordSystem,
    ) -> tuple[torch.Tensor, CoordSystem]:
        """Apply metric to data `x` and `y`, checking that their coordinates
        are broadcastable while reducing over `reduction_dims`.

        Parameters
        ----------
        x : torch.Tensor
            Input tensor of ensemble forecast or prediction data.
        x_coords : CoordSystem
            Ordered dict representing coordinate system that describes the `x` tensor.
        y : torch.Tensor
            Observation or validation tensor.
        y_coords : CoordSystem
            Ordered dict representing coordinate system that describes the `y` tensor.

        Returns
        -------
        tuple[torch.Tensor, CoordSystem]
            Returns CRPS tensor with appropriate reduced coordinates.
        """
        if not all([rd in x_coords for rd in self.reduction_dimensions]):
            raise ValueError(
                "Initialized reduction dimension does not appear in passed coords"
            )

        # Do some coordinate checking
        # Assume ensemble_dim is in x_coords but not y_coords
        if self.ensemble_dimension in y_coords:
            raise ValueError(
                f"{self.ensemble_dimension} should not be in y_coords but is."
            )
        if x.ndim != y.ndim + 1:
            raise ValueError(
                "x and y must have broadcastable shapes but got"
                + f"{x.shape} and {y.shape}"
            )
        # Input coordinate checking
        coord_count = 0
        for c in x_coords:
            if c != self.ensemble_dimension:
                handshake_dim(y_coords, c, coord_count)
                handshake_coords(y_coords, x_coords, c)
                coord_count += 1

        dim = list(x_coords).index(self.ensemble_dimension)
        out = compute_crps(x, y, dim=dim, fair=self.fair)
        out_coords = y_coords.copy()

        if self._reduction_dimensions is not None:
            out, out_coords = self.mean(out, out_coords)
        return out, out_coords
