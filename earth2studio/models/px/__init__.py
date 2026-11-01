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
# Compliance: .agents/rules/e2s-009-prognostic-models.mdc, .agents/rules/e2s-014-scientific-integrity.mdc

import importlib
import warnings

from loguru import logger

# Core PrognosticModel protocol and core implementations
from earth2studio.models.px.base import PrognosticModel
from earth2studio.models.px.climax import ClimaX
from earth2studio.models.px.multi_model import MultiModelEnsemble
from earth2studio.models.px.persistence import Persistence

# Optional models loaded with exception handling so missing dependencies
# (e.g. zarr.abc, makani, weathernext) do not break the px package import
_OPTIONAL_MODELS: list[tuple[str, list[str]]] = [
    ("ace2", ["ACE2ERA5"]),
    ("aifs", ["AIFS"]),
    ("aifs2", ["AIFS2"]),
    ("aifs2ens", ["AIFS2ENS"]),
    ("aifsens", ["AIFSENS"]),
    ("atlas", ["Atlas"]),
    ("atlas_crps", ["AtlasCRPS"]),
    ("aurora", ["Aurora"]),
    (
        "aurora1p5",
        [
            "Aurora1p5",
            "Aurora1p5_6h",
            "Aurora1p5Ensemble",
            "Aurora1p5Ensemble_6h",
        ],
    ),
    ("camulator", ["CAMulator"]),
    ("cbottle_video", ["CBottleVideo"]),
    ("datareplay", ["DataReplay"]),
    ("dlesym", ["DLESyM", "DLESyMLatLon"]),
    (
        "dlesym_v0_isccp_era5",
        ["DLESyMv0_ISCCP_ERA5", "DLESyMv0_ISCCP_ERA5LatLon"],
    ),
    ("dlwp", ["DLWP"]),
    ("dxwrapper", ["DiagnosticWrapper"]),
    ("fcn", ["FCN"]),
    ("fcn3", ["FCN3"]),
    ("fengwu", ["FengWu"]),
    ("fuxi", ["FuXi"]),
    ("fuxi_s2s", ["FuXiS2S"]),
    ("gencast_mini", ["GenCastMini"]),
    ("graphcast_operational", ["GraphCastOperational"]),
    ("graphcast_small", ["GraphCastSmall"]),
    ("interpcrpsdit", ["InterpCRPSDiT"]),
    ("interpmodafno", ["InterpModAFNO"]),
    ("pangu", ["Pangu3", "Pangu6", "Pangu24"]),
    ("samudrace", ["SamudrACE"]),
    ("sfno", ["SFNO"]),
    ("stormcast", ["StormCast"]),
    ("stormcastconus", ["StormCastCONUS"]),
    ("stormscope", ["StormScopeGOES", "StormScopeMRMS"]),
    ("stormscope_meteosat", ["StormScopeMeteosatEU"]),
    ("ucast", ["UCast"]),
    (
        "weathernext2_cyclones",
        ["WeatherNext2Cyclones", "WeatherNext2CyclonesMini"],
    ),
]

for mod_name, class_names in _OPTIONAL_MODELS:
    try:
        mod = importlib.import_module(f"earth2studio.models.px.{mod_name}")
        for cls_name in class_names:
            if hasattr(mod, cls_name):
                globals()[cls_name] = getattr(mod, cls_name)
    except Exception as err:
        logger.trace(f"Optional model {mod_name} could not be loaded: {err}")

# Silence warning spam from various models
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=FutureWarning)
