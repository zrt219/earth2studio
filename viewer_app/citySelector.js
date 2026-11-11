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
 * Interactive Italy & Japan City Target Selector & 3D Surface Beacons
 *
 * Module: viewer_app/citySelector.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 */

import * as THREE from 'three';
import studyData from './studyData.js';
import layers3D from './layers3D.js';

export const CITY_SHELL_RADIUS = 5.056;

let parentGlobe = null;
let cityGroup = null;
let cityPickables = [];
let haloMeshes = [];
let markersVisible = true;
let activeCityId = null;
let onVisibilityChangeCb = null;

function createCityBeacon(city) {
  const payload = {
    ...city,
    type: 'target_city',
    isTargetCity: true
  };

  const pos = layers3D.latLonToVector3(city.lat, city.lon, CITY_SHELL_RADIUS);
  const normal = pos.clone().normalize();
  const markerRoot = new THREE.Group();
  markerRoot.position.copy(pos);
  markerRoot.name = `city_beacon_${city.id}`;
  markerRoot.userData = {
    type: 'target_city',
    isTargetCity: true,
    cityId: city.id,
    data: payload
  };

  const isItaly = city.country === 'Italy';
  const primaryColor = isItaly ? 0x38bdf8 : 0xf43f5e;
  const accentColor = isItaly ? 0x10b981 : 0xfbbf24;

  // Tangent outer surface ring
  const ringGeom = new THREE.RingGeometry(0.042, 0.068, 24);
  const ringMat = new THREE.MeshBasicMaterial({
    color: primaryColor,
    transparent: true,
    opacity: 0.78,
    side: THREE.DoubleSide,
    depthWrite: false
  });
  const ringMesh = new THREE.Mesh(ringGeom, ringMat);
  ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
  ringMesh.userData = { type: 'target_city', isTargetCity: true, cityId: city.id, data: payload };
  markerRoot.add(ringMesh);
  haloMeshes.push({ mesh: ringMesh, cityId: city.id, baseOpacity: 0.78 });

  // Core emissive dot
  const coreGeom = new THREE.SphereGeometry(0.026, 12, 12);
  const coreMat = new THREE.MeshBasicMaterial({
    color: accentColor
  });
  const coreMesh = new THREE.Mesh(coreGeom, coreMat);
  coreMesh.userData = { type: 'target_city', isTargetCity: true, cityId: city.id, data: payload };
  markerRoot.add(coreMesh);

  // Invisible generous click target for reliable orbital raycasting
  const hitGeom = new THREE.SphereGeometry(0.095, 10, 10);
  const hitMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    transparent: true,
    opacity: 0.0,
    depthWrite: false
  });
  const hitMesh = new THREE.Mesh(hitGeom, hitMat);
  hitMesh.userData = { type: 'target_city', isTargetCity: true, cityId: city.id, data: payload };
  markerRoot.add(hitMesh);

  cityPickables.push(hitMesh, coreMesh, ringMesh);
  return markerRoot;
}

export function initCitySelector(globe, callbacks = {}) {
  disposeCitySelector();
  parentGlobe = globe || null;
  onVisibilityChangeCb = typeof callbacks.onVisibilityChange === 'function' ? callbacks.onVisibilityChange : null;

  if (parentGlobe) {
    cityGroup = new THREE.Group();
    cityGroup.name = 'city_target_markers_group';
    cityGroup.visible = markersVisible;

    const cities = studyData.getTargetCities();
    cities.forEach((city) => {
      const beacon = createCityBeacon(city);
      cityGroup.add(beacon);
    });
    parentGlobe.add(cityGroup);
  }

  if (typeof document !== 'undefined') {
    const selItaly = document.getElementById('city-select-italy');
    const selJapan = document.getElementById('city-select-japan');
    const btnToggle = document.getElementById('layer-cities');
    const quickChips = document.querySelectorAll('.city-quick-chip');

    if (selItaly) {
      selItaly.addEventListener('change', (e) => {
        if (e.target.value) {
          if (selJapan) selJapan.value = '';
          focusCity(e.target.value, callbacks);
        }
      });
    }

    if (selJapan) {
      selJapan.addEventListener('change', (e) => {
        if (e.target.value) {
          if (selItaly) selItaly.value = '';
          focusCity(e.target.value, callbacks);
        }
      });
    }

    if (btnToggle) {
      btnToggle.addEventListener('click', () => {
        setCityMarkersVisibility(!markersVisible);
      });
    }

    quickChips.forEach((chip) => {
      chip.addEventListener('click', () => {
        const cid = chip.getAttribute('data-city-id');
        if (cid) focusCity(cid, callbacks);
      });
    });
  }

  return cityGroup;
}

export function setCityMarkersVisibility(visible) {
  markersVisible = Boolean(visible);
  if (cityGroup) {
    cityGroup.visible = markersVisible;
  }
  if (typeof document !== 'undefined') {
    const btn = document.getElementById('layer-cities');
    if (btn) {
      btn.classList.toggle('active-btn', markersVisible);
      btn.setAttribute('aria-pressed', String(markersVisible));
    }
    const tbBtn = document.getElementById('btn-toolbar-cities');
    if (tbBtn) {
      tbBtn.classList.toggle('active-btn', markersVisible);
      tbBtn.setAttribute('aria-pressed', String(markersVisible));
    }
  }
  onVisibilityChangeCb?.(markersVisible);
  return markersVisible;
}

export function getCityMarkersVisibility() {
  return markersVisible;
}

export function getInteractiveCityObjects({ visibleOnly = false } = {}) {
  if (visibleOnly) {
    return markersVisible ? cityPickables : [];
  }
  return cityPickables;
}

export function getActiveCityId() {
  return activeCityId;
}

export function focusCity(cityId, callbacks = {}) {
  const city = studyData.getTargetCityById(cityId);
  if (!city) return null;

  activeCityId = city.id;

  if (!markersVisible) {
    setCityMarkersVisibility(true);
  }

  callbacks.setSpinState?.(false);
  callbacks.flyToLatLon?.(city.lat, city.lon, city.zoomDistance || 5.95);

  if (typeof document !== 'undefined') {
    const selItaly = document.getElementById('city-select-italy');
    const selJapan = document.getElementById('city-select-japan');
    if (city.country === 'Italy') {
      if (selItaly) selItaly.value = city.id;
      if (selJapan) selJapan.value = '';
    } else if (city.country === 'Japan') {
      if (selJapan) selJapan.value = city.id;
      if (selItaly) selItaly.value = '';
    }

    const quickChips = document.querySelectorAll('.city-quick-chip');
    quickChips.forEach((chip) => {
      chip.classList.toggle('active-btn', chip.getAttribute('data-city-id') === city.id);
    });
  }

  const w = typeof window !== 'undefined' && window.innerWidth ? window.innerWidth : 1920;
  const h = typeof window !== 'undefined' && window.innerHeight ? window.innerHeight : 1080;
  const screenPos = {
    x: Math.round(w * 0.54),
    y: Math.round(h * 0.42)
  };

  callbacks.showPopup?.(
    {
      ...city,
      type: 'target_city',
      isTargetCity: true
    },
    screenPos
  );

  return city;
}

export function updateCityMarkers(elapsedTime = 0) {
  if (!markersVisible || haloMeshes.length === 0) return;
  const wave = 0.5 + 0.5 * Math.sin(elapsedTime * 3.2);
  for (let i = 0; i < haloMeshes.length; i += 1) {
    const item = haloMeshes[i];
    const isActive = item.cityId === activeCityId;
    const scale = isActive ? 1.35 + 0.25 * wave : 1.0 + 0.08 * wave;
    item.mesh.scale.set(scale, scale, 1);
    if (item.mesh.material) {
      item.mesh.material.opacity = isActive ? 0.95 : item.baseOpacity;
    }
  }
}

export function disposeCitySelector() {
  if (cityGroup && parentGlobe) {
    parentGlobe.remove(cityGroup);
  }
  if (cityGroup) {
    cityGroup.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((m) => m.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  }
  cityGroup = null;
  cityPickables = [];
  haloMeshes = [];
}

export default {
  CITY_SHELL_RADIUS,
  initCitySelector,
  setCityMarkersVisibility,
  getCityMarkersVisibility,
  getInteractiveCityObjects,
  getActiveCityId,
  focusCity,
  updateCityMarkers,
  disposeCitySelector
};
