# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

"""Generate 10+ high-resolution 3D perspective renders of Italy & Japan using authentic GFS data."""

from pathlib import Path
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "scientific_study_verified" / "figures" / "3d_regions"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Load verified GFS initial condition and 24h verification fields
fc_path = ROOT / "outputs" / "scientific_study_verified" / "forecast" / "forecast_t2m.npy"
truth_path = ROOT / "outputs" / "scientific_study_verified" / "verification" / "verifying_truth_t2m.npy"

t2m_global = np.load(fc_path) - 273.15  # Celsius, shape (721, 1440)
truth_global = np.load(truth_path) - 273.15
tend_global = truth_global - t2m_global

# Latitudes: 90 down to -90, Longitudes: 0 to 360
lats_global = np.linspace(90, -90, 721)
lons_global = np.linspace(0, 360, 1440, endpoint=False)

def extract_box(lat_min, lat_max, lon_min, lon_max):
    lat_idx = np.where((lats_global >= lat_min) & (lats_global <= lat_max))[0]
    lon_idx = np.where((lons_global >= lon_min) & (lons_global <= lon_max))[0]
    
    # Sort lat ascending for smooth 3D surfaces
    if lats_global[lat_idx[0]] > lats_global[lat_idx[-1]]:
        lat_idx = lat_idx[::-1]
        
    sub_lats = lats_global[lat_idx]
    sub_lons = lons_global[lon_idx]
    sub_t2m = t2m_global[np.ix_(lat_idx, lon_idx)]
    sub_tend = tend_global[np.ix_(lat_idx, lon_idx)]
    
    return sub_lats, sub_lons, sub_t2m, sub_tend

# Box 1: Italy / Central Mediterranean: lat 35 to 48, lon 6 to 19
it_lats, it_lons, it_t2m, it_tend = extract_box(34.0, 48.5, 5.0, 20.0)

# Box 2: Japan / Western Pacific: lat 30 to 46, lon 128 to 146
jp_lats, jp_lons, jp_t2m, jp_tend = extract_box(29.0, 46.5, 127.0, 147.0)

print(f"Extracted Italy: {it_t2m.shape}, Japan: {jp_t2m.shape}")

def render_3d_surface(lons, lats, field, title, fname, z_label="Elevation / Relief", 
                      cmap="turbo", vmin=None, vmax=None, elev=30, azim=-60, exaggeration=1.0):
    LON, LAT = np.meshgrid(lons, lats)
    Z = (field - np.nanmean(field)) * exaggeration
    
    fig = plt.figure(figsize=(11, 8.5), facecolor="#0a0a0f")
    ax = fig.add_subplot(111, projection="3d", facecolor="#0a0a0f")
    
    if vmin is None: vmin = np.nanpercentile(field, 2)
    if vmax is None: vmax = np.nanpercentile(field, 98)
    
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    colors = plt.get_cmap(cmap)(norm(field))
    
    surf = ax.plot_surface(LON, LAT, Z, facecolors=colors, rstride=1, cstride=1, 
                           antialiased=True, shade=True, alpha=0.95)
    
    ax.view_init(elev=elev, azim=azim)
    ax.set_xlabel("Longitude (°E)", color="white", fontsize=9, labelpad=8)
    ax.set_ylabel("Latitude (°N)", color="white", fontsize=9, labelpad=8)
    ax.set_zlabel(z_label, color="white", fontsize=9, labelpad=8)
    ax.tick_params(colors="gray", labelsize=8)
    
    # Stylize 3D panes
    ax.xaxis.pane.set_edgecolor("#222233")
    ax.yaxis.pane.set_edgecolor("#222233")
    ax.zaxis.pane.set_edgecolor("#222233")
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    
    # Title & Colorbar
    plt.title(title, color="white", fontsize=12, fontweight="bold", pad=15)
    
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, shrink=0.55, aspect=20, pad=0.08)
    cbar.set_label(title.split("\n")[-1], color="white", fontsize=9, fontweight="bold")
    cbar.ax.tick_params(colors="white", labelsize=8)
    
    out_file = OUT_DIR / fname
    plt.savefig(out_file, dpi=250, bbox_inches="tight", facecolor="#0a0a0f")
    plt.close(fig)
    print(f"[✓] Saved {fname}")

def render_3d_globe_view(center_lat, center_lon, fname, title, elev=30, azim=0):
    R = 6371.0
    step = 4
    sub_t2m = t2m_global[::step, ::step]
    lats = np.linspace(90, -90, sub_t2m.shape[0]) * np.pi / 180.0
    lons = np.linspace(0, 360, sub_t2m.shape[1]) * np.pi / 180.0
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    X = R * np.cos(lat_grid) * np.cos(lon_grid)
    Y = R * np.cos(lat_grid) * np.sin(lon_grid)
    Z = R * np.sin(lat_grid)
    
    fig = plt.figure(figsize=(10, 8.5), facecolor="black")
    ax = fig.add_subplot(111, projection="3d", facecolor="black")
    
    norm = plt.Normalize(vmin=-40, vmax=35)
    colors = plt.cm.turbo(norm(sub_t2m))
    
    surf = ax.plot_surface(X, Y, Z, facecolors=colors, rstride=1, cstride=1, antialiased=True, shade=False)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    
    sm = plt.cm.ScalarMappable(cmap="turbo", norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", shrink=0.5, pad=0.02, aspect=25)
    cbar.set_label("Surface Temperature T2m (°C)", color="white", fontsize=9, fontweight="bold")
    cbar.ax.tick_params(labelsize=8, colors="white")
    
    plt.title(title, color="white", fontsize=12, fontweight="bold", pad=10)
    out_file = OUT_DIR / fname
    plt.savefig(out_file, dpi=250, bbox_inches="tight", facecolor="black")
    plt.close(fig)
    print(f"[✓] Saved {fname}")

print("Rendering 10 3D Regional Atmospheric Images...")

# --- ITALY / CENTRAL MEDITERRANEAN (5 RENDERS) ---
# 1. Oblique Temperature Relief
render_3d_surface(it_lons, it_lats, it_t2m,
                  "Central Mediterranean (Italy): 3D Oblique Thermal Relief\nSurface Temperature T2m (°C)",
                  "01_italy_3d_oblique_t2m.png", cmap="turbo", elev=35, azim=-55, exaggeration=0.15)

# 2. 24h Diurnal Tendency Relief
render_3d_surface(it_lons, it_lats, it_tend,
                  "Central Mediterranean (Italy): 3D 24h Atmospheric Tendency\nΔT = T(t+24h) - T(t0) (°C)",
                  "02_italy_3d_tendency_relief.png", cmap="coolwarm", vmin=-5, vmax=5, elev=28, azim=-40, exaggeration=0.35)

# 3. High-Angle Thermal Bathymetry
render_3d_surface(it_lons, it_lats, it_t2m,
                  "Central Mediterranean: High-Angle Nadir Coastal Thermal Gradient\nSurface Temperature T2m (°C)",
                  "03_italy_3d_coastal_thermal.png", cmap="plasma", elev=65, azim=-80, exaggeration=0.1)

# 4. Alpine Horizon Front Perspective
render_3d_surface(it_lons, it_lats, it_t2m,
                  "Central Mediterranean: Alpine Front Low-Horizon View\nSurface Temperature T2m (°C)",
                  "04_italy_3d_alpine_front.png", cmap="magma", elev=18, azim=-30, exaggeration=0.25)

# 5. European / Mediterranean Spherical Macro Globe
render_3d_globe_view(42, 12, "05_italy_3d_synoptic_globe.png",
                     "3D Synoptic Spherical Perspective: Europe & Mediterranean\n(Focus: Italy / Tyrrhenian Sea at 42°N, 12°E)",
                     elev=35, azim=15)

# --- JAPAN / WESTERN PACIFIC (5 RENDERS) ---
# 6. Oblique Temperature Relief
render_3d_surface(jp_lons, jp_lats, jp_t2m,
                  "Western Pacific (Japan): 3D Oblique Thermal Relief\nSurface Temperature T2m (°C)",
                  "06_japan_3d_oblique_t2m.png", cmap="turbo", elev=32, azim=-50, exaggeration=0.15)

# 7. 24h Diurnal Tendency Relief
render_3d_surface(jp_lons, jp_lats, jp_tend,
                  "Western Pacific (Japan): 3D 24h Atmospheric Tendency\nΔT = T(t+24h) - T(t0) (°C)",
                  "07_japan_3d_tendency_relief.png", cmap="coolwarm", vmin=-5, vmax=5, elev=28, azim=-45, exaggeration=0.35)

# 8. High-Angle Baroclinic Trough
render_3d_surface(jp_lons, jp_lats, jp_t2m,
                  "Western Pacific: Baroclinic Frontal Trough & Coastal Sea Gradient\nSurface Temperature T2m (°C)",
                  "08_japan_3d_baroclinic_trough.png", cmap="viridis", elev=55, azim=-70, exaggeration=0.12)

# 9. Pacific Marine Horizon Boundary
render_3d_surface(jp_lons, jp_lats, jp_t2m,
                  "Western Pacific: Low-Horizon Marine Boundary Layer Perspective\nSurface Temperature T2m (°C)",
                  "09_japan_3d_marine_boundary.png", cmap="inferno", elev=16, azim=-25, exaggeration=0.22)

# 10. East Asian / Western Pacific Spherical Macro Globe
render_3d_globe_view(36, 138, "10_japan_3d_synoptic_globe.png",
                     "3D Synoptic Spherical Perspective: Western Pacific Rim\n(Focus: Japan / Kuroshio Current at 36°N, 138°E)",
                     elev=30, azim=138)

print("All 10 3D Regional Atmospheric Renders successfully generated!")
