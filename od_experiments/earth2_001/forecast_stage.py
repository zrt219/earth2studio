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

"""Earth2-001 Forecast Stage & Anti-Leakage Guardrail Interface.

Exposes the permanent runtime and AST anti-leakage guardrails for Stage A
forecast generation under `od_experiments.earth2_001.forecast_stage`.

Attribution: Zhane Daye, Origin Datum (https://origindatum.space, contact@origindatum.space)
"""

from __future__ import annotations

from od_experiments.scientific_study.exceptions import (
    AntiLeakageError,
    ForbiddenFutureAccessError,
    TargetLeakageError,
)
from od_experiments.scientific_study.pipeline.forecast_stage import (
    FORBIDDEN_AST_IDENTIFIERS,
    FORBIDDEN_TARGET_PARAMS,
    anti_leakage_forecast_guard,
    enforce_call_stack_isolation,
    inspect_callable_for_leakage,
    run_forecast,
)

__all__ = [
    "AntiLeakageError",
    "ForbiddenFutureAccessError",
    "TargetLeakageError",
    "FORBIDDEN_AST_IDENTIFIERS",
    "FORBIDDEN_TARGET_PARAMS",
    "anti_leakage_forecast_guard",
    "enforce_call_stack_isolation",
    "inspect_callable_for_leakage",
    "run_forecast",
]
