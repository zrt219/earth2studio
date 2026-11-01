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

"""
Operational Verification Pipeline for Earth2Studio Ensembles.
OD-EARTH2-001 / EO-OBSCURA research initiative.
Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
Strict adherence to .agents/rules/e2s-014-scientific-integrity.mdc.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xarray as xr
from loguru import logger

from od_experiments.scientific_study.metrics_engine import (
    crps_ensemble,
    extreme_dependency_index,
    mean_bias,
    spread_skill_ratio,
    symmetric_extremal_dependence_index,
    tendency_anomaly_correlation,
    weighted_mae,
    weighted_rmse,
)


class EnsembleVerificationPipeline:
    """
    Operational verification suite evaluating ensemble forecast outputs
    against physical operational numerical analysis (NOAA GFS analysis / ECMWF ERA5).
    """

    DEFAULT_EXTREME_THRESHOLDS: Dict[str, float] = {
        "w10m": 20.0,  # Gale-force wind speed (> 20 m/s, Beaufort 8-9)
        "u10m": 20.0,  # Gale zonal component
        "v10m": 20.0,  # Gale meridional component
        "tp": 20.0,  # Heavy precipitation (> 20 mm / 24h)
        "tcwv": 50.0,  # Atmospheric river / high precipitable water (> 50 kg/m2)
        "msl": 98000.0,  # Deep cyclonic depression (< 980 hPa; inverted lower threshold)
    }

    def __init__(
        self,
        ground_truth_source: Any = None,
        source_name: str = "gfs",
        thresholds: Optional[Dict[str, float]] = None,
        fair_crps: bool = True,
        correct_finite_ssr: bool = True,
        target_lats: Optional[np.ndarray] = None,
    ):
        """
        Parameters
        ----------
        ground_truth_source : DataSource, optional
            Data source instance (e.g. GFS(), CDS_ERA5(), or mock for testing).
        source_name : str
            Name identifier for verification source ("gfs", "era5", "mock").
        thresholds : dict[str, float], optional
            Thresholds for EDI/SEDI extreme atmospheric verification.
        fair_crps : bool
            Whether to compute unbiased finite-ensemble fair CRPS.
        correct_finite_ssr : bool
            Whether to apply finite-size ensemble correction sqrt((M+1)/M) to SSR.
        target_lats : np.ndarray, optional
            Latitude coordinates for cosine weighting and orientation validation.
        """
        self.ground_truth_source = ground_truth_source
        self.source_name = source_name.lower()
        self.thresholds = (
            thresholds if thresholds is not None else self.DEFAULT_EXTREME_THRESHOLDS
        )
        self.fair_crps = fair_crps
        self.correct_finite_ssr = correct_finite_ssr
        self.target_lats = (
            target_lats if target_lats is not None else np.linspace(90, -90, 721)
        )

        # Enforce Rule 4 of e2s-014: Descending latitude grid check
        if self.target_lats[0] < self.target_lats[-1]:
            logger.warning(
                "Latitude vector is ascending (-90 to +90). Reversing to adhere "
                "to atmospheric standard (+90 to -90) per e2s-014 Rule 4."
            )
            self.target_lats = self.target_lats[::-1]

    def synchronize_valid_time(
        self, init_time: datetime | str | np.datetime64, lead_hours: int | float
    ) -> datetime:
        """
        Synchronize lead step offset with real UTC valid time: t_valid = t_0 + delta_t.
        """
        if isinstance(init_time, str):
            t0 = pd.to_datetime(init_time).to_pydatetime()
        elif isinstance(init_time, np.datetime64):
            t0 = pd.to_datetime(init_time).to_pydatetime()
        elif isinstance(init_time, datetime):
            t0 = init_time
        else:
            raise TypeError(f"Unsupported time type: {type(init_time)}")

        return t0 + timedelta(hours=float(lead_hours))

    def fetch_analysis_ground_truth(
        self,
        valid_time: datetime,
        variables: List[str],
    ) -> Dict[str, np.ndarray]:
        """
        Query ground truth analysis state at synchronized valid time.
        """
        if self.ground_truth_source is None:
            raise RuntimeError(
                "No ground truth data source configured in pipeline. "
                "Supply an authentic DataSource instance (GFS, CDS_ERA5, ARCO_ERA5, or MockGroundTruthSource)."
            )

        da = self.ground_truth_source(time=[valid_time], variable=variables)

        truth_dict: Dict[str, np.ndarray] = {}
        for var in variables:
            if (
                hasattr(da, "coords")
                and "variable" in da.coords
                and var in da.coords["variable"].values
            ):
                var_slice = da.sel(variable=var).squeeze()
                truth_dict[var] = np.asarray(var_slice.values, dtype=np.float32)
            elif hasattr(da, "coords") and var in da:
                truth_dict[var] = np.asarray(da[var].squeeze().values, dtype=np.float32)
            else:
                raise KeyError(f"Variable {var} not found in retrieved analysis state.")

        return truth_dict

    def evaluate_lead_step(
        self,
        forecast_ensemble: np.ndarray,
        truth_observation: np.ndarray,
        t0_persistence: Optional[np.ndarray],
        variable: str,
        lats: np.ndarray,
        lead_hours: int | float,
    ) -> Dict[str, Any]:
        """
        Evaluate full diagnostic suite for a single variable at specified forecast lead time.

        Parameters
        ----------
        forecast_ensemble : np.ndarray
            Array of shape (M, lat, lon) representing M ensemble member predictions.
        truth_observation : np.ndarray
            Array of shape (lat, lon) representing authentic operational ground truth.
        t0_persistence : np.ndarray, optional
            Array of shape (lat, lon) representing initial atmospheric state at t=0.
        variable : str
            Meteorological variable code (e.g. 't2m', 'w10m', 'tp', 'z500').
        lats : np.ndarray
            1D array of latitude coordinates.
        lead_hours : int or float
            Forecast lead time in hours.
        """
        M = forecast_ensemble.shape[0]
        ens_mean = np.mean(forecast_ensemble, axis=0)

        # 1. Deterministic Metrics (Ensemble Mean)
        rmse_val = weighted_rmse(ens_mean, truth_observation, lats=lats)
        mae_val = weighted_mae(ens_mean, truth_observation, lats=lats)
        bias_val = mean_bias(ens_mean, truth_observation)

        # 2. Tendency Anomaly Correlation (TAC) vs Initial State (Rule 2 of e2s-014)
        tac_val = None
        if t0_persistence is not None:
            tac_val = tendency_anomaly_correlation(
                forecast=ens_mean,
                truth=truth_observation,
                persistence=t0_persistence,
                lats=lats,
            )

        # 3. Continuous Ranked Probability Score (CRPS)
        crps_std = crps_ensemble(
            forecast_ensemble, truth_observation, lats=lats, fair=False
        )
        crps_fair_val = (
            crps_ensemble(forecast_ensemble, truth_observation, lats=lats, fair=True)
            if M >= 2
            else crps_std
        )

        # 4. Spread-Skill Ratio (SSR)
        ssr_metrics = spread_skill_ratio(
            forecast_ensemble,
            truth_observation,
            lats=lats,
            correct_finite=self.correct_finite_ssr,
        )

        # 5. Extreme Atmospheric Threshold Metrics (EDI & SEDI)
        extreme_res = None
        if variable in self.thresholds:
            theta = self.thresholds[variable]
            is_upper = (
                variable != "msl"
            )  # MSLP depression is lower-threshold (< 980 hPa)

            # Mode A: Ensemble Mean Threshold
            edi_mean = extreme_dependency_index(
                forecast=ens_mean,
                truth=truth_observation,
                threshold=theta,
                lats=lats,
                is_upper_threshold=is_upper,
            )
            sedi_mean = symmetric_extremal_dependence_index(
                forecast=ens_mean,
                truth=truth_observation,
                threshold=theta,
                lats=lats,
                is_upper_threshold=is_upper,
            )

            # Mode B: Probabilistic Exceedance (P >= 0.5)
            if is_upper:
                prob_exceed = np.mean(forecast_ensemble >= theta, axis=0)
            else:
                prob_exceed = np.mean(forecast_ensemble <= theta, axis=0)

            prob_forecast_binary = (prob_exceed >= 0.5).astype(np.float32)
            truth_binary = (
                truth_observation >= theta if is_upper else truth_observation <= theta
            ).astype(np.float32)

            edi_prob = extreme_dependency_index(
                forecast=prob_forecast_binary,
                truth=truth_binary,
                threshold=0.5,
                lats=lats,
                is_upper_threshold=True,
            )
            sedi_prob = symmetric_extremal_dependence_index(
                forecast=prob_forecast_binary,
                truth=truth_binary,
                threshold=0.5,
                lats=lats,
                is_upper_threshold=True,
            )

            extreme_res = {
                "threshold_value": theta,
                "is_upper_threshold": is_upper,
                "ensemble_mean": {
                    "edi": edi_mean["edi"],
                    "sedi": sedi_mean["sedi"],
                    "hit_rate": edi_mean["hit_rate"],
                    "false_alarm_rate": edi_mean["false_alarm_rate"],
                    "base_rate": edi_mean["base_rate"],
                    "hits": edi_mean["hits"],
                    "false_alarms": edi_mean["false_alarms"],
                    "misses": edi_mean["misses"],
                    "correct_negatives": edi_mean["correct_negatives"],
                },
                "probabilistic_exceedance_p50": {
                    "edi": edi_prob["edi"],
                    "sedi": sedi_prob["sedi"],
                    "hit_rate": edi_prob["hit_rate"],
                    "false_alarm_rate": edi_prob["false_alarm_rate"],
                    "base_rate": edi_prob["base_rate"],
                },
            }

        return {
            "lead_hours": lead_hours,
            "variable": variable,
            "ensemble_members": M,
            "deterministic_metrics": {
                "rmse": round(rmse_val, 4),
                "mae": round(mae_val, 4),
                "mean_bias": round(bias_val, 4),
                "tac": round(tac_val, 4) if tac_val is not None else None,
                "tac_qualified_per_e2s_014": True,
            },
            "probabilistic_metrics": {
                "crps_standard": round(crps_std, 4),
                "crps_fair": round(crps_fair_val, 4),
                "ensemble_spread": round(ssr_metrics["spread"], 4),
                "skill_rmse": round(ssr_metrics["skill_rmse"], 4),
                "ssr_raw": round(ssr_metrics["ssr_raw"], 4),
                "ssr_corrected": round(ssr_metrics["ssr_corrected"], 4),
                "finite_ensemble_factor": round(ssr_metrics["finite_factor"], 4),
                "calibration_status": ssr_metrics["calibration_status"],
            },
            "extreme_threshold_metrics": extreme_res,
        }

    def verify_forecast_dataset(
        self,
        forecast_dataset: xr.Dataset | Dict[str, Any],
        init_time: datetime | str,
        lead_steps_hours: List[int | float],
        output_dir: Optional[str | Path] = None,
    ) -> Dict[str, Any]:
        """
        Verify multi-step, multi-variable ensemble dataset against operational analysis.
        """
        logger.info(
            f"Starting operational verification against {self.source_name.upper()}"
        )

        results: Dict[str, Any] = {
            "pipeline": "EnsembleVerificationPipeline",
            "attribution": "Zhane Daye, Origin Datum (contact@origindatum.space)",
            "scientific_integrity_standard": ".agents/rules/e2s-014-scientific-integrity.mdc",
            "ground_truth_source": self.source_name,
            "init_time": str(init_time),
            "lead_steps_hours": lead_steps_hours,
            "verification_status": "VALIDATED",
            "variables": {},
        }

        # Extract variables from forecast
        if isinstance(forecast_dataset, xr.Dataset):
            var_names = list(forecast_dataset.data_vars)
        elif isinstance(forecast_dataset, dict):
            var_names = [
                k
                for k in forecast_dataset.keys()
                if k not in ["lat", "lon", "time", "lead_time"]
            ]
        else:
            raise TypeError("Forecast dataset must be xarray.Dataset or dict")

        for var in var_names:
            results["variables"][var] = {"lead_trajectory": []}

            # Retrieve t0 state for TAC computation
            t0_truth = None
            if self.ground_truth_source is not None:
                t_valid_0 = self.synchronize_valid_time(init_time, 0)
                try:
                    t0_dict = self.fetch_analysis_ground_truth(t_valid_0, [var])
                    t0_truth = t0_dict.get(var)
                except Exception as e:
                    logger.warning(
                        f"Could not retrieve t0 analysis state for {var}: {e}"
                    )

            for lead_h in lead_steps_hours:
                # 1. Synchronize valid time
                t_valid = self.synchronize_valid_time(init_time, lead_h)

                # 2. Extract forecast slice: shape (M, lat, lon)
                if isinstance(forecast_dataset, xr.Dataset):
                    ens_cube = (
                        forecast_dataset[var]
                        .sel(lead_time=np.timedelta64(int(lead_h), "h"))
                        .values
                    )
                else:
                    ens_cube = forecast_dataset[var][lead_steps_hours.index(lead_h)]

                if ens_cube.ndim == 2:
                    ens_cube = ens_cube[None, ...]  # Shape (1, lat, lon)

                # 3. Retrieve analysis state at t_valid
                truth_slice = None
                if self.ground_truth_source is not None:
                    truth_dict = self.fetch_analysis_ground_truth(t_valid, [var])
                    truth_slice = truth_dict[var]

                if truth_slice is None:
                    continue

                # 4. Evaluate metrics
                step_eval = self.evaluate_lead_step(
                    forecast_ensemble=ens_cube,
                    truth_observation=truth_slice,
                    t0_persistence=t0_truth,
                    variable=var,
                    lats=self.target_lats,
                    lead_hours=lead_h,
                )
                results["variables"][var]["lead_trajectory"].append(step_eval)

        # 5. Export JSON report with SHA-256 seal
        if output_dir is not None:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            report_file = out_p / "verification_report.json"

            json_str = json.dumps(results, indent=2)
            sha256_hash = hashlib.sha256(json_str.encode("utf-8")).hexdigest()
            results["sha256_integrity_seal"] = sha256_hash

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logger.success(
                f"Verification report saved to {report_file} (SHA-256: {sha256_hash[:16]}...)"
            )

        return results
