# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
# SPDX-License-Identifier: Apache-2.0
"""Historical Research Artifacts Namespace (QUARANTINED_DEFECTIVE_SYNTHETIC).

CLASSIFICATION: QUARANTINED_DEFECTIVE_SYNTHETIC (TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC)

WARNING:
This package contains preserved historical prototypes evaluated in scientific_study_v2.
These modules contain known target leakage (future verifying truth directly injected
into synthetic forecast arrays) and model misattributions.
Preserved strictly for historical audit, provenance, and defect reproduction.
DO NOT USE AS EMPIRICAL BENCHMARKS.
"""

from .study_runner_historical import (
    QUARANTINE_STAMP,
    assert_quarantine_stamped,
    fetch_cycle_pair,
    run_full_study,
    stamp_quarantined_dict,
)

__all__ = [
    "QUARANTINE_STAMP",
    "assert_quarantine_stamped",
    "fetch_cycle_pair",
    "run_full_study",
    "stamp_quarantined_dict",
]
