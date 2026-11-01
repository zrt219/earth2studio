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
# Compliance: .agents/rules/e2s-014-scientific-integrity.mdc

"""Earth2-001 Verify Stage & Statistical/Cryptographic Anti-Leakage Guardrails.

Exposes the permanent statistical residual & correlation anomaly detector and
cryptographic `execution_manifest.json` sealing validator under
`od_experiments.earth2_001.verify_stage`.

Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
"""

from __future__ import annotations

from od_experiments.scientific_study.exceptions import (
    AntiLeakageError,
    ChronologyError,
    ModelIdentityMismatchError,
    ProvenanceIntegrityError,
    SyntheticSubstitutionError,
    TargetLeakageError,
)
from od_experiments.scientific_study.pipeline.verify_stage import (
    DEFAULT_VERIFIED_MANIFEST_PATH,
    compute_sha256,
    detect_residual_leakage_anomaly,
    seal_execution_manifest,
    validate_execution_manifest,
    verify_forecast,
)

__all__ = [
    "AntiLeakageError",
    "ChronologyError",
    "ModelIdentityMismatchError",
    "ProvenanceIntegrityError",
    "SyntheticSubstitutionError",
    "TargetLeakageError",
    "DEFAULT_VERIFIED_MANIFEST_PATH",
    "compute_sha256",
    "detect_residual_leakage_anomaly",
    "seal_execution_manifest",
    "validate_execution_manifest",
    "verify_forecast",
]
