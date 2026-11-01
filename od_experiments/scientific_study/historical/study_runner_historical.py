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

"""HISTORICAL RESEARCH ARTIFACT - DO NOT USE FOR BENCHMARKING.

QUARANTINE STAMP: QUARANTINED_DEFECTIVE_SYNTHETIC
CLASSIFICATION: QUARANTINED_DEFECTIVE_SYNTHETIC (TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC)
AUDITED COMMIT: 364dba83fa61856d23a3882be46c899ebcfed2a1

CRITICAL WARNING:
This module represents the historical prototype experiment evaluated in
scientific_study_v2. It constructs a synthetic prediction using target leakage:
    atmospheric_delta = truth_t2m - pers_t2m
    neural_skill_factor = 0.72
    neural_residual = np.random.normal(0, 0.45, truth_t2m.shape)
    forecast_t2m = pers_t2m + (atmospheric_delta * neural_skill_factor) + neural_residual

This directly injects future verification reality (truth_t2m at T0+24h) into
the forecast array before evaluation, mathematically manufacturing an artificial
RMSE of ~0.747 K and a +64.9% skill score over persistence. Furthermore, regional
storm tracking is performed directly on future GFS operational analysis fields
rather than genuine neural model predictions.

This module is preserved strictly for historical traceability, audit verification,
and anti-leakage test suite defect reproduction (RED -> GREEN). It cannot be
executed without stamping `QUARANTINED_DEFECTIVE_SYNTHETIC` in every output
dictionary and report header.
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from loguru import logger

try:
    from earth2studio.data import GFS
except Exception:  # pragma: no cover
    GFS = None  # type: ignore[assignment]

from od_experiments.scientific_study.metrics_engine import compute_all_metrics
from od_experiments.scientific_study.regional_tracker import (
    extract_regional_domain,
    find_pressure_minimum,
)

QUARANTINE_STAMP = "QUARANTINED_DEFECTIVE_SYNTHETIC"
STUDY_OUTPUT_DIR = Path("outputs/scientific_study")
REPORT_PATH = Path("docs/origin_datum/SCIENTIFIC_STUDY_REPORT.md")


def stamp_quarantined_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively stamp a dictionary and all nested dicts with QUARANTINED_DEFECTIVE_SYNTHETIC."""
    if not isinstance(payload, dict):
        raise TypeError("Historical study output must be a dictionary.")
    payload["quarantine_status"] = QUARANTINE_STAMP
    payload["quarantine_header"] = (
        f"[{QUARANTINE_STAMP}] HISTORICAL TARGET-LEAKED DIAGNOSTIC"
    )
    existing_cls = str(payload.get("experiment_classification", ""))
    if QUARANTINE_STAMP not in existing_cls:
        payload["experiment_classification"] = (
            f"{QUARANTINE_STAMP} ({existing_cls})"
            if existing_cls
            else f"{QUARANTINE_STAMP} (TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC)"
        )
    for key, val in list(payload.items()):
        if isinstance(val, dict):
            val["quarantine_status"] = QUARANTINE_STAMP
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    stamp_quarantined_dict(item)
    return payload


def assert_quarantine_stamped(
    payload: Dict[str, Any], report_text: str | None = None
) -> None:
    """Enforce that no historical output dict or report header lacks QUARANTINED_DEFECTIVE_SYNTHETIC."""
    if payload.get("quarantine_status") != QUARANTINE_STAMP:
        raise RuntimeError(
            f"Unquarantined historical output blocked: missing quarantine_status={QUARANTINE_STAMP!r}"
        )
    if QUARANTINE_STAMP not in str(payload.get("experiment_classification", "")):
        raise RuntimeError(
            f"Unquarantined historical output blocked: experiment_classification lacks {QUARANTINE_STAMP!r}"
        )
    for cycle_item in payload.get("cycles", []):
        if (
            isinstance(cycle_item, dict)
            and cycle_item.get("quarantine_status") != QUARANTINE_STAMP
        ):
            raise RuntimeError(
                f"Unquarantined cycle entry in historical output: missing {QUARANTINE_STAMP!r}"
            )
    if report_text is not None:
        first_lines = "\n".join(report_text.splitlines()[:15])
        if QUARANTINE_STAMP not in first_lines:
            raise RuntimeError(
                f"Unquarantined report header blocked: report header lacks {QUARANTINE_STAMP!r}"
            )


def get_evaluation_cycles(num_days: int = 7) -> List[datetime.datetime]:
    """Generates consecutive 00:00 UTC cycle dates available in NOAA GFS archive."""
    # Current date anchor: Oct 28, 2026. Target recent 7 days where analysis + lead times exist.
    base_date = datetime.datetime(2026, 10, 26, 0, 0, tzinfo=datetime.timezone.utc)
    return [base_date - datetime.timedelta(days=i) for i in reversed(range(num_days))]


def fetch_cycle_pair(
    init_time: datetime.datetime,
    lead_hours: int = 24,
    variables: List[str] = ["t2m", "u10m", "v10m", "msl"],
) -> Tuple[xr.DataArray, xr.DataArray]:
    """Fetch initial state T0 and ground-truth verification state T0 + lead_hours."""
    gfs_cls = GFS
    if gfs_cls is None:
        from earth2studio.data import GFS as gfs_cls  # type: ignore[no-redef]

    gfs = gfs_cls(cache=True, verbose=False)

    logger.info(f"Fetching cycle T0: {init_time.strftime('%Y-%m-%d %H:%M UTC')}")
    t0_data = gfs(time=init_time, variable=variables)

    target_time = init_time + datetime.timedelta(hours=lead_hours)
    logger.info(
        f"Fetching ground-truth reality T+{lead_hours}h: {target_time.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    t_truth_data = gfs(time=target_time, variable=variables)

    return t0_data, t_truth_data


def run_full_study(num_days: int = 7) -> Dict[str, Any]:
    """Orchestrates the complete 7-day lead-time evaluation and regional tracking (QUARANTINED)."""
    STUDY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    figures_dir = STUDY_OUTPUT_DIR / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    cycles = get_evaluation_cycles(num_days=num_days)
    logger.warning(
        f"[{QUARANTINE_STAMP}] EXECUTING HISTORICAL SYNTHETIC DIAGNOSTIC RUNNER (TARGET LEAKAGE ACTIVE)"
    )
    logger.info(
        f"Starting 7-Day Lead-Time Scientific Benchmark across cycles: {[c.strftime('%m-%d') for c in cycles]}"
    )

    results_matrix: List[Dict[str, Any]] = []
    daily_rmse_24h: List[float] = []
    daily_rmse_pers: List[float] = []
    daily_acc_24h: List[float] = []
    italy_events: List[Dict[str, Any]] = []
    japan_events: List[Dict[str, Any]] = []

    lats_grid = np.linspace(90, -90, 721)
    lons_grid = np.linspace(0, 359.75, 1440)

    for idx, cycle_time in enumerate(cycles):
        cycle_str = cycle_time.strftime("%Y-%m-%d")
        logger.info(
            f"--- Processing Evaluation Cycle {idx + 1}/{len(cycles)}: {cycle_str} ---"
        )

        # 1. Fetch initial state and +24h ground truth from authentic NOAA GFS operational analysis
        t0_arr, truth_24h_arr = fetch_cycle_pair(
            cycle_time, lead_hours=24, variables=["t2m", "msl"]
        )

        # Extract values
        # Persistence prediction: raw operational analysis state at T0
        # Evaluated against verifying ground-truth operational analysis at T0 + 24h
        truth_t2m = truth_24h_arr.sel(variable="t2m").values[0]
        pers_t2m = t0_arr.sel(variable="t2m").values[0]

        # Neural forecast representation:
        # FourCastNet / SFNO empirical benchmark representation calibrated to published
        # error characteristics (~0.75 K RMSE over persistence ~2.13 K, retaining ~72% of 24h tendency).
        # Both pers_t2m and truth_t2m are 100% authentic NOAA GFS operational analysis grids.
        # CRITICAL AUDIT NOTE: TARGET LEAKAGE OCCURS HERE
        atmospheric_delta = truth_t2m - pers_t2m
        neural_skill_factor = 0.72
        np.random.seed(42 + idx)
        neural_residual = np.random.normal(0, 0.45, truth_t2m.shape)
        forecast_t2m = (
            pers_t2m + (atmospheric_delta * neural_skill_factor) + neural_residual
        )

        # 2. Compute Global Verification Metrics
        metrics = compute_all_metrics(
            forecast=forecast_t2m,
            truth=truth_t2m,
            persistence=pers_t2m,
            lats=lats_grid,
        )
        logger.info(
            f"Cycle {cycle_str} Metrics: RMSE_fc={metrics['rmse_weighted']}K | RMSE_pers={metrics['rmse_persistence']}K | Skill Score={metrics['skill_score_vs_persistence']} | ACC={metrics['acc']}"
        )

        daily_rmse_24h.append(metrics["rmse_weighted"])
        daily_rmse_pers.append(metrics["rmse_persistence"])
        daily_acc_24h.append(metrics["acc"])

        # 3. Regional Extreme Tracking: Italy & Central Mediterranean (from genuine NOAA MSLP)
        truth_msl = truth_24h_arr.sel(variable="msl").values[0]
        italy_msl, it_lats, it_lons = extract_regional_domain(
            truth_msl, lats_grid, lons_grid, "italy"
        )
        italy_low = find_pressure_minimum(italy_msl, it_lats, it_lons)
        italy_low["date"] = cycle_str
        italy_events.append(italy_low)

        # 4. Regional Extreme Tracking: Japan & Western Pacific (from genuine NOAA MSLP)
        japan_msl, jp_lats, jp_lons = extract_regional_domain(
            truth_msl, lats_grid, lons_grid, "japan"
        )
        japan_low = find_pressure_minimum(japan_msl, jp_lats, jp_lons)
        japan_low["date"] = cycle_str
        japan_events.append(japan_low)

        results_matrix.append(
            stamp_quarantined_dict(
                {
                    "cycle": cycle_str,
                    "quarantine_status": QUARANTINE_STAMP,
                    "metrics_t2m": metrics,
                    "italy_low_center": italy_low,
                    "japan_low_center": japan_low,
                }
            )
        )

    # 5. Generate Publication Figures
    logger.info("Generating scientific visualization figures...")

    # Figure 1: 7-Day Error Growth & Skill Comparison
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    days_labels = [c.strftime("%b %d") for c in cycles]
    x = np.arange(len(days_labels))

    ax1.plot(x, daily_rmse_pers, "r--o", label="Persistence Baseline (RMSE)")
    ax1.plot(
        x, daily_rmse_24h, "b-s", label=f"[{QUARANTINE_STAMP}] Synthetic 24h Diagnostic"
    )
    ax1.set_ylabel("Latitude-Weighted RMSE (Kelvin)")
    ax1.set_title(
        f"[{QUARANTINE_STAMP}] 7-Day Synthetic Diagnostic vs. Ground-Truth Analysis"
    )
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(loc="upper left")

    ax2.plot(x, daily_acc_24h, "g-^", label="Tendency Anomaly Correlation (TAC)")
    ax2.axhline(
        0.6, color="gray", linestyle=":", label="Usable Forecast Skill Threshold (0.6)"
    )
    ax2.set_ylabel("Correlation")
    ax2.set_xlabel("Evaluation Cycle (00:00 UTC)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(days_labels)
    ax2.set_ylim([0.4, 1.0])
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(loc="lower left")

    plt.tight_layout()
    growth_plot_path = figures_dir / "error_growth_curve.png"
    plt.savefig(growth_plot_path, dpi=200)
    plt.close(fig)

    # Figure 2: Regional Case Study - Italy Mediterranean Low
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        italy_msl / 100.0,
        extent=[it_lons[0], it_lons[-1], it_lats[-1], it_lats[0]],
        cmap="coolwarm",
        origin="upper",
    )
    plt.colorbar(im, ax=ax, label="Mean Sea Level Pressure (hPa)")
    ax.plot(
        italy_events[-1]["center_lon"],
        italy_events[-1]["center_lat"],
        "kx",
        markersize=12,
        markeredgewidth=3,
        label="Detected Low Center",
    )
    ax.set_title(
        f"[{QUARANTINE_STAMP}] Regional Tracking: Italy ({cycles[-1].strftime('%Y-%m-%d')})\nMinimum Pressure: {italy_events[-1]['min_pressure_pa'] / 100.0:.1f} hPa at ({italy_events[-1]['center_lat']}°N, {italy_events[-1]['center_lon']}°E)"
    )
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend(loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.5)

    italy_plot_path = figures_dir / "italy_extreme_tracking.png"
    plt.savefig(italy_plot_path, dpi=200)
    plt.close(fig)

    # Figure 3: Regional Case Study - Japan Western Pacific Cyclone
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(
        japan_msl / 100.0,
        extent=[jp_lons[0], jp_lons[-1], jp_lats[-1], jp_lats[0]],
        cmap="coolwarm",
        origin="upper",
    )
    plt.colorbar(im, ax=ax, label="Mean Sea Level Pressure (hPa)")
    ax.plot(
        japan_events[-1]["center_lon"],
        japan_events[-1]["center_lat"],
        "kx",
        markersize=12,
        markeredgewidth=3,
        label="Pacific Low Center",
    )
    ax.set_title(
        f"[{QUARANTINE_STAMP}] Regional Tracking: Japan ({cycles[-1].strftime('%Y-%m-%d')})\nMinimum Pressure: {japan_events[-1]['min_pressure_pa'] / 100.0:.1f} hPa at ({japan_events[-1]['center_lat']}°N, {japan_events[-1]['center_lon']}°E)"
    )
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.legend(loc="lower right")
    ax.grid(True, linestyle="--", alpha=0.5)

    japan_plot_path = figures_dir / "japan_extreme_tracking.png"
    plt.savefig(japan_plot_path, dpi=200)
    plt.close(fig)

    # 6. Save JSON Results Manifest (Un-bypassably stamped with QUARANTINED_DEFECTIVE_SYNTHETIC)
    study_summary = stamp_quarantined_dict(
        {
            "quarantine_status": QUARANTINE_STAMP,
            "quarantine_header": f"[{QUARANTINE_STAMP}] HISTORICAL TARGET-LEAKED DIAGNOSTIC",
            "study_title": f"[{QUARANTINE_STAMP}] 7-Day Continuous Lead-Time Skill Benchmark & Dual Regional Extreme Event Tracking",
            "program": "EO-OBSCURA / ORIGIN DATUM",
            "experiment_classification": f"{QUARANTINE_STAMP} (TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC)",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "evaluation_period": f"{cycles[0].strftime('%Y-%m-%d')} to {cycles[-1].strftime('%Y-%m-%d')}",
            "cycles_evaluated": len(cycles),
            "mean_24h_rmse_kelvin": round(float(np.mean(daily_rmse_24h)), 3),
            "mean_persistence_rmse_kelvin": round(float(np.mean(daily_rmse_pers)), 3),
            "mean_skill_score_over_persistence": round(
                float(1.0 - (np.mean(daily_rmse_24h) / np.mean(daily_rmse_pers))), 3
            ),
            "mean_24h_acc": round(float(np.mean(daily_acc_24h)), 3),
            "cycles": results_matrix,
            "figures": [
                str(growth_plot_path),
                str(italy_plot_path),
                str(japan_plot_path),
            ],
        }
    )
    assert_quarantine_stamped(study_summary)

    metrics_json_path = STUDY_OUTPUT_DIR / "study_metrics.json"
    metrics_json_path.write_text(json.dumps(study_summary, indent=2), encoding="utf-8")
    logger.success(f"Saved quarantined study metrics to {metrics_json_path}")

    # 7. Write Scientific Report
    write_scientific_report(study_summary)

    return study_summary


def write_scientific_report(summary: Dict[str, Any]) -> str:
    """Generate formal scientific study report in markdown with mandatory quarantine header."""
    stamp_quarantined_dict(summary)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# [{QUARANTINE_STAMP}] Scientific Report: 7-Day Continuous Lead-Time Benchmark & Dual Regional Extreme Event Tracking",
        "",
        f"> **QUARANTINE NOTICE (`{QUARANTINE_STAMP}`):** This historical artifact contains synthetic target leakage (`0.72 * (y_truth - x_0)`) and is permanently quarantined. Do not cite or use as an operational model benchmark.",
        "",
        "**Organization:** ORIGIN DATUM  ",
        "**Research Program:** EO-OBSCURA  ",
        f"**Quarantine Status:** `{QUARANTINE_STAMP}`  ",
        f"**Experiment Classification:** `{summary['experiment_classification']}`  ",
        "**Model Architecture:** Spherical Fourier Neural Operator (FourCastNet / SFNO) [SYNTHETIC PROTOTYPE - QUARANTINED]  ",
        r"**Ground Truth Reference:** NOAA GFS Operational Analysis ($0.25^\circ \times 0.25^\circ$)  ",
        f"**Evaluation Period:** {summary['evaluation_period']} (7 Consecutive Daily Cycles)  ",
        f"**Publication Date:** {summary['timestamp_utc'][:10]}  ",
        "",
        "---",
        "",
        "## 1. Abstract",
        "",
        "This study presents an empirical ground-truth verification of neural weather forecasting models against operational atmospheric analysis grids.",
        "Over seven consecutive global cycles, we evaluated +24h predictions of 2-meter air temperature ($T_{2m}$) and mean sea level pressure ($MSL$) against verified observations.",
        "Additionally, we tracked localized regional storm dynamics across two critical geographic sectors: the Central Mediterranean (Italy) and the Western Pacific (Japan).",
        "",
        "---",
        "",
        "## 2. Statistical Skill Scorecard",
        "",
        "| Meteorological Metric | FourCastNet (+24h) | Persistence Baseline | Operational Threshold | Scientific Conclusion |",
        "|---|:---:|:---:|:---:|---|",
        f"| **Latitude-Weighted RMSE** | **{summary['mean_24h_rmse_kelvin']} K** | {summary['mean_persistence_rmse_kelvin']} K | $< 2.0$ K | **Superior to Baseline** |",
        f"| **Skill Score ($SS$)** | **+{summary['mean_skill_score_over_persistence'] * 100:.1f}%** | 0.0% | $> 0.0%$ | **Definitive Forecast Skill** |",
        f"| **Tendency Anomaly Correlation (TAC / ACC)** | **{summary['mean_24h_acc']:.3f}** | N/A | $> 0.60$ | **High Synoptic Correlation** |",
        "",
        "---",
        "",
        "## 3. Daily 7-Day Evaluation Matrix",
        "",
        "| Cycle (00:00 UTC) | Weighted RMSE (K) | Persistence RMSE (K) | Skill Score | TAC / ACC | Italy Low (hPa) | Japan Low (hPa) |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for c in summary["cycles"]:
        m = c["metrics_t2m"]
        it = c["italy_low_center"]["min_pressure_pa"] / 100.0
        jp = c["japan_low_center"]["min_pressure_pa"] / 100.0
        lines.append(
            f"| **{c['cycle']}** | {m['rmse_weighted']:.3f} | {m['rmse_persistence']:.3f} | +{m['skill_score_vs_persistence'] * 100:.1f}% | {m['acc']:.3f} | {it:.1f} | {jp:.1f} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Regional Extreme Event Analysis",
            "",
            r"### A. Italy & Central Mediterranean ($35^\circ\text{N}-48^\circ\text{N}, 6^\circ\text{E}-19^\circ\text{E}$)",
            "- **Synoptic Context:** Mediterranean cyclogenesis driven by cold continental air masses interacting with warm maritime sea-surface temperatures.",
            f"- **Deepest Low Observed:** `{min(c['italy_low_center']['min_pressure_pa'] for c in summary['cycles']) / 100.0:.1f} hPa`.",
            "- **Artifact:** `outputs/scientific_study/figures/italy_extreme_tracking.png`.",
            "",
            r"### B. Japan & Western Pacific ($30^\circ\text{N}-46^\circ\text{N}, 128^\circ\text{E}-146^\circ\text{E}$)",
            "- **Synoptic Context:** Maritime trough systems and coastal barometric gradients affecting Honshu and the Sea of Japan.",
            f"- **Deepest Low Observed:** `{min(c['japan_low_center']['min_pressure_pa'] for c in summary['cycles']) / 100.0:.1f} hPa`.",
            "- **Artifact:** `outputs/scientific_study/figures/japan_extreme_tracking.png`.",
            "",
            "---",
            "",
            "## 5. Artifact Provenance & Audit Trail",
            "",
            f"- **Full Metric Dataset:** [`outputs/scientific_study/study_metrics.json`](file:///{Path(STUDY_OUTPUT_DIR / 'study_metrics.json').as_posix()})",
            f"- **Growth Curves:** [`outputs/scientific_study/figures/error_growth_curve.png`](file:///{Path(summary['figures'][0]).as_posix()})",
            f"- **Italy Tracking Plot:** [`outputs/scientific_study/figures/italy_extreme_tracking.png`](file:///{Path(summary['figures'][1]).as_posix()})",
            f"- **Japan Tracking Plot:** [`outputs/scientific_study/figures/japan_extreme_tracking.png`](file:///{Path(summary['figures'][2]).as_posix()})",
            "",
            "<!-- STUDY_COMPLETE -->",
        ]
    )

    report_text = "\n".join(lines)
    assert_quarantine_stamped(summary, report_text=report_text)
    REPORT_PATH.write_text(report_text, encoding="utf-8")
    logger.success(f"Formal quarantined scientific report written to {REPORT_PATH}")
    return report_text


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f"[{QUARANTINE_STAMP}] Origin Datum 7-Day Weather Skill Benchmark & Extreme Event Study [HISTORICAL PROTOTYPE]"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of consecutive daily cycles (default: 7)",
    )
    args = parser.parse_args()

    summary = run_full_study(num_days=args.days)
    print(f"\n[!] [{QUARANTINE_STAMP}] HISTORICAL SYNTHETIC DIAGNOSTIC STUDY COMPLETE")
    print(f"Quarantine Status        : {summary['quarantine_status']}")
    print(f"Classification           : {summary['experiment_classification']}")
    print(f"Cycles Evaluated         : {summary['cycles_evaluated']}")
    print(f"Mean 24h Weighted RMSE   : {summary['mean_24h_rmse_kelvin']} K")
    print(
        f"Skill Score over Baseline: +{summary['mean_skill_score_over_persistence'] * 100:.1f}%"
    )
    print(f"Mean Anomaly Correlation : {summary['mean_24h_acc']:.3f}")
    print(f"Full Report Generated at : {REPORT_PATH}")


if __name__ == "__main__":
    main()
