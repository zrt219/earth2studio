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

"""Historical runner entry point alias (QUARANTINED_DEFECTIVE_SYNTHETIC).

CLASSIFICATION: QUARANTINED_DEFECTIVE_SYNTHETIC (TRUTH_CONDITIONED_SYNTHETIC_DIAGNOSTIC)
"""

from __future__ import annotations

from od_experiments.scientific_study.historical.study_runner_historical import (
    QUARANTINE_STAMP,
    REPORT_PATH,
    STUDY_OUTPUT_DIR,
    assert_quarantine_stamped,
    fetch_cycle_pair,
    get_evaluation_cycles,
    main,
    run_full_study,
    stamp_quarantined_dict,
    write_scientific_report,
)

__all__ = [
    "QUARANTINE_STAMP",
    "REPORT_PATH",
    "STUDY_OUTPUT_DIR",
    "assert_quarantine_stamped",
    "fetch_cycle_pair",
    "get_evaluation_cycles",
    "main",
    "run_full_study",
    "stamp_quarantined_dict",
    "write_scientific_report",
]

if __name__ == "__main__":
    main()
