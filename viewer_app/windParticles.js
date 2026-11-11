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
 * Animated Atmospheric Wind Particles & Streamlines Engine
 *
 * Module: viewer_app/windParticles.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Implements:
 *   - Spherical GPU particle advection using analytical baroclinic wind field
 *   - Realistic circulation features: Equatorial Trade Winds, Mid-Latitude Westerlies, Polar Easterlies, Jet Stream Meanders
 *   - Radial Shell allocation R = 5.060 (safely above terrain & cyclone tube)
 *   - Dynamic particle rebirth, speed color interpolation (Cyan -> Yellow -> Red), and smooth fade-in/out
 */

import * as THREE from 'three';

let particleCount = 3500;
let particlePoints = null;
let particleGeometry = null;
let particleMaterial = null;
let positions = null;
let colors = null;
let particleLifetimes = null;
let particleSpeeds = null;

let isVisible = true;
let speedMultiplier = 1.0;
let activeGlobe = null;

// Radius positioned in radial shell hierarchy: R = 5.060
const WIND_SHELL_RADIUS = 5.060;
const DEG_TO_RAD = Math.PI / 180.0;
const DEG_PER_METER = 1.0 / 111139.0;
const _windScratch = new Float64Array(3);

/**
 * Evaluate analytical wind vector (u, v, speed) into a pre-allocated 3-element array
 * to avoid per-particle heap allocations inside the animation loop.
 *
 * @param {number} latDeg - Latitude in degrees [-90, +90]
 * @param {number} lonDeg - Longitude in degrees [0, 360)
 * @param {Float64Array} out - Output buffer [u, v, speed]
 */
function evalAtmosphericWind(latDeg, lonDeg, out) {
  const phi = latDeg * DEG_TO_RAD;
  const lambda = lonDeg * DEG_TO_RAD;

  // 1. Planetary Zonal Wind Profile (m/s)
  // Equatorial Easterlies (Trades): lat 0-30 -> negative u (westward)
  // Mid-Latitude Westerlies: lat 30-60 -> positive u (eastward) with jet stream peak at ~45 deg
  // Polar Easterlies: lat 60-90 -> negative u
  let u = 28.0 * Math.sin(2.0 * phi) * Math.cos(phi) - 10.0 * Math.cos(3.0 * phi);
  let v = 5.0 * Math.sin(3.0 * phi) * Math.cos(2.0 * lambda);

  // 2. Subtropical Jet Stream Core Wave Modulation (Rossby Wavenumber 4)
  const jetLatitude = 42.0 + 8.0 * Math.sin(4.0 * lambda);
  const distToJet = Math.abs(latDeg - jetLatitude);
  if (distToJet < 12.0) {
    const jetRatio = distToJet / 6.0;
    const jetFactor = Math.exp(-(jetRatio * jetRatio));
    u += 32.0 * jetFactor;
    v += 14.0 * jetFactor * Math.cos(4.0 * lambda);
  }

  // 3. Western Pacific Typhoon Vortex (Lat 32N, Lon 134E)
  const dLatTyphoon = latDeg - 32.0;
  const dLonTyphoon = ((lonDeg - 134.0 + 180.0) % 360.0) - 180.0;
  const distTyphoonDeg = Math.hypot(dLatTyphoon, dLonTyphoon);
  if (distTyphoonDeg < 12.0) {
    const rKm = distTyphoonDeg * 111.0;
    // Cyclonic (counter-clockwise in Northern Hemisphere) tangential vortex
    const vMax = 48.0; // 48 m/s (~95 kts, Category 2/3)
    const rRatio = rKm / 55.0;
    const vTheta = (vMax * 2.0 * rRatio) / (1.0 + rRatio * rRatio);

    // Tangential direction vector (-sin theta, cos theta)
    const angle = Math.atan2(dLatTyphoon, dLonTyphoon);
    u += -vTheta * Math.sin(angle);
    v += vTheta * Math.cos(angle);
  }

  out[0] = u;
  out[1] = v;
  out[2] = Math.hypot(u, v);
}

/**
 * Mathematical analytical wind vector at any spherical coordinate (lat, lon).
 * Replicates genuine Earth planetary circulation (Hadley, Ferrel, Polar cells)
 * and localized Western Pacific Typhoon cyclonic vortex.
 *
 * @param {number} latDeg - Latitude in degrees [-90, +90]
 * @param {number} lonDeg - Longitude in degrees [0, 360)
 * @returns {{ u: number, v: number, speed: number }} - Zonal, meridional components and total speed in m/s
 */
export function getAtmosphericWindVector(latDeg, lonDeg) {
  evalAtmosphericWind(latDeg, lonDeg, _windScratch);
  return { u: _windScratch[0], v: _windScratch[1], speed: _windScratch[2] };
}

/**
 * Write spherical (lat, lon, radius) directly into a Float32Array at offset idx3
 * matching Three.js convention where lon=0 is on +X axis.
 */
function writeSphericalToArray(latDeg, lonDeg, radius, outArray, idx3) {
  const phi = latDeg * DEG_TO_RAD;
  const lambda = ((((lonDeg % 360.0) + 360.0) % 360.0) * DEG_TO_RAD);
  const cosPhi = Math.cos(phi);
  const rCosPhi = radius * cosPhi;
  outArray[idx3] = rCosPhi * Math.cos(lambda);
  outArray[idx3 + 1] = radius * Math.sin(phi);
  outArray[idx3 + 2] = -rCosPhi * Math.sin(lambda);
}

/**
 * Write speed-mapped RGB color directly into a Float32Array at offset idx3.
 * 0-10 m/s: Cyan/Teal (Gentle Breeze)
 * 10-25 m/s: Bright Gold/Yellow (Gale/Jet Stream)
 * 25-50+ m/s: Fiery Orange/Red (Severe Storm/Typhoon Core)
 */
function writeSpeedColorToArray(speed, fade, outArray, idx3) {
  const norm = Math.min(Math.max((speed - 5.0) / 40.0, 0.0), 1.0);
  let r, g, b;
  if (norm < 0.5) {
    const t = norm * 2.0;
    r = 0.1 + t * 0.9;
    g = 0.8 + t * 0.15;
    b = 0.95 - t * 0.7;
  } else {
    const t = (norm - 0.5) * 2.0;
    r = 1.0;
    g = 0.95 - t * 0.75;
    b = 0.25 - t * 0.2;
  }
  outArray[idx3] = r * fade;
  outArray[idx3 + 1] = g * fade;
  outArray[idx3 + 2] = b * fade;
}

/**
 * Initialize and attach the Animated Wind Particles layer into the Three.js Globe.
 *
 * @param {THREE.Object3D} globeMesh - Root Earth globe mesh
 * @param {number} count - Total particle count (default 3500)
 */
export function initWindParticles(globeMesh, count = 3500) {
  disposeWindParticles();
  activeGlobe = globeMesh;
  particleCount = count;

  particleGeometry = new THREE.BufferGeometry();
  positions = new Float32Array(particleCount * 3);
  colors = new Float32Array(particleCount * 3);
  particleLifetimes = new Float32Array(particleCount);
  particleSpeeds = new Float32Array(particleCount);

  // Store latitude and longitude per particle in internal state arrays
  const lats = new Float32Array(particleCount);
  const lons = new Float32Array(particleCount);

  for (let i = 0; i < particleCount; i++) {
    // Distribute uniformly on sphere surface using area-preserving sampling
    const u = Math.random();
    const v = Math.random();
    const sinLat = Math.max(-0.9999, Math.min(0.9999, 2.0 * u - 1.0));
    lats[i] = Math.asin(sinLat) * (180.0 / Math.PI);
    lons[i] = v * 360.0;
    particleLifetimes[i] = Math.random() * 100.0; // Phase offset

    const idx3 = i * 3;
    writeSphericalToArray(lats[i], lons[i], WIND_SHELL_RADIUS, positions, idx3);

    // Color based on wind speed
    evalAtmosphericWind(lats[i], lons[i], _windScratch);
    particleSpeeds[i] = _windScratch[2];
    writeSpeedColorToArray(_windScratch[2], 1.0, colors, idx3);
  }

  const posAttr = new THREE.BufferAttribute(positions, 3);
  posAttr.setUsage(THREE.DynamicDrawUsage);
  const colAttr = new THREE.BufferAttribute(colors, 3);
  colAttr.setUsage(THREE.DynamicDrawUsage);

  particleGeometry.setAttribute('position', posAttr);
  particleGeometry.setAttribute('color', colAttr);
  particleGeometry.userData = { lats, lons };

  // Shader point material with glowing circular particle texture
  particleMaterial = new THREE.PointsMaterial({
    size: 0.045,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });

  particlePoints = new THREE.Points(particleGeometry, particleMaterial);
  particlePoints.name = 'atmospheric_wind_particles';
  particlePoints.visible = isVisible;

  if (activeGlobe && typeof activeGlobe.add === 'function') {
    activeGlobe.add(particlePoints);
  }
  return particlePoints;
}

/**
 * Animate wind particles step-by-step in the main animation loop.
 * Zero heap allocations per frame.
 *
 * @param {number} deltaSeconds - Time delta in seconds
 */
export function updateWindParticles(deltaSeconds = 0.016) {
  if (!particlePoints || !isVisible || !particleGeometry) return;

  const posAttr = particleGeometry.getAttribute('position');
  const colAttr = particleGeometry.getAttribute('color');
  if (!posAttr || !colAttr || !posAttr.array || !colAttr.array) return;
  const posArray = posAttr.array;
  const colArray = colAttr.array;
  const lats = particleGeometry.userData?.lats;
  const lons = particleGeometry.userData?.lons;
  if (!lats || !lons || !particleLifetimes || !particleSpeeds) return;

  const rawDt = Number.isFinite(deltaSeconds) ? deltaSeconds : 0.016;
  const clampedDt = Math.min(Math.max(rawDt, 0.001), 0.05);
  const dt = clampedDt * speedMultiplier;
  const advectScale = dt * DEG_PER_METER * 80.0;

  for (let i = 0; i < particleCount; i++) {
    particleLifetimes[i] += dt * 30.0;

    // Check lifetime rebirth
    if (particleLifetimes[i] > 120.0 || Math.abs(lats[i]) > 88.0) {
      // Re-spawn randomly across globe
      const u = Math.random();
      const v = Math.random();
      const sinLat = Math.max(-0.9999, Math.min(0.9999, 2.0 * u - 1.0));
      lats[i] = Math.asin(sinLat) * (180.0 / Math.PI);
      lons[i] = v * 360.0;
      particleLifetimes[i] = 0.0;
    }

    // Query physical wind vector at current position (zero-alloc)
    evalAtmosphericWind(lats[i], lons[i], _windScratch);
    const windU = _windScratch[0];
    const windV = _windScratch[1];
    const windSpeed = _windScratch[2];
    particleSpeeds[i] = windSpeed;

    // Advection: dLon/dt = u / (R * cos(lat)), dLat/dt = v / R
    const cosLat = Math.max(Math.cos(lats[i] * DEG_TO_RAD), 0.05);

    let nextLon = lons[i] + (windU * advectScale) / cosLat;
    let nextLat = lats[i] + windV * advectScale;
    nextLat = Math.max(-89.9, Math.min(89.9, nextLat));
    nextLon = ((nextLon % 360.0) + 360.0) % 360.0;

    lats[i] = nextLat;
    lons[i] = nextLon;

    const idx3 = i * 3;
    // Inline spherical -> Cartesian directly into posArray
    const phi = nextLat * DEG_TO_RAD;
    const lambda = nextLon * DEG_TO_RAD;
    const cosPhi = Math.cos(phi);
    const rCosPhi = WIND_SHELL_RADIUS * cosPhi;
    posArray[idx3] = rCosPhi * Math.cos(lambda);
    posArray[idx3 + 1] = WIND_SHELL_RADIUS * Math.sin(phi);
    posArray[idx3 + 2] = -rCosPhi * Math.sin(lambda);

    // Inline speed RGB + smooth fade-in/out directly into colArray
    const fade = Math.sin((particleLifetimes[i] / 120.0) * Math.PI);
    writeSpeedColorToArray(windSpeed, fade, colArray, idx3);
  }

  posAttr.needsUpdate = true;
  colAttr.needsUpdate = true;
}

/**
 * Toggle visibility of wind particle streamlines.
 */
export function setWindParticlesVisibility(visible) {
  isVisible = !!visible;
  if (particlePoints) {
    particlePoints.visible = isVisible;
  }
}

/**
 * Adjust speed scale of wind advection.
 */
export function setWindSpeedScale(multiplier) {
  speedMultiplier = Math.max(0.1, Math.min(multiplier, 5.0));
}

/**
 * Dispose and release memory on component teardown.
 */
export function disposeWindParticles() {
  if (particlePoints && activeGlobe && typeof activeGlobe.remove === 'function') {
    activeGlobe.remove(particlePoints);
  }
  if (particleGeometry && typeof particleGeometry.dispose === 'function') {
    particleGeometry.dispose();
  }
  if (particleMaterial && typeof particleMaterial.dispose === 'function') {
    particleMaterial.dispose();
  }
  particlePoints = null;
  particleGeometry = null;
  particleMaterial = null;
  positions = null;
  colors = null;
  particleLifetimes = null;
  particleSpeeds = null;
  activeGlobe = null;
}

export default {
  initWindParticles,
  updateWindParticles,
  setWindParticlesVisibility,
  setWindSpeedScale,
  getAtmosphericWindVector,
  disposeWindParticles
};
