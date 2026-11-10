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
 * Multi-Resolution 16K Global Octant & 65K–131K Sentinel-2 Spherical Tile Streaming Engine
 *
 * Module: viewer_app/tiledEarth.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Implements:
 *   - Tier 1 (R = 5.002): 8 x 4096x4096 Pre-Baked 16K (16384x8192) Global Spherical Octants
 *   - Tier 2 (R = 5.005): 131K-Density Regional Sentinel-2 Insets (Italy/Po Valley & Japan/Honshu)
 *   - Tier 3 (R = 5.003): Live Zoom-Adaptive WGS84 EOX Sentinel-2 Tile Streaming (z=6 32K, z=7 65K)
 */

import * as THREE from 'three';
import { createSphericalPatchGeometry } from './layers3D.js';

export const TILED_SHELLS = Object.freeze({
  TILED_16K_OCTANTS: 5.002,
  SENTINEL2_LIVE_TILES: 5.003,
  SENTINEL2_REGION_INSETS: 5.005
});

const REGIONAL_INSET_SPECS = Object.freeze([
  {
    id: 'italy_sentinel2_131k',
    name: 'Italy / Alps / Po Valley Sentinel-2 (z=8, 131K Density)',
    bounds: [38.0, 48.0, 6.0, 18.0],
    url: '/textures/tiles/sentinel2_italy_4k.jpg'
  },
  {
    id: 'japan_sentinel2_131k',
    name: 'Japan / Honshu Sentinel-2 (z=8, 131K Density)',
    bounds: [30.0, 42.0, 128.0, 145.0],
    url: '/textures/tiles/sentinel2_japan_4k.jpg'
  }
]);

const S2_LIVE_URL =
  'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021/default/WGS84/{z}/{row}/{col}.jpg';

const MAX_LIVE_CACHE = 48;

let activeGlobe = null;
let tiledRootGroup = null;
let octantGroup = null;
let liveGroup = null;
let regionGroup = null;

let isLodEnabled = true;
let isSatelliteMode = true;
let octantsLoaded = false;
let regionsLoaded = false;
let currentResolutionLabel = '16K Global Octants';
let lastStreamKey = '';
let lastCheckMs = 0;

const octantMeshes = [];
const regionMeshes = [];
const liveTileCache = new Map(); // key -> { mesh, lastUsed }
const inFlightKeys = new Set();

function configureTileTexture(tex, maxAniso = 8) {
  if (!tex) return tex;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.anisotropy = maxAniso;
  return tex;
}

/**
 * Convert camera position relative to rotated globe back into geographic (lat, lon) boresight.
 * Exact inverse of layers3D.latLonToVector3().
 *
 * @param {THREE.Camera} camera
 * @param {THREE.Object3D} globe
 * @returns {{ lat: number, lon: number, dist: number }}
 */
export function getCameraBoresightLatLon(camera, globe) {
  if (!camera) return { lat: 0, lon: 0, dist: 14.0 };
  const globePos = (globe && globe.position) ? globe.position : new THREE.Vector3(0, 0, 0);
  const camPos = camera.position ? camera.position.clone() : new THREE.Vector3(0, 0, 14);
  const toCam = camPos.clone().sub(globePos);
  const dist = toCam.length() || 14.0;
  const localDir = toCam.normalize();

  if (globe && globe.quaternion) {
    const invQuat = globe.quaternion.clone().invert();
    localDir.applyQuaternion(invQuat);
  }

  const ny = Math.max(-1.0, Math.min(1.0, localDir.y));
  const lat = Math.asin(ny) * (180.0 / Math.PI);
  let lon = Math.atan2(-localDir.z, localDir.x) * (180.0 / Math.PI);
  lon = ((((lon + 180.0) % 360.0) + 360.0) % 360.0) - 180.0;
  return { lat, lon, dist };
}

function loadOctantsIfNeeded(maxAniso = 8) {
  if (octantsLoaded || !octantGroup || typeof THREE.TextureLoader !== 'function') return;
  octantsLoaded = true;
  const loader = new THREE.TextureLoader();

  for (let r = 0; r < 2; r++) {
    const maxLat = r === 0 ? 90.0 : 0.0;
    const minLat = r === 0 ? 0.0 : -90.0;
    for (let c = 0; c < 4; c++) {
      const minLon = -180.0 + c * 90.0;
      const maxLon = minLon + 90.0;
      const geom = createSphericalPatchGeometry(
        minLat,
        maxLat,
        minLon,
        maxLon,
        TILED_SHELLS.TILED_16K_OCTANTS,
        48
      );
      const url = `/textures/tiles/octant_r${r}_c${c}.jpg`;
      const tex = configureTileTexture(loader.load(url), maxAniso);
      const mat = new THREE.MeshStandardMaterial({
        map: tex,
        roughness: 0.78,
        metalness: 0.05,
        transparent: false,
        opacity: 1.0,
        depthWrite: true,
        polygonOffset: true,
        polygonOffsetFactor: -0.5,
        polygonOffsetUnits: -0.5
      });
      const mesh = new THREE.Mesh(geom, mat);
      mesh.name = `octant_r${r}_c${c}`;
      octantGroup.add(mesh);
      octantMeshes.push(mesh);
    }
  }
}

function loadRegionalInsetsIfNeeded(maxAniso = 8) {
  if (regionsLoaded || !regionGroup || typeof THREE.TextureLoader !== 'function') return;
  regionsLoaded = true;
  const loader = new THREE.TextureLoader();

  REGIONAL_INSET_SPECS.forEach(spec => {
    const [minLat, maxLat, minLon, maxLon] = spec.bounds;
    const geom = createSphericalPatchGeometry(
      minLat,
      maxLat,
      minLon,
      maxLon,
      TILED_SHELLS.SENTINEL2_REGION_INSETS,
      48
    );
    const tex = configureTileTexture(loader.load(spec.url), maxAniso);
    const mat = new THREE.MeshStandardMaterial({
      map: tex,
      roughness: 0.85,
      metalness: 0.04,
      transparent: true,
      opacity: 0.96,
      depthWrite: false,
      polygonOffset: true,
      polygonOffsetFactor: -1.0,
      polygonOffsetUnits: -1.0
    });
    const mesh = new THREE.Mesh(geom, mat);
    mesh.name = spec.id;
    mesh.userData = { bounds: spec.bounds };
    regionGroup.add(mesh);
    regionMeshes.push(mesh);
  });
}

function evictOldestLiveTiles() {
  if (liveTileCache.size <= MAX_LIVE_CACHE) return;
  const entries = Array.from(liveTileCache.entries()).sort(
    (a, b) => a[1].lastUsed - b[1].lastUsed
  );
  const toRemove = entries.length - MAX_LIVE_CACHE;
  for (let i = 0; i < toRemove; i++) {
    const [key, entry] = entries[i];
    if (liveGroup && entry.mesh) {
      liveGroup.remove(entry.mesh);
    }
    if (entry.mesh?.geometry) entry.mesh.geometry.dispose();
    if (entry.mesh?.material?.map) entry.mesh.material.map.dispose();
    if (entry.mesh?.material) entry.mesh.material.dispose();
    liveTileCache.delete(key);
  }
}

function streamLiveSentinel2Tiles(lat, lon, dist, maxAniso = 8) {
  if (!liveGroup || typeof THREE.TextureLoader !== 'function') return;
  if (typeof window === 'undefined') return; // skip network fetches in pure Node tests

  const zoom = dist < 7.2 ? 7 : 6; // z=6 (32K global density), z=7 (65K global density)
  const nCols = 1 << (zoom + 1);
  const nRows = 1 << zoom;
  const degPerTile = 360.0 / nCols;

  const centerCol = Math.max(0, Math.min(nCols - 1, Math.floor((lon + 180.0) / degPerTile)));
  const centerRow = Math.max(0, Math.min(nRows - 1, Math.floor((90.0 - lat) / degPerTile)));
  const streamKey = `${zoom}:${centerRow}:${centerCol}`;
  if (streamKey === lastStreamKey) return;
  lastStreamKey = streamKey;

  const loader = new THREE.TextureLoader();
  loader.setCrossOrigin?.('anonymous');

  for (let dr = -1; dr <= 1; dr++) {
    const row = centerRow + dr;
    if (row < 0 || row >= nRows) continue;
    const maxLat = 90.0 - row * degPerTile;
    const minLat = 90.0 - (row + 1) * degPerTile;

    for (let dc = -1; dc <= 1; dc++) {
      const col = ((centerCol + dc) % nCols + nCols) % nCols;
      const key = `${zoom}/${row}/${col}`;

      if (liveTileCache.has(key)) {
        liveTileCache.get(key).lastUsed = Date.now();
        continue;
      }
      if (inFlightKeys.has(key)) continue;

      const minLon = -180.0 + col * degPerTile;
      const maxLon = minLon + degPerTile;
      const url = S2_LIVE_URL.replace('{z}', zoom).replace('{row}', row).replace('{col}', col);

      inFlightKeys.add(key);
      loader.load(
        url,
        tex => {
          inFlightKeys.delete(key);
          if (!liveGroup) {
            tex.dispose();
            return;
          }
          configureTileTexture(tex, maxAniso);
          const geom = createSphericalPatchGeometry(
            minLat,
            maxLat,
            minLon,
            maxLon,
            TILED_SHELLS.SENTINEL2_LIVE_TILES,
            16
          );
          const mat = new THREE.MeshStandardMaterial({
            map: tex,
            roughness: 0.85,
            metalness: 0.04,
            transparent: true,
            opacity: 0.96,
            depthWrite: false
          });
          const mesh = new THREE.Mesh(geom, mat);
          mesh.name = `s2_live_${zoom}_${row}_${col}`;
          liveGroup.add(mesh);
          liveTileCache.set(key, { mesh, lastUsed: Date.now() });
          evictOldestLiveTiles();
        },
        undefined,
        () => {
          inFlightKeys.delete(key);
        }
      );
    }
  }
}

function updateResolutionBadge(label) {
  currentResolutionLabel = label;
  if (typeof document === 'undefined') return;
  const el = document.getElementById('lod-res-badge');
  if (el) el.innerText = label;
}

export function initTiledEarth(globeMesh, renderer = null) {
  disposeTiledEarth();
  activeGlobe = globeMesh;

  tiledRootGroup = new THREE.Group();
  tiledRootGroup.name = 'tiled_earth_lod_root';

  octantGroup = new THREE.Group();
  octantGroup.name = 'tiled_16k_octants';
  liveGroup = new THREE.Group();
  liveGroup.name = 'sentinel2_live_stream';
  regionGroup = new THREE.Group();
  regionGroup.name = 'sentinel2_regional_131k';

  tiledRootGroup.add(octantGroup);
  tiledRootGroup.add(liveGroup);
  tiledRootGroup.add(regionGroup);

  const maxAniso = Math.min(8, renderer?.capabilities?.getMaxAnisotropy?.() || 4);
  if (typeof window !== 'undefined' && typeof document?.createElementNS === 'function') {
    loadOctantsIfNeeded(maxAniso);
    loadRegionalInsetsIfNeeded(maxAniso);
  }

  tiledRootGroup.visible = isLodEnabled && isSatelliteMode;
  if (activeGlobe && typeof activeGlobe.add === 'function') {
    activeGlobe.add(tiledRootGroup);
  }
  updateResolutionBadge(isLodEnabled ? '16K Global Octants' : '8K NASA PBR');
  return tiledRootGroup;
}

export function updateTiledEarth(camera, globe, renderer = null) {
  if (!tiledRootGroup) return;
  const show = isLodEnabled && isSatelliteMode;
  tiledRootGroup.visible = show;
  if (!show) {
    updateResolutionBadge(isSatelliteMode ? '8K NASA PBR' : '4K GFS Thermal');
    return;
  }

  const now = Date.now();
  if (now - lastCheckMs < 180) return;
  lastCheckMs = now;

  const { lat, lon, dist } = getCameraBoresightLatLon(camera, globe);
  const showHighRes = dist < 12.2;
  if (regionGroup) regionGroup.visible = showHighRes;
  if (liveGroup) liveGroup.visible = dist < 9.8;

  const inItaly = lat >= 36 && lat <= 50 && lon >= 4 && lon <= 20;
  const inJapan = lat >= 28 && lat <= 44 && lon >= 126 && lon <= 147;

  if (showHighRes && (inItaly || inJapan)) {
    updateResolutionBadge('131K Sentinel-2 Regional');
  } else if (dist < 7.2) {
    updateResolutionBadge('65K Sentinel-2 Live');
  } else if (dist < 9.8) {
    updateResolutionBadge('32K Sentinel-2 Live');
  } else {
    updateResolutionBadge('16K Global Octants');
  }

  if (dist < 9.8 && !(showHighRes && (inItaly || inJapan))) {
    const maxAniso = Math.min(8, renderer?.capabilities?.getMaxAnisotropy?.() || 4);
    streamLiveSentinel2Tiles(lat, lon, dist, maxAniso);
  }
}

export function setTiledEarthEnabled(enabled) {
  isLodEnabled = Boolean(enabled);
  if (tiledRootGroup) {
    tiledRootGroup.visible = isLodEnabled && isSatelliteMode;
  }
  updateResolutionBadge(
    !isSatelliteMode ? '4K GFS Thermal' : isLodEnabled ? '16K Global Octants' : '8K NASA PBR'
  );
  return isLodEnabled;
}

export function isTiledEarthEnabled() {
  return isLodEnabled;
}

export function setSatelliteModeActive(active) {
  isSatelliteMode = Boolean(active);
  if (tiledRootGroup) {
    tiledRootGroup.visible = isLodEnabled && isSatelliteMode;
  }
  updateResolutionBadge(
    !isSatelliteMode ? '4K GFS Thermal' : isLodEnabled ? '16K Global Octants' : '8K NASA PBR'
  );
}

export function getActiveResolutionLabel() {
  return currentResolutionLabel;
}

export function disposeTiledEarth() {
  if (tiledRootGroup && activeGlobe && typeof activeGlobe.remove === 'function') {
    activeGlobe.remove(tiledRootGroup);
  }
  if (tiledRootGroup && typeof tiledRootGroup.traverse === 'function') {
    tiledRootGroup.traverse(child => {
      if (child.geometry?.dispose) child.geometry.dispose();
      if (child.material) {
        if (child.material.map?.dispose) child.material.map.dispose();
        if (child.material.dispose) child.material.dispose();
      }
    });
  }
  octantMeshes.length = 0;
  regionMeshes.length = 0;
  liveTileCache.clear();
  inFlightKeys.clear();
  octantsLoaded = false;
  regionsLoaded = false;
  lastStreamKey = '';
  tiledRootGroup = null;
  octantGroup = null;
  liveGroup = null;
  regionGroup = null;
  activeGlobe = null;
}

export default {
  TILED_SHELLS,
  initTiledEarth,
  updateTiledEarth,
  setTiledEarthEnabled,
  isTiledEarthEnabled,
  setSatelliteModeActive,
  getCameraBoresightLatLon,
  getActiveResolutionLabel,
  disposeTiledEarth
};
