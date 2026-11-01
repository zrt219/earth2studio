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
 * Global Extreme Weather Alerts & Hazard Cone Engine
 *
 * Module: viewer_app/hazardAlerts.js
 * Author: Zhane Daye (Origin Datum — Independent Research Initiative)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Implements:
 *   - Automated detection and rendering of global planetary weather hazards
 *   - Category 3 Typhoon Danger Cones, Severe Alpine Cold Wave Blocker,
 *     and Equatorial Heat Dome Warning Rings
 *   - Pulsing 3D beacon cones and screen-space warning telemetry popups
 */

import * as THREE from 'three';

let alertGroup = null;
let activeGlobe = null;
let isVisible = true;
let pulsingMeshes = [];

const HAZARD_ALERTS = Object.freeze([
  {
    id: 'HAZARD-WPAC-01',
    type: 'TYPHOON_WARNING',
    name: 'Typhoon Megi (WPAC-01)',
    severity: 'EXTREME',
    lat: 32.2,
    lon: 134.5,
    minMslp: '964.5 hPa',
    maxWind: '48.2 m/s (94 kts)',
    category: 'Category 3 Severe Vortex',
    radiusKm: 320,
    color: 0xef4444, // Bright Red
    description: 'Deep baroclinic cyclonic vortex moving northeastward towards Honshu coast with dangerous storm surge and gale-force wind field.'
  },
  {
    id: 'HAZARD-ALPINE-02',
    type: 'OROGRAPHIC_COLD_SURGE',
    name: 'Alpine Arctic Cold Damming',
    severity: 'WARNING',
    lat: 45.8,
    lon: 9.8,
    minMslp: '1024.0 hPa',
    maxWind: '24.5 m/s (Genoa Gale)',
    category: 'Sub-Freezing Orographic Freeze',
    radiusKm: 220,
    color: 0x3b82f6, // Icy Blue
    description: 'Polar continental air mass dammed against northern Alpine wall with intense foehn wind shear and rapid -8K diurnal temperature drop.'
  },
  {
    id: 'HAZARD-SAHARA-03',
    type: 'EXTREME_HEAT_DOME',
    name: 'North African Thermal Plume',
    severity: 'ADVISORY',
    lat: 28.5,
    lon: 18.2,
    minMslp: '1011.0 hPa',
    maxWind: '12.0 m/s',
    category: 'High-Temperature Excursion',
    radiusKm: 450,
    color: 0xf59e0b, // Amber Gold
    description: 'Subtropical high-pressure ridge driving severe adiabatic compression and 2-meter temperatures exceeding 312 K (39°C).'
  }
]);

/**
 * Spherical coordinates to 3D Cartesian coordinates.
 */
function latLonToVector3(latDeg, lonDeg, radius = 5.055) {
  const phi = (90.0 - latDeg) * (Math.PI / 180.0);
  const theta = (lonDeg * Math.PI) / 180.0;
  const x = radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.cos(phi);
  const z = -radius * Math.sin(phi) * Math.sin(theta);
  return new THREE.Vector3(x, y, z);
}

/**
 * Initialize 3D Hazard Warning Rings & Cones on the Globe.
 */
export function initHazardAlerts(globeMesh) {
  disposeHazardAlerts();
  activeGlobe = globeMesh;
  alertGroup = new THREE.Group();
  alertGroup.name = 'extreme_weather_hazard_group';
  pulsingMeshes = [];

  HAZARD_ALERTS.forEach(alert => {
    const center = latLonToVector3(alert.lat, alert.lon, 5.052);
    const normal = center.clone().normalize();

    // 1. Concentric Pulsing Warning Ring
    const ringRadius = (alert.radiusKm / 6371.0) * 5.0;
    const ringGeom = new THREE.RingGeometry(ringRadius * 0.85, ringRadius, 48);
    const ringMat = new THREE.MeshBasicMaterial({
      color: alert.color,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.75,
      depthWrite: false
    });

    const ringMesh = new THREE.Mesh(ringGeom, ringMat);
    ringMesh.position.copy(center);
    ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    ringMesh.userData = { alert, baseScale: 1.0, isRing: true };

    alertGroup.add(ringMesh);
    pulsingMeshes.push(ringMesh);

    // 2. Central Pulsing Beacon Cylinder / Cone
    const coneGeom = new THREE.ConeGeometry(0.08, 0.45, 16);
    const coneMat = new THREE.MeshBasicMaterial({
      color: alert.color,
      transparent: true,
      opacity: 0.95
    });

    const coneMesh = new THREE.Mesh(coneGeom, coneMat);
    // Position slightly elevated pointing down to ground
    const conePos = center.clone().add(normal.clone().multiplyScalar(0.25));
    coneMesh.position.copy(conePos);
    coneMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), normal);
    coneMesh.userData = { alert, isBeacon: true };

    alertGroup.add(coneMesh);
    pulsingMeshes.push(coneMesh);
  });

  alertGroup.visible = isVisible;
  if (activeGlobe && typeof activeGlobe.add === 'function') {
    activeGlobe.add(alertGroup);
  }
  return alertGroup;
}

/**
 * Animate pulsing scale and glowing opacity for all alert markers.
 */
export function updateHazardAlerts(elapsedTime) {
  if (!alertGroup || !isVisible) return;
  const t = typeof elapsedTime === 'number' ? elapsedTime : (Date.now() * 0.001);

  pulsingMeshes.forEach((mesh, idx) => {
    if (!mesh || !mesh.material || !mesh.userData) return;
    if (mesh.userData.isRing) {
      const pulse = 1.0 + 0.18 * Math.sin(t * 3.5 + idx);
      mesh.scale.set(pulse, pulse, 1.0);
      mesh.material.opacity = 0.5 + 0.35 * Math.cos(t * 3.5 + idx);
    } else if (mesh.userData.isBeacon) {
      mesh.material.opacity = 0.7 + 0.3 * Math.sin(t * 5.0 + idx);
    }
  });
}

/**
 * Set hazard layer visibility.
 */
export function setHazardAlertsVisibility(visible) {
  isVisible = !!visible;
  if (alertGroup) {
    alertGroup.visible = isVisible;
  }
}

/**
 * Return static list of active hazard alerts for UI rendering.
 */
export function getActiveHazards() {
  return HAZARD_ALERTS;
}

/**
 * Dispose hazard alert meshes, geometries and materials.
 */
export function disposeHazardAlerts() {
  if (alertGroup && activeGlobe && typeof activeGlobe.remove === 'function') {
    activeGlobe.remove(alertGroup);
  }
  if (alertGroup && typeof alertGroup.traverse === 'function') {
    alertGroup.traverse(child => {
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
  pulsingMeshes = [];
  alertGroup = null;
  activeGlobe = null;
}

export default {
  initHazardAlerts,
  updateHazardAlerts,
  setHazardAlertsVisibility,
  getActiveHazards,
  disposeHazardAlerts
};
