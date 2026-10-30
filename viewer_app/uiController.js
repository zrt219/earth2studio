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
 * OD-EARTH2-001 / EO-OBSCURA: 3D WebGL Digital Twin
 * Interactive User Interface Controller & Glassmorphic HUD
 *
 * Module: viewer_app/uiController.js
 * Author: Zhane Daye (Origin Datum — Independent Research Initiative)
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
  }
}

// =============================================================================
// 3. SCREEN-SPACE GLASSMORPHIC POPUP CARD
// =============================================================================

/**
 * Displays glassmorphic popup card pinned to screen coordinates
 * Conforms to F9.5, T3.2, T3.10
 *
 * @param {object} poiData - Station or Cyclone Waypoint data
 * @param {{ x: number, y: number, visible?: boolean }} screenPos
 */
export function showPopup(poiData, screenPos) {
  if (typeof document === 'undefined') return;

  const popup = document.getElementById('poi-popup-card') || document.getElementById('poi-popup');
  if (!popup) return;

  if (!poiData) {
    hidePopup();
    return;
  }

  activePopupPOI = poiData;

  const titleEl = document.getElementById('popup-title');
  const bodyEl = document.getElementById('popup-body');

  const isStation = Boolean(poiData.increment !== undefined || poiData.wmoId || poiData.type?.includes('Sounding'));

  if (isStation) {
    if (titleEl) {
      titleEl.innerText = `${poiData.name || 'Station'} (${poiData.id || poiData.wmoId})`;
    }
    if (bodyEl) {
      const inc = poiData.increment !== undefined ? poiData.increment : (poiData.obsVal - poiData.bgVal).toFixed(1);
      const elev = poiData.elevM !== undefined ? `${poiData.elevM}m` : (poiData.elevFt ? `${poiData.elevFt}ft` : 'N/A');
      bodyEl.innerHTML = `
        <div style="font-size:0.75rem; line-height:1.45; color:#cbd5e1;">
          <div style="margin-bottom:4px;"><strong>Location:</strong> ${poiData.lat.toFixed(2)}°N, ${poiData.lon.toFixed(2)}°E (${elev})</div>
          <div style="margin-bottom:4px;"><strong>Background (T2m):</strong> ${poiData.bgVal !== undefined ? poiData.bgVal + ' °C' : 'N/A'}</div>
          <div style="margin-bottom:4px;"><strong>Observation:</strong> ${poiData.obsVal !== undefined ? poiData.obsVal + ' °C' : 'N/A'}</div>
          <div style="margin-bottom:4px;"><strong>Innovation:</strong> ${poiData.innovation !== undefined ? poiData.innovation + ' K' : ((poiData.obsVal - poiData.bgVal).toFixed(1) + ' K')}</div>
          <div style="margin-bottom:4px;"><strong>DA Increment:</strong> <span style="color:#f43f5e; font-weight:700;">+${inc} K</span></div>
          <div><strong>QC Status:</strong> <span style="background:rgba(16,185,129,0.2); color:#10b981; padding:2px 6px; border-radius:4px; font-weight:700; font-size:0.7rem;">${sanitizeHTML(poiData.qc || 'PASS')}</span></div>
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
          <div style="margin-bottom:4px;"><strong>Coordinates:</strong> ${poiData.lat.toFixed(2)}°N, ${poiData.lon.toFixed(2)}°E</div>
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

    const clampedX = Math.max(16, Math.min(vpW - 320, posX + 16));
    const clampedY = Math.max(16, Math.min(vpH - 240, posY - 40));

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
 * Renders the 3-column comparison grid with metrics, architecture, and badges
 */
function renderComparisonGrid() {
  const grid = document.getElementById('comparison-grid');
  if (!grid) return;

  const versions = studyData.getStudyVersions ? studyData.getStudyVersions() : null;
  const v1 = versions?.V1 || {};
  const v2 = versions?.V2 || {};
  const v3 = versions?.V3 || {};

  const b1 = getBadge('V1');
  const b2 = getBadge('V2');
  const b3 = getBadge('V3');

  grid.innerHTML = `
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; width:100%;">
      <!-- Column V1 -->
      <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:10px; padding:16px;">
        <div style="display:inline-block; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#ef4444; color:#fff; margin-bottom:8px;">${b1.label}</div>
        <h3 style="font-size:0.95rem; color:#ef4444; margin-bottom:6px;">V1: Quarantined Synthetic Audit</h3>
        <p style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin-bottom:12px;">Historical benchmark with target leakage (ŷ = x₀ + 0.72Δ + ε). Illustrative diagnostic only.</p>
        
        <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; font-size:0.73rem; line-height:1.6;">
          <div><strong>RMSE (T2m):</strong> <span style="color:#ef4444;">0.747 K</span> (Illusory)</div>
          <div><strong>MAE:</strong> 0.582 K</div>
          <div><strong>TAC:</strong> 0.892 (Claimed)</div>
          <div><strong>ACC:</strong> 0.941 (Misattributed)</div>
          <div><strong>Cadence:</strong> 7-day cycles</div>
          <div><strong>Status:</strong> Quarantined</div>
        </div>
      </div>

      <!-- Column V2 -->
      <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:10px; padding:16px;">
        <div style="display:inline-block; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#10b981; color:#fff; margin-bottom:8px;">${b2.label}</div>
        <h3 style="font-size:0.95rem; color:#10b981; margin-bottom:6px;">V2: Decoupled 3-Stage Baseline</h3>
        <p style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin-bottom:12px;">Operational NOAA GFS 0.25° run across strict Forecast → Freeze → Verify pipeline with SHA-256 seal.</p>
        
        <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; font-size:0.73rem; line-height:1.6;">
          <div><strong>RMSE (T2m):</strong> <span style="color:#10b981;">2.129 K</span> (Authentic)</div>
          <div><strong>MAE:</strong> 1.037 K</div>
          <div><strong>TAC:</strong> 0.000 (Exact persistence)</div>
          <div><strong>ACC:</strong> <span style="color:#94a3b8;">null</span> (Rule e2s-014)</div>
          <div><strong>Pipeline:</strong> Forecast → Freeze → Verify</div>
          <div><strong>Hardware:</strong> AMD GPU Blocked</div>
        </div>
      </div>

      <!-- Column V3 -->
      <div style="background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.3); border-radius:10px; padding:16px;">
        <div style="display:inline-block; font-size:0.65rem; font-weight:800; padding:2px 8px; border-radius:4px; background:#0284c7; color:#fff; margin-bottom:8px;">${b3.label}</div>
        <h3 style="font-size:0.95rem; color:#38bdf8; margin-bottom:6px;">V3: 7 Advanced Capability Pillars</h3>
        <p style="font-size:0.75rem; color:#94a3b8; line-height:1.4; margin-bottom:12px;">Massive Ensembles (N=25), Typhoon Tracking, Multi-Source Data, Neural Benchmarks, Alpine Downscaling, DA Pins & 3D Twin.</p>
        
        <div style="background:rgba(0,0,0,0.3); border-radius:8px; padding:10px; font-size:0.73rem; line-height:1.6;">
          <div><strong>Ensemble N=25:</strong> Mean 0.427K | Max 1.182K</div>
          <div><strong>Cyclone WPAC:</strong> 5 Waypoints (935-998 hPa)</div>
          <div><strong>AI Models:</strong> FourCastNet, SFNO, DLWP, ClimaX</div>
          <div><strong>DA Network:</strong> 4 Soundings (+3K to +8K)</div>
          <div><strong>Downscaling:</strong> 8x Alpine Inset (128x128)</div>
          <div><strong>Twin:</strong> 3D Concentric Shells</div>
        </div>
      </div>
    </div>
  `;
}

// =============================================================================
// 5. TIMELINE & STATE SYNCHRONIZATION
// =============================================================================

/**
 * Transitions active study version across UI controls
 * Conforms to F10.1, F10.2, F10.3, F10.4, T3.1, T3.4
 *
 * @param {string} versionId - 'V1', 'V2', 'V3'
 */
export function setStudyVersion(versionId) {
  const norm = String(versionId).toUpperCase();
  if (norm !== 'V1' && norm !== 'V2' && norm !== 'V3') return;

  if (studyData.setActiveVersion) {
    studyData.setActiveVersion(norm);
  }

  // Update tabs
  ['v1', 'v2', 'v3'].forEach(id => {
    const tab = document.getElementById(`tab-${id}`);
    if (tab) {
      if (id === norm.toLowerCase()) {
        tab.classList.add('active-tab');
      } else {
        tab.classList.remove('active-tab');
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

  if (btnCyclone) {
    btnCyclone.classList.toggle('active-btn', isV3);
    btnCyclone.disabled = !isV3;
    btnCyclone.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnDA) {
    btnDA.classList.toggle('active-btn', isV3);
    btnDA.disabled = !isV3;
    btnDA.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnSpread) {
    btnSpread.classList.toggle('active-btn', false);
    btnSpread.disabled = !isV3;
    btnSpread.style.opacity = isV3 ? '1.0' : '0.4';
  }
  if (btnMeso) {
    btnMeso.classList.toggle('active-btn', isV3);
    btnMeso.disabled = !isV3;
    btnMeso.style.opacity = isV3 ? '1.0' : '0.4';
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

  // 3. POI Popup Close Button
  const popupClose = document.getElementById('popup-close');
  if (popupClose) {
    popupClose.addEventListener('click', hidePopup);
  }

  // 4. Global Keyboard Escape Handler (Prioritizes modal over popup per T3.12)
  if (typeof window !== 'undefined') {
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        const modalEl = document.getElementById('comparison-modal');
        const popupEl = document.getElementById('poi-popup-card') || document.getElementById('poi-popup');

        const isModalOpen = modalEl && (modalEl.style.display === 'flex' || !modalEl.classList.contains('hidden'));
        const isPopupOpen = popupEl && (popupEl.style.display === 'block' || !popupEl.classList.contains('hidden'));

        if (isModalOpen) {
          closeComparisonModal();
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
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('cyclone', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('cyclone', active);
    });
  }

  if (btnDA) {
    btnDA.addEventListener('click', () => {
      const active = btnDA.classList.toggle('active-btn');
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('da_stations', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('da_stations', active);
    });
  }

  if (btnSpread) {
    btnSpread.addEventListener('click', () => {
      const active = btnSpread.classList.toggle('active-btn');
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('ensemble_spread', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('ensemble_spread', active);
      if (active) updateLegend('spread');
      else updateLegend(studyData.getActiveVersionId ? studyData.getActiveVersionId() : 'V3');
    });
  }

  if (btnMeso) {
    btnMeso.addEventListener('click', () => {
      const active = btnMeso.classList.toggle('active-btn');
      if (studyData.setLayerVisibility) studyData.setLayerVisibility('mesoscale_insets', active);
      if (activeLayers3D?.setLayerVisibility) activeLayers3D.setLayerVisibility('mesoscale_insets', active);
    });
  }

  if (spreadSlider) {
    spreadSlider.addEventListener('input', (e) => {
      const val = parseFloat(e.target.value);
      if (studyData.setSpreadOpacity) studyData.setSpreadOpacity(val);
      if (activeLayers3D?.setEnsembleSpreadOpacity) activeLayers3D.setEnsembleSpreadOpacity(val);
    });
  }

  // 6. Baseline Atmospheric Layer Toggles (T2m & Tendency)
  const btnT2m = document.getElementById('layer-t2m');
  const btnTend = document.getElementById('layer-tend');

  if (btnT2m) {
    btnT2m.addEventListener('click', () => {
      btnT2m.classList.add('active-btn');
      if (btnTend) btnTend.classList.remove('active-btn');
      updateLegend('t2m');
    });
  }

  if (btnTend) {
    btnTend.addEventListener('click', () => {
      btnTend.classList.add('active-btn');
      if (btnT2m) btnT2m.classList.remove('active-btn');
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

  // 8. Topographic Relief Toggle
  const btnRelief = document.getElementById('toggle-relief');
  if (btnRelief) {
    btnRelief.addEventListener('click', () => {
      isReliefActiveState = !isReliefActiveState;
      if (globe && globe.material) {
        globe.material.bumpScale = isReliefActiveState ? 0.18 : 0.0;
        globe.material.needsUpdate = true;
      }
      btnRelief.classList.toggle('active-btn', isReliefActiveState);
    });
  }

  // Initialize active version to V3
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
  initUI
};
