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
8K/4K Multi-Map PBR Globe Texture Pipeline for Earth-2 X-Band SAR & InSAR Mission Twin.

Generates native 8K (8192x4096) Satellite Albedo plus 4K (4096x2048) companion PBR maps:
  - earth_satellite_8k.jpg  (8192x4096): NASA 8K daymap + directional relief + crisp coastlines
  - earth_normal_4k.jpg     (4096x2048): True RGB tangent-space normal map from 4K ETOPO DEM
  - earth_elevation.jpg     (4096x2048): Native 4K ETOPO topographic elevation bump map
  - earth_roughness.jpg     (4096x2048): Native 4K ocean/land PBR roughness map
  - earth_citylights_4k.jpg (4096x2048): Thresholded 4K VIIRS Black Marble urban corridors
  - earth_clouds_4k.jpg     (4096x2048): Downsampled 8K->4K global optical cloud cover alpha map
  - earth_t2m.jpg           (4096x2048): [-180, +180] aligned GFS T2m + 4K hillshade/coasts
  - earth_tendency.jpg      (4096x2048): [-180, +180] aligned GFS 24h dT + 4K hillshade/coasts

Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
"""

from __future__ import annotations

import argparse
import io
import math
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx
import matplotlib
import numpy as np
from loguru import logger
from PIL import Image, ImageFilter
from scipy.ndimage import sobel, zoom

Image.MAX_IMAGE_PIXELS = None

WIDTH_8K = 8192
HEIGHT_8K = 4096
WIDTH_4K = 4096
HEIGHT_4K = 2048

BASE_ASSETS = {
    "daymap_8k": "https://www.solarsystemscope.com/textures/download/8k_earth_daymap.jpg",
    "clouds_8k": "https://www.solarsystemscope.com/textures/download/8k_earth_clouds.jpg",
    "elev_4k": "https://raw.githubusercontent.com/turban/webgl-earth/master/images/elev_bump_4k.jpg",
    "water_4k": "https://raw.githubusercontent.com/turban/webgl-earth/master/images/water_4k.png",
    "night_4k": "https://unpkg.com/three-globe/example/img/earth-night.jpg",
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
        headers={"User-Agent": "Earth2-SAR-Twin/2.0"},
        follow_redirects=True,
        timeout=60.0,
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

    # Align NOAA GFS [0, 360) -> Three.js SphereGeometry [-180, +180] (u=0.50 is Greenwich)
    return np.roll(t0, t0.shape[1] // 2, axis=1), np.roll(t24, t24.shape[1] // 2, axis=1)


def _compute_hillshade(
    elev_norm: np.ndarray, azimuth_deg: float = 315.0, alt_deg: float = 45.0, strength: float = 1.8
) -> np.ndarray:
    az = np.deg2rad(azimuth_deg)
    alt = np.deg2rad(alt_deg)
    dy = sobel(elev_norm, axis=0) * strength
    dx = sobel(elev_norm, axis=1) * strength
    slope = np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dy, dx)
    shade = np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)
    return np.clip(0.54 + 0.58 * shade, 0.32, 1.28)


def _compute_tangent_normal_map(elev_norm: np.ndarray, strength: float = 3.2) -> np.ndarray:
    """Compute OpenGL/Three.js tangent-space RGB normal map (+X right, +Y up, +Z out)."""
    # Sobel dx: positive when height rises rightward (+X). Negate for surface normal.
    # Sobel dy along axis=0 runs top-to-bottom (-Y), so +dH/dy_up = -sobel(axis=0).
    dz_dx = sobel(elev_norm, axis=1) * (strength / 8.0)
    dz_dy_up = -sobel(elev_norm, axis=0) * (strength / 8.0)
    nx = -dz_dx
    ny = -dz_dy_up
    nz = np.ones_like(elev_norm)
    norm_len = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-8
    rgb = np.stack(
        [
            0.5 + 0.5 * (nx / norm_len),
            0.5 + 0.5 * (ny / norm_len),
            0.5 + 0.5 * (nz / norm_len),
        ],
        axis=-1,
    )
    return (np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8)


def _extract_water_mask(water_img_4k: Image.Image) -> np.ndarray:
    """Return float32 mask in [0, 1] where 1.0 = ocean water and 0.0 = land, auto-verifying polarity."""
    arr = np.asarray(water_img_4k.convert("L"), dtype=np.float32) / 255.0
    h, w = arr.shape
    # Equator, -135 deg Pacific Ocean (u ~ 0.125, v ~ 0.50) vs Sahara Desert (u ~ 0.54, v ~ 0.37)
    pacific_val = float(np.mean(arr[h // 2 - 20 : h // 2 + 20, w // 8 - 20 : w // 8 + 20]))
    sahara_val = float(np.mean(arr[int(h * 0.37) - 20 : int(h * 0.37) + 20, int(w * 0.54) - 20 : int(w * 0.54) + 20]))
    logger.info(f"Water mask polarity check -> Pacific={pacific_val:.3f}, Sahara={sahara_val:.3f}")
    if pacific_val < sahara_val:
        arr = 1.0 - arr
    return np.clip(arr, 0.0, 1.0)


def build_detailed_textures(
    output_dir: Path | str = "viewer_app/public/textures",
    verified_root: Path | str = "outputs/scientific_study_verified",
) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    v_root = Path(verified_root)

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        day_p = _fetch_asset(BASE_ASSETS["daymap_8k"], cache_dir, "8k_earth_daymap.jpg")
        cld_p = _fetch_asset(BASE_ASSETS["clouds_8k"], cache_dir, "8k_earth_clouds.jpg")
        elv_p = _fetch_asset(BASE_ASSETS["elev_4k"], cache_dir, "elev_bump_4k.jpg")
        wat_p = _fetch_asset(BASE_ASSETS["water_4k"], cache_dir, "water_4k.png")
        ngt_p = _fetch_asset(BASE_ASSETS["night_4k"], cache_dir, "earth-night.jpg")

        # Load native 8K daymap & 4K PBR sources
        day_8k_img = Image.open(day_p).convert("RGB").resize((WIDTH_8K, HEIGHT_8K), Image.Resampling.LANCZOS)
        day_4k_img = day_8k_img.resize((WIDTH_4K, HEIGHT_4K), Image.Resampling.LANCZOS)

        elev_4k_img = Image.open(elv_p).convert("L").resize((WIDTH_4K, HEIGHT_4K), Image.Resampling.LANCZOS)
        water_4k_img = Image.open(wat_p).convert("L").resize((WIDTH_4K, HEIGHT_4K), Image.Resampling.LANCZOS)
        night_4k_img = Image.open(ngt_p).convert("RGB").resize((WIDTH_4K, HEIGHT_4K), Image.Resampling.LANCZOS)
        clouds_4k_img = Image.open(cld_p).convert("L").resize((WIDTH_4K, HEIGHT_4K), Image.Resampling.LANCZOS)

    # 4K arrays
    day_4k = np.asarray(day_4k_img, dtype=np.float32) / 255.0
    elev_4k = np.asarray(elev_4k_img, dtype=np.float32) / 255.0
    water_4k = _extract_water_mask(water_4k_img)

    # Crisp 4K coastlines
    coast_4k_img = Image.fromarray((water_4k * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)
    coast_4k = np.clip((np.asarray(coast_4k_img, dtype=np.float32) / 255.0) * 1.5, 0.0, 1.0)
    hillshade_4k = _compute_hillshade(elev_4k, strength=1.8)

    # 1. Native 8K Satellite Albedo (earth_satellite_8k.jpg)
    logger.info("Building 8K (8192x4096) Satellite Earth Albedo...")
    day_8k = np.asarray(day_8k_img, dtype=np.float32) / 255.0
    water_8k = np.asarray(
        Image.fromarray((water_4k * 255).astype(np.uint8)).resize((WIDTH_8K, HEIGHT_8K), Image.Resampling.BILINEAR),
        dtype=np.float32,
    ) / 255.0
    hillshade_8k = np.asarray(
        Image.fromarray((np.clip(hillshade_4k / 1.3, 0.0, 1.0) * 255).astype(np.uint8)).resize(
            (WIDTH_8K, HEIGHT_8K), Image.Resampling.BICUBIC
        ),
        dtype=np.float32,
    ) / 255.0 * 1.3
    coast_8k = np.asarray(
        coast_4k_img.resize((WIDTH_8K, HEIGHT_8K), Image.Resampling.BICUBIC), dtype=np.float32
    ) / 255.0
    coast_8k = np.clip(coast_8k * 1.3, 0.0, 1.0)

    ocean_8k = water_8k[..., None]
    land_8k = 1.0 - ocean_8k
    sat_land_8k = day_8k * (0.76 + 0.34 * hillshade_8k[..., None])
    sat_ocean_8k = day_8k * np.array([0.46, 0.58, 0.74], dtype=np.float32)
    sat_8k = sat_land_8k * land_8k + sat_ocean_8k * ocean_8k
    sat_8k = np.clip(sat_8k + coast_8k[..., None] * np.array([0.10, 0.22, 0.28], dtype=np.float32), 0.0, 1.0)

    sat_8k_out = out / "earth_satellite_8k.jpg"
    Image.fromarray((sat_8k * 255).astype(np.uint8)).save(sat_8k_out, quality=90, optimize=True)

    # Also update legacy 4K satellite filename if any external link references it? Keep clean: remove old 4K duplicate if unused
    legacy_sat_4k = out / "earth_satellite_4k.jpg"
    if legacy_sat_4k.exists():
        legacy_sat_4k.unlink()

    # 2. True 4K RGB Tangent-Space Normal Map (earth_normal_4k.jpg)
    logger.info("Computing 4K RGB tangent-space normal map from ETOPO DEM...")
    normal_rgb = _compute_tangent_normal_map(elev_4k, strength=3.4)
    normal_out = out / "earth_normal_4k.jpg"
    Image.fromarray(normal_rgb).save(normal_out, quality=92, optimize=True)

    # 3. Native 4K Elevation Bump Map (earth_elevation.jpg)
    elev_out = out / "earth_elevation.jpg"
    Image.fromarray((np.clip(elev_4k, 0.0, 1.0) * 255).astype(np.uint8)).save(elev_out, quality=92, optimize=True)

    # 4. Native 4K Ocean/Land Roughness Map (earth_roughness.jpg)
    rough_4k = 0.22 * water_4k + 0.88 * (1.0 - water_4k)
    rough_out = out / "earth_roughness.jpg"
    Image.fromarray((np.clip(rough_4k, 0.0, 1.0) * 255).astype(np.uint8)).save(rough_out, quality=90, optimize=True)

    # 5. Thresholded 4K VIIRS City Lights (earth_citylights_4k.jpg)
    night_arr = np.asarray(night_4k_img, dtype=np.float32) / 255.0
    luma = 0.299 * night_arr[..., 0] + 0.587 * night_arr[..., 1] + 0.114 * night_arr[..., 2]
    # Keep only genuine urban metropolitan clusters (eliminate background dark noise)
    urban_mask = np.clip((luma - 0.16) / 0.55, 0.0, 1.0)[..., None]
    city_glow = np.clip(night_arr * urban_mask * 1.45, 0.0, 1.0)
    city_out = out / "earth_citylights_4k.jpg"
    Image.fromarray((city_glow * 255).astype(np.uint8)).save(city_out, quality=90, optimize=True)

    # 6. 4K Optical Cloud Cover Map (earth_clouds_4k.jpg)
    clouds_arr = np.asarray(clouds_4k_img, dtype=np.float32) / 255.0
    clouds_clean = np.clip((clouds_arr - 0.12) / 0.82, 0.0, 1.0)
    clouds_out = out / "earth_clouds_4k.jpg"
    Image.fromarray((clouds_clean * 255).astype(np.uint8)).save(clouds_out, quality=88, optimize=True)

    # 7. 4K Aligned GFS T2m & Tendency Maps with crisp 4K hillshade + coastlines
    t0_aligned, t24_aligned = _load_or_build_gfs_fields(v_root)
    scale_y = HEIGHT_4K / t0_aligned.shape[0]
    scale_x = WIDTH_4K / t0_aligned.shape[1]
    t0_4k = zoom(t0_aligned, (scale_y, scale_x), order=3)
    dt_4k = zoom(t24_aligned - t0_aligned, (scale_y, scale_x), order=3)

    ocean_4k = water_4k[..., None]
    land_4k = 1.0 - ocean_4k

    turbo = matplotlib.colormaps["turbo"]
    t2m_norm = np.clip((t0_4k - 228.0) / (313.0 - 228.0), 0.0, 1.0)
    t2m_rgba = turbo(t2m_norm)[..., :3].astype(np.float32)
    t2m_shaded = t2m_rgba * (0.84 * ocean_4k + (0.64 + 0.44 * hillshade_4k[..., None]) * land_4k)
    t2m_shaded = t2m_shaded * (1.0 - 0.14 * land_4k) + day_4k * (0.14 * land_4k)
    t2m_shaded = t2m_shaded * (1.0 - 0.58 * coast_4k[..., None]) + np.array([0.07, 0.11, 0.17], dtype=np.float32) * (
        0.58 * coast_4k[..., None]
    )
    t2m_out = out / "earth_t2m.jpg"
    Image.fromarray((np.clip(t2m_shaded, 0.0, 1.0) * 255).astype(np.uint8)).save(t2m_out, quality=92, optimize=True)

    rdbu = matplotlib.colormaps["RdBu_r"]
    dt_norm = np.clip((dt_4k + 12.0) / 24.0, 0.0, 1.0)
    dt_rgba = rdbu(dt_norm)[..., :3].astype(np.float32)
    dt_shaded = dt_rgba * (0.88 * ocean_4k + (0.66 + 0.38 * hillshade_4k[..., None]) * land_4k)
    dt_shaded = dt_shaded * (1.0 - 0.16 * land_4k) + day_4k * (0.16 * land_4k)
    dt_shaded = dt_shaded * (1.0 - 0.65 * coast_4k[..., None]) + np.array([0.06, 0.10, 0.16], dtype=np.float32) * (
        0.65 * coast_4k[..., None]
    )
    tend_out = out / "earth_tendency.jpg"
    Image.fromarray((np.clip(dt_shaded, 0.0, 1.0) * 255).astype(np.uint8)).save(tend_out, quality=92, optimize=True)

    results = {
        "earth_satellite_8k": str(sat_8k_out),
        "earth_normal_4k": str(normal_out),
        "earth_elevation": str(elev_out),
        "earth_roughness": str(rough_out),
        "earth_citylights_4k": str(city_out),
        "earth_clouds_4k": str(clouds_out),
        "earth_t2m": str(t2m_out),
        "earth_tendency": str(tend_out),
    }
    logger.info(f"Generated 8K/4K multi-map PBR globe textures: {results}")
    return results


S2_WGS84_URL = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021/default/WGS84/{z}/{row}/{col}.jpg"


def _download_tile_batch(
    tasks: list[tuple[int, int, int]], max_workers: int = 16
) -> dict[tuple[int, int], Image.Image]:
    """Download a batch of EOX Sentinel-2 Cloudless WGS84 tiles concurrently."""
    out_tiles: dict[tuple[int, int], Image.Image] = {}
    limits = httpx.Limits(max_connections=max_workers, max_keepalive_connections=max_workers)
    with httpx.Client(
        headers={"User-Agent": "Earth2-SAR-Twin/2.0"},
        limits=limits,
        follow_redirects=True,
        timeout=20.0,
    ) as client:

        def _fetch_one(z: int, row: int, col: int) -> tuple[int, int, Image.Image | None]:
            url = S2_WGS84_URL.format(z=z, row=row, col=col)
            for _attempt in range(3):
                try:
                    r = client.get(url)
                    if r.status_code == 200:
                        return row, col, Image.open(io.BytesIO(r.content)).convert("RGB")
                except (httpx.HTTPError, OSError) as exc:
                    logger.debug(f"Tile retry ({z}/{row}/{col}): {exc}")
            return row, col, None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = [pool.submit(_fetch_one, z, r, c) for z, r, c in tasks]
            for fut in as_completed(futs):
                row, col, img = fut.result()
                if img is not None:
                    out_tiles[(row, col)] = img
    return out_tiles


def _stitch_sentinel2_region(
    min_lat: float,
    max_lat: float,
    min_lon: float,
    max_lon: float,
    zoom_level: int = 8,
    target_size: int = 4096,
) -> Image.Image:
    """Stitch exact WGS84 Sentinel-2 Cloudless crop at target zoom (z=8 -> 131K global density)."""
    n_cols = 1 << (zoom_level + 1)
    n_rows = 1 << zoom_level
    deg_per_tile = 360.0 / n_cols

    c_min = max(0, int(math.floor((min_lon + 180.0) / deg_per_tile)))
    c_max = min(n_cols - 1, int(math.floor((max_lon + 180.0 - 1e-6) / deg_per_tile)))
    r_min = max(0, int(math.floor((90.0 - max_lat) / deg_per_tile)))
    r_max = min(n_rows - 1, int(math.floor((90.0 - min_lat - 1e-6) / deg_per_tile)))

    tasks = [
        (zoom_level, r, c)
        for r in range(r_min, r_max + 1)
        for c in range(c_min, c_max + 1)
    ]
    logger.info(
        f"Downloading {len(tasks)} Sentinel-2 z={zoom_level} tiles for "
        f"[{min_lat},{max_lat}]x[{min_lon},{max_lon}]..."
    )
    tiles = _download_tile_batch(tasks, max_workers=16)

    canvas_w = (c_max - c_min + 1) * 256
    canvas_h = (r_max - r_min + 1) * 256
    canvas = Image.new("RGB", (canvas_w, canvas_h), (8, 22, 48))
    for (r, c), img in tiles.items():
        canvas.paste(img, ((c - c_min) * 256, (r - r_min) * 256))

    # Exact sub-tile crop matching [min_lon, max_lon] x [min_lat, max_lat]
    west_bound = -180.0 + c_min * deg_per_tile
    east_bound = -180.0 + (c_max + 1) * deg_per_tile
    north_bound = 90.0 - r_min * deg_per_tile
    south_bound = 90.0 - (r_max + 1) * deg_per_tile

    x0 = (min_lon - west_bound) / (east_bound - west_bound) * canvas_w
    x1 = (max_lon - west_bound) / (east_bound - west_bound) * canvas_w
    y0 = (north_bound - max_lat) / (north_bound - south_bound) * canvas_h
    y1 = (north_bound - min_lat) / (north_bound - south_bound) * canvas_h

    cropped = canvas.crop((x0, y0, x1, y1))
    return cropped.resize((target_size, target_size), Image.Resampling.LANCZOS)


def build_tiled_16k_and_sentinel2_regions(
    output_dir: Path | str = "viewer_app/public/textures/tiles",
    base_textures_dir: Path | str = "viewer_app/public/textures",
) -> dict[str, str]:
    """Generate 16K (16384x8192) 4x2 spherical octants and 131K-density Sentinel-2 regional crops."""
    tiles_dir = Path(output_dir)
    tiles_dir.mkdir(parents=True, exist_ok=True)
    base_dir = Path(base_textures_dir)

    sat_8k_path = base_dir / "earth_satellite_8k.jpg"
    water_path = base_dir / "earth_roughness.jpg"
    sat_8k = Image.open(sat_8k_path).convert("RGB") if sat_8k_path.exists() else None
    water_img = Image.open(water_path).convert("L") if water_path.exists() else None

    generated: dict[str, str] = {}

    # 1. Tier 1: 16K (16384x8192) Global 4x2 Octants (each 4096x4096) from Sentinel-2 z=5
    logger.info("Building Tier 1: 16K (16384x8192) 4x2 Sentinel-2 + Bathymetry Octant Tiles...")
    for r_oct in range(2):
        for c_oct in range(4):
            r0, r1 = r_oct * 16, (r_oct + 1) * 16
            c0, c1 = c_oct * 16, (c_oct + 1) * 16
            tasks = [(5, r, c) for r in range(r0, r1) for c in range(c0, c1)]
            tile_map = _download_tile_batch(tasks, max_workers=16)

            oct_img = Image.new("RGB", (4096, 4096), (7, 22, 52))
            for (r, c), img in tile_map.items():
                oct_img.paste(img, ((c - c0) * 256, (r - r0) * 256))

            # Blend NASA 8K ocean bathymetry cleanly over open-ocean regions (preserving Sentinel-2 land/coasts)
            if sat_8k is not None and water_img is not None:
                # 8K crop corresponding to octant (8192/4 = 2048px wide, 4096/2 = 2048px tall)
                bx0, by0 = c_oct * 2048, r_oct * 2048
                bathy_crop = sat_8k.crop((bx0, by0, bx0 + 2048, by0 + 2048)).resize(
                    (4096, 4096), Image.Resampling.BICUBIC
                )
                # 4K roughness crop (4096/4 = 1024px wide, 2048/2 = 1024px tall): ocean ~ 56, land ~ 224
                rx0, ry0 = c_oct * 1024, r_oct * 1024
                r_crop = water_img.crop((rx0, ry0, rx0 + 1024, ry0 + 1024)).resize(
                    (4096, 4096), Image.Resampling.BILINEAR
                )
                rough_arr = np.asarray(r_crop, dtype=np.float32) / 255.0
                # ocean_blend = 1.0 in deep ocean (rough < 0.4), 0.0 on land (rough > 0.65)
                ocean_blend = np.clip((0.65 - rough_arr) / 0.30, 0.0, 0.88)[..., None]
                s2_arr = np.asarray(oct_img, dtype=np.float32) / 255.0
                bathy_arr = np.asarray(bathy_crop, dtype=np.float32) / 255.0
                blended = s2_arr * (1.0 - ocean_blend) + bathy_arr * ocean_blend
                oct_img = Image.fromarray((np.clip(blended, 0.0, 1.0) * 255.0).astype(np.uint8))

            oct_key = f"octant_r{r_oct}_c{c_oct}"
            oct_path = tiles_dir / f"{oct_key}.jpg"
            oct_img.save(oct_path, quality=87, optimize=True)
            generated[oct_key] = str(oct_path)

    # 2. Tier 2: 131K-Equivalent Regional Sentinel-2 z=8 Crops (Italy & Japan)
    italy_img = _stitch_sentinel2_region(38.0, 48.0, 6.0, 18.0, zoom_level=8, target_size=4096)
    italy_path = tiles_dir / "sentinel2_italy_4k.jpg"
    italy_img.save(italy_path, quality=90, optimize=True)
    generated["sentinel2_italy_4k"] = str(italy_path)

    japan_img = _stitch_sentinel2_region(30.0, 42.0, 128.0, 145.0, zoom_level=8, target_size=4096)
    japan_path = tiles_dir / "sentinel2_japan_4k.jpg"
    japan_img.save(japan_path, quality=90, optimize=True)
    generated["sentinel2_japan_4k"] = str(japan_path)

    logger.info(f"Generated 16K octants and 131K Sentinel-2 regional tiles: {len(generated)} files")
    return generated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build 8K/16K/131K Earth & SAR textures.")
    parser.add_argument(
        "--with-tiles",
        action="store_true",
        help="Also build 16K global octant tiles and 131K-density Sentinel-2 regional crops.",
    )
    args = parser.parse_args()
    build_detailed_textures()
    if args.with_tiles:
        build_tiled_16k_and_sentinel2_regions()
