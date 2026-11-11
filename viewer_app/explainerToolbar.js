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
 * Floating Quick-Toolbar & Interactive '?' Contextual Explainer Drawer
 *
 * Module: viewer_app/explainerToolbar.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 */

export const EXPLAINER_TOPICS = Object.freeze([
  {
    id: 'overview',
    tabLabel: 'Mission Overview',
    badge: 'SYSTEM ARCHITECTURE',
    title: 'Earth-2 X-Band SAR & InSAR Mission Twin',
    summary:
      'Interactive 3D digital twin coupling NOAA GFS / Earth-2 weather hazards with autonomous X-band SAR tasking (ICEYE-X38 & Synspective StriX-3) and CATALYST tropospheric APS phase mitigation.',
    howToUse:
      'Use the floating top bar or the left HUD controls to inspect cities, toggle SAR swaths, enable CATALYST APS phase correction, or launch the 6-step Mission Tutorial.',
    keyMetrics: [
      'X-Band Center Frequency: 9.65 GHz (λ = 3.107 cm)',
      '13 Verified Target Cities inside 131K Sentinel-2 regional crops (Italy & Japan)',
      'Zero synthetic leakage: strict V1 Quarantine -> V2 Decoupled -> V3 7 Pillars lineage'
    ],
    tryActionLabel: '🎓 Start 6-Step Tour',
    tryActionKey: 'start_tour'
  },
  {
    id: 'base_lod',
    tabLabel: '8K–131K Imagery',
    badge: 'BASE GLOBE & SURFACE LOD',
    title: '8K Global PBR + 16K–131K Sentinel-2 Regional LOD',
    summary:
      'Blends an 8K global multi-map PBR globe (albedo, bump, roughness, night lights) with adaptive 16K global octants and ultra-crisp 131K Sentinel-2 cloudless tiles over Italy and Japan as you zoom closer.',
    howToUse:
      'Zoom into Italy or Japan (or pick any city from Target Cities) with "16K–131K Sentinel-2 LOD" active to watch high-resolution regional imagery stream in seamlessly.',
    keyMetrics: [
      'Base Sphere Radius: R = 5.000 (LOD octants R = 5.002–5.005)',
      'Italy Sentinel-2 Crop: 38°N–48°N, 6°E–18°E',
      'Japan Sentinel-2 Crop: 30°N–42°N, 128°E–145°E'
    ],
    tryActionLabel: '📍 Focus Venice Lagoon',
    tryActionKey: 'focus_venice'
  },
  {
    id: 'sar_tasking',
    tabLabel: 'SAR & CATALYST APS',
    badge: 'SAR TIP-AND-CUE & APS FIX',
    title: 'X-Band SAR Swaths & Tropospheric APS Decoupling',
    summary:
      'Simulated atmospheric moisture gradients introduce 9–12 false interferometric fringes (13.8–14.8 rad RMSE). Enabling CATALYST APS correction subtracts the NWP wet+hydrostatic Zenith Total Delay (ZTD), isolating real flood backscatter and slope coherence decay.',
    howToUse:
      'Toggle "SAR Orbits & Swaths", switch between "InSAR Fringes" and "σ⁰ Flood / Coherence", or click "CATALYST APS Fix" to compare raw vs. atmospherically corrected phase.',
    keyMetrics: [
      'Italy ICEYE-X38 (0.5m Spotlight, 28.4°): ZTD 2.3225 m, 12.20 fringes, RMSE 14.78 -> 0.19 rad (-98.73%)',
      'Japan StriX-3 (3.0m StripMap, 34.1°): ZTD 2.369 m, 9.24 fringes, RMSE 13.82 -> 0.16 rad (-98.81%)',
      'STAC v1.0.0 GeoJSON tasking manifest downloadable via Export STAC Order'
    ],
    tryActionLabel: '🌈 Toggle CATALYST APS Fix',
    tryActionKey: 'toggle_aps'
  },
  {
    id: 'cities',
    tabLabel: 'Italy & Japan Cities',
    badge: 'CITY TARGET PICKER',
    title: 'Precision Boresight City Targets (Italy & Japan)',
    summary:
      'All 13 city targets sit inside verified 131K Sentinel-2 regional bounds and lock dead-on to screen center using exact XYZ boresight rotation math (rotX = latRad, rotY = -lonRad - π/2).',
    howToUse:
      'Choose any city from the Italy (7 cities) or Japan (6 cities) dropdowns, click a quick-pick chip, or click any glowing surface beacon directly on the 3D globe.',
    keyMetrics: [
      'Italy (7): Milan, Turin, Venice Lagoon, Bologna / Po Delta, Florence, Rome, Naples / Vesuvius',
      'Japan (6): Tokyo, Mount Fuji, Nagoya, Osaka, Kyoto / Lake Biwa, Sendai',
      '3D Beacon Radial Shell: R = 5.056 (clear of R = 5.050 cyclone tube & R = 5.350 DA caps)'
    ],
    tryActionLabel: '🇯🇵 Fly to Tokyo Bay',
    tryActionKey: 'focus_tokyo'
  },
  {
    id: 'pillars',
    tabLabel: 'V3 7 Pillars',
    badge: 'DATA ASSIMILATION & MESOSCALE',
    title: '3D Advanced Capability Pillars (V3)',
    summary:
      'Combines 25-member ensemble spread shells, 5-waypoint Typhoon Megi trajectory tubes, 8x Alpine/Japan lapse-rate downscaling (6.5 K/km), and 4 Italian WMO radiosonde assimilation beacons.',
    howToUse:
      'Toggle any V3 pillar button in the HUD or click a 3D cyclone waypoint / sounding tower on the globe to inspect WMO background vs. observation increments.',
    keyMetrics: [
      '25-Member Ensemble: CRPS = 0.2896, SSR = 0.892, mean spread = 0.4273 K',
      'Typhoon Megi Track: 964.5 hPa / 105 kt peak -> 981.0 hPa / 65 kt recurvature',
      'Italian Radiosondes: Milan (16080), Bologna (16144), Rome (16245), Naples (16289)'
    ],
    tryActionLabel: '🇮🇹 Fly to Milan',
    tryActionKey: 'focus_milan'
  },
  {
    id: 'cinematic',
    tabLabel: 'Clouds, Wind & Hazards',
    badge: 'CINEMATIC DYNAMICS',
    title: 'Optical Clouds, Wind Streamlines & Hazard Alerts',
    summary:
      'Real-time layered atmospheric context: translucent 3D optical cloud shell (R = 5.012), 3,500 GPU-advected wind particles following baroclinic jets, and clickable extreme hazard alert rings.',
    howToUse:
      'Toggle Clouds, Wind Streamlines, or Extreme Hazards from either the HUD or the top toolbar buttons to reduce visual clutter when inspecting ground-level SAR swaths.',
    keyMetrics: [
      'Cloud Shell Radius: R = 5.012 | Wind Particle Pool: 3,500 advected tracers',
      'Hazard Alert Ring Radius: R = 5.052 (Mediterranean Po Flood & WPAC Typhoon Megi)',
      'Keyboard Controls: Drag orbit, Shift+Drag pan, R / Space reset camera'
    ],
    tryActionLabel: '☁️ Toggle Optical Clouds',
    tryActionKey: 'toggle_clouds'
  },
  {
    id: 'timeline',
    tabLabel: 'V1 -> V2 -> V3 Lineage',
    badge: 'SCIENTIFIC INTEGRITY',
    title: 'Study Trajectory & Rule e2s-014 Audit',
    summary:
      'Documents how synthetic target leakage (V1: alpha = 0.72, RMSE 0.747 K) was quarantined and replaced by genuinely decoupled GFS baselines (V2: RMSE 2.1290 K, TAC = 0.0000) and the verified 7-pillar operational suite (V3).',
    howToUse:
      'Switch V1 / V2 / V3 in the bottom Study Trajectory bar, scrub "+0h to +24h", or open "Compare Versions" for the full SHA-256 audit table.',
    keyMetrics: [
      'V1 (Quarantined): alpha=0.72 leakage, commit 364dba8',
      'V2 (Genuine Baseline): GFS RMSE 2.1290 K, MAE 1.0369 K, TAC 0.0000',
      'V3 (Operational Suite): SHA-256 61a196c1, CATALYST APS -98.7%/-98.8% RMSE'
    ],
    tryActionLabel: '📊 Open Version Matrix',
    tryActionKey: 'open_comparison'
  }
]);

let modalOpen = false;
let currentTopicId = 'overview';
let activeCallbacks = {};

export function getExplainerTopics() {
  return EXPLAINER_TOPICS;
}

export function isExplainerOpen() {
  return modalOpen;
}

function renderTopicContent(topicId) {
  const topic = EXPLAINER_TOPICS.find((t) => t.id === topicId) || EXPLAINER_TOPICS[0];
  currentTopicId = topic.id;

  if (typeof document === 'undefined') return topic;

  const badgeEl = document.getElementById('explainer-topic-badge');
  const titleEl = document.getElementById('explainer-topic-title');
  const summaryEl = document.getElementById('explainer-topic-summary');
  const howToEl = document.getElementById('explainer-topic-howto');
  const metricsEl = document.getElementById('explainer-topic-metrics');
  const tryBtn = document.getElementById('explainer-try-btn');
  const tabBtns = document.querySelectorAll('.explainer-tab-btn');

  if (badgeEl) badgeEl.textContent = topic.badge;
  if (titleEl) titleEl.textContent = topic.title;
  if (summaryEl) summaryEl.textContent = topic.summary;
  if (howToEl) howToEl.textContent = topic.howToUse;
  if (metricsEl) {
    metricsEl.innerHTML = '';
    topic.keyMetrics.forEach((line) => {
      const li = document.createElement('li');
      li.textContent = line;
      metricsEl.appendChild(li);
    });
  }
  if (tryBtn) {
    tryBtn.textContent = topic.tryActionLabel || 'Apply Example';
    tryBtn.setAttribute('data-action-key', topic.tryActionKey || '');
  }
  tabBtns.forEach((btn) => {
    btn.classList.toggle('active-btn', btn.getAttribute('data-topic-id') === topic.id);
  });

  return topic;
}

export function openExplainer(topicId = 'overview') {
  const topic = renderTopicContent(topicId);
  modalOpen = true;
  if (typeof document !== 'undefined') {
    const drawer = document.getElementById('explainer-drawer');
    const helpBtn = document.getElementById('btn-toolbar-help');
    if (drawer) {
      drawer.classList.remove('hidden');
      drawer.style.display = 'flex';
    }
    if (helpBtn) helpBtn.classList.add('active-btn');
  }
  return topic;
}

export function closeExplainer() {
  modalOpen = false;
  if (typeof document !== 'undefined') {
    const drawer = document.getElementById('explainer-drawer');
    const helpBtn = document.getElementById('btn-toolbar-help');
    if (drawer) {
      drawer.classList.add('hidden');
      drawer.style.display = 'none';
    }
    if (helpBtn) helpBtn.classList.remove('active-btn');
  }
}

export function syncToolbarStates() {
  if (typeof document === 'undefined') return;
  const pairs = [
    ['btn-toolbar-cities', 'layer-cities'],
    ['btn-toolbar-sar', 'layer-sar-tasking'],
    ['btn-toolbar-aps', 'toggle-catalyst-aps'],
    ['btn-toolbar-clouds', 'layer-clouds']
  ];
  pairs.forEach(([tbId, hudId]) => {
    const tbEl = document.getElementById(tbId);
    const hudEl = document.getElementById(hudId);
    if (tbEl && hudEl && hudEl.classList) {
      tbEl.classList.toggle('active-btn', hudEl.classList.contains('active-btn'));
    }
  });
}

function runTryAction(actionKey) {
  closeExplainer();
  if (actionKey === 'start_tour') {
    activeCallbacks.startTour?.();
  } else if (actionKey === 'focus_venice') {
    activeCallbacks.focusCity?.('it_venice');
  } else if (actionKey === 'focus_tokyo') {
    activeCallbacks.focusCity?.('jp_tokyo');
  } else if (actionKey === 'focus_milan') {
    activeCallbacks.focusCity?.('it_milan');
  } else if (actionKey === 'toggle_aps') {
    document.getElementById('toggle-catalyst-aps')?.click();
  } else if (actionKey === 'toggle_clouds') {
    document.getElementById('layer-clouds')?.click();
  } else if (actionKey === 'open_comparison') {
    document.getElementById('open-comparison')?.click();
  }
  syncToolbarStates();
}

export function initExplainerToolbar(callbacks = {}) {
  activeCallbacks = callbacks || {};

  if (typeof document === 'undefined') return;

  // Render topic tabs once
  const tabsWrap = document.getElementById('explainer-topic-tabs');
  if (tabsWrap && tabsWrap.children && tabsWrap.children.length === 0) {
    EXPLAINER_TOPICS.forEach((topic) => {
      const btn = document.createElement('button');
      btn.className = 'explainer-tab-btn';
      btn.setAttribute('data-topic-id', topic.id);
      btn.textContent = topic.tabLabel;
      btn.addEventListener('click', () => renderTopicContent(topic.id));
      tabsWrap.appendChild(btn);
    });
  }

  // Help chip triggers inside HUD section headers
  const helpChips = document.querySelectorAll('.help-chip');
  helpChips.forEach((chip) => {
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      const topicId = chip.getAttribute('data-help-topic') || 'overview';
      openExplainer(topicId);
    });
  });

  // Modal close / overlay click / Try It button
  const closeBtn = document.getElementById('explainer-close-btn');
  const drawer = document.getElementById('explainer-drawer');
  const tryBtn = document.getElementById('explainer-try-btn');

  if (closeBtn) closeBtn.addEventListener('click', closeExplainer);
  if (drawer) {
    drawer.addEventListener('click', (e) => {
      if (e.target === drawer) closeExplainer();
    });
  }
  if (tryBtn) {
    tryBtn.addEventListener('click', () => {
      const actionKey = tryBtn.getAttribute('data-action-key');
      if (actionKey) runTryAction(actionKey);
    });
  }

  // Quick-toolbar buttons
  const btnTbCities = document.getElementById('btn-toolbar-cities');
  const btnTbTour = document.getElementById('btn-toolbar-tour');
  const btnTbSar = document.getElementById('btn-toolbar-sar');
  const btnTbAps = document.getElementById('btn-toolbar-aps');
  const btnTbClouds = document.getElementById('btn-toolbar-clouds');
  const btnTbHelp = document.getElementById('btn-toolbar-help');

  if (btnTbCities) {
    btnTbCities.addEventListener('click', () => {
      const targetEl = document.getElementById('city-select-italy');
      if (targetEl && typeof targetEl.scrollIntoView === 'function') {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      if (!activeCallbacks.getActiveCityId?.()) {
        activeCallbacks.focusCity?.('it_milan');
      } else if (typeof targetEl?.focus === 'function') {
        targetEl.focus();
      }
      syncToolbarStates();
    });
  }

  if (btnTbTour) {
    btnTbTour.addEventListener('click', () => {
      closeExplainer();
      activeCallbacks.startTour?.();
    });
  }

  if (btnTbSar) {
    btnTbSar.addEventListener('click', () => {
      document.getElementById('layer-sar-tasking')?.click();
      syncToolbarStates();
    });
  }

  if (btnTbAps) {
    btnTbAps.addEventListener('click', () => {
      document.getElementById('toggle-catalyst-aps')?.click();
      syncToolbarStates();
    });
  }

  if (btnTbClouds) {
    btnTbClouds.addEventListener('click', () => {
      document.getElementById('layer-clouds')?.click();
      syncToolbarStates();
    });
  }

  if (btnTbHelp) {
    btnTbHelp.addEventListener('click', () => {
      if (modalOpen) closeExplainer();
      else openExplainer(currentTopicId || 'overview');
    });
  }

  // Keep toolbar active pills synced when HUD buttons are clicked directly
  ['layer-cities', 'layer-sar-tasking', 'toggle-catalyst-aps', 'layer-clouds'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('click', () => setTimeout(syncToolbarStates, 0));
  });

  syncToolbarStates();
  renderTopicContent('overview');
}

export default {
  EXPLAINER_TOPICS,
  initExplainerToolbar,
  openExplainer,
  closeExplainer,
  isExplainerOpen,
  getExplainerTopics,
  syncToolbarStates
};
