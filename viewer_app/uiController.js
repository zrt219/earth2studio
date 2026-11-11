// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * Earth-2 X-Band SAR & InSAR Mission Twin
 * Interactive User Interface Controller & Glassmorphic HUD
 *
 * Module: viewer_app/uiController.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Features:
 *   - Study Version Timeline Navigation (V1 Audit, V2 Decoupled, V3 7-Pillars)
 *   - 3-Column Version Comparison Modal with Scientific Metrics & Integrity Badges
 *   - Glassmorphic Interactive Layer Toggles HUD & Opacity Controls
 *   - Screen-Space Pinned POI Popup Card with Station/Storm Telemetry
 *   - Dynamic Colormap Legends (Turbo T2m, RdBu Tendency, Plasma Spread, Inferno DA)
 *   - Boresight Synoptic Camera Navigation
 */

import studyData from './studyData.js';
import windParticles from './windParticles.js';
import hazardAlerts from './hazardAlerts.js';
import sarTasking from './sarTasking.js';
import citySelector from './citySelector.js';
import explainerToolbar from './explainerToolbar.js';

// =============================================================================
// 1. UTILITIES & SECURITY SANITIZATION
// =============================================================================

/**
 * Defends against XSS / HTML injection in POI popups and modal content
 * Conforms to Tier 2 boundary test T2.14
 *
 * @param {string|number} str
 * @returns {string}
 */
export function sanitizeHTML(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Version integrity badge specification
 * Conforms to Tier 1 test F11.4
 *
 * @param {string} vId - 'V1', 'V2', 'V3'
 * @returns {{ label: string, variant: string, color: string }}
 */
export function getBadge(vId) {
  const norm = String(vId).toUpperCase();
  if (norm === 'V1') {
    return { label: 'LEAKAGE DETECTED', variant: 'danger', color: '#ef4444' };
  }
  if (norm === 'V2') {
    return { label: 'VERIFIED PHYSICAL BASELINE', variant: 'success', color: '#10b981' };
  }
  if (norm === 'V3') {
    return { label: '7-PILLAR SUITE', variant: 'primary', color: '#38bdf8' };
  }
  return { label: 'UNKNOWN', variant: 'secondary', color: '#64748b' };
}

// Module-level context
let activeGlobe = null;
let activeCamera = null;
let activeRenderer = null;
let activeLayers3D = null;
let isSpinningState = true;
let isReliefActiveState = true;
let activePopupPOI = null;
let isPlayingForecast = false;
let forecastStep = 0;
let forecastInterval = null;
let externalCallbacks = {};
let activePresetId = 'clean_globe';
let tooltipShowTimer = null;
let tooltipTargetEl = null;

const OVERLAY_KEYS = [
  'city_markers',
  'da_stations',
  'hazards',
  'cyclone',
  'mesoscale_insets',
  'ensemble_spread',
  'wind',
  'sar_tasking'
];

const OVERLAY_PRESETS = {
  clean_globe: {
    city_markers: false,
    da_stations: false,
    hazards: false,
    cyclone: false,
    mesoscale_insets: false,
    ensemble_spread: false,
    wind: false,
    sar_tasking: false,
    clouds: true,
    baseTexture: 'sat',
    lod: true,
    relief: true
  },
  sar_focus: {
    city_markers: true,
    da_stations: false,
    hazards: false,
    cyclone: false,
    mesoscale_insets: false,
    ensemble_spread: false,
    wind: false,
    sar_tasking: true,
    clouds: false
  },
  extreme_weather: {
    city_markers: false,
    da_stations: false,
    hazards: true,
    cyclone: true,
    mesoscale_insets: false,
    ensemble_spread: false,
    wind: true,
    sar_tasking: false,
    clouds: true
  },
  all_telemetry: {
    city_markers: true,
    da_stations: true,
    hazards: true,
    cyclone: true,
    mesoscale_insets: true,
    ensemble_spread: true,
    wind: true,
    sar_tasking: true,
    clouds: true
  },
  clear_all: {
    city_markers: false,
    da_stations: false,
    hazards: false,
    cyclone: false,
    mesoscale_insets: false,
    ensemble_spread: false,
    wind: false,
    sar_tasking: false,
    clouds: false
  }
};

export function setSceneCallbacks(callbacks = {}) {
  externalCallbacks = { ...externalCallbacks, ...callbacks };
}

// =============================================================================
// 2. DYNAMIC COLORMAP LEGENDS
// =============================================================================

/**
 * Updates dynamic colormap legend title, gradient bar, and min/max bounds
 * Conforms to F12.2, F12.3, T3.9
 *
 * @param {string} typeOrVersion - 'V1'|'V2'|'V3'|'t2m'|'tendency'|'spread'|'da'
 */
export function updateLegend(typeOrVersion = 'V3') {
  if (typeof document === 'undefined') return;

  const legendTitle = document.getElementById('legend-title');
  const legendBar = document.getElementById('legend-bar');
  const legendMin = document.getElementById('legend-min');
  const legendMax = document.getElementById('legend-max');

  if (!legendTitle || !legendBar) return;

  const key = String(typeOrVersion).toLowerCase();

  if (key === 'v1') {
    legendTitle.innerText = 'Synthetic Audit Diagnostic T2m (°C)';
    legendBar.style.background = 'linear-gradient(to right, #e11d48, #fbbf24)';
    if (legendMin) legendMin.innerText = '-45°C';
    if (legendMax) legendMax.innerText = '+38°C';
  } else if (key === 'v2') {
    legendTitle.innerText = 'NOAA GFS Physical Persistence T2m (°C)';
    legendBar.style.background = 'linear-gradient(to right, #30123b, #4686fb, #1ae4b6, #a2fc3c, #fbb41a, #e4460a, #7a0403)';
    if (legendMin) legendMin.innerText = '-45°C';
    if (legendMax) legendMax.innerText = '+38°C';
  } else if (key === 'v3' || key === 'spread' || key === 'ensemble') {
    legendTitle.innerText = 'Ensemble Spread & DA Increments (K)';
    legendBar.style.background = 'linear-gradient(to right, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)';
    if (legendMin) legendMin.innerText = '0.0 K';
    if (legendMax) legendMax.innerText = '1.5 K';
  } else if (key === 'sat' || key === 'satellite') {
    legendTitle.innerText = '8K NASA PBR Earth + 4K Normal/ETOPO & VIIRS Cities';
    legendBar.style.background = 'linear-gradient(to right, #061838, #14406b, #3a6b40, #9b8c5c, #f59e0b)';
    if (legendMin) legendMin.innerText = 'Ocean';
    if (legendMax) legendMax.innerText = 'Peaks / Cities';
  } else if (key === 't2m' || key === 'surface') {
    legendTitle.innerText = 'Surface Temperature (°C)';
    legendBar.style.background = 'linear-gradient(to right, #30123b, #4686fb, #1ae4b6, #a2fc3c, #fbb41a, #e4460a, #7a0403)';
    if (legendMin) legendMin.innerText = '-45°C';
    if (legendMax) legendMax.innerText = '+38°C';
  } else if (key === 'tendency' || key === 'tend' || key === 'delta') {
    legendTitle.innerText = '24h Tendency ΔT (°C)';
    legendBar.style.background = 'linear-gradient(to right, #3b4cc0, #8cb2f9, #f7f7f7, #f49a7b, #b40426)';
    if (legendMin) legendMin.innerText = '-6°C';
    if (legendMax) legendMax.innerText = '+6°C';
  } else if (key === 'da' || key === 'increment') {
    legendTitle.innerText = 'DA Analysis Increment (+3K to +8K)';
    legendBar.style.background = 'linear-gradient(to right, #000004, #51127c, #b63679, #fb8861, #fcfdbf)';
    if (legendMin) legendMin.innerText = '+3.0 K';
    if (legendMax) legendMax.innerText = '+8.0 K';
  } else if (key === 'sar' || key === 'insar' || key === 'aps') {
    legendTitle.innerText = 'X-Band InSAR Wrapped Phase [-π, +π] (λ=3.11 cm)';
    legendBar.style.background = 'linear-gradient(to right, #1f1447, #2694e0, #2ee0a6, #f5d138, #eb3861)';
    if (legendMin) legendMin.innerText = '-π rad';
    if (legendMax) legendMax.innerText = '+π rad';
  } else if (key === 'sar_flood' || key === 'flood_coherence') {
    legendTitle.innerText = 'SAR Flood Backscatter σ⁰ (dB) & Slope Coherence γ';
    legendBar.style.background = 'linear-gradient(to right, #05c7fa, #2e425c, #291f57, #fa3d52)';
    if (legendMin) legendMin.innerText = 'Flood <-16.5 dB';
    if (legendMax) legendMax.innerText = 'Hazard γ<0.32';
  }
}

// =============================================================================
// 3. SCREEN-SPACE GLASSMORPHIC POPUP CARD
// =============================================================================

/**
 * Displays glassmorphic popup card pinned to screen coordinates
 * Conforms to F9.5, T3.2, T3.10
 *
 * @param {object} rawPoiData - Station, Cyclone Waypoint, or SAR Satellite/Swath data
 * @param {{ x: number, y: number, visible?: boolean }} screenPos
 */
export function showPopup(rawPoiData, screenPos) {
  if (typeof document === 'undefined') return;

  const popup = document.getElementById('poi-popup-card') || document.getElementById('poi-popup');
  if (!popup) return;

  if (!rawPoiData) {
    hidePopup();
    return;
  }

  const poiData = (rawPoiData.data && typeof rawPoiData.data === 'object' && !rawPoiData.operator && !rawPoiData.wmoId && rawPoiData.mslp === undefined)
    ? { ...rawPoiData.data, type: rawPoiData.type || rawPoiData.data.type }
    : rawPoiData;

  activePopupPOI = poiData;

  const titleEl = document.getElementById('popup-title');
  const bodyEl = document.getElementById('popup-body');

  const isSar = Boolean(poiData.isSarSatellite || poiData.isSarSwath || poiData.operator === 'ICEYE' || poiData.operator === 'Synspective');
  const isCity = !isSar && Boolean(poiData.isTargetCity || poiData.type === 'target_city');
  const isStation = !isSar && !isCity && Boolean(poiData.increment !== undefined || poiData.wmoId || poiData.type?.includes('Sounding'));
  const isHazard = !isSar && !isCity && !isStation && Boolean(poiData.isHazardAlert || poiData.type === 'hazard_alert' || poiData.severity);

  const rawLat = poiData.lat !== undefined ? poiData.lat : poiData.center?.lat;
  const rawLon = poiData.lon !== undefined ? poiData.lon : poiData.center?.lon;
  const latVal = typeof rawLat === 'number' ? rawLat.toFixed(2) : (Number(rawLat) ? Number(rawLat).toFixed(2) : '0.00');
  const lonVal = typeof rawLon === 'number' ? rawLon.toFixed(2) : (Number(rawLon) ? Number(rawLon).toFixed(2) : '0.00');

  if (isSar) {
    if (titleEl) {
      titleEl.innerText = `🛰️ ${poiData.name || poiData.id || 'SAR Acquisition'}`;
    }
    if (bodyEl) {
      const aps = poiData.apsMetrics || {};
      const attr = poiData.attributionMetrics || {};
      const hazardLine = attr.hazardType === 'FLOOD_SPECULAR_BACKSCATTER'
        ? `Flood σ⁰ &lt; ${attr.thresholdDb} dB: <b>${attr.inundatedAreaKm2} km²</b> (min ${attr.minSigma0VvDb} dB)`
        : `Slope CCD γ &lt; ${attr.coherenceThreshold}: <b>${attr.highRiskSlopeAreaKm2} km²</b> (min γ=${attr.minCoherenceGamma})`;
      bodyEl.innerHTML = `
        <div style="font-size:0.75rem; line-height:1.45; color:#cbd5e1;">
          <div style="margin-bottom:4px;"><strong>Operator / Mode:</strong> ${sanitizeHTML(poiData.operator)} — ${sanitizeHTML(poiData.mode)}</div>
          <div style="margin-bottom:4px;"><strong>Geometry:</strong> ${sanitizeHTML(poiData.orbitState)} | Inc: <b>${poiData.incidenceAngleDeg}°</b> | 9.65 GHz</div>
          <div style="margin-bottom:4px;"><strong>CATALYST APS ZTD:</strong> ${aps.meanZtdM} m (${aps.fringesRemoved} fringes removed)</div>
          <div style="margin-bottom:4px;"><strong>InSAR Phase RMSE:</strong> <span style="color:#f43f5e;">${aps.uncorrectedRmseRad} rad</span> → <span style="color:#10b981; font-weight:700;">${aps.correctedRmseRad} rad (-${aps.rmseReductionPct}%)</span></div>
          <div><strong>Attribution:</strong> ${hazardLine}</div>
        </div>
      `;
    }
  } else if (isCity) {
    const cityLatPrecise = typeof rawLat === 'number' ? rawLat.toFixed(4) : latVal;
    const cityLonPrecise = typeof rawLon === 'number' ? rawLon.toFixed(4) : lonVal;
    if (titleEl) {
      titleEl.innerText = `📍 ${poiData.name || 'Target City'} (${poiData.country || 'Target'})`;
    }
    if (bodyEl) {
      bodyEl.innerHTML = `
        <div style="font-size:0.75rem; line-height:1.45; color:#cbd5e1;">
          <div style="margin-bottom:4px;"><strong>Corridor:</strong> ${sanitizeHTML(poiData.region || 'Verified 131K Domain')}</div>
          <div style="margin-bottom:4px;"><strong>Coordinates:</strong> ${cityLatPrecise}°N, ${cityLonPrecise}°E (Elev: <b>${poiData.elevM ?? 0} m</b>)</div>
          <div style="margin-bottom:4px;"><strong>Sensor Tasking:</strong> <span style="color:#38bdf8; font-weight:700;">${sanitizeHTML(poiData.sarSatelliteId || 'X-BAND')}</span> (Inc: ${poiData.incidenceAngleDeg ?? 30}°)</div>
          <div style="margin-bottom:4px;"><strong>CATALYST APS:</strong> ZTD <b>${poiData.apsZtdM ?? 'N/A'} m</b> | ${poiData.fringesRemoved ?? 'N/A'} fringes | <span style="color:#10b981; font-weight:700;">-${poiData.rmseReductionPct ?? 98}% RMSE</span></div>
          <div style="margin-bottom:4px;"><strong>Optical Surface:</strong> ${sanitizeHTML(poiData.sentinel2Lod || '131K Regional Crop')}</div>
          <div style="margin-top:5px; font-size:0.71rem; color:#94a3b8; border-top:1px solid rgba(255,255,255,0.08); padding-top:4px;">${sanitizeHTML(poiData.roleSummary || '')}</div>
        </div>
      `;
    }
  } else if (isStation) {
    if (titleEl) {
      titleEl.innerText = `${poiData.name || 'Station'} (${poiData.id || poiData.wmoId || 'N/A'})`;
    }
    if (bodyEl) {
      const inc = poiData.increment !== undefined ? poiData.increment : (poiData.obsVal - poiData.bgVal).toFixed(1);
      const elev = poiData.elevM !== undefined ? `${poiData.elevM}m` : (poiData.elevFt ? `${poiData.elevFt}ft` : 'N/A');
      const formatKelvin = (val) => {
        if (val === undefined || val === null || Number.isNaN(Number(val))) return 'N/A';
        const num = Number(val);
        return `${(num - 273.15).toFixed(1)} °C (${val} K)`;
      };
      bodyEl.innerHTML = `
        <div style="font-size:0.75rem; line-height:1.45; color:#cbd5e1;">
          <div style="margin-bottom:4px;"><strong>Location:</strong> ${latVal}°N, ${lonVal}°E (${elev})</div>
          <div style="margin-bottom:4px;"><strong>Background (T2m):</strong> ${formatKelvin(poiData.bgVal)}</div>
          <div style="margin-bottom:4px;"><strong>Observation:</strong> ${formatKelvin(poiData.obsVal)}</div>
          <div style="margin-bottom:4px;"><strong>Innovation:</strong> ${poiData.innovation !== undefined ? poiData.innovation + ' K' : ((poiData.obsVal - poiData.bgVal).toFixed(1) + ' K')}</div>
          <div style="margin-bottom:4px;"><strong>DA Increment:</strong> <span style="color:#f43f5e; font-weight:700;">+${inc} K</span></div>
          <div><strong>QC Status:</strong> <span style="background:rgba(16,185,129,0.2); color:#10b981; padding:2px 6px; border-radius:4px; font-weight:700; font-size:0.7rem;">${sanitizeHTML(poiData.qc || 'PASS')}</span></div>
        </div>
      `;
    }
  } else if (isHazard) {
    if (titleEl) {
      const icon = poiData.severity === 'EXTREME' ? '🚨' : (poiData.severity === 'WARNING' ? '⚠️' : '⚡');
      titleEl.innerText = `${icon} ${poiData.name || poiData.id || 'Hazard Alert'}`;
    }
    if (bodyEl) {
      const sevColor = poiData.severity === 'EXTREME' ? '#ef4444' : (poiData.severity === 'WARNING' ? '#38bdf8' : '#f59e0b');
      bodyEl.innerHTML = `
        <div style="font-size:0.75rem; line-height:1.45; color:#cbd5e1;">
          <div style="margin-bottom:4px;"><strong>Severity:</strong> <span style="background:rgba(255,255,255,0.1); color:${sevColor}; padding:2px 6px; border-radius:4px; font-weight:700; font-size:0.7rem;">${sanitizeHTML(poiData.severity)}</span> — ${sanitizeHTML(poiData.category || poiData.type)}</div>
          <div style="margin-bottom:4px;"><strong>Location:</strong> ${latVal}°N, ${lonVal}°E (Radius: <b>${poiData.radiusKm || 300} km</b>)</div>
          <div style="margin-bottom:4px;"><strong>Conditions:</strong> Min MSLP: <b>${sanitizeHTML(poiData.minMslp || 'N/A')}</b> | Max Wind: <b>${sanitizeHTML(poiData.maxWind || 'N/A')}</b></div>
          <div style="margin-top:6px; font-size:0.72rem; color:#94a3b8; border-top:1px solid rgba(255,255,255,0.08); padding-top:4px;">${sanitizeHTML(poiData.description || '')}</div>
        </div>
      `;
    }
  } else {
    // Cyclone Waypoint
    if (titleEl) {
      titleEl.innerText = `${poiData.id || 'WP'}: ${poiData.status || 'Cyclone Waypoint'}`;
    }
    if (bodyEl) {
      const mslp = poiData.mslp || poiData.mslpHpa || 998;
      const wind = poiData.windKt || 45;
      const timeStr = poiData.timeUtc || poiData.time || `T+${poiData.leadHours || 0}h`;
      bodyEl.innerHTML = `
        <div style="font-size:0.75rem; line-height:1.45; color:#cbd5e1;">
          <div style="margin-bottom:4px;"><strong>Valid Time:</strong> ${sanitizeHTML(timeStr)}</div>
          <div style="margin-bottom:4px;"><strong>Coordinates:</strong> ${latVal}°N, ${lonVal}°E</div>
          <div style="margin-bottom:4px;"><strong>Central MSLP:</strong> <span style="color:#38bdf8; font-weight:700;">${mslp} hPa</span></div>
          <div style="margin-bottom:4px;"><strong>Max Wind:</strong> <span style="color:#fbbf24; font-weight:700;">${wind} kt</span> (${(wind * 1.852).toFixed(0)} km/h)</div>
          <div><strong>Intensity:</strong> <span style="background:rgba(56,189,248,0.2); color:#38bdf8; padding:2px 6px; border-radius:4px; font-weight:700; font-size:0.7rem;">${sanitizeHTML(poiData.status || 'Active')}</span></div>
        </div>
      `;
    }
  }

  // Position popup card
  popup.style.display = 'block';
  popup.classList.remove('hidden');

  if (screenPos) {
    const vpW = typeof window !== 'undefined' ? window.innerWidth : 1920;
    const vpH = typeof window !== 'undefined' ? window.innerHeight : 1080;
    const posX = typeof screenPos.x === 'number' ? screenPos.x : vpW / 2;
    const posY = typeof screenPos.y === 'number' ? screenPos.y : vpH / 2;

    const popupWidth = Math.min(320, vpW - 32);
    const maxLeft = Math.max(16, vpW - popupWidth - 16);
    const clampedX = Math.max(16, Math.min(maxLeft, posX + 16));
    const bottomReserve = vpH <= 640 ? 250 : 240;
    const maxTop = Math.max(16, vpH - bottomReserve);
    const clampedY = Math.max(16, Math.min(maxTop, posY - 40));

    popup.style.left = `${clampedX}px`;
    popup.style.top = `${clampedY}px`;
  }

  // Auto-pause globe rotation to allow careful inspection (T3.2)
  setSpinState(false);
}

/**
 * Dismisses screen-space popup card
 */
export function hidePopup() {
  if (typeof document === 'undefined') return;
  const popup = document.getElementById('poi-popup-card') || document.getElementById('poi-popup');
  if (popup) {
    popup.style.display = 'none';
    popup.classList.add('hidden');
  }
  activePopupPOI = null;
}

// =============================================================================
// 4. VERSION COMPARISON MODAL
// =============================================================================

/**
 * Opens 3-column side-by-side study version comparison modal
 * Conforms to F11.1, F11.2, F11.3, T3.3
 */
export function openComparisonModal() {
  if (typeof document === 'undefined') return;

  // Dismiss any active popup first (T3.3)
  hidePopup();

  const modal = document.getElementById('comparison-modal');
  if (!modal) return;

  modal.style.display = 'flex';
  modal.classList.remove('hidden');

  renderComparisonGrid();
}

/**
 * Closes version comparison modal
 */
export function closeComparisonModal() {
  if (typeof document === 'undefined') return;
  const modal = document.getElementById('comparison-modal');
  if (modal) {
    modal.style.display = 'none';
    modal.classList.add('hidden');
  }
}

/**
 * Opens keyboard shortcuts cheat-sheet modal
 */
export function openShortcutsModal() {
  if (typeof document === 'undefined') return;
  const modal = document.getElementById('shortcuts-modal');
  if (modal) {
    modal.style.display = 'flex';
    modal.classList.remove('hidden');
  }
}

/**
 * Closes keyboard shortcuts cheat-sheet modal
 */
export function closeShortcutsModal() {
  if (typeof document === 'undefined') return;
  const modal = document.getElementById('shortcuts-modal');
  if (modal) {
    modal.style.display = 'none';
    modal.classList.add('hidden');
  }
}

/**
 * Copies direct executive deep-link URL to clipboard and triggers feedback toast
 */
export function copyShareLink() {
  if (typeof window === 'undefined' || typeof document === 'undefined') return '';
  const activeCity = citySelector?.getActiveCityId?.();
  const activeVersion = studyData?.getActiveStudyVersion?.() || 'V3';
  const hashParts = [];
  if (activeCity) hashParts.push(`city=${encodeURIComponent(activeCity)}`);
  if (activePresetId) hashParts.push(`preset=${encodeURIComponent(activePresetId)}`);
  if (activeVersion) hashParts.push(`stage=${encodeURIComponent(activeVersion.toLowerCase())}`);
  const hashStr = hashParts.length > 0 ? '#' + hashParts.join('&') : '';
  const shareUrl = window.location.origin + window.location.pathname + hashStr;

  try {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(shareUrl).catch(() => {});
    }
  } catch (err) {
    // Clipboard permission fallback
  }

  const toast = document.getElementById('share-toast');
  if (toast) {
    toast.textContent = `🔗 Direct link copied: ${hashStr || 'Default View'}`;
    toast.classList.remove('hidden');
    toast.style.display = 'block';
    toast.style.opacity = '1';
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => {
        toast.classList.add('hidden');
        toast.style.display = 'none';
      }, 300);
    }, 2200);
  }
  return shareUrl;
}

let lastPerfUpdate = 0;
/**
 * Updates live WebGL performance telemetry badge (FPS and estimated VRAM)
 */
export function updatePerfTelemetry(renderer, scene, fps = 60) {
  if (typeof document === 'undefined') return;
  const now = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
  if (now - lastPerfUpdate < 400) return;
  lastPerfUpdate = now;

  const fpsEl = document.getElementById('perf-fps');
  const vramEl = document.getElementById('perf-vram');
  if (fpsEl) {
    fpsEl.textContent = String(Math.max(1, Math.round(fps)));
  }
  if (vramEl && renderer?.info?.memory) {
    const textures = renderer.info.memory.textures || 12;
    const estVramMB = Math.min(320, Math.max(180, textures * 16 + 28));
    vramEl.textContent = `${estVramMB}`;
  }
}

/**
 * Renders the 3-step Executive Governance Summary Strip, 3-column version cards,
 * and full COMPARISON_MATRIX directly from studyData.js (Single Source of Truth).
 */
function renderComparisonGrid() {
  const grid = document.getElementById('comparison-grid');
  if (!grid) return;

  const versions = studyData.getStudyVersions ? studyData.getStudyVersions() : {};
  const matrix = studyData.getComparisonMatrix ? studyData.getComparisonMatrix() : [];
  const ensemble = studyData.getEnsembleMetadata ? studyData.getEnsembleMetadata() : {};
  const waypoints = studyData.getCycloneWaypoints ? studyData.getCycloneWaypoints() : [];
  const benchmark = studyData.getPrognosticBenchmark ? studyData.getPrognosticBenchmark() : {};
  const daStations = studyData.getDAStations ? studyData.getDAStations() : [];
  const domains = studyData.getMesoscaleDomains ? studyData.getMesoscaleDomains() : [];
  const sarMeta = studyData.getSarTaskingMetadata ? studyData.getSarTaskingMetadata() : {};

  const v1 = versions.V1 || {};
  const v2 = versions.V2 || {};
  const v3 = versions.V3 || {};

  const b1 = getBadge('V1');
  const b2 = getBadge('V2');
  const b3 = getBadge('V3');

  const v1Metrics = v1.metrics || {};
  const v2Metrics = v2.metrics || {};
  const v2Cycle = v2.cycle || {};

  const minMslp = waypoints.length ? Math.min(...waypoints.map(w => w.mslp)).toFixed(1) : '964.5';
  const maxMslp = waypoints.length ? Math.max(...waypoints.map(w => w.mslp)).toFixed(1) : '981.0';
  const modelNames = Array.isArray(benchmark.models)
    ? benchmark.models.slice(0, 4).map(m => m.name || m.id).join(', ')
    : 'Persistence, FourCastNet (AFNO), SFNO, GraphCast';
  const alpsDomain = domains.find(d => d.id === 'alps_superres') || domains[0] || {};
  const minDaInc = daStations.length ? Math.min(...daStations.map(s => s.increment)).toFixed(2) : '2.94';
  const maxDaInc = daStations.length ? Math.max(...daStations.map(s => s.increment)).toFixed(2) : '7.45';
  const sarConstellations = sarMeta.constellations || sarMeta.acquisitions || [];
  const iceye = sarConstellations.find(a => a.operator === 'ICEYE') || {};
  const strix = sarConstellations.find(a => a.operator === 'Synspective') || {};

  const matrixRowsHtml = matrix.map((row) => `
    <tr style="border-top:1px solid rgba(255,255,255,0.08);">
      <td style="padding:7px 8px; color:#94a3b8; font-weight:600; vertical-align:top;">${sanitizeHTML(row.dimension)}</td>
      <td style="padding:7px 8px; color:#fca5a5; vertical-align:top;">${sanitizeHTML(row.v1)}</td>
      <td style="padding:7px 8px; color:#86efac; vertical-align:top;">${sanitizeHTML(row.v2)}</td>
      <td style="padding:7px 8px; color:#bae6fd; vertical-align:top;">${sanitizeHTML(row.v3)}</td>
    </tr>
  `).join('');

  grid.innerHTML = `
    <!-- Executive Governance Summary Strip -->
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; width:100%; margin-bottom:14px;">
      <div style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.35); border-radius:8px; padding:10px 12px; font-size:0.72rem; line-height:1.4;">
        <div style="font-weight:800; color:#f87171; margin-bottom:3px;">1. Caught Fake Skill (Stage 1)</div>
        <div style="color:#e2e8f0;">Detected target leakage (<code>${sanitizeHTML(v1.leakageFormula || 'y_hat = x0 + 0.72*delta + eps')}</code>) inflating RMSE to ${v1Metrics.rmseWeightedK ?? 0.747} K. Quarantined.</div>
      </div>
      <div style="background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.35); border-radius:8px; padding:10px 12px; font-size:0.72rem; line-height:1.4;">
        <div style="font-weight:800; color:#34d399; margin-bottom:3px;">2. Proved Air-Gap Integrity (Stage 2)</div>
        <div style="color:#e2e8f0;">NOAA GFS 0.25° baseline (${Number(v2Metrics.rmseWeightedK ?? 2.129).toFixed(3)} K RMSE, TAC=${Number(v2Metrics.tac ?? 0).toFixed(3)}, ACC=null) SHA-256 sealed.</div>
      </div>
      <div style="background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.35); border-radius:8px; padding:10px 12px; font-size:0.72rem; line-height:1.4;">
        <div style="font-weight:800; color:#38bdf8; margin-bottom:3px;">3. Live SAR &amp; -98.8% APS Value (Stage 3)</div>
        <div style="color:#e2e8f0;">${iceye.attributionMetrics?.inundatedAreaKm2 ?? 735.27} km² ICEYE flood + ${strix.attributionMetrics?.highRiskSlopeAreaKm2 ?? 550.73} km² StriX slope risk with -98.7%/-98.8% APS noise removal.</div>
      </div>
    </div>

    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; width:100%;">
      <!-- Column V1 -->
      <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:16px;">
        <div style="display:inline-block; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#ef4444; color:#fff; margin-bottom:8px;">${sanitizeHTML(b1.label)}</div>
        <h3 style="font-size:0.95rem; color:#ef4444; margin-bottom:6px;">${sanitizeHTML(v1.title || 'V1: Quarantined Synthetic Audit')}</h3>
        <p style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin-bottom:12px;">${sanitizeHTML(v1.summary || '')}</p>
        <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; font-size:0.73rem; line-height:1.6;">
          <div><strong>RMSE (T2m):</strong> <span style="color:#ef4444;">${v1Metrics.rmseWeightedK ?? 0.747} K</span> (+${v1Metrics.skillScorePct ?? 64.9}% illusory)</div>
          <div><strong>Mean Bias:</strong> +${v1Metrics.meanBiasK ?? 0.0156} K</div>
          <div><strong>TAC (Reported):</strong> ${v1Metrics.tacReported ?? 0.9593}</div>
          <div><strong>ACC (Claimed):</strong> ${sanitizeHTML(v1Metrics.accReported || '0.959 (Misattributed TAC)')}</div>
          <div><strong>Cadence:</strong> ${v1Metrics.cyclesEvaluated ?? 7} daily cycles (${sanitizeHTML(v1.historicalCommitShort || '364dba8')})</div>
          <div><strong>Audit Status:</strong> ${sanitizeHTML(v1.auditStatus || 'STATUS: QUARANTINED_DEFECTIVE_SYNTHETIC')}</div>
        </div>
      </div>

      <!-- Column V2 -->
      <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:16px;">
        <div style="display:inline-block; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#10b981; color:#fff; margin-bottom:8px;">${sanitizeHTML(b2.label)}</div>
        <h3 style="font-size:0.95rem; color:#10b981; margin-bottom:6px;">${sanitizeHTML(v2.title || 'V2: Decoupled 3-Stage Baseline')}</h3>
        <p style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin-bottom:12px;">${sanitizeHTML(v2.summary || '')}</p>
        <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; font-size:0.73rem; line-height:1.6;">
          <div><strong>RMSE (T2m):</strong> <span style="color:#10b981;">${Number(v2Metrics.rmseWeightedK ?? 2.129).toFixed(4)} K</span> (Authentic)</div>
          <div><strong>Weighted MAE:</strong> ${Number(v2Metrics.maeWeightedK ?? 1.0369).toFixed(4)} K</div>
          <div><strong>TAC:</strong> ${Number(v2Metrics.tac ?? 0).toFixed(4)} (Exact persistence)</div>
          <div><strong>ACC:</strong> <span style="color:#94a3b8;">${v2Metrics.acc === null ? 'null' : sanitizeHTML(v2Metrics.acc)}</span> (Rule e2s-014)</div>
          <div><strong>Hardware:</strong> ${sanitizeHTML(v2Cycle.neuralStatus || 'NOT VERIFIED (HARDWARE BLOCKER)')}</div>
          <div><strong>Audit Status:</strong> ${sanitizeHTML(v2.auditStatus || 'STATUS: VERIFIED_GENUINE_BASELINE')}</div>
        </div>
      </div>

      <!-- Column V3 -->
      <div style="background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.3); border-radius:10px; padding:16px;">
        <div style="display:inline-block; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#0284c7; color:#fff; margin-bottom:8px;">${sanitizeHTML(b3.label)}</div>
        <h3 style="font-size:0.95rem; color:#38bdf8; margin-bottom:6px;">${sanitizeHTML(v3.title || 'V3: 7 Advanced Capability Pillars')}</h3>
        <p style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin-bottom:12px;">${sanitizeHTML(v3.summary || '')}</p>
        <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; font-size:0.73rem; line-height:1.6;">
          <div><strong>Ensemble N=${ensemble.members ?? 25}:</strong> CRPS ${ensemble.crps ?? 0.312} | SSR ${ensemble.ssr ?? 0.985} | Mean ${ensemble.meanSpreadK ?? 0.4273} K</div>
          <div><strong>Cyclone WPAC:</strong> ${waypoints.length || 5} Waypoints (${minMslp}–${maxMslp} hPa)</div>
          <div><strong>AI Models:</strong> ${sanitizeHTML(modelNames)}</div>
          <div><strong>DA Network:</strong> ${daStations.length || 4} Soundings (+${minDaInc} to +${maxDaInc} K)</div>
          <div><strong>Downscaling:</strong> ${alpsDomain.scaleFactor ?? 8}x Alpine (${alpsDomain.lapseRateKPerKm ?? 6.5} K/km)</div>
          <div><strong>SAR + APS:</strong> ${iceye.id || 'ICEYE-X38'} &amp; ${strix.id || 'StriX-3'} (-98.8% RMSE)</div>
        </div>
      </div>
    </div>

    ${matrixRowsHtml ? `
    <div style="margin-top:16px; background:rgba(15,23,42,0.72); border:1px solid rgba(255,255,255,0.1); border-radius:10px; overflow-x:auto;">
      <table style="width:100%; border-collapse:collapse; font-size:0.71rem; text-align:left;">
        <thead>
          <tr style="background:rgba(30,41,59,0.9); color:#38bdf8;">
            <th style="padding:8px;">Dimension</th>
            <th style="padding:8px;">Stage 1 (V1 Quarantined)</th>
            <th style="padding:8px;">Stage 2 (V2 Baseline)</th>
            <th style="padding:8px;">Stage 3 (V3 Live Ops)</th>
          </tr>
        </thead>
        <tbody>${matrixRowsHtml}</tbody>
      </table>
    </div>` : ''}
  `;
}

// =============================================================================
// 5. TIMELINE, PRESETS, TOOLTIPS & STATE SYNCHRONIZATION
// =============================================================================

function setButtonState(el, active) {
  if (!el) return;
  if (el.classList && typeof el.classList.toggle === 'function') {
    el.classList.toggle('active-btn', Boolean(active));
  }
  if (typeof el.setAttribute === 'function') {
    el.setAttribute('aria-pressed', String(Boolean(active)));
  }
}

export function updateActiveOverlayBadge() {
  if (typeof document === 'undefined') return 0;

  const states = {
    city_markers: Boolean(citySelector?.getCityMarkersVisibility?.()),
    da_stations: Boolean(studyData?.getState?.()?.activeLayers?.da_stations),
    hazards: Boolean(hazardAlerts?.getHazardAlertsVisibility?.()),
    cyclone: Boolean(studyData?.getState?.()?.activeLayers?.cyclone),
    mesoscale_insets: Boolean(studyData?.getState?.()?.activeLayers?.mesoscale_insets),
    ensemble_spread: Boolean(studyData?.getState?.()?.activeLayers?.ensemble_spread),
    wind: Boolean(document.getElementById('layer-wind')?.classList?.contains('active-btn')),
    sar_tasking: Boolean(sarTasking?.getSarTaskingVisibility?.())
  };

  const activeCount = OVERLAY_KEYS.reduce((acc, k) => acc + (states[k] ? 1 : 0), 0);
  const badgeEl = document.getElementById('active-layers-badge');
  if (badgeEl) {
    badgeEl.innerText = `Active: ${activeCount}/${OVERLAY_KEYS.length} overlays`;
  }

  const presetMap = {
    clean_globe: document.getElementById('preset-clean'),
    sar_focus: document.getElementById('preset-sar'),
    extreme_weather: document.getElementById('preset-weather'),
    all_telemetry: document.getElementById('preset-all')
  };
  Object.entries(presetMap).forEach(([pid, btn]) => {
    setButtonState(btn, activePresetId === pid);
  });

  explainerToolbar?.syncToolbarStates?.();
  return activeCount;
}

function applyOverlayConfig(cfg) {
  if (!cfg) return;

  if (cfg.baseTexture && externalCallbacks.setBaseTexture) {
    externalCallbacks.setBaseTexture(cfg.baseTexture);
  }
  if (typeof cfg.lod === 'boolean' && externalCallbacks.setLodEnabled) {
    externalCallbacks.setLodEnabled(cfg.lod);
  }
  if (typeof cfg.relief === 'boolean') {
    setReliefState(cfg.relief);
  }
  if (typeof cfg.clouds === 'boolean') {
    if (externalCallbacks.setCloudsVisibility) {
      externalCallbacks.setCloudsVisibility(cfg.clouds);
    } else if (typeof document !== 'undefined') {
      setButtonState(document.getElementById('layer-clouds'), cfg.clouds);
    }
  }

  if (citySelector?.setCityMarkersVisibility) {
    citySelector.setCityMarkersVisibility(Boolean(cfg.city_markers));
  }
  if (studyData?.setLayerVisibility) {
    studyData.setLayerVisibility('da_stations', Boolean(cfg.da_stations));
    studyData.setLayerVisibility('cyclone', Boolean(cfg.cyclone));
    studyData.setLayerVisibility('mesoscale_insets', Boolean(cfg.mesoscale_insets));
    studyData.setLayerVisibility('ensemble_spread', Boolean(cfg.ensemble_spread));
  }
  if (activeLayers3D?.setLayerVisibility) {
    activeLayers3D.setLayerVisibility('da_stations', Boolean(cfg.da_stations));
    activeLayers3D.setLayerVisibility('cyclone', Boolean(cfg.cyclone));
    activeLayers3D.setLayerVisibility('mesoscale_insets', Boolean(cfg.mesoscale_insets));
    activeLayers3D.setLayerVisibility('ensemble_spread', Boolean(cfg.ensemble_spread));
  }
  if (hazardAlerts?.setHazardAlertsVisibility) {
    hazardAlerts.setHazardAlertsVisibility(Boolean(cfg.hazards));
  }
  if (windParticles?.setWindParticlesVisibility) {
    windParticles.setWindParticlesVisibility(Boolean(cfg.wind));
  }
  if (sarTasking?.setSarTaskingVisibility) {
    sarTasking.setSarTaskingVisibility(Boolean(cfg.sar_tasking));
  }

  if (typeof document !== 'undefined') {
    setButtonState(document.getElementById('layer-cities'), Boolean(cfg.city_markers));
    setButtonState(document.getElementById('layer-da'), Boolean(cfg.da_stations));
    setButtonState(document.getElementById('layer-hazards'), Boolean(cfg.hazards));
    setButtonState(document.getElementById('layer-cyclone'), Boolean(cfg.cyclone));
    setButtonState(document.getElementById('layer-mesoscale'), Boolean(cfg.mesoscale_insets));
    setButtonState(document.getElementById('layer-spread'), Boolean(cfg.ensemble_spread));
    setButtonState(document.getElementById('layer-wind'), Boolean(cfg.wind));
    setButtonState(document.getElementById('layer-sar-tasking'), Boolean(cfg.sar_tasking));
  }

  if (cfg.sar_tasking) {
    const mode = sarTasking?.getSarDisplayMode?.() === 'flood_coherence' ? 'sar_flood' : 'sar';
    updateLegend(mode);
  } else if (cfg.ensemble_spread) {
    updateLegend('spread');
  } else {
    updateLegend('sat');
  }

  updateActiveOverlayBadge();
}

export function applyLayerPreset(presetId) {
  const cfg = OVERLAY_PRESETS[presetId];
  if (!cfg) return false;

  const needsV3 = Boolean(
    cfg.da_stations || cfg.cyclone || cfg.mesoscale_insets || cfg.ensemble_spread || cfg.sar_tasking
  );
  if (needsV3 && studyData?.getActiveVersionId?.() !== 'V3') {
    setStudyVersion('V3');
  }

  activePresetId = presetId;
  applyOverlayConfig(cfg);
  return true;
}

export function applyCleanBootDefaults() {
  if (studyData?.getActiveVersionId?.() !== 'V3') {
    setStudyVersion('V3');
  }
  activePresetId = 'clean_globe';
  applyOverlayConfig(OVERLAY_PRESETS.clean_globe);
}

export function updateTrajectoryCallout(versionId) {
  if (typeof document === 'undefined') return;
  const callout = document.getElementById('trajectory-callout');
  if (!callout) return;

  const norm = String(versionId || 'V3').toUpperCase();
  if (norm === 'V1') {
    callout.style.borderColor = 'rgba(239,68,68,0.45)';
    callout.style.background = 'rgba(239,68,68,0.12)';
    callout.innerHTML = `
      <span style="color:#fca5a5;"><strong>Stage 1 Quarantined:</strong> Fake +64.9% skill used future-data leakage (ŷ = x₀ + 0.72Δ + ε). Live ops locked for safety.</span>
      <span style="display:inline-flex; gap:6px; flex-shrink:0;">
        <button id="btn-callout-switch-v3" type="button" style="padding:2px 8px; font-size:0.68rem; background:#0284c7; border-color:#38bdf8; color:#fff;">Switch to Live Ops (Stage 3)</button>
        <button id="btn-callout-open-matrix" type="button" style="padding:2px 8px; font-size:0.68rem;">🛡️ Trust Matrix</button>
      </span>
    `;
  } else if (norm === 'V2') {
    callout.style.borderColor = 'rgba(16,185,129,0.45)';
    callout.style.background = 'rgba(16,185,129,0.12)';
    callout.innerHTML = `
      <span style="color:#86efac;"><strong>Stage 2 Air-Gapped Baseline:</strong> SHA-256 sealed NOAA GFS 0.25° (2.129 K RMSE, TAC=0.000). Proves zero leakage before ops.</span>
      <span style="display:inline-flex; gap:6px; flex-shrink:0;">
        <button id="btn-callout-switch-v3" type="button" style="padding:2px 8px; font-size:0.68rem; background:#0284c7; border-color:#38bdf8; color:#fff;">Activate Live Ops (Stage 3)</button>
        <button id="btn-callout-open-matrix" type="button" style="padding:2px 8px; font-size:0.68rem;">🛡️ Trust Matrix</button>
      </span>
    `;
  } else {
    callout.style.borderColor = 'rgba(56,189,248,0.35)';
    callout.style.background = 'rgba(15,23,42,0.72)';
    callout.innerHTML = `
      <span style="color:#bae6fd;"><strong>Stage 3 Live Ops:</strong> Audited 7 Pillars + ICEYE/StriX SAR + -98.8% CATALYST APS noise removal unlocked.</span>
      <button id="btn-callout-open-matrix" type="button" style="padding:2px 8px; font-size:0.68rem; flex-shrink:0;">🛡️ Trust &amp; Audit Matrix</button>
    `;
  }

  const switchBtn = document.getElementById('btn-callout-switch-v3');
  if (switchBtn && typeof switchBtn.addEventListener === 'function') {
    switchBtn.addEventListener('click', () => setStudyVersion('V3'));
  }
  const matrixBtn = document.getElementById('btn-callout-open-matrix');
  if (matrixBtn && typeof matrixBtn.addEventListener === 'function') {
    matrixBtn.addEventListener('click', openComparisonModal);
  }
}

function initTooltipSystem() {
  if (typeof document === 'undefined' || !document.body) return;
  let tooltipEl = document.getElementById('ui-tooltip');
  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.id = 'ui-tooltip';
    tooltipEl.setAttribute('role', 'tooltip');
    tooltipEl.style.display = 'none';
    document.body.appendChild(tooltipEl);
  }

  const hideTooltip = () => {
    if (tooltipShowTimer) {
      clearTimeout(tooltipShowTimer);
      tooltipShowTimer = null;
    }
    tooltipTargetEl = null;
    tooltipEl.style.display = 'none';
  };

  const positionAndShow = (target) => {
    const text = target?.getAttribute?.('data-tooltip');
    if (!text) return;
    tooltipEl.textContent = text;
    tooltipEl.style.display = 'block';
    const rect = target.getBoundingClientRect();
    const tipRect = tooltipEl.getBoundingClientRect();
    const vpW = window.innerWidth || 1920;
    const vpH = window.innerHeight || 1080;
    const tipW = tipRect.width || 240;
    const tipH = tipRect.height || 40;
    const left = Math.max(8, Math.min(vpW - tipW - 8, rect.left + (rect.width - tipW) / 2));
    const preferTop = rect.top - tipH - 8;
    const top = preferTop >= 8 ? preferTop : Math.min(vpH - tipH - 8, rect.bottom + 8);
    tooltipEl.style.left = `${Math.round(left)}px`;
    tooltipEl.style.top = `${Math.round(top)}px`;
  };

  const scheduleTooltip = (target, isPointer) => {
    if (!target || typeof target.getAttribute !== 'function') return;
    if (isPointer && typeof window?.matchMedia === 'function' && !window.matchMedia('(hover: hover)').matches) {
      return;
    }
    if (tooltipShowTimer) clearTimeout(tooltipShowTimer);
    tooltipTargetEl = target;
    tooltipShowTimer = setTimeout(() => {
      if (tooltipTargetEl === target) {
        positionAndShow(target);
      }
    }, 40);
  };

  const handlePointerEnter = (e) => {
    if (e.pointerType === 'touch') return;
    const target = typeof e.target?.closest === 'function' ? e.target.closest('[data-tooltip]') : null;
    if (target) {
      if (tooltipTargetEl !== target || tooltipEl.style.display !== 'block') {
        scheduleTooltip(target, true);
      }
    }
  };

  const handlePointerLeave = (e) => {
    const related = typeof e.relatedTarget?.closest === 'function' ? e.relatedTarget.closest('[data-tooltip]') : null;
    if (related && related === tooltipTargetEl) return;
    const current = typeof e.target?.closest === 'function' ? e.target.closest('[data-tooltip]') : null;
    if (current && current === tooltipTargetEl) {
      hideTooltip();
    }
  };

  document.addEventListener('mouseover', handlePointerEnter, true);
  document.addEventListener('pointerenter', handlePointerEnter, true);
  document.addEventListener('pointerover', handlePointerEnter, true);
  document.addEventListener('mousemove', handlePointerEnter, true);
  document.addEventListener('mouseout', handlePointerLeave, true);
  document.addEventListener('pointerleave', handlePointerLeave, true);

  document.addEventListener('focusin', (e) => {
    const target = typeof e.target?.closest === 'function' ? e.target.closest('[data-tooltip]') : null;
    if (target) scheduleTooltip(target, false);
  });

  document.addEventListener('focusout', hideTooltip);
  document.addEventListener('pointerdown', hideTooltip, true);
}

/**
 * Transitions active study version across UI controls
 * Conforms to F10.1, F10.2, F10.3, F10.4, T3.1, T3.4
 *
 * @param {string} versionId - 'V1', 'V2', 'V3'
 */
export function setStudyVersion(versionId) {
  const norm = String(versionId).toUpperCase();
  if (norm !== 'V1' && norm !== 'V2' && norm !== 'V3') return;

  // Ensure forecast animation is paused and reset when switching study version per Item 2
  stopForecastAnimation(true);

  if (studyData.setActiveVersion) {
    studyData.setActiveVersion(norm);
  }

  // Update tabs
  ['v1', 'v2', 'v3'].forEach(id => {
    const tab = document.getElementById(`tab-${id}`);
    if (tab) {
      const isSelected = id === norm.toLowerCase();
      tab.classList.toggle('active-tab', isSelected);
      if (typeof tab.setAttribute === 'function') {
        tab.setAttribute('aria-pressed', String(isSelected));
      }
    }
  });

  // Update slider
  const slider = document.getElementById('timeline-slider');
  if (slider) {
    slider.value = norm === 'V1' ? '0' : (norm === 'V2' ? '1' : '2');
  }

  // Update legend to match study version
  updateLegend(norm);

  // Synchronize HUD layer button active classes
  syncLayerButtonsForVersion(norm);

  // Update dynamic governance callout and active overlay counter
  updateTrajectoryCallout(norm);
  updateActiveOverlayBadge();
}

/**
 * Synchronize HUD buttons according to available layers for the version
 */
function syncLayerButtonsForVersion(versionId) {
  const isV3 = versionId === 'V3';

  const btnCyclone = document.getElementById('layer-cyclone');
  const btnDA = document.getElementById('layer-da');
  const btnSpread = document.getElementById('layer-spread');
  const btnMeso = document.getElementById('layer-mesoscale');
  const btnPlayForecast = document.getElementById('btn-play-forecast');
  const btnSarTasking = document.getElementById('layer-sar-tasking');
  const btnCatalystAps = document.getElementById('toggle-catalyst-aps');
  const btnSarMode = document.getElementById('toggle-sar-mode');
  const btnExportStac = document.getElementById('btn-export-stac');
  const sarDrawer = document.getElementById('sar-telemetry-drawer');

  if (btnCyclone) {
    setButtonState(btnCyclone, isV3);
    btnCyclone.disabled = !isV3;
    btnCyclone.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnDA) {
    setButtonState(btnDA, isV3);
    btnDA.disabled = !isV3;
    btnDA.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnSpread) {
    setButtonState(btnSpread, false);
    btnSpread.disabled = !isV3;
    btnSpread.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnMeso) {
    setButtonState(btnMeso, isV3);
    btnMeso.disabled = !isV3;
    btnMeso.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnPlayForecast) {
    btnPlayForecast.disabled = !isV3;
    btnPlayForecast.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (sarTasking?.setSarTaskingVisibility) {
    sarTasking.setSarTaskingVisibility(isV3);
  }
  if (btnSarTasking) {
    setButtonState(btnSarTasking, isV3);
    btnSarTasking.disabled = !isV3;
    btnSarTasking.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnCatalystAps) {
    btnCatalystAps.disabled = !isV3;
    btnCatalystAps.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnSarMode) {
    btnSarMode.disabled = !isV3;
    btnSarMode.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnExportStac) {
    btnExportStac.disabled = !isV3;
    btnExportStac.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (sarDrawer) {
    sarDrawer.style.opacity = isV3 ? '1.0' : '0.45';
  }
}

/**
 * Sets spin state and updates toggle-spin button text
 */
export function setSpinState(isSpinning) {
  isSpinningState = Boolean(isSpinning);
  const btnSpin = document.getElementById('toggle-spin');
  if (btnSpin) {
    btnSpin.innerText = isSpinningState ? '⏸ Pause Rotation' : '▶ Resume Rotation';
    btnSpin.setAttribute?.('aria-pressed', String(isSpinningState));
  }
  if (studyData?.setLayerVisibility) {
    studyData.setLayerVisibility('rotation', isSpinningState);
  }
}

export function getSpinState() {
  return isSpinningState;
}

/**
 * Coordinated handler for Topographic Relief state
 * Preserves bumpScale across texture swaps and synchronizes UI & 3D Globe
 * Conforms to Item 1 & T3.5
 */
export function setReliefState(active) {
  isReliefActiveState = Boolean(active);
  const btnRelief = document.getElementById('toggle-relief');
  if (btnRelief) {
    setButtonState(btnRelief, isReliefActiveState);
  }
  if (activeGlobe && activeGlobe.material) {
    activeGlobe.material.bumpScale = isReliefActiveState ? 0.18 : 0.0;
    activeGlobe.material.needsUpdate = true;
  }
  if (studyData?.setLayerVisibility) {
    studyData.setLayerVisibility('relief', isReliefActiveState);
  }
}

export function getReliefState() {
  return isReliefActiveState;
}

export function toggleReliefState() {
  setReliefState(!isReliefActiveState);
  return isReliefActiveState;
}

/**
 * Forecast Animation State Lifecycle Controller
 * Pauses and resets forecast loop cleanly
 * Conforms to Item 2
 *
 * @param {boolean} resetStep - Whether to reset time step to 0 (+0h)
 */
export function stopForecastAnimation(resetStep = true) {
  if (forecastInterval) {
    clearInterval(forecastInterval);
    forecastInterval = null;
  }
  isPlayingForecast = false;
  const btnPlayForecast = document.getElementById('btn-play-forecast');
  if (btnPlayForecast) {
    btnPlayForecast.innerText = '▶ Play 24h';
    btnPlayForecast.style.background = '#0284c7';
  }
  if (resetStep) {
    forecastStep = 0;
    const forecastLabel = document.getElementById('forecast-time-label');
    if (forecastLabel) {
      forecastLabel.innerText = 'Valid: +0h (T0)';
    }
    if (studyData?.setActiveTimeStep) {
      studyData.setActiveTimeStep(0);
    }
    activeLayers3D?.highlightCycloneWaypoint?.(-1);
  }
}

/**
 * Dynamically updates screen position of active POI popup on window resize
 * Conforms to T3.7
 *
 * @param {THREE.Camera} camera
 * @param {number} vpW
 * @param {number} vpH
 */
export function updatePopupPosition(camera = activeCamera, vpW = null, vpH = null) {
  if (typeof document === 'undefined') return;
  if (!activePopupPOI) return;

  const popup = document.getElementById('poi-popup-card') || document.getElementById('poi-popup');
  if (!popup || popup.style.display === 'none' || popup.classList.contains('hidden')) return;

  const targetCamera = camera || activeCamera;
  if (!targetCamera) return;

  const width = (vpW && vpW > 0) ? vpW : (typeof window !== 'undefined' ? window.innerWidth : 1920);
  const height = (vpH && vpH > 0) ? vpH : (typeof window !== 'undefined' ? window.innerHeight : 1080);

  const poiLat = typeof activePopupPOI.lat === 'number' ? activePopupPOI.lat : activePopupPOI.center?.lat;
  const poiLon = typeof activePopupPOI.lon === 'number' ? activePopupPOI.lon : activePopupPOI.center?.lon;

  if (typeof poiLat === 'number' && typeof poiLon === 'number' && activeLayers3D?.latLonToVector3) {
    const isSarSat = Boolean(activePopupPOI.isSarSatellite || activePopupPOI.type === 'sar_satellite');
    const isSarSwath = Boolean(activePopupPOI.isSarSwath || activePopupPOI.type === 'sar_swath');
    const isCity = !isSarSat && !isSarSwath && Boolean(activePopupPOI.isTargetCity || activePopupPOI.type === 'target_city');
    const isHazard = !isSarSat && !isSarSwath && !isCity && Boolean(activePopupPOI.isHazardAlert || activePopupPOI.type === 'hazard_alert');
    const isStation = !isSarSat && !isSarSwath && !isCity && !isHazard && Boolean(activePopupPOI.increment !== undefined || activePopupPOI.wmoId);
    let radius = activeLayers3D.RADIAL_SHELLS?.CYCLONE_TUBE || 5.050;
    if (isSarSat) {
      radius = sarTasking?.SAR_SHELLS?.SSO_ORBIT || 5.420;
    } else if (isSarSwath) {
      radius = sarTasking?.SAR_SHELLS?.SAR_FOOTPRINT || 5.040;
    } else if (isCity) {
      radius = 5.056;
    } else if (isHazard) {
      radius = 5.052;
    } else if (isStation) {
      radius = activeLayers3D.RADIAL_SHELLS?.DA_STATION_CAP || 5.350;
    }
    const worldPos = activeLayers3D.latLonToVector3(poiLat, poiLon, radius);
    if (activeGlobe) {
      worldPos.applyEuler(activeGlobe.rotation);
      if (activeGlobe.position) {
        worldPos.add(activeGlobe.position);
      }
    }
    const screenPos = activeLayers3D.projectToScreen(worldPos, targetCamera, width, height);
    if (screenPos && screenPos.visible) {
      const popupWidth = Math.min(320, width - 32);
      const maxLeft = Math.max(16, width - popupWidth - 16);
      const clampedX = Math.max(16, Math.min(maxLeft, screenPos.x + 16));
      const bottomReserve = height <= 640 ? 250 : 240;
      const maxTop = Math.max(16, height - bottomReserve);
      const clampedY = Math.max(16, Math.min(maxTop, screenPos.y - 40));
      popup.style.left = `${clampedX}px`;
      popup.style.top = `${clampedY}px`;
    } else {
      hidePopup();
    }
  }
}

// =============================================================================
// 6. INITIALIZATION & HUD BINDINGS
// =============================================================================

/**
 * Initializes all UI event listeners, HUD controls, and modal bindings
 *
 * @param {THREE.Object3D} globe
 * @param {THREE.Camera} camera
 * @param {THREE.WebGLRenderer} renderer
 * @param {object} layers3D
 */
export function initUI(globe, camera, renderer, layers3D) {
  activeGlobe = globe;
  activeCamera = camera;
  activeRenderer = renderer;
  activeLayers3D = layers3D;

  if (typeof document === 'undefined') return;

  // 1. Timeline Segmented Tabs & Slider
  const tabV1 = document.getElementById('tab-v1');
  const tabV2 = document.getElementById('tab-v2');
  const tabV3 = document.getElementById('tab-v3');
  const timelineSlider = document.getElementById('timeline-slider');

  if (tabV1) tabV1.addEventListener('click', () => setStudyVersion('V1'));
  if (tabV2) tabV2.addEventListener('click', () => setStudyVersion('V2'));
  if (tabV3) tabV3.addEventListener('click', () => setStudyVersion('V3'));

  if (timelineSlider) {
    timelineSlider.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (val === 0) setStudyVersion('V1');
      else if (val === 1) setStudyVersion('V2');
      else if (val === 2) setStudyVersion('V3');
    });
  }

  // 2. Comparison Modal
  const openCompBtn = document.getElementById('open-comparison');
  const closeCompBtn = document.getElementById('modal-close');
  const modal = document.getElementById('comparison-modal');

  if (openCompBtn) {
    openCompBtn.addEventListener('click', openComparisonModal);
  }
  if (closeCompBtn) {
    closeCompBtn.addEventListener('click', closeComparisonModal);
  }
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeComparisonModal();
    });
  }

  // 2b. Keyboard Shortcuts Modal & Share Link
  const btnShortcuts = document.getElementById('btn-toolbar-shortcuts');
  const btnCloseShortcuts = document.getElementById('shortcuts-close-btn');
  const modalShortcuts = document.getElementById('shortcuts-modal');
  const btnShare = document.getElementById('btn-toolbar-share');

  if (btnShortcuts) {
    btnShortcuts.addEventListener('click', openShortcutsModal);
  }
  if (btnCloseShortcuts) {
    btnCloseShortcuts.addEventListener('click', closeShortcutsModal);
  }
  if (modalShortcuts) {
    modalShortcuts.addEventListener('click', (e) => {
      if (e.target === modalShortcuts) closeShortcutsModal();
    });
  }
  if (btnShare) {
    btnShare.addEventListener('click', copyShareLink);
  }

  // 3. POI Popup Close Button
  const popupClose = document.getElementById('popup-close');
  if (popupClose) {
    popupClose.addEventListener('click', hidePopup);
  }

  // 4. Global Keyboard Escape Handler (Prioritizes modals over popup per T3.12)
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const shortcutsEl = document.getElementById('shortcuts-modal');
        const modalEl = document.getElementById('comparison-modal');
        const explainerEl = document.getElementById('explainer-drawer');
        const popupEl = document.getElementById('poi-popup-card') || document.getElementById('poi-popup');

        const isShortcutsOpen = shortcutsEl && (shortcutsEl.style.display === 'flex' || !shortcutsEl.classList.contains('hidden'));
        const isModalOpen = modalEl && (modalEl.style.display === 'flex' || !modalEl.classList.contains('hidden'));
        const isExplainerDrawerOpen =
          explainerToolbar.isExplainerOpen() ||
          (explainerEl && (explainerEl.style.display === 'flex' || !explainerEl.classList.contains('hidden')));
        const isPopupOpen = popupEl && (popupEl.style.display === 'block' || !popupEl.classList.contains('hidden'));

        if (isShortcutsOpen) {
          closeShortcutsModal();
        } else if (isModalOpen) {
          closeComparisonModal();
        } else if (isExplainerDrawerOpen) {
          explainerToolbar.closeExplainer();
        } else if (isPopupOpen) {
          hidePopup();
        }
      }
    });
  }

  // 5. 3D Pillar Layer Toggles
  const btnCyclone = document.getElementById('layer-cyclone');
  const btnDA = document.getElementById('layer-da');
  const btnSpread = document.getElementById('layer-spread');
  const btnMeso = document.getElementById('layer-mesoscale');
  const spreadSlider = document.getElementById('spread-opacity-slider');

  if (btnCyclone) {
    btnCyclone.addEventListener('click', () => {
      const active = btnCyclone.classList.toggle('active-btn');
      setButtonState(btnCyclone, active);
      activePresetId = null;
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('cyclone', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('cyclone', active);
      updateActiveOverlayBadge();
    });
  }

  if (btnDA) {
    btnDA.addEventListener('click', () => {
      const active = btnDA.classList.toggle('active-btn');
      setButtonState(btnDA, active);
      activePresetId = null;
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('da_stations', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('da_stations', active);
      updateActiveOverlayBadge();
    });
  }

  if (btnSpread) {
    btnSpread.addEventListener('click', () => {
      const active = btnSpread.classList.toggle('active-btn');
      setButtonState(btnSpread, active);
      activePresetId = null;
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('ensemble_spread', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('ensemble_spread', active);
      if (active) updateLegend('spread');
      else updateLegend(studyData.getActiveVersionId ? studyData.getActiveVersionId() : 'V3');
      updateActiveOverlayBadge();
    });
  }

  if (btnMeso) {
    btnMeso.addEventListener('click', () => {
      const active = btnMeso.classList.toggle('active-btn');
      setButtonState(btnMeso, active);
      activePresetId = null;
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('mesoscale_insets', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('mesoscale_insets', active);
      updateActiveOverlayBadge();
    });
  }

  if (spreadSlider) {
    spreadSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (studyData.setSpreadOpacity) studyData.setSpreadOpacity(val);
      if (activeLayers3D?.setEnsembleSpreadOpacity) activeLayers3D.setEnsembleSpreadOpacity(val);
    });
  }

  // 5b. Cinematic Atmospheric Layers (Wind Particles & Extreme Hazards)
  const btnWind = document.getElementById('layer-wind');
  const btnHazards = document.getElementById('layer-hazards');

  if (btnWind) {
    btnWind.addEventListener('click', () => {
      const active = btnWind.classList.toggle('active-btn');
      setButtonState(btnWind, active);
      activePresetId = null;
      windParticles.setWindParticlesVisibility(active);
      updateActiveOverlayBadge();
    });
  }

  if (btnHazards) {
    btnHazards.addEventListener('click', () => {
      const active = btnHazards.classList.toggle('active-btn');
      setButtonState(btnHazards, active);
      activePresetId = null;
      hazardAlerts.setHazardAlertsVisibility(active);
      updateActiveOverlayBadge();
    });
  }

  // 5b-2. GEOINT SAR Tip-and-Cue & CATALYST X-Band APS Controls
  const btnSarTasking = document.getElementById('layer-sar-tasking');
  const btnCatalystAps = document.getElementById('toggle-catalyst-aps');
  const btnSarMode = document.getElementById('toggle-sar-mode');
  const btnExportStac = document.getElementById('btn-export-stac');
  const apsStatusLine = document.getElementById('sar-aps-status-line');

  if (btnSarTasking) {
    btnSarTasking.addEventListener('click', () => {
      const active = btnSarTasking.classList.toggle('active-btn');
      setButtonState(btnSarTasking, active);
      activePresetId = null;
      sarTasking.setSarTaskingVisibility(active);
      if (active) {
        updateLegend(sarTasking.getSarDisplayMode() === 'flood_coherence' ? 'sar_flood' : 'sar');
      } else {
        updateLegend(studyData.getActiveVersionId ? studyData.getActiveVersionId() : 'V3');
      }
      updateActiveOverlayBadge();
    });
  }

  if (btnCatalystAps) {
    btnCatalystAps.addEventListener('click', () => {
      const nextAps = !sarTasking.getCatalystApsCorrection();
      sarTasking.setCatalystApsCorrection(nextAps);
      setButtonState(btnCatalystAps, nextAps);
      btnCatalystAps.innerText = nextAps
        ? '🌈 Atmospheric Noise Fix (APS): ON'
        : '🌈 Atmospheric Noise Fix (APS): OFF';
      if (apsStatusLine) {
        apsStatusLine.innerText = nextAps
          ? 'APS STATUS: CATALYST GFS-Corrected (RMSE: 0.16 rad, -98.8%)'
          : 'APS STATUS: Uncorrected Raw Phase (9.2–12.2 Tropo Fringes)';
        apsStatusLine.style.color = nextAps ? '#10b981' : '#fbbf24';
      }
      updateLegend('sar');
      explainerToolbar?.syncToolbarStates?.();
    });
  }

  if (btnSarMode) {
    btnSarMode.addEventListener('click', () => {
      const currentMode = sarTasking.getSarDisplayMode();
      const nextMode = currentMode === 'insar_fringes' ? 'flood_coherence' : 'insar_fringes';
      sarTasking.setSarDisplayMode(nextMode);
      setButtonState(btnSarMode, nextMode === 'flood_coherence');
      btnSarMode.innerText = nextMode === 'flood_coherence'
        ? '🌊 Mode: Flood σ⁰ / γ CCD'
        : '🌊 Mode: InSAR Fringes';
      updateLegend(nextMode === 'flood_coherence' ? 'sar_flood' : 'sar');
    });
  }

  if (btnExportStac) {
    btnExportStac.addEventListener('click', () => {
      const stacOrder = sarTasking.exportStacTaskingOrder(true);
      if (apsStatusLine && stacOrder?.features) {
        apsStatusLine.innerText = `STAC v1.0.0 EXPORTED: ${stacOrder.features.length} Tasking Orders (ICEYE-X38 & StriX-3)`;
        apsStatusLine.style.color = '#38bdf8';
      }
    });
  }

  // 5b-3. Quick View Presets, Clear All, HUD Collapse & Mobile Cam Drawer
  const presetBindings = [
    ['preset-clean', 'clean_globe'],
    ['preset-sar', 'sar_focus'],
    ['preset-weather', 'extreme_weather'],
    ['preset-all', 'all_telemetry'],
    ['btn-clear-layers', 'clear_all']
  ];
  presetBindings.forEach(([elId, presetId]) => {
    const el = document.getElementById(elId);
    if (el) {
      el.addEventListener('click', () => applyLayerPreset(presetId));
    }
  });

  const btnHudCollapse = document.getElementById('btn-hud-collapse');
  const hudPanel = document.querySelector?.('.hud-panel');
  if (btnHudCollapse && hudPanel) {
    btnHudCollapse.addEventListener('click', () => {
      const collapsed = hudPanel.classList.toggle('hud-collapsed');
      btnHudCollapse.innerText = collapsed ? '▾ Expand' : '▴ Collapse';
      btnHudCollapse.setAttribute('aria-expanded', String(!collapsed));
    });
  }

  const btnMobileCam = document.getElementById('btn-mobile-cam-toggle');
  const camWidget = document.getElementById('camera-controls-widget');
  if (btnMobileCam && camWidget) {
    btnMobileCam.addEventListener('click', () => {
      const open = camWidget.classList.toggle('cam-drawer-open');
      setButtonState(btnMobileCam, open);
    });
  }

  // 5c. Forecast Lead-Time Animation Scrubber
  const btnPlayForecast = document.getElementById('btn-play-forecast');
  const forecastLabel = document.getElementById('forecast-time-label');

  if (btnPlayForecast) {
    btnPlayForecast.addEventListener('click', () => {
      isPlayingForecast = !isPlayingForecast;
      btnPlayForecast.innerText = isPlayingForecast ? '⏸ Pause' : '▶ Play 24h';
      btnPlayForecast.style.background = isPlayingForecast ? '#e11d48' : '#0284c7';

      if (isPlayingForecast) {
        if (forecastInterval) clearInterval(forecastInterval);
        activeLayers3D?.highlightCycloneWaypoint?.(forecastStep);
        forecastInterval = setInterval(() => {
          forecastStep = (forecastStep + 1) % 5;
          const leadHours = forecastStep * 6;
          if (forecastLabel) {
            forecastLabel.innerText = `Valid: +${leadHours}h (Step ${forecastStep})`;
          }
          if (studyData?.setActiveTimeStep) {
            studyData.setActiveTimeStep(forecastStep);
          }
          activeLayers3D?.highlightCycloneWaypoint?.(forecastStep);
          // Slight rotational nudge to simulate dynamic atmospheric wave translation
          if (activeGlobe) {
            activeGlobe.rotation.y += 0.04;
          }
        }, 1200);
      } else {
        stopForecastAnimation(false);
      }
    });
  }

  // 6. Baseline Atmospheric & Satellite Layer Toggles (Sat, T2m, Tendency)
  const btnSat = document.getElementById('layer-sat');
  const btnT2m = document.getElementById('layer-t2m');
  const btnTend = document.getElementById('layer-tend');

  if (btnSat) {
    btnSat.addEventListener('click', () => {
      setButtonState(btnSat, true);
      setButtonState(btnT2m, false);
      setButtonState(btnTend, false);
      updateLegend('sat');
    });
  }

  if (btnT2m) {
    btnT2m.addEventListener('click', () => {
      setButtonState(btnT2m, true);
      setButtonState(btnSat, false);
      setButtonState(btnTend, false);
      updateLegend('t2m');
    });
  }

  if (btnTend) {
    btnTend.addEventListener('click', () => {
      setButtonState(btnTend, true);
      setButtonState(btnSat, false);
      setButtonState(btnT2m, false);
      updateLegend('tendency');
    });
  }

  // 7. Auto-Rotation Toggle
  const btnSpin = document.getElementById('toggle-spin');
  if (btnSpin) {
    btnSpin.addEventListener('click', () => {
      setSpinState(!isSpinningState);
    });
  }

  // 8. Topographic Relief Toggle (Single coordinated handler)
  const btnRelief = document.getElementById('toggle-relief');
  if (btnRelief) {
    btnRelief.addEventListener('click', () => {
      toggleReliefState();
    });
  }

  // 9. Resize Listener for Dynamic POI Popup Positioning (T3.7)
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', () => {
      updatePopupPosition(activeCamera, window.innerWidth, window.innerHeight);
    });
  }

  // 10. Listen for external version change to reset forecast animation
  if (studyData?.on) {
    studyData.on('study-version-changed', () => {
      stopForecastAnimation(true);
    });

    studyData.on('timestep-changed', ({ stepIndex }) => {
      if (typeof stepIndex === 'number') {
        activeLayers3D?.highlightCycloneWaypoint?.(stepIndex);
      }
    });

    studyData.on('layer-toggled', ({ layerId, visible }) => {
      if (layerId === 'relief') {
        isReliefActiveState = Boolean(visible);
        const btnRelief = document.getElementById('toggle-relief');
        if (btnRelief) {
          btnRelief.classList.toggle('active-btn', isReliefActiveState);
        }
        if (activeGlobe && activeGlobe.material) {
          activeGlobe.material.bumpScale = isReliefActiveState ? 0.12 : 0.0;
          if (activeGlobe.material.normalScale) {
            activeGlobe.material.normalScale.set(
              isReliefActiveState ? 1.35 : 0.0,
              isReliefActiveState ? 1.35 : 0.0
            );
          }
          activeGlobe.material.needsUpdate = true;
        }
      } else if (layerId === 'rotation') {
        isSpinningState = Boolean(visible);
        const btnSpin = document.getElementById('toggle-spin');
        if (btnSpin) {
          btnSpin.innerText = isSpinningState ? '⏸ Pause Rotation' : '▶ Resume Rotation';
        }
      }
    });
  }

  // Initialize tooltip system and active version to V3
  initTooltipSystem();
  setStudyVersion('V3');
}

// =============================================================================
// 7. DEFAULT CONSOLIDATED EXPORT
// =============================================================================

export default {
  sanitizeHTML,
  getBadge,
  updateLegend,
  showPopup,
  hidePopup,
  openComparisonModal,
  closeComparisonModal,
  setStudyVersion,
  setSpinState,
  getSpinState,
  setReliefState,
  getReliefState,
  toggleReliefState,
  stopForecastAnimation,
  updatePopupPosition,
  setSceneCallbacks,
  applyLayerPreset,
  applyCleanBootDefaults,
  updateActiveOverlayBadge,
  updateTrajectoryCallout,
  openShortcutsModal,
  closeShortcutsModal,
  copyShareLink,
  updatePerfTelemetry,
  initUI
};
