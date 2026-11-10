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
 * Interactive 6-Step Guided Mission Briefing Tutorial
 *
 * Module: viewer_app/tutorialTour.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 */

import studyData from './studyData.js';
import sarTasking from './sarTasking.js';

export const TOUR_STEPS = Object.freeze([
  {
    id: 'step-1-global',
    badge: 'STEP 1 / 6 · MISSION OVERVIEW',
    title: '4K Earth-2 Twin & Anti-Leakage Architecture',
    targetLabel: 'CATALYST · ICEYE · Synspective',
    body:
      'Welcome to the Earth-2 X-Band (9.65 GHz) SAR & InSAR Mission Twin. Built on verified NOAA GFS 0.25° global analyses (Forecast → Freeze → Verify), this 4K physical globe aligns ETOPO mountain relief, ocean roughness, and atmospheric state with 3D LEO SAR constellations.',
    equation: 'λ_X = c / 9.65 GHz = 3.1067 cm  |  4096×2048 [-180°, +180°] Aligned',
    action: ctx => {
      studyData.setActiveVersion('V3');
      ctx.setBaseTexture?.('sat');
      sarTasking.setSarTaskingVisibility(true);
      sarTasking.setCatalystApsCorrection(false);
      sarTasking.setSarDisplayMode('insar_fringes');
      ctx.setSpinState?.(false);
      if (ctx.flyToLatLon) {
        ctx.flyToLatLon(0.0, 0.0, 14.0);
      } else {
        ctx.flyTo?.(0, 0, 14);
      }
    }
  },
  {
    id: 'step-2-iceye-flood',
    badge: 'STEP 2 / 6 · ICEYE FLOOD ATTRIBUTION',
    title: 'ICEYE-X38 Po Valley Specular Flood Mask',
    targetLabel: 'ICEYE Spotlight 0.5m VV (Inc 28.4°)',
    body:
      'An Alpine cold surge triggers autonomous Tip-and-Cue tasking for ICEYE-X38 over Northern Italy. Calm floodwaters in the Po River corridor act as specular reflectors, dropping X-band VV backscatter below -16.5 dB across 735.27 km² while rejecting offshore Bragg sea clutter.',
    equation: 'σ⁰_VV < -16.5 dB  →  735.27 km² Po Valley Flood (min -31.77 dB)',
    action: ctx => {
      studyData.setActiveVersion('V3');
      ctx.setBaseTexture?.('sat');
      sarTasking.setSarTaskingVisibility(true);
      sarTasking.setSarDisplayMode('flood_coherence');
      ctx.setSpinState?.(false);
      ctx.flyToLatLon?.(45.1, 10.6, 8.2);
    }
  },
  {
    id: 'step-3-catalyst-raw',
    badge: 'STEP 3 / 6 · THE INSAR APS BOTTLENECK',
    title: 'Uncorrected X-Band Interferogram (12.2 Fringes)',
    targetLabel: 'CATALYST Tropospheric Delay Challenge',
    body:
      'At X-band, every 1.55 cm change in slant-range tropospheric delay wraps into a full 2π phase fringe. Before atmospheric correction, frontal moisture and Alpine topography inject 12.20 false atmospheric fringes (14.78 rad RMSE), completely burying surface deformation.',
    equation: 'Δφ_APS = (4π / λ_X) · (ZHD + ZWD) / cos(θ_inc)  →  14.78 rad RMSE',
    action: ctx => {
      studyData.setActiveVersion('V3');
      sarTasking.setSarTaskingVisibility(true);
      sarTasking.setSarDisplayMode('insar_fringes');
      sarTasking.setCatalystApsCorrection(false);
      ctx.setSpinState?.(false);
      ctx.flyToLatLon?.(45.1, 10.6, 8.2);
    }
  },
  {
    id: 'step-4-catalyst-fixed',
    badge: 'STEP 4 / 6 · CATALYST APS COMPENSATION',
    title: 'Earth-2 / GFS APS Removal (-98.73% Error)',
    targetLabel: 'CATALYST Phase Screen Correction ON',
    body:
      'Applying our Saastamoinen + Askne–Nordius 8× Nyquist-resolved (0.03125°) phase screen strips away the tropospheric distortion, slashing phase RMSE from 14.78 rad down to 0.187 rad (-98.73%) and cleanly isolating the true 2.2 cm surface deformation bowl.',
    equation: 'φ_corr = φ_raw − φ̂_APS  →  0.1874 rad residual (-98.73% RMSE)',
    action: ctx => {
      studyData.setActiveVersion('V3');
      sarTasking.setSarTaskingVisibility(true);
      sarTasking.setSarDisplayMode('insar_fringes');
      sarTasking.setCatalystApsCorrection(true);
      ctx.setSpinState?.(false);
      ctx.flyToLatLon?.(45.1, 10.6, 8.2);
    }
  },
  {
    id: 'step-5-synspective',
    badge: 'STEP 5 / 6 · SYNSPECTIVE STRIX-3 COHERENCE',
    title: 'Typhoon Megi Slope Coherence Loss (Honshu)',
    targetLabel: 'Synspective StriX-3 StripMap 3.0m (Inc 34.1°)',
    body:
      'Crossing to the Western Pacific, Typhoon Megi (964.5 hPa) cues StriX-3 over Honshu. Repeat-pass Coherent Change Detection (γ_CCD < 0.32) isolates 550.73 km² of steep mountain slope decorrelation while CATALYST APS compensation removes 9.24 typhoon fringes (-98.81%).',
    equation: 'γ_CCD < 0.32 on >300 m slopes  →  550.73 km² Landslide Risk Zone',
    action: ctx => {
      studyData.setActiveVersion('V3');
      sarTasking.setSarTaskingVisibility(true);
      sarTasking.setSarDisplayMode('flood_coherence');
      sarTasking.setCatalystApsCorrection(true);
      ctx.setSpinState?.(false);
      ctx.flyToLatLon?.(35.5, 137.0, 8.4);
    }
  },
  {
    id: 'step-6-stac-report',
    badge: 'STEP 6 / 6 · STAC EXPORT & REPORT',
    title: 'Autonomous STAC v1.0.0 & Engineering Report',
    targetLabel: 'End-to-End Operational Handoff',
    body:
      'Every triggered acquisition exports directly as an OGC STAC v1.0.0 FeatureCollection (with sar:frequency_band, view:incidence_angle, and catalyst:aps_* metadata). Click any 3D satellite/swath on the globe, export STAC JSON, or open the Engineering Report PDF in the HUD.',
    equation: 'OGC STAC v1.0.0 · 321 Pytest + 117 Node E2E + Headless CDP Verified',
    action: ctx => {
      studyData.setActiveVersion('V3');
      ctx.setBaseTexture?.('t2m');
      sarTasking.setSarTaskingVisibility(true);
      sarTasking.setSarDisplayMode('insar_fringes');
      sarTasking.setCatalystApsCorrection(true);
      ctx.setSpinState?.(false);
      ctx.flyToLatLon?.(35.5, 137.0, 9.8);
    }
  }
]);

let isTourActive = false;
let currentStepIndex = 0;
let tourContext = {};
let keydownBound = false;

function syncHudControlsAfterStep() {
  if (typeof document === 'undefined') return;
  const apsBtn = document.getElementById('toggle-catalyst-aps');
  const apsStatus = document.getElementById('sar-aps-status-line');
  const modeBtn = document.getElementById('toggle-sar-mode');
  const sarBtn = document.getElementById('layer-sar-tasking');

  const isCorrected = sarTasking.getCatalystApsCorrection();
  const mode = sarTasking.getSarDisplayMode();
  const visible = sarTasking.getSarTaskingVisibility();

  if (sarBtn) sarBtn.classList.toggle('active-btn', visible);
  if (apsBtn) {
    apsBtn.classList.toggle('active-btn', isCorrected);
    apsBtn.innerText = isCorrected ? '🌈 CATALYST APS Fix: ON' : '🌈 CATALYST APS Fix: OFF';
  }
  if (apsStatus) {
    apsStatus.style.color = isCorrected ? '#10b981' : '#fbbf24';
    apsStatus.innerText = isCorrected
      ? 'APS STATUS: CATALYST GFS-Corrected (RMSE: 0.16 rad, -98.8%)'
      : 'APS STATUS: Uncorrected Raw Phase (9.2–12.2 Tropo Fringes)';
  }
  if (modeBtn) {
    modeBtn.classList.toggle('active-btn', mode === 'flood_coherence');
    modeBtn.innerText =
      mode === 'flood_coherence' ? '🌊 Mode: Flood σ⁰ / γ CCD' : '🌊 Mode: InSAR Fringes';
  }
}

function renderStep(index) {
  if (typeof document === 'undefined') return;
  const clamped = Math.max(0, Math.min(TOUR_STEPS.length - 1, index));
  currentStepIndex = clamped;
  const step = TOUR_STEPS[clamped];

  const card = document.getElementById('mission-tour-card');
  const badgeEl = document.getElementById('tour-step-badge');
  const titleEl = document.getElementById('tour-step-title');
  const targetEl = document.getElementById('tour-step-target');
  const bodyEl = document.getElementById('tour-step-body');
  const eqEl = document.getElementById('tour-step-eq');
  const progEl = document.getElementById('tour-progress-fill');
  const prevBtn = document.getElementById('tour-prev-btn');
  const nextBtn = document.getElementById('tour-next-btn');
  const triggerBtn = document.getElementById('btn-mission-tutorial');

  if (card) card.classList.remove('hidden');
  if (triggerBtn) triggerBtn.classList.add('active-btn');
  if (badgeEl) badgeEl.innerText = step.badge;
  if (titleEl) titleEl.innerText = step.title;
  if (targetEl) targetEl.innerText = step.targetLabel;
  if (bodyEl) bodyEl.innerText = step.body;
  if (eqEl) eqEl.innerText = step.equation;
  if (progEl) progEl.style.width = `${Math.round(((clamped + 1) / TOUR_STEPS.length) * 100)}%`;
  if (prevBtn) prevBtn.disabled = clamped === 0;
  if (nextBtn) {
    nextBtn.innerText = clamped === TOUR_STEPS.length - 1 ? 'Finish ✓' : 'Next →';
  }

  try {
    step.action(tourContext);
    syncHudControlsAfterStep();
  } catch {
    // Safe fallback in headless unit tests without DOM/Three canvas
  }
}

export function startTour(stepIndex = 0) {
  isTourActive = true;
  renderStep(stepIndex);
}

export function nextTourStep() {
  if (!isTourActive) return startTour(0);
  if (currentStepIndex >= TOUR_STEPS.length - 1) {
    stopTour();
    return false;
  }
  renderStep(currentStepIndex + 1);
  return true;
}

export function prevTourStep() {
  if (!isTourActive) return;
  if (currentStepIndex > 0) {
    renderStep(currentStepIndex - 1);
  }
}

export function stopTour() {
  isTourActive = false;
  if (typeof document !== 'undefined') {
    const card = document.getElementById('mission-tour-card');
    const triggerBtn = document.getElementById('btn-mission-tutorial');
    if (card) card.classList.add('hidden');
    if (triggerBtn) triggerBtn.classList.remove('active-btn');
  }
}

export function isMissionTourActive() {
  return isTourActive;
}

export function getCurrentTourStep() {
  return currentStepIndex;
}

const boundElements = new WeakSet();

function bindClickOnce(el, handler) {
  if (!el || boundElements.has(el)) return;
  boundElements.add(el);
  el.addEventListener('click', handler);
}

export function initMissionTutorial(context = {}) {
  tourContext = { ...context };
  if (typeof document === 'undefined') return;

  const btnStart = document.getElementById('btn-mission-tutorial');
  const btnPrev = document.getElementById('tour-prev-btn');
  const btnNext = document.getElementById('tour-next-btn');
  const btnClose = document.getElementById('tour-close-btn');

  bindClickOnce(btnStart, () => {
    if (isTourActive) {
      stopTour();
    } else {
      startTour(0);
    }
  });
  bindClickOnce(btnPrev, prevTourStep);
  bindClickOnce(btnNext, nextTourStep);
  bindClickOnce(btnClose, stopTour);

  if (!keydownBound && typeof window !== 'undefined') {
    keydownBound = true;
    window.addEventListener('keydown', e => {
      if (!isTourActive) return;
      if (e.key === 'ArrowRight') {
        nextTourStep();
      } else if (e.key === 'ArrowLeft') {
        prevTourStep();
      } else if (e.key === 'Escape') {
        const modalEl = document.getElementById('comparison-modal');
        if (modalEl && (modalEl.style.display === 'flex' || !modalEl.classList.contains('hidden'))) {
          // Comparison modal has priority for Escape dismissal
          return;
        }
        stopTour();
      }
    });
  }
}

export default {
  TOUR_STEPS,
  initMissionTutorial,
  startTour,
  nextTourStep,
  prevTourStep,
  stopTour,
  isMissionTourActive,
  getCurrentTourStep
};
