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
# Compliance: .agents/rules/e2s-000-python-style-guide.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

"""Origin Datum Earth-2 Research Lab CLI (OD-EARTH2-001).

Provides command-line interfaces for:
- Environment and GPU diagnostics (doctor)
- Component inspection (inspect)
- Baseline deterministic forecasting (run)
- Diagnostic forecast validation against reference analyses (validate)
- Hosted NVIDIA FourCastNet API inference and live test suite (api)
- 5-Model comparative prognostic benchmarking (benchmark)
- Operational multi-model ensemble verification against GFS/ERA5 (verify-ensemble)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m od_experiments.earth2_001.cli",
        description="Origin Datum Earth-2 Research Lab CLI (OD-EARTH2-001)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # doctor
    doc_parser = subparsers.add_parser(
        "doctor", help="Run environment and hardware diagnostics"
    )
    doc_parser.add_argument(
        "--json", action="store_true", help="Output diagnostic in JSON format"
    )

    # inspect
    insp_parser = subparsers.add_parser(
        "inspect", help="Inspect available models and data components"
    )
    insp_parser.add_argument(
        "--json", action="store_true", help="Output schema in JSON format"
    )

    # run
    run_parser = subparsers.add_parser("run", help="Run baseline forecast workflow")
    run_parser.add_argument(
        "--config", type=str, default=None, help="Path to config.yaml"
    )
    run_parser.add_argument(
        "--source",
        type=str,
        choices=["gfs", "random"],
        default=None,
        help="Override data source ('gfs' or 'random')",
    )
    run_parser.add_argument(
        "--output-dir", type=str, default=None, help="Custom output directory"
    )
    run_parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Compute device",
    )

    # validate
    val_parser = subparsers.add_parser(
        "validate", help="Validate forecast results against reference data"
    )
    val_parser.add_argument(
        "--forecast", type=str, required=False, help="Path to forecast file (.npy)"
    )
    val_parser.add_argument(
        "--reference", type=str, required=False, help="Path to reference file (.npy)"
    )
    val_parser.add_argument(
        "--lats",
        type=str,
        required=False,
        help="Path to latitude grid (.npy) for weighting",
    )
    val_parser.add_argument(
        "--output-dir", type=str, default="outputs/earth2_001", help="Output directory"
    )

    # benchmark & benchmark-models
    for bm_cmd, bm_help in [
        (
            "benchmark-models",
            "Benchmark prognostic models (GraphCast, SFNO, Pangu, ClimaX, Persistence, MultiModel)",
        ),
        (
            "benchmark",
            "Run 5-model prognostic benchmark suite (alias for benchmark-models)",
        ),
    ]:
        p = subparsers.add_parser(bm_cmd, help=bm_help)
        p.add_argument(
            "--mock",
            nargs="?",
            const=True,
            default=True,
            type=lambda v: str(v).lower() in ("true", "1", "yes"),
            help="Run in ultra-fast CPU mock mode (default: True)",
        )
        p.add_argument(
            "--steps",
            type=int,
            default=4,
            help="Forecast lead steps (each step = 6h, 4 steps = 24h)",
        )
        p.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Optional output directory to save benchmark_report.json",
        )
        p.add_argument(
            "--models",
            type=str,
            default=None,
            help="Comma-separated model names or 'all'",
        )
        p.add_argument(
            "--json",
            action="store_true",
            help="Output benchmark results in JSON format",
        )

    # verify-ensemble
    ve_parser = subparsers.add_parser(
        "verify-ensemble",
        help="Run operational ensemble verification pipeline (CRPS, SSR, EDI, SEDI)",
    )
    ve_parser.add_argument(
        "--forecast",
        type=str,
        default=None,
        help="Path to forecast tensor (.npy, .nc) or mock flag",
    )
    ve_parser.add_argument(
        "--reference",
        type=str,
        default=None,
        help="Path to reference operational analysis tensor (.npy, .nc) or mock flag",
    )
    ve_parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Optional output directory to save verification_report.json",
    )
    ve_parser.add_argument(
        "--threshold-wind",
        type=float,
        default=20.0,
        help="Extreme wind speed threshold in m/s for EDI/SEDI (default: 20.0)",
    )
    ve_parser.add_argument(
        "--threshold-precip",
        type=float,
        default=10.0,
        help="Heavy precipitation threshold in mm/24h for EDI/SEDI (default: 10.0)",
    )
    ve_parser.add_argument(
        "--mock",
        nargs="?",
        const=True,
        default=True,
        type=lambda v: str(v).lower() in ("true", "1", "yes"),
        help="Run with authentic analytical mock tensors (default: True)",
    )
    ve_parser.add_argument(
        "--steps",
        type=str,
        default="6,12,18,24",
        help="Comma-separated lead steps in hours (default: '6,12,18,24')",
    )
    ve_parser.add_argument(
        "--source",
        type=str,
        default="mock",
        choices=["mock", "gfs", "era5"],
        help="Ground truth data source when fetching live (default: mock)",
    )
    ve_parser.add_argument(
        "--variables",
        type=str,
        default="w10m,tp,t2m,msl",
        help="Comma-separated variables",
    )
    ve_parser.add_argument(
        "--json",
        action="store_true",
        help="Output verification report in JSON format",
    )

    # api subcommands
    api_parser = subparsers.add_parser(
        "api", help="Hosted NVIDIA FourCastNet API commands"
    )
    api_sub = api_parser.add_subparsers(dest="api_command", help="API operations")

    api_sub.add_parser(
        "doctor", help="Check NVIDIA API authentication and endpoint reachability"
    )

    api_infer = api_sub.add_parser(
        "infer", help="Execute hosted FourCastNet inference request"
    )
    api_infer.add_argument(
        "--input-id", type=int, default=0, help="Sample scenario index (0..4)"
    )
    api_infer.add_argument(
        "--variables", type=str, default="t2m", help="Comma-separated variables"
    )
    api_infer.add_argument(
        "--steps", type=int, default=1, help="Simulation steps (1 step = 6h)"
    )
    api_infer.add_argument(
        "--ensemble-size", type=int, default=1, help="Ensemble members (1..4)"
    )
    api_infer.add_argument(
        "--output-dir",
        type=str,
        default="outputs/earth2_001/api_live",
        help="Output directory",
    )

    api_sub.add_parser(
        "tests", help="Run the official 18-test live API verification suite"
    )

    args = parser.parse_args(argv)

    if args.command == "doctor":
        from od_experiments.earth2_001.doctor import run_doctor

        run_doctor(as_json=args.json)
    elif args.command == "inspect":
        from od_experiments.earth2_001.inspect import inspect_components

        inspect_components(as_json=args.json)
    elif args.command in ("benchmark", "benchmark-models"):
        from od_experiments.model_comparison.benchmark_runner import (
            print_benchmark_table,
            run_benchmark_comparison,
        )

        model_names = (
            [m.strip() for m in args.models.split(",") if m.strip()]
            if getattr(args, "models", None) and args.models.lower() != "all"
            else None
        )
        report = run_benchmark_comparison(
            models=model_names,
            mock=args.mock,
            steps=args.steps,
            output_dir=args.output_dir,
        )
        if getattr(args, "json", False):
            print(json.dumps(report, indent=2))
        else:
            print_benchmark_table(report)
    elif args.command == "verify-ensemble":
        import xarray as xr

        from od_experiments.ensemble.verification import EnsembleVerificationPipeline
        from od_experiments.tests.test_metrics_operational import MockGroundTruthSource

        lead_steps = [int(s.strip()) for s in args.steps.split(",") if s.strip()]
        var_list = [v.strip() for v in args.variables.split(",") if v.strip()]

        lats = np.linspace(90.0, -90.0, 721)
        lons = np.linspace(0.0, 360.0, 1440, endpoint=False)

        eval_lats = np.linspace(90.0, -90.0, 32) if args.mock else lats
        eval_lons = np.linspace(0.0, 360.0, 64, endpoint=False) if args.mock else lons

        if args.reference:
            ref_path = Path(args.reference)
            if ref_path.suffix in [".nc", ".netcdf"]:
                ref_ds = xr.open_dataset(ref_path)
            elif ref_path.suffix == ".zarr":
                ref_ds = xr.open_zarr(ref_path)
            else:
                ref_raw = np.load(ref_path)
                ref_ds = (
                    {k: ref_raw[k] for k in ref_raw.files}
                    if hasattr(ref_raw, "files")
                    else {"t2m": ref_raw}
                )

            class DatasetGroundTruthSource:
                def __init__(self, ds: Any) -> None:
                    self.ds = ds

                def __call__(self, time: Any, variable: Any) -> np.ndarray:
                    var_name = variable[0] if isinstance(variable, list) else variable
                    if hasattr(self.ds, "__getitem__"):
                        data = self.ds[var_name]
                        if hasattr(data, "values"):
                            data = data.values
                        return np.expand_dims(data, axis=0) if data.ndim == 2 else data
                    return np.zeros((1, 1, 64, 64))

            gt_source = DatasetGroundTruthSource(ref_ds)
        elif args.mock or args.source == "mock":
            gt_source = MockGroundTruthSource(lats=eval_lats, lons=eval_lons, seed=42)
        elif args.source == "gfs":
            from earth2studio.data import GFS

            gt_source = GFS()
        elif args.source == "era5":
            from earth2studio.data import CDS_ERA5

            gt_source = CDS_ERA5()
        else:
            gt_source = MockGroundTruthSource(lats=eval_lats, lons=eval_lons, seed=42)

        # Load or generate forecast dataset
        if args.forecast:
            fc_p = Path(args.forecast)
            if fc_p.suffix in [".nc", ".netcdf"]:
                forecast_ds = xr.open_dataset(fc_p)
            elif fc_p.suffix == ".zarr":
                forecast_ds = xr.open_zarr(fc_p)
            else:
                raw = np.load(fc_p)
                forecast_ds = (
                    {k: raw[k] for k in raw.files}
                    if hasattr(raw, "files")
                    else {"t2m": raw}
                )
        else:
            # Deterministic mock multi-member ensemble dataset
            M = 5
            rng = np.random.default_rng(101)
            ds_dict = {}
            for var in var_list:
                cube = rng.uniform(
                    250.0,
                    310.0,
                    size=(len(lead_steps), M, len(eval_lats), len(eval_lons)),
                ).astype(np.float32)
                if var in ["w10m", "u10m", "v10m"]:
                    cube = rng.exponential(
                        scale=6.0,
                        size=(len(lead_steps), M, len(eval_lats), len(eval_lons)),
                    ).astype(np.float32)
                    cube[:, :, 0:3, 0:3] = 25.0
                elif var == "msl":
                    cube = rng.uniform(
                        99000.0,
                        103000.0,
                        size=(len(lead_steps), M, len(eval_lats), len(eval_lons)),
                    ).astype(np.float32)
                    cube[:, :, 0:2, 0:2] = 97500.0
                ds_dict[var] = cube

            forecast_ds = xr.Dataset(
                {
                    var: (
                        ["lead_time", "ensemble", "lat", "lon"],
                        ds_dict[var],
                    )
                    for var in var_list
                },
                coords={
                    "lead_time": np.array([np.timedelta64(h, "h") for h in lead_steps]),
                    "ensemble": np.arange(M),
                    "lat": eval_lats,
                    "lon": eval_lons,
                },
            )

        thresholds = {
            "w10m": float(args.threshold_wind),
            "u10m": float(args.threshold_wind),
            "v10m": float(args.threshold_wind),
            "tp": float(args.threshold_precip),
            "msl": 98000.0,
        }

        pipeline = EnsembleVerificationPipeline(
            ground_truth_source=gt_source,
            source_name=args.source if not args.reference else "reference_file",
            thresholds=thresholds,
            target_lats=eval_lats,
            fair_crps=True,
            correct_finite_ssr=True,
        )

        init_time = "2026-10-28T00:00:00"
        out_dir = args.output_dir or "outputs/earth2_001/verification"
        report = pipeline.verify_forecast_dataset(
            forecast_dataset=forecast_ds,
            init_time=init_time,
            lead_steps_hours=lead_steps,
            output_dir=out_dir,
        )

        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("\n" + "=" * 96)
            print("  OPERATIONAL ENSEMBLE VERIFICATION REPORT")
            print(
                "  Standard: e2s-014 (CRPS, SSR, EDI, SEDI) | Attribution: Zhane Daye, Origin Datum"
            )
            print("=" * 96)
            print(
                f"Ground Truth Source: {args.source.upper()} | Status: {report.get('verification_status')}"
            )
            print(f"Lead Time Steps: {', '.join(f'{h}h' for h in lead_steps)}")

            # Extract aggregate metrics across variables and steps
            for var, var_data in report.get("variables", {}).items():
                print(f"\n▸ Variable: {var.upper()}")
                for step_eval in var_data.get("lead_trajectory", []):
                    lh = step_eval.get("lead_hours")
                    det = step_eval.get("deterministic_metrics", {})
                    prob = step_eval.get("probabilistic_metrics", {})
                    ext = step_eval.get("extreme_threshold_metrics")
                    ext_str = ""
                    if ext and "ensemble_mean" in ext:
                        ext_str = f" | EDI = {ext['ensemble_mean'].get('edi', 'N/A')}, SEDI = {ext['ensemble_mean'].get('sedi', 'N/A')}"
                    print(
                        f"  • {lh}h: RMSE = {det.get('rmse')}, TAC = {det.get('tac')}, "
                        f"CRPS = {prob.get('crps_standard')}, SSR = {prob.get('ssr_corrected')} ({prob.get('calibration_status')}){ext_str}"
                    )

            seal = report.get("sha256_integrity_seal", "N/A")
            print(
                f"\n[*] Report saved to: {Path(out_dir) / 'verification_report.json'}"
            )
            print(f"[*] Integrity Seal: SHA-256:{seal}")
            print("=" * 96 + "\n")
    elif args.command == "api":
        from od_experiments.earth2_001.api.artifact_processor import (
            ForecastArtifactProcessor,
        )
        from od_experiments.earth2_001.api.fourcastnet_hosted import (
            ForecastRequest,
            FourCastNetHostedClient,
        )

        client = FourCastNetHostedClient()

        if args.api_command == "doctor":
            print("[*] Checking NVIDIA Hosted FourCastNet API Configuration:")
            print(f"  • Endpoint: {client.endpoint}")
            print(f"  • Key: {client.get_masked_key()}")
            try:
                # Issue lightweight validation probe
                req = ForecastRequest(input_id=0, variables="t2m", simulation_length=1)
                resp = client.infer(req)
                print(f"  • Connection: SUCCESS (HTTP {resp.status_code})")
                print(f"  • NVCF Request ID: {resp.req_id}")
                print(f"  • NVCF Status: {resp.nvcf_status}")
            except Exception as e:
                print(f"  • Connection Error: {e}")
        elif args.api_command == "infer":
            req = ForecastRequest(
                input_id=args.input_id,
                variables=args.variables,
                simulation_length=args.steps,
                ensemble_size=args.ensemble_size,
            )
            print(
                f"[*] Submitting FourCastNet hosted inference (input_id={req.input_id}, vars={req.variables}, steps={req.simulation_length})..."
            )
            resp = client.infer(req)
            out_path = Path(args.output_dir)
            proc = ForecastArtifactProcessor(out_path)
            artifacts = proc.process_response(req, resp, test_id="CLI")
            print(
                f"[✓] Inference successful (HTTP {resp.status_code}, NVCF Reqid: {resp.req_id})"
            )
            print(f"Saved {len(artifacts)} artifact(s) to {out_path}:")
            for a in artifacts:
                print(
                    f"  • {a.filename} (SHA-256: {a.sha256[:16]}..., size: {a.size_bytes} bytes)"
                )
        elif args.api_command == "tests":
            import subprocess

            print("[*] Running official 18-test live API verification suite...")
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                "od_experiments/tests/test_fourcastnet_live.py",
                "-v",
                "-s",
            ]
            res = subprocess.run(cmd)  # noqa: S603
            sys.exit(res.returncode)
        else:
            api_parser.print_help()
    elif args.command == "run":
        from od_experiments.earth2_001.forecast import run_forecast

        res = run_forecast(
            config_path=args.config,
            output_dir=args.output_dir,
            device=args.device,
            override_source=args.source,
        )
        print("\n[✓] FORECAST COMPLETED SUCCESSFULLY")
        print(f"Classification: {res['classification']}")
        print(f"Output Directory: {res['output_directory']}")
        print(f"Artifacts generated: {len(res['manifest']['artifacts'])}")
        print(f"Validation Status: {res['validation'].get('validation_status')}")
        if res["validation"].get("validation_status") == "VALIDATED":
            for var, metrics in res["validation"]["metrics"].items():
                print(
                    f"  • {var.upper()}: MAE = {metrics['mae']}, RMSE = {metrics['rmse']}, Mean Bias = {metrics['mean_bias']}"
                )
        else:
            print(f"  Reason: {res['validation'].get('reason')}")
    elif args.command == "validate":
        from od_experiments.earth2_001.validate import evaluate_forecast

        out_dir = Path(args.output_dir)
        fc_dict = {}
        rf_dict = {}

        if args.forecast:
            fc_path = Path(args.forecast)
            if not fc_path.exists():
                print(f"[!] Error: Forecast file {fc_path} not found.")
                sys.exit(1)
            fc_dict["var"] = np.load(fc_path)
        else:
            fc_files = list(out_dir.glob("forecast_*.npy"))
            if not fc_files:
                print(
                    f"[!] Error: No forecast_*.npy files found in {out_dir}. Run 'run' subcommand first."
                )
                sys.exit(1)
            for f in fc_files:
                var_name = f.stem.replace("forecast_", "")
                fc_dict[var_name] = np.load(f)

        if args.reference:
            rf_path = Path(args.reference)
            if not rf_path.exists():
                print(f"[!] Error: Reference file {rf_path} not found.")
                sys.exit(1)
            rf_dict["var"] = np.load(rf_path)
        else:
            rf_files = list(out_dir.glob("reference_*.npy"))
            if not rf_files:
                print(f"[!] Error: No reference_*.npy files found in {out_dir}.")
                sys.exit(1)
            for f in rf_files:
                var_name = f.stem.replace("reference_", "")
                rf_dict[var_name] = np.load(f)

        lats = (
            np.load(args.lats)
            if args.lats and Path(args.lats).exists()
            else np.linspace(90, -90, 721)
        )

        val_res = evaluate_forecast(
            fc_dict, rf_dict if rf_dict else None, lats=lats, output_dir=out_dir
        )
        print("[✓] VALIDATION COMPLETED:")
        print(f"Status: {val_res.get('validation_status')}")
        if val_res.get("validation_status") == "VALIDATED":
            for var, metrics in val_res.get("metrics", {}).items():
                print(
                    f"  • {var.upper()}: MAE = {metrics['mae']}, RMSE = {metrics['rmse']}, Mean Bias = {metrics['mean_bias']}"
                )
        else:
            print(f"  Note: {val_res.get('reason')}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
