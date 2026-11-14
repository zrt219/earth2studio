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
  const isJapan = city.country === 'Japan';
  const isMexico = city.country === 'Mexico';
  const isRussia = city.country === 'Russia';
  const isSouthAfrica = city.country === 'South Africa' || city.country === 'Lesotho';
  const isSouthernItaly = ['it_mount_etna', 'it_campi_flegrei', 'it_aspromonte_sila', 'it_apulia_karst', 'it_catania_simeto', 'it_vesuvius'].includes(city.id);
  const isFinland = city.country === 'Finland' || city.id.startsWith('fi_');
  const isJapanFarmland = ['jp_yamakoshi_tanada', 'jp_hoshitoge_tanada', 'jp_obasute_tanada', 'jp_iya_valley_terrace', 'jp_kamikatsu_terrace', 'jp_shiroyone_senmaida'].includes(city.id);
  const isBrazil = city.country === 'Brazil' || city.id.startsWith('br_');
  const isVancouver = city.country === 'Canada' || city.id.startsWith('van_');

  let primaryColor = 0x38bdf8;
  let accentColor = 0x10b981;
  if (isSouthernItaly) {
    primaryColor = 0xff4757; // Volcanic Coral / Magma
    accentColor = 0xffa502; // Flare Orange
  } else if (isFinland) {
    primaryColor = 0x70d6ff; // Polar Ice / Glacial Cyan
    accentColor = 0x00f0ff; // Borealis Glow
  } else if (isJapanFarmland) {
    primaryColor = 0xe0a96d; // Terraced Amber / Harvest Gold
    accentColor = 0x80b918; // Bamboo Green
  } else if (isBrazil) {
    primaryColor = 0x06d6a0; // Amazonian Emerald / Rainforest Green
    accentColor = 0x00f5d4; // Tropical Turquoise
  } else if (isVancouver) {
    primaryColor = 0x00b4d8; // Pacific Marine Teal
    accentColor = 0x90e0ef; // Salish Sea Cyan
  } else if (isJapan) {
    primaryColor = 0xf43f5e; // Rose / Crimson
    accentColor = 0xfbbf24; // Amber / Gold
  } else if (isMexico) {
    primaryColor = 0xf59e0b; // Amber / Terracotta
    accentColor = 0x10b981; // Emerald / Jade
  } else if (isRussia) {
    primaryColor = 0x06b6d4; // Cyan / Arctic Blue
    accentColor = 0xa855f7; // Violet / Aurora
  } else if (isSouthAfrica) {
    primaryColor = 0x10b981; // Emerald / Savanna
    accentColor = 0xf59e0b; // Warm Gold
  }

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

export function addCityBeacon(city) {
  if (!parentGlobe || !cityGroup || !city) return null;
  const existing = cityGroup.getObjectByName(`city_beacon_${city.id}`);
  if (existing) return existing;
  const beacon = createCityBeacon(city);
  cityGroup.add(beacon);
  return beacon;
}

export function loadHiddenTerrainBeacons() {
  if (!parentGlobe || !cityGroup) return [];
  const allCities = studyData.getAllTargetCities ? studyData.getAllTargetCities() : (studyData.getHiddenTerrainTargetCities ? studyData.getHiddenTerrainTargetCities() : []);
  const added = [];
  allCities.forEach((city) => {
    if (!cityGroup.getObjectByName(`city_beacon_${city.id}`)) {
      const b = addCityBeacon(city);
      if (b) added.push(b);
    }
  });
  return added;
}

export function initCitySelector(globe, callbacks = {}) {
  disposeCitySelector();
  parentGlobe = globe || null;
  onVisibilityChangeCb = typeof callbacks.onVisibilityChange === 'function' ? callbacks.onVisibilityChange : null;

  if (parentGlobe) {
    cityGroup = new THREE.Group();
    cityGroup.name = 'city_target_markers_group';
    cityGroup.visible = markersVisible;

    const includeHidden = Boolean(callbacks.includeHiddenTerrain);
    const cities = includeHidden && studyData.getAllTargetCities
      ? studyData.getAllTargetCities()
      : studyData.getTargetCities();

    cities.forEach((city) => {
      const beacon = createCityBeacon(city);
      cityGroup.add(beacon);
    });
    parentGlobe.add(cityGroup);
  }

  if (typeof document !== 'undefined') {
    const selItaly = document.getElementById('city-select-italy');
    const selJapan = document.getElementById('city-select-japan');
    const selSouthAfrica = document.getElementById('city-select-south-africa');
    const selMexico = document.getElementById('city-select-mexico');
    const selRussia = document.getElementById('city-select-russia');
    const selSouthernItaly = document.getElementById('city-select-southern-italy');
    const selFinland = document.getElementById('city-select-finland');
    const selJapanFarmland = document.getElementById('city-select-japan-farmland');
    const selBrazil = document.getElementById('city-select-brazil');
    const selVancouver = document.getElementById('city-select-vancouver');
    const allSelects = [
      selItaly, selJapan, selSouthAfrica, selMexico, selRussia,
      selSouthernItaly, selFinland, selJapanFarmland, selBrazil, selVancouver
    ].filter(Boolean);

    const btnToggle = document.getElementById('layer-cities');
    const quickChips = document.querySelectorAll('.city-quick-chip');
    const searchInput = document.getElementById('city-search-input');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const q = (e.target.value || '').trim().toLowerCase();
        allSelects.forEach((sel) => {
          Array.from(sel.options).forEach((opt, idx) => {
            if (idx === 0) return;
            const match = !q || opt.text.toLowerCase().includes(q) || opt.value.toLowerCase().includes(q);
            opt.hidden = !match;
          });
        });
        quickChips.forEach((chip) => {
          const cid = chip.getAttribute('data-city-id') || '';
          const txt = (chip.textContent || '').toLowerCase();
          const match = !q || txt.includes(q) || cid.toLowerCase().includes(q);
          chip.style.display = match ? '' : 'none';
        });
      });

      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const q = (searchInput.value || '').trim().toLowerCase();
          if (!q) return;
          const allCities = studyData.getAllTargetCities ? studyData.getAllTargetCities() : (studyData.getTargetCities ? studyData.getTargetCities() : (studyData.TARGET_CITIES || []));
          const match = allCities.find((c) =>
            c.name.toLowerCase().includes(q) ||
            c.id.toLowerCase().includes(q) ||
            (c.country && c.country.toLowerCase().includes(q)) ||
            (c.region && c.region.toLowerCase().includes(q)) ||
            (c.district && c.district.toLowerCase().includes(q)) ||
            (c.radarTarget && c.radarTarget.toLowerCase().includes(q))
          );
          if (match) {
            focusCity(match.id, callbacks);
            searchInput.blur();
          }
        }
      });
    }

    allSelects.forEach((sel) => {
      sel.addEventListener('change', (e) => {
        if (e.target.value) {
          allSelects.forEach((other) => {
            if (other !== sel) other.value = '';
          });
          focusCity(e.target.value, callbacks);
        }
      });
    });

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

  if (cityGroup && !cityGroup.getObjectByName(`city_beacon_${city.id}`)) {
    addCityBeacon(city);
  }

  if (!markersVisible) {
    setCityMarkersVisibility(true);
  }

  callbacks.setSpinState?.(false);
  callbacks.flyToLatLon?.(city.lat, city.lon, city.zoomDistance || 5.95);

  if (typeof document !== 'undefined') {
    const selItaly = document.getElementById('city-select-italy');
    const selJapan = document.getElementById('city-select-japan');
    const selSouthAfrica = document.getElementById('city-select-south-africa');
    const selMexico = document.getElementById('city-select-mexico');
    const selRussia = document.getElementById('city-select-russia');
    const selSouthernItaly = document.getElementById('city-select-southern-italy');
    const selFinland = document.getElementById('city-select-finland');
    const selJapanFarmland = document.getElementById('city-select-japan-farmland');
    const selBrazil = document.getElementById('city-select-brazil');
    const selVancouver = document.getElementById('city-select-vancouver');

    const sItalyIds = ['it_mount_etna', 'it_campi_flegrei', 'it_aspromonte_sila', 'it_apulia_karst', 'it_catania_simeto', 'it_vesuvius'];
    const jpFarmIds = ['jp_yamakoshi_tanada', 'jp_hoshitoge_tanada', 'jp_obasute_tanada', 'jp_iya_valley_terrace', 'jp_kamikatsu_terrace', 'jp_shiroyone_senmaida'];

    let targetSelect = null;
    if (sItalyIds.includes(city.id)) {
      targetSelect = selSouthernItaly || selItaly;
    } else if (jpFarmIds.includes(city.id)) {
      targetSelect = selJapanFarmland || selJapan;
    } else if (city.country === 'Finland' || city.id.startsWith('fi_')) {
      targetSelect = selFinland;
    } else if (city.country === 'Brazil' || city.id.startsWith('br_')) {
      targetSelect = selBrazil;
    } else if (city.country === 'Canada' || city.id.startsWith('van_')) {
      targetSelect = selVancouver;
    } else if (city.country === 'Mexico' || city.id.startsWith('mx_')) {
      targetSelect = selMexico;
    } else if (city.country === 'Russia' || city.id.startsWith('ru_')) {
      targetSelect = selRussia;
    } else if (city.country === 'South Africa' || city.country === 'Lesotho' || city.id.startsWith('za_')) {
      targetSelect = selSouthAfrica;
    } else if (city.country === 'Japan' || city.id.startsWith('jp_')) {
      targetSelect = selJapan;
    } else if (city.country === 'Italy' || city.id.startsWith('it_')) {
      targetSelect = selItaly;
    }

    const allDropdowns = [
      selItaly, selJapan, selSouthAfrica, selMexico, selRussia,
      selSouthernItaly, selFinland, selJapanFarmland, selBrazil, selVancouver
    ].filter(Boolean);

    allDropdowns.forEach((sel) => {
      if (sel === targetSelect) {
        sel.value = city.id;
      } else {
        sel.value = '';
      }
    });

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
  addCityBeacon,
  loadHiddenTerrainBeacons,
  setCityMarkersVisibility,
  getCityMarkersVisibility,
  getInteractiveCityObjects,
  getActiveCityId,
  focusCity,
  updateCityMarkers,
  disposeCitySelector
};
