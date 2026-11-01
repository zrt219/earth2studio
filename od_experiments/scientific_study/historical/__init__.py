# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Historical Research Artifacts Namespace.

CLASSIFICATION: TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC

WARNING:
This package contains preserved historical prototypes evaluated in scientific_study_v2.
These modules contain known target leakage (future verifying truth directly injected
into synthetic forecast arrays) and model misattributions.
Preserved strictly for historical audit, provenance, and defect reproduction.
DO NOT USE AS EMPIRICAL BENCHMARKS.
"""

from .study_runner_historical import fetch_cycle_pair, run_full_study

__all__ = ["run_full_study", "fetch_cycle_pair"]
