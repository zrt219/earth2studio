# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-FileCopyrightText: All rights reserved.
# SPDX-FileCopyrightText: Copyright (c) 2026 Zhane Daye (zhanedaye@umattr.ca)
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
4K Geospatially-Aligned Globe Texture Pipeline for Earth-2 X-Band SAR & InSAR Mission Twin.

Fixes the historical 180-degree longitude misalignment (GFS [0, 360) -> SphereGeometry [-180, +180])
and replaces the temperature-derived elevation image with genuine ETOPO topography, NASA Blue Marble
satellite relief, ocean specular/roughness masking, and 4K (4096x2048) GFS atmospheric overlays.

Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
import matplotlib
import numpy as np
from loguru import logger
from PIL import Image, ImageFilter
from scipy.ndimage import sobel, zoom

TARGET_WIDTH = 4096
TARGET_HEIGHT = 2048

BASE_ASSETS = {
    "blue_marble": "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
    "topology": "https://unpkg.com/three-globe/example/img/earth-topology.png",
    "water": "https://unpkg.com/three-globe/example/img/earth-water.png",
}


def _fetch_asset(url: str, cache_dir: Path, filename: str) -> Path:
    dest = cache_dir / filename
    if dest.exists() and dest.stat().st_size > 10_000:
        return dest
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Only HTTPS asset URLs are permitted, got {parsed.scheme!r}")
    logger.info(f"Fetching public-domain Earth reference asset: {url}")
    resp = httpx.get(
        url,
        headers={"User-Agent": "Earth2-SAR-Twin/1.0"},
        follow_redirects=True,
        timeout=30.0,
    )
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def _load_or_build_gfs_fields(verified_root: Path) -> tuple[np.ndarray, np.ndarray]:
    init_path = verified_root / "forecast" / "initial_condition.npy"
    truth_path = verified_root / "verification" / "verifying_truth_t2m.npy"
    if init_path.exists() and truth_path.exists():
        logger.info("Loading verified NOAA GFS 0.25 deg global T2m tensors...")
        t0 = np.load(init_path).astype(np.float64)
        t24 = np.load(truth_path).astype(np.float64)
    else:
        logger.warning("Verified GFS tensors not found; using deterministic baroclinic reference.")
        lats = np.linspace(90.0, -90.0, 721)[:, None]
        lons = np.linspace(0.0, 360.0, 1440, endpoint=False)[None, :]
        lat_r = np.deg2rad(lats)
        lon_r = np.deg2rad(lons)
        t0 = 284.0 + 18.0 * np.cos(lat_r) + 4.5 * np.sin(2.0 * lat_r) * np.cos(3.0 * lon_r)
        t24 = (
            284.0
            + 18.0 * np.cos(lat_r)
            + 4.5 * np.sin(2.0 * lat_r) * np.cos(3.0 * (lon_r - np.deg2rad(12.0)))
        )

    # CRITICAL FIX: NOAA GFS stores longitudes [0, 360). Three.js SphereGeometry UV maps
    # u=0.0 -> -180 (Dateline), u=0.5 -> 0 (Greenwich), u=1.0 -> +180 (Dateline).
    # Roll horizontally by W//2 so GFS data aligns pixel-for-pixel with Blue Marble & 3D pins.
    t0_aligned = np.roll(t0, t0.shape[1] // 2, axis=1)
    t24_aligned = np.roll(t24, t24.shape[1] // 2, axis=1)
    return t0_aligned, t24_aligned


def _compute_hillshade(elev_norm: np.ndarray, azimuth_deg: float = 315.0, alt_deg: float = 45.0) -> np.ndarray:
    az = np.deg2rad(azimuth_deg)
    alt = np.deg2rad(alt_deg)
    dy = sobel(elev_norm, axis=0) * 1.4
    dx = sobel(elev_norm, axis=1) * 1.4
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dy, dx)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(0.55 + 0.55 * shade, 0.35, 1.25)


def build_4k_textures(
    output_dir: Path | str = "viewer_app/public/textures",
    verified_root: Path | str = "outputs/scientific_study_verified",
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    v_root = Path(verified_root)

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        bm_path = _fetch_asset(BASE_ASSETS["blue_marble"], cache_dir, "earth-blue-marble.jpg")
        topo_path = _fetch_asset(BASE_ASSETS["topology"], cache_dir, "earth-topology.png")
        water_path = _fetch_asset(BASE_ASSETS["water"], cache_dir, "earth-water.png")

        # 1. Load and upscale NASA Blue Marble, ETOPO Topology, and Water Mask to 4K (4096x2048)
        bm_img = Image.open(bm_path).convert("RGB").resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        topo_img = Image.open(topo_path).convert("L").resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        water_img = Image.open(water_path).convert("L").resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)

    bm_arr = np.asarray(bm_img, dtype=np.float32) / 255.0
    topo_arr = np.asarray(topo_img, dtype=np.float32) / 255.0
    water_arr = np.asarray(water_img, dtype=np.float32) / 255.0  # 1.0 = ocean water, 0.0 = land

    # Extract crisp coastline contours from the land/water boundary
    water_edge_img = water_img.filter(ImageFilter.FIND_EDGES)
    coast_mask = np.clip((np.asarray(water_edge_img, dtype=np.float32) / 255.0) * 1.4, 0.0, 1.0)

    # Compute genuine topographic hillshade from ETOPO relief
    hillshade = _compute_hillshade(topo_arr)

    # 2. Build 4K Aerospace Dark-Slate GEOINT Satellite Base (earth_satellite_4k.jpg)
    # Enhances land/ocean contrast & crisp cyan-tinted coastlines so SAR swaths & fringes pop cleanly
    ocean_mask = water_arr[..., None]
    land_mask = 1.0 - ocean_mask

    sat_land = bm_arr * (0.72 + 0.38 * hillshade[..., None])
    # Slightly deepen ocean saturation into dark aerospace navy/slate for SAR readability
    sat_ocean = bm_arr * np.array([0.48, 0.58, 0.72], dtype=np.float32)
    sat_rgb = sat_land * land_mask + sat_ocean * ocean_mask
    # Add crisp subtle teal-white coastline rim
    sat_rgb = np.clip(sat_rgb + coast_mask[..., None] * np.array([0.12, 0.24, 0.30], dtype=np.float32), 0.0, 1.0)

    sat_out = out / "earth_satellite_4k.jpg"
    Image.fromarray((sat_rgb * 255).astype(np.uint8)).save(sat_out, quality=94, optimize=True)

    # 3. Save genuine 4K ETOPO elevation bump map (earth_elevation.jpg)
    elev_enhanced = np.clip((topo_arr - 0.05) * 1.15, 0.0, 1.0)
    elev_out = out / "earth_elevation.jpg"
    Image.fromarray((elev_enhanced * 255).astype(np.uint8)).save(elev_out, quality=92, optimize=True)

    # 4. Save 4K Ocean/Land Roughness Map (earth_roughness.jpg)
    # Smooth specular water (~0.26 -> 66), matte terrain (~0.88 -> 224)
    rough_arr = 0.26 * water_arr + 0.88 * (1.0 - water_arr)
    rough_out = out / "earth_roughness.jpg"
    Image.fromarray((np.clip(rough_arr, 0.0, 1.0) * 255).astype(np.uint8)).save(rough_out, quality=90, optimize=True)

    # 5. Upsample [-180, +180] aligned NOAA GFS T2m and Tendency fields to 4K
    t0_aligned, t24_aligned = _load_or_build_gfs_fields(v_root)
    scale_y = TARGET_HEIGHT / t0_aligned.shape[0]
    scale_x = TARGET_WIDTH / t0_aligned.shape[1]

    t0_4k = zoom(t0_aligned, (scale_y, scale_x), order=3)
    dt_4k = zoom(t24_aligned - t0_aligned, (scale_y, scale_x), order=3)

    # Render T2m with Turbo colormap + subtle topographic hillshade + crisp dark coastlines
    turbo = matplotlib.colormaps["turbo"]
    t2m_norm = np.clip((t0_4k - 228.0) / (313.0 - 228.0), 0.0, 1.0)
    t2m_rgba = turbo(t2m_norm)[..., :3].astype(np.float32)
    t2m_shaded = t2m_rgba * (0.82 * ocean_mask + (0.65 + 0.42 * hillshade[..., None]) * land_mask)
    # Crisp dark-slate coastline borders + subtle Blue Marble texture bleed on land
    t2m_shaded = t2m_shaded * (1.0 - 0.16 * land_mask) + bm_arr * (0.16 * land_mask)
    t2m_shaded = t2m_shaded * (1.0 - 0.55 * coast_mask[..., None]) + np.array([0.08, 0.12, 0.18], dtype=np.float32) * (0.55 * coast_mask[..., None])

    t2m_out = out / "earth_t2m.jpg"
    Image.fromarray((np.clip(t2m_shaded, 0.0, 1.0) * 255).astype(np.uint8)).save(t2m_out, quality=93, optimize=True)

    # Render 24h Tendency (RdBu_r) + topographic hillshade + crisp coastlines
    rdbu = matplotlib.colormaps["RdBu_r"]
    dt_norm = np.clip((dt_4k + 12.0) / 24.0, 0.0, 1.0)
    dt_rgba = rdbu(dt_norm)[..., :3].astype(np.float32)
    dt_shaded = dt_rgba * (0.88 * ocean_mask + (0.68 + 0.36 * hillshade[..., None]) * land_mask)
    dt_shaded = dt_shaded * (1.0 - 0.18 * land_mask) + bm_arr * (0.18 * land_mask)
    dt_shaded = dt_shaded * (1.0 - 0.65 * coast_mask[..., None]) + np.array([0.06, 0.10, 0.16], dtype=np.float32) * (0.65 * coast_mask[..., None])

    tend_out = out / "earth_tendency.jpg"
    Image.fromarray((np.clip(dt_shaded, 0.0, 1.0) * 255).astype(np.uint8)).save(tend_out, quality=93, optimize=True)

    results = {
        "earth_satellite_4k": str(sat_out),
        "earth_t2m": str(t2m_out),
        "earth_tendency": str(tend_out),
        "earth_elevation": str(elev_out),
        "earth_roughness": str(rough_out),
    }
    logger.info(f"Generated 4K geospatially-aligned globe textures: {results}")
    return results


if __name__ == "__main__":
    build_4k_textures()
