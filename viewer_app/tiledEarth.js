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
    triggerBounds: [36.0, 50.0, 4.0, 20.0],
    url: '/textures/tiles/sentinel2_italy_4k.jpg'
  },
  {
    id: 'japan_sentinel2_131k',
    name: 'Japan / Honshu Sentinel-2 (z=8, 131K Density)',
    bounds: [30.0, 42.0, 128.0, 145.0],
    triggerBounds: [28.0, 44.0, 126.0, 147.0],
    url: '/textures/tiles/sentinel2_japan_4k.jpg'
  }
]);

const S2_LIVE_URL =
  'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2021/default/WGS84/{z}/{row}/{col}.jpg';

const MAX_OCTANT_CACHE = 5;
const MAX_LIVE_CACHE = 48;
const OCTANT_RADIUS = TILED_SHELLS.TILED_16K_OCTANTS;

const OCTANT_SPECS = (() => {
  const specs = [];
  const degToRad = Math.PI / 180.0;
  const gridSteps = 6; // 7x7 surface points (15 deg spacing) for exact frustum + horizon testing
  for (let r = 0; r < 2; r++) {
    const maxLat = r === 0 ? 90.0 : 0.0;
    const minLat = r === 0 ? 0.0 : -90.0;
    for (let c = 0; c < 4; c++) {
      const minLon = -180.0 + c * 90.0;
      const maxLon = minLon + 90.0;
      const sampleCount = (gridSteps + 1) * (gridSteps + 1);
      const sampleLocalPts = new Float32Array(sampleCount * 3);
      const sampleDirs = new Float32Array(sampleCount * 3);
      let sIdx = 0;

      for (let i = 0; i <= gridSteps; i++) {
        const lat = minLat + (i / gridSteps) * (maxLat - minLat);
        const phi = lat * degToRad;
        const cosPhi = Math.cos(phi);
        const sinPhi = Math.sin(phi);
        for (let j = 0; j <= gridSteps; j++) {
          const lon = minLon + (j / gridSteps) * (maxLon - minLon);
          const lambda = ((((lon % 360.0) + 360.0) % 360.0) * degToRad);
          const dx = cosPhi * Math.cos(lambda);
          const dy = sinPhi;
          const dz = -cosPhi * Math.sin(lambda);
          sampleDirs[sIdx] = dx;
          sampleDirs[sIdx + 1] = dy;
          sampleDirs[sIdx + 2] = dz;
          sampleLocalPts[sIdx] = OCTANT_RADIUS * dx;
          sampleLocalPts[sIdx + 1] = OCTANT_RADIUS * dy;
          sampleLocalPts[sIdx + 2] = OCTANT_RADIUS * dz;
          sIdx += 3;
        }
      }

      const centerLat = (minLat + maxLat) * 0.5;
      const centerLon = (minLon + maxLon) * 0.5;
      const cPhi = centerLat * degToRad;
      const cLam = ((((centerLon % 360.0) + 360.0) % 360.0) * degToRad);
      const centerDir = new THREE.Vector3(
        Math.cos(cPhi) * Math.cos(cLam),
        Math.sin(cPhi),
        -Math.cos(cPhi) * Math.sin(cLam)
      ).normalize();

      specs.push({
        key: `octant_r${r}_c${c}`,
        r,
        c,
        minLat,
        maxLat,
        minLon,
        maxLon,
        url: `/textures/tiles/octant_r${r}_c${c}.jpg`,
        centerDir,
        sampleLocalPts,
        sampleDirs
      });
    }
  }
  return Object.freeze(specs);
})();

let activeGlobe = null;
let tiledRootGroup = null;
let octantGroup = null;
let liveGroup = null;
let regionGroup = null;

let isLodEnabled = true;
let isSatelliteMode = true;
let currentResolutionLabel = '16K Global Octants';
let lastStreamKey = '';
let lastCheckMs = 0;
let generationId = 0;

let sharedImageBitmapLoader = null;
let sharedTextureLoader = null;

const octantMeshes = [];
const regionMeshes = [];
const octantCache = new Map(); // key -> { mesh, key, lastUsed, loaded }
const octantInFlight = new Set();
const regionCache = new Map(); // id -> { mesh, loaded }
const regionInFlight = new Set();
const liveTileCache = new Map(); // key -> { mesh, lastUsed }
const inFlightKeys = new Set();

const _scratchGlobePos = new THREE.Vector3();
const _scratchCamPos = new THREE.Vector3();
const _scratchToCam = new THREE.Vector3();
const _scratchInvQuat = new THREE.Quaternion();
const _scratchLocalDir = new THREE.Vector3();
const _scratchPt = new THREE.Vector3();
const _projScreenMatrix = new THREE.Matrix4();
const _frustum = new THREE.Frustum();

function configureTileTexture(tex, maxAniso = 4) {
  if (!tex) return tex;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = THREE.ClampToEdgeWrapping;
  tex.wrapT = THREE.ClampToEdgeWrapping;
  tex.generateMipmaps = true;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.magFilter = THREE.LinearFilter;
  tex.anisotropy = Math.min(4, Math.max(1, Number.isFinite(maxAniso) ? maxAniso : 4));
  return tex;
}

function canUseImageBitmapLoader() {
  return (
    typeof createImageBitmap === 'function' &&
    typeof THREE.ImageBitmapLoader === 'function'
  );
}

function getSharedTileLoader() {
  if (canUseImageBitmapLoader()) {
    if (!sharedImageBitmapLoader) {
      sharedImageBitmapLoader = new THREE.ImageBitmapLoader();
      sharedImageBitmapLoader.setOptions?.({ imageOrientation: 'flipY' });
      sharedImageBitmapLoader.setCrossOrigin?.('anonymous');
    }
    return { loader: sharedImageBitmapLoader, isBitmap: true };
  }
  if (typeof THREE.TextureLoader === 'function') {
    if (!sharedTextureLoader) {
      sharedTextureLoader = new THREE.TextureLoader();
      sharedTextureLoader.setCrossOrigin?.('anonymous');
    }
    return { loader: sharedTextureLoader, isBitmap: false };
  }
  return null;
}

function canFetchTextures() {
  return (
    typeof window !== 'undefined' &&
    (canUseImageBitmapLoader() || typeof document?.createElementNS === 'function')
  );
}

function loadTileTexture(url, maxAniso, onReady, onError) {
  const loaderInfo = getSharedTileLoader();
  if (!loaderInfo) {
    onError?.(new Error('No Three.js texture loader available'));
    return;
  }

  if (loaderInfo.isBitmap) {
    loaderInfo.loader.load(
      url,
      imageBitmap => {
        const tex = new THREE.Texture(imageBitmap);
        tex.flipY = false;
        configureTileTexture(tex, maxAniso);
        tex.needsUpdate = true;
        onReady(tex);
      },
      undefined,
      err => onError?.(err)
    );
  } else {
    loaderInfo.loader.load(
      url,
      tex => {
        configureTileTexture(tex, maxAniso);
        onReady(tex);
      },
      undefined,
      err => onError?.(err)
    );
  }
}

function computeCameraLocalState(camera, globe) {
  if (!camera) {
    _scratchLocalDir.set(0, 0, 1);
    return { lat: 0, lon: 0, dist: 14.0, localCamDir: _scratchLocalDir };
  }

  if (globe && globe.position) {
    _scratchGlobePos.copy(globe.position);
  } else {
    _scratchGlobePos.set(0, 0, 0);
  }

  if (camera.position) {
    _scratchCamPos.copy(camera.position);
  } else {
    _scratchCamPos.set(0, 0, 14);
  }

  _scratchToCam.subVectors(_scratchCamPos, _scratchGlobePos);
  const dist = _scratchToCam.length() || 14.0;
  _scratchLocalDir.copy(_scratchToCam).divideScalar(dist);

  if (globe && globe.quaternion) {
    _scratchInvQuat.copy(globe.quaternion).invert();
    _scratchLocalDir.applyQuaternion(_scratchInvQuat);
  }

  const ny = Math.max(-1.0, Math.min(1.0, _scratchLocalDir.y));
  const lat = Math.asin(ny) * (180.0 / Math.PI);
  let lon = Math.atan2(-_scratchLocalDir.z, _scratchLocalDir.x) * (180.0 / Math.PI);
  lon = ((((lon + 180.0) % 360.0) + 360.0) % 360.0) - 180.0;
  return { lat, lon, dist, localCamDir: _scratchLocalDir };
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
  const { lat, lon, dist } = computeCameraLocalState(camera, globe);
  return { lat, lon, dist };
}

function evictOctantCacheIfNeeded() {
  while (octantCache.size > MAX_OCTANT_CACHE) {
    const oldest = octantCache.entries().next().value;
    if (!oldest) break;
    const [oldKey, oldEntry] = oldest;
    octantCache.delete(oldKey);
    if (octantGroup && oldEntry.mesh) {
      octantGroup.remove(oldEntry.mesh);
    }
    const meshIdx = octantMeshes.indexOf(oldEntry.mesh);
    if (meshIdx !== -1) octantMeshes.splice(meshIdx, 1);
    if (oldEntry.mesh?.geometry?.dispose) oldEntry.mesh.geometry.dispose();
    if (oldEntry.mesh?.material?.map?.dispose) oldEntry.mesh.material.map.dispose();
    if (oldEntry.mesh?.material?.dispose) oldEntry.mesh.material.dispose();
  }
}

function isOctantVisible(spec, lat, lon, globe, dist, localCamDir, hasFrustum) {
  if (lat >= spec.minLat && lat <= spec.maxLat && lon >= spec.minLon && lon <= spec.maxLon) {
    return true;
  }

  const cosAlpha = Math.min(1.0, OCTANT_RADIUS / Math.max(dist, OCTANT_RADIUS));
  const dirs = spec.sampleDirs;
  const pts = spec.sampleLocalPts;
  const lx = localCamDir.x;
  const ly = localCamDir.y;
  const lz = localCamDir.z;

  for (let i = 0; i < dirs.length; i += 3) {
    // Front-hemisphere horizon test: ptDir . localCamDir > R / dist
    const dot = dirs[i] * lx + dirs[i + 1] * ly + dirs[i + 2] * lz;
    if (dot <= cosAlpha) continue;

    if (!hasFrustum) return true;

    _scratchPt.set(pts[i], pts[i + 1], pts[i + 2]);
    if (globe && globe.matrixWorld) {
      _scratchPt.applyMatrix4(globe.matrixWorld);
    } else if (globe && globe.quaternion) {
      _scratchPt.applyQuaternion(globe.quaternion);
      if (globe.position) _scratchPt.add(globe.position);
    }
    if (_frustum.containsPoint(_scratchPt)) {
      return true;
    }
  }

  return false;
}

function loadVisibleOctants(lat, lon, camera, globe, dist, localCamDir, maxAniso) {
  if (!octantGroup || dist >= 12.2 || !canFetchTextures()) return;

  const hasFrustum = Boolean(
    camera &&
    camera.projectionMatrix &&
    camera.matrixWorldInverse &&
    typeof camera.updateMatrixWorld === 'function'
  );
  if (hasFrustum) {
    camera.updateMatrixWorld();
    globe?.updateMatrixWorld?.();
    _projScreenMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse);
    _frustum.setFromProjectionMatrix(_projScreenMatrix);
  }

  const now = Date.now();
  const cbGen = generationId;
  const visibleSpecs = [];

  for (let i = 0; i < OCTANT_SPECS.length; i++) {
    const spec = OCTANT_SPECS[i];
    if (isOctantVisible(spec, lat, lon, globe, dist, localCamDir, hasFrustum)) {
      visibleSpecs.push({
        spec,
        score: spec.centerDir.dot(localCamDir)
      });
    }
  }

  // Prioritize octants closest to camera boresight and cap at MAX_OCTANT_CACHE to prevent thrashing
  visibleSpecs.sort((a, b) => b.score - a.score);
  const targetCount = Math.min(visibleSpecs.length, MAX_OCTANT_CACHE);

  for (let i = 0; i < targetCount; i++) {
    const { spec } = visibleSpecs[i];
    const cached = octantCache.get(spec.key);
    if (cached) {
      // Refresh LRU position (delete + re-insert moves key to tail)
      octantCache.delete(spec.key);
      cached.lastUsed = now;
      octantCache.set(spec.key, cached);
      if (cached.mesh) cached.mesh.visible = true;
    }
  }

  for (let i = 0; i < targetCount; i++) {
    const { spec } = visibleSpecs[i];
    if (octantCache.has(spec.key) || octantInFlight.has(spec.key)) continue;

    octantInFlight.add(spec.key);
    loadTileTexture(
      spec.url,
      maxAniso,
      tex => {
        octantInFlight.delete(spec.key);
        if (cbGen !== generationId || !octantGroup || !isLodEnabled || !isSatelliteMode || !octantGroup.visible) {
          tex.dispose();
          return;
        }
        const geom = createSphericalPatchGeometry(
          spec.minLat,
          spec.maxLat,
          spec.minLon,
          spec.maxLon,
          OCTANT_RADIUS,
          48
        );
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
        mesh.name = spec.key;
        octantGroup.add(mesh);
        octantMeshes.push(mesh);
        octantCache.set(spec.key, { mesh, key: spec.key, lastUsed: Date.now(), loaded: true });
        evictOctantCacheIfNeeded();
      },
      () => {
        octantInFlight.delete(spec.key);
      }
    );
  }
}

function loadVisibleRegionalInsets(lat, lon, dist, maxAniso) {
  if (!regionGroup || dist >= 12.2 || !canFetchTextures()) return;
  const cbGen = generationId;

  for (let i = 0; i < REGIONAL_INSET_SPECS.length; i++) {
    const spec = REGIONAL_INSET_SPECS[i];
    const [tMinLat, tMaxLat, tMinLon, tMaxLon] = spec.triggerBounds;
    const isOverRegion = lat >= tMinLat && lat <= tMaxLat && lon >= tMinLon && lon <= tMaxLon;

    const cached = regionCache.get(spec.id);
    if (cached) {
      if (cached.mesh) cached.mesh.visible = isOverRegion;
      continue;
    }

    if (!isOverRegion || regionInFlight.has(spec.id)) continue;

    regionInFlight.add(spec.id);
    loadTileTexture(
      spec.url,
      maxAniso,
      tex => {
        regionInFlight.delete(spec.id);
        if (cbGen !== generationId || !regionGroup || !isLodEnabled || !isSatelliteMode) {
          tex.dispose();
          return;
        }
        const [minLat, maxLat, minLon, maxLon] = spec.bounds;
        const geom = createSphericalPatchGeometry(
          minLat,
          maxLat,
          minLon,
          maxLon,
          TILED_SHELLS.SENTINEL2_REGION_INSETS,
          48
        );
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
        regionCache.set(spec.id, { mesh, loaded: true });
      },
      () => {
        regionInFlight.delete(spec.id);
      }
    );
  }
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

function isLiveTileStale(zoom, row, col, cbGen) {
  if (cbGen !== generationId || !liveGroup || !isLodEnabled || !isSatelliteMode) return true;
  if (!lastStreamKey) return true;
  const parts = lastStreamKey.split(':');
  const curZoom = Number(parts[0]);
  const curRow = Number(parts[1]);
  const curCol = Number(parts[2]);
  if (curZoom !== zoom) return true;
  const nCols = 1 << (zoom + 1);
  const dRow = Math.abs(row - curRow);
  const rawDCol = Math.abs(col - curCol);
  const dCol = Math.min(rawDCol, nCols - rawDCol);
  return dRow > 2 || dCol > 2;
}

function streamLiveSentinel2Tiles(lat, lon, dist, maxAniso = 4) {
  if (!liveGroup || !canFetchTextures()) return;

  const zoom = dist < 7.2 ? 7 : 6; // z=6 (32K global density), z=7 (65K global density)
  const nCols = 1 << (zoom + 1);
  const nRows = 1 << zoom;
  const degPerTile = 360.0 / nCols;

  const centerCol = Math.max(0, Math.min(nCols - 1, Math.floor((lon + 180.0) / degPerTile)));
  const centerRow = Math.max(0, Math.min(nRows - 1, Math.floor((90.0 - lat) / degPerTile)));
  const streamKey = `${zoom}:${centerRow}:${centerCol}`;
  if (streamKey === lastStreamKey) return;
  lastStreamKey = streamKey;

  const cbGen = generationId;

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
      loadTileTexture(
        url,
        maxAniso,
        tex => {
          inFlightKeys.delete(key);
          if (isLiveTileStale(zoom, row, col, cbGen)) {
            tex.dispose();
            return;
          }
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
        () => {
          inFlightKeys.delete(key);
        }
      );
    }
  }
}

function updateResolutionBadge(label, force = false) {
  if (!force && label === currentResolutionLabel) return;
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
  octantGroup.visible = false;
  liveGroup = new THREE.Group();
  liveGroup.name = 'sentinel2_live_stream';
  liveGroup.visible = false;
  regionGroup = new THREE.Group();
  regionGroup.name = 'sentinel2_regional_131k';
  regionGroup.visible = false;

  tiledRootGroup.add(octantGroup);
  tiledRootGroup.add(liveGroup);
  tiledRootGroup.add(regionGroup);

  tiledRootGroup.visible = isLodEnabled && isSatelliteMode;
  if (activeGlobe && typeof activeGlobe.add === 'function') {
    activeGlobe.add(tiledRootGroup);
  }
  updateResolutionBadge(
    !isSatelliteMode ? '4K GFS Thermal' : isLodEnabled ? '16K Global Octants' : '8K NASA PBR',
    true
  );
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

  const { lat, lon, dist, localCamDir } = computeCameraLocalState(camera, globe);
  const showHighRes = dist < 12.2;
  if (octantGroup) octantGroup.visible = showHighRes;
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

  const maxAniso = Math.min(4, renderer?.capabilities?.getMaxAnisotropy?.() || 4);

  if (showHighRes) {
    loadVisibleOctants(lat, lon, camera, globe, dist, localCamDir, maxAniso);
    loadVisibleRegionalInsets(lat, lon, dist, maxAniso);
  }

  if (dist < 9.8 && !(showHighRes && (inItaly || inJapan))) {
    streamLiveSentinel2Tiles(lat, lon, dist, maxAniso);
  }
}

export function hasActiveOctantCoverage() {
  if (!tiledRootGroup || !isLodEnabled || !isSatelliteMode || !octantGroup || !octantGroup.visible) {
    return false;
  }
  for (const entry of octantCache.values()) {
    if (entry.loaded && entry.mesh && entry.mesh.visible !== false && entry.mesh.material?.map?.image) {
      return true;
    }
  }
  return false;
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
  generationId++;
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
  octantCache.clear();
  octantInFlight.clear();
  regionCache.clear();
  regionInFlight.clear();
  liveTileCache.clear();
  inFlightKeys.clear();
  lastStreamKey = '';
  lastCheckMs = 0;
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
  hasActiveOctantCoverage,
  disposeTiledEarth
};
