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
 * Main Application Orchestrator & Scene Coordinator
 *
 * Module: viewer_app/main.js
 * Author: Zhane Daye (Origin Datum — Independent Research Initiative)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Coordinates:
 *   - Three.js Scene, Camera, WebGLRenderer, Lighting, Atmosphere & Starfield
 *   - Radial Shell Hierarchy (Base Globe R=5.000)
 *   - 3D Scientific Layers Engine (layers3D.js)
 *   - UI Controller & Glassmorphic HUD (uiController.js)
 *   - Central Scientific Data Store & Event Bus (studyData.js)
 *   - Interactive Raycasting, Drag-vs-Click POI Inspection
 *   - Boresight Navigation & Synoptic Regional Camera Transitions
 */

import * as THREE from 'three';
import studyData from './studyData.js';
import layers3D from './layers3D.js';
import uiController from './uiController.js';

// =============================================================================
// 1. APPLICATION STATE & CONTEXT
// =============================================================================

let scene = null;
let camera = null;
let renderer = null;
let globe = null;
let atmosMesh = null;
let starField = null;

let isSpinning = true;
let isReliefActive = true;
let bumpScaleValue = 0.18;
let currentTextureName = 'earth_t2m.jpg';

// Pointer interaction tracking
let isDragging = false;
let pointerDownPos = { x: 0, y: 0 };
let previousPointerPos = { x: 0, y: 0 };

// Smooth Camera Navigation targets
let isFlying = false;
let targetCameraPos = null;
let targetGlobeRot = null;

// Clock for time-based animation updates
const clock = new THREE.Clock();

// Texture Assets
const textureLoader = new THREE.TextureLoader();
const t2mTex = textureLoader.load('/textures/earth_t2m.jpg');
const tendTex = textureLoader.load('/textures/earth_tendency.jpg');
const bumpTex = textureLoader.load('/textures/earth_elevation.jpg');

// Ensure textures wrap and filter cleanly
[t2mTex, tendTex, bumpTex].forEach(tex => {
  if (tex) {
    tex.wrapS = THREE.ClampToEdgeWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.minFilter = THREE.LinearFilter;
    tex.generateMipmaps = false;
  }
});

// =============================================================================
// 2. SCENE INITIALIZATION
// =============================================================================

export function init() {
  const container = document.getElementById('canvas-container');
  if (!container) return;

  // 1. Create Scene
  scene = new THREE.Scene();

  // 2. Perspective Camera (FOV 45, Near 0.1, Far 1000)
  const width = window.innerWidth || 1920;
  const height = window.innerHeight || 1080;
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, 5, 14);

  // 3. WebGL Renderer
  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance'
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  container.innerHTML = '';
  container.appendChild(renderer.domElement);

  // 4. Illumination
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
  scene.add(ambientLight);

  const sunLight = new THREE.DirectionalLight(0xffffff, 1.25);
  sunLight.position.set(12, 10, 15);
  scene.add(sunLight);

  // 5. Procedural Starfield Background
  createStarfield();

  // 6. Base Earth Sphere Mesh (R = 5.000)
  const geometry = new THREE.SphereGeometry(layers3D.RADIAL_SHELLS.BASE_GLOBE, 128, 128);
  const material = new THREE.MeshStandardMaterial({
    map: t2mTex,
    bumpMap: bumpTex,
    bumpScale: bumpScaleValue,
    roughness: 0.55,
    metalness: 0.1
  });
  globe = new THREE.Mesh(geometry, material);
  scene.add(globe);

  // 7. Atmospheric Glow Shell (R = 5.150)
  const atmosGeom = new THREE.SphereGeometry(layers3D.RADIAL_SHELLS.ATMOSPHERE_GLOW, 64, 64);
  const atmosMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.14,
    side: THREE.BackSide
  });
  atmosMesh = new THREE.Mesh(atmosGeom, atmosMat);
  scene.add(atmosMesh);

  // 8. Initialize 3D Scientific Layers Engine
  layers3D.initLayers(globe, camera, renderer);

  // 9. Initialize UI Controller & Glassmorphic HUD
  uiController.initUI(globe, camera, renderer, layers3D);

  // 10. Wire DOM Event Listeners
  window.addEventListener('resize', onWindowResize);
  setupPointerEvents(renderer.domElement);
  setupNavigationButtons();
  setupAtmosphereLayerButtons();

  // 11. Connect studyData events
  studyData.on('domain-focused', ({ domainInfo }) => {
    if (domainInfo) {
      flyToLatLon(domainInfo.lat, domainInfo.lon, domainInfo.distance || 8.5);
    }
  });

  studyData.on('study-version-changed', ({ versionId }) => {
    if (versionId === 'V1') {
      // V1 defaults to global synoptic perspective
      flyTo(0, 0, 14);
    }
  });

  // Start Animation Loop
  animate();
}

/**
 * Creates 1,200 particle celestial starfield background
 */
function createStarfield() {
  const starCount = 1200;
  const positions = new Float32Array(starCount * 3);

  for (let i = 0; i < starCount * 3; i += 3) {
    positions[i] = (Math.random() - 0.5) * 350;
    positions[i + 1] = (Math.random() - 0.5) * 350;
    positions[i + 2] = (Math.random() - 0.5) * 350;
  }

  const starGeom = new THREE.BufferGeometry();
  starGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const starMat = new THREE.PointsMaterial({
    color: 0x94a3b8,
    size: 0.8,
    transparent: true,
    opacity: 0.75
  });
  starField = new THREE.Points(starGeom, starMat);
  scene.add(starField);
}

// =============================================================================
// 3. POINTER EVENTS & INTERACTIVE RAYCASTING
// =============================================================================

function setupPointerEvents(canvas) {
  canvas.addEventListener('pointerdown', (e) => {
    isDragging = true;
    pointerDownPos = { x: e.clientX, y: e.clientY };
    previousPointerPos = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener('pointermove', (e) => {
    if (!isDragging || !globe) return;

    const deltaX = e.clientX - previousPointerPos.x;
    const deltaY = e.clientY - previousPointerPos.y;

    globe.rotation.y += deltaX * 0.005;
    globe.rotation.x += deltaY * 0.005;

    // Interrupt active fly-to if user manually drags
    isFlying = false;

    previousPointerPos = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener('pointerup', (e) => {
    if (!isDragging) return;
    isDragging = false;

    const deltaDist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);

    // Click threshold (<=5px): execute raycast POI selection
    if (deltaDist <= 5) {
      const hit = layers3D.handleRaycast(e, camera, window.innerWidth, window.innerHeight);
      if (hit && hit.data) {
        uiController.showPopup(hit.data, hit.screenPos);
        isSpinning = false;
        uiController.setSpinState(false);
      } else {
        // Clicked empty space or base globe: dismiss active popup
        uiController.hidePopup();
      }
    } else {
      // Drag action completed: dismiss popup
      uiController.hidePopup();
    }
  });

  // Zoom clamp [7.0, 22.0]
  window.addEventListener('wheel', (e) => {
    if (!camera) return;
    const nextZ = camera.position.z + e.deltaY * 0.01;
    camera.position.z = Math.max(7.0, Math.min(22.0, nextZ));
  }, { passive: true });
}

// =============================================================================
// 4. ATMOSPHERIC TEXTURE & TOPOGRAPHIC RELIEF CONTROLS
// =============================================================================

function setupAtmosphereLayerButtons() {
  const btnT2m = document.getElementById('layer-t2m');
  const btnTend = document.getElementById('layer-tend');
  const btnRelief = document.getElementById('toggle-relief');
  const btnSpin = document.getElementById('toggle-spin');

  if (btnT2m) {
    btnT2m.addEventListener('click', () => {
      currentTextureName = 'earth_t2m.jpg';
      if (globe && globe.material) {
        globe.material.map = t2mTex;
        // Preserve bumpScale across texture swaps per T3.5
        globe.material.bumpScale = isReliefActive ? bumpScaleValue : 0.0;
        globe.material.needsUpdate = true;
      }
    });
  }

  if (btnTend) {
    btnTend.addEventListener('click', () => {
      currentTextureName = 'earth_tendency.jpg';
      if (globe && globe.material) {
        globe.material.map = tendTex;
        // Preserve bumpScale across texture swaps per T3.5
        globe.material.bumpScale = isReliefActive ? bumpScaleValue : 0.0;
        globe.material.needsUpdate = true;
      }
    });
  }

  if (btnRelief) {
    btnRelief.addEventListener('click', () => {
      isReliefActive = !isReliefActive;
      if (globe && globe.material) {
        globe.material.bumpScale = isReliefActive ? bumpScaleValue : 0.0;
        globe.material.needsUpdate = true;
      }
    });
  }

  if (btnSpin) {
    btnSpin.addEventListener('click', () => {
      isSpinning = !isSpinning;
      uiController.setSpinState(isSpinning);
    });
  }
}

// =============================================================================
// 5. CAMERA NAVIGATION & BORESIGHT ROTATION
// =============================================================================

export function flyToLatLon(lat, lon, distance = 8.5) {
  const { rotX, rotY } = layers3D.boresightRotation(lat, lon);
  targetGlobeRot = { x: rotX, y: rotY };
  targetCameraPos = { x: 0, y: 1.5, z: distance };
  isFlying = true;
}

export function flyTo(x, y, z) {
  targetCameraPos = { x, y, z };
  targetGlobeRot = { x: 0, y: targetGlobeRot ? targetGlobeRot.y : (globe ? globe.rotation.y : 0) };
  isFlying = true;
}

function setupNavigationButtons() {
  const btnGlobal = document.getElementById('fly-global');
  const btnItaly = document.getElementById('fly-italy');
  const btnJapan = document.getElementById('fly-japan');

  if (btnGlobal) {
    btnGlobal.addEventListener('click', () => {
      flyTo(0, 0, 14);
    });
  }

  if (btnItaly) {
    btnItaly.addEventListener('click', () => {
      isSpinning = false;
      uiController.setSpinState(false);
      // Italy synoptic domain (42°N, 12°E)
      flyToLatLon(42.0, 12.0, 8.5);
    });
  }

  if (btnJapan) {
    btnJapan.addEventListener('click', () => {
      isSpinning = false;
      uiController.setSpinState(false);
      // Japan synoptic domain (36°N, 138°E)
      flyToLatLon(36.0, 138.0, 8.5);
    });
  }
}

// =============================================================================
// 6. ANIMATION & RENDER LOOP
// =============================================================================

function onWindowResize() {
  if (!camera || !renderer) return;
  const w = window.innerWidth;
  const h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
}

function animate() {
  requestAnimationFrame(animate);

  const delta = clock.getDelta();
  const elapsedTime = clock.getElapsedTime();

  // 1. Smooth Camera & Globe Navigation Interpolation
  if (isFlying && targetCameraPos && targetGlobeRot && globe && camera) {
    // Lerp camera position
    camera.position.x += (targetCameraPos.x - camera.position.x) * 0.08;
    camera.position.y += (targetCameraPos.y - camera.position.y) * 0.08;
    camera.position.z += (targetCameraPos.z - camera.position.z) * 0.08;

    // Lerp globe rotation
    globe.rotation.x += (targetGlobeRot.x - globe.rotation.x) * 0.08;
    globe.rotation.y += (targetGlobeRot.y - globe.rotation.y) * 0.08;

    const distCam = Math.hypot(
      targetCameraPos.x - camera.position.x,
      targetCameraPos.y - camera.position.y,
      targetCameraPos.z - camera.position.z
    );
    const distRot = Math.hypot(
      targetGlobeRot.x - globe.rotation.x,
      targetGlobeRot.y - globe.rotation.y
    );

    if (distCam < 0.02 && distRot < 0.01) {
      camera.position.set(targetCameraPos.x, targetCameraPos.y, targetCameraPos.z);
      globe.rotation.set(targetGlobeRot.x, targetGlobeRot.y, 0);
      isFlying = false;
    }
  }

  // 2. Earth Constant Auto-Rotation (F13.3)
  if (isSpinning && globe && !isDragging && !isFlying) {
    globe.rotation.y += 0.0018;
  }

  // 3. Update 3D Scientific Layers (Pulsing Beacons, Plasma Shaders)
  layers3D.updateLayers(elapsedTime, camera);

  // 4. Render Scene
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

// =============================================================================
// 7. AUTO-INITIALIZATION ON PAGE LOAD
// =============================================================================

if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}

export default {
  init,
  flyToLatLon,
  flyTo
};
