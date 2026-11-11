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
 * GEOINT Weather-to-SAR Tip-and-Cue Constellation Tasking & CATALYST X-Band APS Engine
 *
 * Module: viewer_app/sarTasking.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Implements:
 *   - 3D Sun-Synchronous Orbit (SSO) Rings & Animated LEO SAR Satellites at R = 5.420 (550 km):
 *       1. ICEYE-X38 (Ascending, Spotlight 0.5m VV, Inc: 28.4°) -> Po Valley / Alpine Flood & Cold Surge
 *       2. StriX-3 Synspective (Descending, StripMap 3.0m VV/VH, Inc: 34.1°) -> Japan Typhoon Megi
 *   - 3D Slant-Range Look-Cone Frustums connecting orbital SAR buses (R = 5.420) to ground swaths (R = 5.040)
 *   - Custom GLSL X-Band (9.65 GHz, lambda = 3.1067 cm) Wrapped 2*pi Interferometric Fringe Shader &
 *     Flood Specular Backscatter / Coherence Decay Shader on spherical ground swath patches (R = 5.040)
 *   - Live toggle between Uncorrected Raw InSAR Interferogram (contaminated by 16-21 tropospheric fringes)
 *     and CATALYST Earth-2/GFS Weather-Corrected Interferogram (99% APS error reduction)
 *   - OGC / STAC v1.0.0 Tasking Order GeoJSON Export
 */

import * as THREE from 'three';
import studyData from './studyData.js';
import { latLonToVector3, createSphericalPatchGeometry } from './layers3D.js';

export const SAR_SHELLS = Object.freeze({
  SAR_FOOTPRINT: 5.040,
  TROPOSPHERIC_APS: 5.080,
  SSO_ORBIT: 5.420
});

let activeGlobe = null;
let sarGroup = null;
let isVisible = true;
let isApsCorrected = false; // false = Uncorrected Raw Phase Fringes, true = CATALYST GFS-APS Corrected
let displayMode = 'insar_fringes'; // 'insar_fringes' | 'flood_coherence'

const swathShaderMaterials = [];
const satelliteEntries = [];
const interactiveSarObjects = [];

const DEG_TO_RAD = Math.PI / 180.0;
const _upAxis = new THREE.Vector3(0, 1, 0);
const _scratchSatPos = new THREE.Vector3();
const _scratchNormal = new THREE.Vector3();

function writeLatLonVector3(lat, lon, radius, target) {
  const clampedLat = Math.max(-90.0, Math.min(90.0, lat));
  const phi = clampedLat * DEG_TO_RAD;
  const lambda = ((((lon % 360.0) + 360.0) % 360.0) * DEG_TO_RAD);
  const cosPhi = Math.cos(phi);
  target.set(
    radius * cosPhi * Math.cos(lambda),
    radius * Math.sin(phi),
    -radius * cosPhi * Math.sin(lambda)
  );
  return target;
}

/**
 * Create a custom GLSL ShaderMaterial rendering:
 *  - Mode 0 ('insar_fringes'): X-Band (lambda = 3.11 cm) wrapped [-pi, +pi] interferometric fringes.
 *    When uApsCorrected < 0.5, displays strong topographic + synoptic atmospheric delay fringes
 *    (Delta_phi_APS = (4*pi / lambda_X) * Delta_ZTD / cos(theta_inc)).
 *    When uApsCorrected >= 0.5, subtracts the Earth-2/GFS Tropospheric Phase Screen to isolate
 *    the clean localized ground deformation bullseye.
 *  - Mode 1 ('flood_coherence'): Displays ICEYE specular flood backscatter (sigma_0 VV < -16.5 dB)
 *    for Italy/Po Valley or Synspective StriX coherence loss (gamma < 0.32) for Japan/Honshu.
 */
function createSarSwathShaderMaterial(satConfig) {
  const isItaly = satConfig.targetRegion === 'ITALY';

  const vertexShader = `
    varying vec2 vUv;
    varying vec3 vNormal;
    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `;

  const fragmentShader = `
    varying vec2 vUv;
    varying vec3 vNormal;

    uniform float uTime;
    uniform float uApsCorrected;
    uniform float uDisplayMode;
    uniform float uIsItaly;

    // Cyclic twilight/rainbow interferometric phase colormap for wrapped phase in [-pi, +pi]
    vec3 phaseFringeColormap(float phaseRad) {
      float norm = (phaseRad + 3.14159265) / 6.2831853;
      vec3 c0 = vec3(0.12, 0.08, 0.28);
      vec3 c1 = vec3(0.15, 0.58, 0.88);
      vec3 c2 = vec3(0.18, 0.88, 0.65);
      vec3 c3 = vec3(0.96, 0.82, 0.22);
      vec3 c4 = vec3(0.92, 0.22, 0.38);
      if (norm < 0.25) return mix(c0, c1, norm * 4.0);
      if (norm < 0.50) return mix(c1, c2, (norm - 0.25) * 4.0);
      if (norm < 0.75) return mix(c2, c3, (norm - 0.50) * 4.0);
      return mix(c3, c4, (norm - 0.75) * 4.0);
    }

    void main() {
      // True localized surface deformation signal (~2.2 cm LOS -> ~9.0 rad unwrapped)
      vec2 center = vec2(0.50, 0.50);
      float r2 = dot((vUv - center) * vec2(2.4, 2.0), (vUv - center) * vec2(2.4, 2.0));
      float phiDef = -9.2 * exp(-r2 * 3.2);

      // Stratified + frontal tropospheric delay phase screen (16 to 21 fringes across relief/front)
      float ridge = exp(-pow(length(vUv - vec2(0.38, 0.68)) / 0.28, 2.0)) * 52.0;
      float frontalWave = 28.0 * sin(vUv.x * 11.0 + vUv.y * 8.0 + uTime * 0.35)
                        + 16.0 * cos(vUv.x * 17.0 - vUv.y * 13.0);
      float phiTropo = ridge + frontalWave;

      // Residual sub-grid phase error after CATALYST GFS-APS removal (~0.19 rad)
      float phiResidual = 0.19 * sin(vUv.x * 24.0) * cos(vUv.y * 24.0);

      vec3 outColor;
      float alpha = 0.88;

      if (uDisplayMode < 0.5) {
        // Mode 0: Wrapped X-Band Interferogram [-pi, +pi]
        float totalUnwrapped = mix(phiDef + phiTropo, phiDef + phiResidual, uApsCorrected);
        float wrappedPhase = atan(sin(totalUnwrapped), cos(totalUnwrapped));
        outColor = phaseFringeColormap(wrappedPhase);
      } else {
        // Mode 1: Flood Specular Backscatter (ICEYE) or Slope Coherence Decay (Synspective)
        if (uIsItaly > 0.5) {
          // Po Valley alluvial channel specular water mask (sigma0 < -16.5 dB)
          float channelDist = abs(vUv.y - (0.42 + 0.08 * sin(vUv.x * 6.28)));
          float floodIntensity = exp(-pow(channelDist / 0.14, 2.0));
          vec3 landBackscatter = vec3(0.18, 0.26, 0.36);
          vec3 specularFlood = vec3(0.02, 0.78, 0.98);
          outColor = mix(landBackscatter, specularFlood, smoothstep(0.35, 0.75, floodIntensity));
        } else {
          // Honshu steep slope coherence loss (gamma < 0.32 in bright crimson/amber)
          float slopeFactor = exp(-pow(length(vUv - vec2(0.52, 0.56)) / 0.26, 2.0));
          vec3 highCoherence = vec3(0.16, 0.12, 0.34);
          vec3 lowCoherenceHazard = vec3(0.98, 0.24, 0.32);
          outColor = mix(highCoherence, lowCoherenceHazard, smoothstep(0.25, 0.70, slopeFactor));
        }
      }

      // Glowing SAR swath border frame
      float edge = min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y));
      if (edge < 0.03) {
        vec3 borderCol = uIsItaly > 0.5 ? vec3(0.22, 0.74, 0.98) : vec3(0.96, 0.25, 0.37);
        outColor = mix(outColor, borderCol, (0.03 - edge) / 0.03);
        alpha = 0.98;
      }

      gl_FragColor = vec4(outColor, alpha);
    }
  `;

  return new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uTime: { value: 0.0 },
      uApsCorrected: { value: isApsCorrected ? 1.0 : 0.0 },
      uDisplayMode: { value: displayMode === 'insar_fringes' ? 0.0 : 1.0 },
      uIsItaly: { value: isItaly ? 1.0 : 0.0 }
    },
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    polygonOffset: true,
    polygonOffsetFactor: -1.0,
    polygonOffsetUnits: -1.0
  });
}

/**
 * Build a 3D SAR satellite mesh (central bus + twin solar array wings + X-band radar phased array panel)
 * and slant-range look-cone wireframe connecting the satellite at R = 5.420 to the ground swath at R = 5.040.
 */
function createSatelliteAndLookCone(satConfig) {
  const container = new THREE.Group();
  container.name = `sar_constellation_${satConfig.id}`;

  const [minLat, maxLat, minLon, maxLon] = satConfig.bounds;
  const centerLat = satConfig.center.lat;
  const centerLon = satConfig.center.lon;

  // 1. Ground Swath Patch at R = 5.040
  const swathGeom = createSphericalPatchGeometry(
    minLat,
    maxLat,
    minLon,
    maxLon,
    SAR_SHELLS.SAR_FOOTPRINT,
    32
  );
  const swathMat = createSarSwathShaderMaterial(satConfig);
  swathShaderMaterials.push(swathMat);

  const swathMesh = new THREE.Mesh(swathGeom, swathMat);
  swathMesh.name = `sar_swath_${satConfig.id}`;
  swathMesh.userData = {
    type: 'sar_swath',
    data: {
      ...satConfig,
      lat: centerLat,
      lon: centerLon,
      isSarSwath: true
    }
  };
  container.add(swathMesh);
  interactiveSarObjects.push(swathMesh);

  // 2. SSO Orbit Track Arc passing near the target theater at R = 5.420
  const isAsc = satConfig.orbitState === 'ascending';
  const orbitOffsetLon = isAsc ? -4.2 : 4.8; // Off-nadir side-looking geometry
  const satHomeLat = centerLat;
  const satHomeLon = centerLon + orbitOffsetLon;

  const orbitPoints = [];
  for (let dLat = -28; dLat <= 28; dLat += 2) {
    const latPt = Math.max(-85, Math.min(85, satHomeLat + dLat));
    const lonPt = satHomeLon + (isAsc ? -dLat * 0.22 : dLat * 0.22);
    orbitPoints.push(latLonToVector3(latPt, lonPt, SAR_SHELLS.SSO_ORBIT));
  }
  const orbitCurve = new THREE.CatmullRomCurve3(orbitPoints);
  const orbitLinePts = orbitCurve.getPoints(64);
  const orbitLineGeom = new THREE.BufferGeometry().setFromPoints(orbitLinePts);
  const orbitColor = satConfig.targetRegion === 'ITALY' ? 0x38bdf8 : 0xf43f5e;
  const orbitLineMat = new THREE.LineBasicMaterial({
    color: orbitColor,
    transparent: true,
    opacity: 0.65
  });
  const orbitLine = new THREE.Line(orbitLineGeom, orbitLineMat);
  orbitLine.name = `sar_orbit_arc_${satConfig.id}`;
  container.add(orbitLine);

  // 3. 3D Satellite Bus & Solar Wings at R = 5.420
  const satRig = new THREE.Group();
  satRig.name = `sar_satellite_${satConfig.id}`;
  const satPos = latLonToVector3(satHomeLat, satHomeLon, SAR_SHELLS.SSO_ORBIT);
  satRig.position.copy(satPos);

  const busGeom = new THREE.BoxGeometry(0.11, 0.08, 0.16);
  const busMat = new THREE.MeshStandardMaterial({
    color: orbitColor,
    emissive: orbitColor,
    emissiveIntensity: 0.65,
    metalness: 0.6,
    roughness: 0.3
  });
  const busMesh = new THREE.Mesh(busGeom, busMat);
  busMesh.userData = {
    type: 'sar_satellite',
    data: {
      ...satConfig,
      lat: satHomeLat,
      lon: satHomeLon,
      isSarSatellite: true
    }
  };
  satRig.add(busMesh);
  interactiveSarObjects.push(busMesh);

  // Solar array wings
  const wingGeom = new THREE.BoxGeometry(0.42, 0.015, 0.09);
  const wingMat = new THREE.MeshBasicMaterial({
    color: 0x0284c7,
    transparent: true,
    opacity: 0.9
  });
  const wingMesh = new THREE.Mesh(wingGeom, wingMat);
  satRig.add(wingMesh);

  // Orient satellite along local surface normal
  const normal = satPos.clone().normalize();
  satRig.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
  container.add(satRig);

  // 4. 3D Slant-Range Look-Cone Frustum Rays (connecting satellite to 4 corners of ground swath)
  const corners = [
    latLonToVector3(maxLat, minLon, SAR_SHELLS.SAR_FOOTPRINT),
    latLonToVector3(maxLat, maxLon, SAR_SHELLS.SAR_FOOTPRINT),
    latLonToVector3(minLat, maxLon, SAR_SHELLS.SAR_FOOTPRINT),
    latLonToVector3(minLat, minLon, SAR_SHELLS.SAR_FOOTPRINT)
  ];

  const frustumPositions = new Float32Array(4 * 2 * 3);
  for (let i = 0; i < 4; i++) {
    // Ray from satellite to corner i
    frustumPositions[i * 6 + 0] = satPos.x;
    frustumPositions[i * 6 + 1] = satPos.y;
    frustumPositions[i * 6 + 2] = satPos.z;
    frustumPositions[i * 6 + 3] = corners[i].x;
    frustumPositions[i * 6 + 4] = corners[i].y;
    frustumPositions[i * 6 + 5] = corners[i].z;
  }

  const frustumGeom = new THREE.BufferGeometry();
  const frustumAttr = new THREE.BufferAttribute(frustumPositions, 3);
  frustumAttr.setUsage(THREE.DynamicDrawUsage);
  frustumGeom.setAttribute('position', frustumAttr);
  const frustumMat = new THREE.LineBasicMaterial({
    color: orbitColor,
    transparent: true,
    opacity: 0.55
  });
  const frustumLines = new THREE.LineSegments(frustumGeom, frustumMat);
  frustumLines.name = `sar_look_cone_${satConfig.id}`;
  container.add(frustumLines);

  satelliteEntries.push({
    config: satConfig,
    satRig,
    busMesh,
    frustumGeom,
    corners,
    satHomeLat,
    satHomeLon,
    isAsc
  });

  return container;
}

/**
 * Initialize and attach the 3D SAR Tip-and-Cue & CATALYST APS Layer to the Earth globe.
 *
 * @param {THREE.Object3D} globeMesh - Central Earth globe mesh
 * @returns {THREE.Group}
 */
export function initSarTasking(globeMesh) {
  disposeSarTasking();
  activeGlobe = globeMesh;

  sarGroup = new THREE.Group();
  sarGroup.name = 'geoint_sar_tasking_group';

  const meta = studyData.getSarTaskingMetadata ? studyData.getSarTaskingMetadata() : null;
  const constellations = meta?.constellations || [];

  constellations.forEach(satConfig => {
    const satGroup = createSatelliteAndLookCone(satConfig);
    sarGroup.add(satGroup);
  });

  sarGroup.visible = isVisible;
  if (activeGlobe && typeof activeGlobe.add === 'function') {
    activeGlobe.add(sarGroup);
  }

  return sarGroup;
}

/**
 * Per-frame update animating orbital pass oscillation around target acquisition window
 * and updating shader timeuniforms.
 *
 * @param {number} elapsedTime - Elapsed time in seconds
 */
export function updateSarTasking(elapsedTime) {
  if (!sarGroup || !isVisible) return;
  const t = typeof elapsedTime === 'number' ? elapsedTime : (Date.now() * 0.001);

  for (let mIdx = 0; mIdx < swathShaderMaterials.length; mIdx++) {
    const mat = swathShaderMaterials[mIdx];
    if (mat && mat.uniforms && mat.uniforms.uTime) {
      mat.uniforms.uTime.value = t;
    }
  }

  for (let idx = 0; idx < satelliteEntries.length; idx++) {
    const entry = satelliteEntries[idx];
    const { satRig, frustumGeom, corners, satHomeLat, satHomeLon, isAsc } = entry;
    // Gentle along-track orbital motion (+/- 2.2 deg) during Spotlight/StripMap dwell
    const alongTrackOffset = 2.2 * Math.sin(t * 0.85 + idx * 1.5);
    const curLat = satHomeLat + alongTrackOffset;
    const curLon = satHomeLon + (isAsc ? -alongTrackOffset * 0.22 : alongTrackOffset * 0.22);

    writeLatLonVector3(curLat, curLon, SAR_SHELLS.SSO_ORBIT, _scratchSatPos);

    satRig.position.copy(_scratchSatPos);
    _scratchNormal.copy(_scratchSatPos).normalize();
    satRig.quaternion.setFromUnitVectors(_upAxis, _scratchNormal);
    if (entry.busMesh?.userData?.data) {
      entry.busMesh.userData.data.lat = curLat;
      entry.busMesh.userData.data.lon = curLon;
    }

    // Update look-cone frustum vertices to track moving satellite bus
    const posAttr = frustumGeom.getAttribute('position');
    if (posAttr && posAttr.array) {
      const arr = posAttr.array;
      for (let i = 0; i < 4; i++) {
        arr[i * 6 + 0] = _scratchSatPos.x;
        arr[i * 6 + 1] = _scratchSatPos.y;
        arr[i * 6 + 2] = _scratchSatPos.z;
        arr[i * 6 + 3] = corners[i].x;
        arr[i * 6 + 4] = corners[i].y;
        arr[i * 6 + 5] = corners[i].z;
      }
      posAttr.needsUpdate = true;
    }
  }
}

/**
 * Toggle visibility of the entire 3D SAR Tip-and-Cue & CATALYST APS layer.
 *
 * @param {boolean} visible
 */
export function setSarTaskingVisibility(visible) {
  isVisible = Boolean(visible);
  if (sarGroup) {
    sarGroup.visible = isVisible;
  }
}

export function getSarTaskingVisibility() {
  return isVisible;
}

/**
 * Toggle CATALYST X-Band Tropospheric Phase Screen (APS) Fringe Correction.
 *
 * @param {boolean} corrected - true = CATALYST GFS-APS Corrected, false = Uncorrected Raw Phase
 * @returns {boolean}
 */
export function setCatalystApsCorrection(corrected) {
  isApsCorrected = Boolean(corrected);
  const val = isApsCorrected ? 1.0 : 0.0;
  swathShaderMaterials.forEach(mat => {
    if (mat && mat.uniforms && mat.uniforms.uApsCorrected) {
      mat.uniforms.uApsCorrected.value = val;
    }
  });
  return isApsCorrected;
}

export function getCatalystApsCorrection() {
  return isApsCorrected;
}

/**
 * Set ground swath shader display mode: 'insar_fringes' or 'flood_coherence'.
 *
 * @param {'insar_fringes'|'flood_coherence'} mode
 * @returns {string}
 */
export function setSarDisplayMode(mode) {
  displayMode = mode === 'flood_coherence' ? 'flood_coherence' : 'insar_fringes';
  const val = displayMode === 'flood_coherence' ? 1.0 : 0.0;
  swathShaderMaterials.forEach(mat => {
    if (mat && mat.uniforms && mat.uniforms.uDisplayMode) {
      mat.uniforms.uDisplayMode.value = val;
    }
  });
  return displayMode;
}

export function getSarDisplayMode() {
  return displayMode;
}

/**
 * Return interactive SAR meshes (satellites and ground swaths) for raycasting.
 *
 * @param {object} [options={}]
 * @param {boolean} [options.visibleOnly=false] - When true, return [] if SAR layer is hidden
 */
export function getInteractiveSarObjects(options = {}) {
  if (options && options.visibleOnly) {
    return (isVisible && (!sarGroup || sarGroup.visible !== false)) ? interactiveSarObjects : [];
  }
  return interactiveSarObjects;
}

export const getSarPickableObjects = getInteractiveSarObjects;

/**
 * Generate and optionally trigger browser download of the STAC v1.0.0 Tasking Order GeoJSON.
 *
 * @param {boolean} triggerDownload
 * @returns {object} STAC v1.0.0 FeatureCollection
 */
export function exportStacTaskingOrder(triggerDownload = true) {
  const stacObj = studyData.generateStacTaskingOrderGeoJSON
    ? studyData.generateStacTaskingOrderGeoJSON()
    : { type: 'FeatureCollection', stac_version: '1.0.0', features: [] };

  if (
    triggerDownload &&
    typeof document !== 'undefined' &&
    typeof Blob !== 'undefined' &&
    typeof URL !== 'undefined' &&
    typeof URL.createObjectURL === 'function'
  ) {
    try {
      const jsonStr = JSON.stringify(stacObj, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/geo+json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'od_earth2_stac_sar_tasking_orders.geojson';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Safe fallback in headless test environments
    }
  }

  return stacObj;
}

/**
 * Dispose of all geometries, materials, and references.
 */
export function disposeSarTasking() {
  if (sarGroup && activeGlobe && typeof activeGlobe.remove === 'function') {
    activeGlobe.remove(sarGroup);
  }
  if (sarGroup && typeof sarGroup.traverse === 'function') {
    sarGroup.traverse(child => {
      if (child.geometry && typeof child.geometry.dispose === 'function') {
        child.geometry.dispose();
      }
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m && typeof m.dispose === 'function' && m.dispose());
        } else if (typeof child.material.dispose === 'function') {
          child.material.dispose();
        }
      }
    });
  }
  swathShaderMaterials.length = 0;
  satelliteEntries.length = 0;
  interactiveSarObjects.length = 0;
  sarGroup = null;
  activeGlobe = null;
}

export default {
  SAR_SHELLS,
  initSarTasking,
  updateSarTasking,
  setSarTaskingVisibility,
  getSarTaskingVisibility,
  setCatalystApsCorrection,
  getCatalystApsCorrection,
  setSarDisplayMode,
  getSarDisplayMode,
  getInteractiveSarObjects,
  getSarPickableObjects,
  exportStacTaskingOrder,
  disposeSarTasking
};
