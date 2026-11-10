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
 * Main Application Orchestrator & Scene Coordinator
 *
 * Module: viewer_app/main.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
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
import windParticles from './windParticles.js';
import hazardAlerts from './hazardAlerts.js';
import sarTasking from './sarTasking.js';
import tutorialTour from './tutorialTour.js';
import tiledEarth from './tiledEarth.js';

// =============================================================================
// 1. APPLICATION STATE & CONTEXT
// =============================================================================

let scene = null;
let camera = null;
let renderer = null;
let globe = null;
let cloudMesh = null;
let atmosMesh = null;
let starField = null;

let isSpinning = true;
let isReliefActive = true;
let isCloudsVisible = true;
let bumpScaleValue = 0.12;
let normalScaleValue = 1.35;
let currentTextureName = 'earth_satellite_8k.jpg';

// Pointer interaction tracking
let isDragging = false;
let dragMode = 'rotate'; // 'rotate' | 'pan'
let pointerButton = 0;
let pointerDownPos = { x: 0, y: 0 };
let previousPointerPos = { x: 0, y: 0 };

// Camera target & Smooth Navigation targets
let cameraTarget = new THREE.Vector3(0, 0, 0);
let targetCameraTarget = null;
let isFlying = false;
let targetCameraPos = null;
let targetGlobeRot = null;

// Clock for time-based animation updates
const clock = new THREE.Clock();

// Texture Assets (8K/4K [-180, +180] Geospatially Aligned Multi-Map PBR)
const textureLoader = new THREE.TextureLoader();
const satTex = textureLoader.load('/textures/earth_satellite_8k.jpg');
const normalTex = textureLoader.load('/textures/earth_normal_4k.jpg');
const cityTex = textureLoader.load('/textures/earth_citylights_4k.jpg');
const cloudTex = textureLoader.load('/textures/earth_clouds_4k.jpg');
const t2mTex = textureLoader.load('/textures/earth_t2m.jpg');
const tendTex = textureLoader.load('/textures/earth_tendency.jpg');
const bumpTex = textureLoader.load('/textures/earth_elevation.jpg');
const roughTex = textureLoader.load('/textures/earth_roughness.jpg');

// Ensure textures wrap, generate mipmaps, and use proper color spaces
[satTex, t2mTex, tendTex, cityTex].forEach(tex => {
  if (tex) {
    tex.colorSpace = THREE.SRGBColorSpace;
  }
});

[satTex, normalTex, cityTex, cloudTex, t2mTex, tendTex, bumpTex, roughTex].forEach(tex => {
  if (tex) {
    tex.wrapS = THREE.RepeatWrapping;
    tex.wrapT = THREE.ClampToEdgeWrapping;
    tex.generateMipmaps = true;
    tex.minFilter = THREE.LinearMipmapLinearFilter;
    tex.magFilter = THREE.LinearFilter;
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
  camera.position.set(0, 0, 14);
  cameraTarget = new THREE.Vector3(0, 0, 0);
  camera.lookAt(cameraTarget);

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

  const maxAniso = Math.min(8, renderer.capabilities?.getMaxAnisotropy?.() || 4);
  [satTex, normalTex, cityTex, cloudTex, t2mTex, tendTex, bumpTex, roughTex].forEach(tex => {
    if (tex) tex.anisotropy = maxAniso;
  });

  // 4. Illumination
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.92);
  scene.add(ambientLight);

  const sunLight = new THREE.DirectionalLight(0xffffff, 1.35);
  sunLight.position.set(12, 10, 15);
  scene.add(sunLight);

  // 5. Procedural Starfield Background
  createStarfield();

  // 6. Base Earth Sphere Mesh (R = 5.000, 256x128 high-density mesh + multi-map PBR)
  const geometry = new THREE.SphereGeometry(layers3D.RADIAL_SHELLS.BASE_GLOBE, 256, 128);
  const material = new THREE.MeshStandardMaterial({
    map: satTex,
    normalMap: normalTex,
    normalScale: new THREE.Vector2(normalScaleValue, normalScaleValue),
    bumpMap: bumpTex,
    bumpScale: bumpScaleValue,
    roughnessMap: roughTex,
    roughness: 0.90,
    metalness: 0.08,
    emissiveMap: cityTex,
    emissive: new THREE.Color(0xffb84d),
    emissiveIntensity: 0.55
  });
  globe = new THREE.Mesh(geometry, material);
  scene.add(globe);

  // 6b. 3D Optical Cloud Cover Shell (R = 5.012, safely below Spread 5.020 & SAR Swath 5.040)
  const cloudGeom = new THREE.SphereGeometry(layers3D.RADIAL_SHELLS.BASE_GLOBE + 0.012, 128, 64);
  const cloudMat = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    alphaMap: cloudTex,
    transparent: true,
    opacity: 0.42,
    depthWrite: false,
    roughness: 0.95,
    metalness: 0.0
  });
  cloudMesh = new THREE.Mesh(cloudGeom, cloudMat);
  cloudMesh.name = 'optical_cloud_shell';
  cloudMesh.visible = isCloudsVisible;
  globe.add(cloudMesh);

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

  // 8b. Initialize Animated Atmospheric Wind Particles, Global Hazard Alerts, GEOINT SAR & 16K-131K Tiled Earth
  windParticles.initWindParticles(globe, 3500);
  hazardAlerts.initHazardAlerts(globe);
  sarTasking.initSarTasking(globe);
  tiledEarth.initTiledEarth(globe, renderer);

  // 9. Initialize UI Controller & Glassmorphic HUD
  uiController.initUI(globe, camera, renderer, layers3D);

  // 9b. Initialize Interactive 6-Step Guided Mission Tutorial
  tutorialTour.initMissionTutorial({
    setBaseTexture,
    flyToLatLon,
    flyTo,
    setSpinState
  });

  // 10. Wire DOM Event Listeners
  window.addEventListener('resize', onWindowResize);
  setupPointerEvents(renderer.domElement);
  setupKeyboardControls();
  setupNavigationButtons();
  setupCameraControlButtons();
  setupAtmosphereLayerButtons();

  // 11. Connect studyData events
  studyData.on('domain-focused', ({ domainInfo }) => {
    if (domainInfo) {
      flyToLatLon(domainInfo.lat, domainInfo.lon, domainInfo.distance || 8.5);
    }
  });

  studyData.on('layer-toggled', ({ layerId, visible }) => {
    if (layerId === 'relief') {
      isReliefActive = Boolean(visible);
      if (globe && globe.material) {
        globe.material.bumpScale = isReliefActive ? bumpScaleValue : 0.0;
        if (globe.material.normalScale) {
          globe.material.normalScale.set(
            isReliefActive ? normalScaleValue : 0.0,
            isReliefActive ? normalScaleValue : 0.0
          );
        }
        globe.material.needsUpdate = true;
      }
    } else if (layerId === 'rotation') {
      isSpinning = Boolean(visible);
    }
  });

  studyData.on('study-version-changed', ({ versionId }) => {
    if (uiController?.stopForecastAnimation) {
      uiController.stopForecastAnimation(true);
    }
    if (sarTasking?.setSarTaskingVisibility) {
      sarTasking.setSarTaskingVisibility(versionId === 'V3');
    }
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
// 3. POINTER EVENTS & INTERACTIVE CAMERA CONTROLS
// =============================================================================

export function panCamera(deltaX, deltaY) {
  if (!camera || !cameraTarget) return;
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  camera.matrixWorld.extractBasis(right, up, new THREE.Vector3());

  const dist = camera.position.distanceTo(cameraTarget);
  const factor = Math.max(0.002, dist * 0.0012);

  const moveX = right.multiplyScalar(-deltaX * factor);
  const moveY = up.multiplyScalar(deltaY * factor);

  camera.position.add(moveX).add(moveY);
  cameraTarget.add(moveX).add(moveY);
}

export function zoomCamera(delta) {
  if (!camera || !cameraTarget) return;
  const offset = new THREE.Vector3().subVectors(camera.position, cameraTarget);
  const currentDist = offset.length();
  const newDist = Math.max(5.8, Math.min(26.0, currentDist + delta));
  offset.normalize().multiplyScalar(newDist);
  camera.position.copy(cameraTarget).add(offset);
}

export function rotateGlobe(deltaX, deltaY) {
  if (!globe) return;
  globe.rotation.y += deltaX * 0.005;
  globe.rotation.x += deltaY * 0.005;
  const maxTilt = Math.PI * 0.48;
  globe.rotation.x = Math.max(-maxTilt, Math.min(maxTilt, globe.rotation.x));
}

export function resetCameraView() {
  if (uiController?.stopForecastAnimation) {
    uiController.stopForecastAnimation(true);
  }
  const { rotX, rotY } = layers3D.boresightRotation(0, 0);
  targetCameraPos = { x: 0, y: 0, z: 14 };
  targetCameraTarget = new THREE.Vector3(0, 0, 0);
  targetGlobeRot = { x: rotX, y: rotY };
  isFlying = true;
}

export function recenterCameraTarget() {
  if (!camera) return;
  const currentDist = camera.position.distanceTo(cameraTarget) || 14;
  targetCameraTarget = new THREE.Vector3(0, 0, 0);
  targetCameraPos = { x: 0, y: 0, z: currentDist };
  targetGlobeRot = { x: globe ? globe.rotation.x : 0, y: globe ? globe.rotation.y : 0 };
  isFlying = true;
}

function setupPointerEvents(canvas) {
  canvas.addEventListener('contextmenu', (e) => {
    e.preventDefault();
  });

  const activePointers = new Map();
  let pinchStartDist = 0;
  let pinchStartCenter = { x: 0, y: 0 };

  canvas.addEventListener('pointerdown', (e) => {
    const ptrId = typeof e.pointerId !== 'undefined' ? e.pointerId : 0;
    activePointers.set(ptrId, { x: e.clientX, y: e.clientY });

    isDragging = true;
    pointerButton = typeof e.button === 'number' ? e.button : 0;
    pointerDownPos = { x: e.clientX, y: e.clientY };
    previousPointerPos = { x: e.clientX, y: e.clientY };

    if (activePointers.size >= 2) {
      dragMode = 'pinch';
      const pts = Array.from(activePointers.values());
      pinchStartDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      pinchStartCenter = { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 };
    } else if (e.button === 2 || e.button === 1 || e.shiftKey) {
      dragMode = 'pan';
    } else {
      dragMode = 'rotate';
    }

    isFlying = false;
  });

  window.addEventListener('pointermove', (e) => {
    if (!isDragging || !globe || !camera) return;

    const ptrId = typeof e.pointerId !== 'undefined' ? e.pointerId : 0;
    if (activePointers.has(ptrId)) {
      activePointers.set(ptrId, { x: e.clientX, y: e.clientY });
    }

    if (activePointers.size >= 2) {
      const pts = Array.from(activePointers.values());
      const curDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      const curCenter = { x: (pts[0].x + pts[1].x) / 2, y: (pts[0].y + pts[1].y) / 2 };

      if (pinchStartDist > 0) {
        const pinchDelta = (pinchStartDist - curDist) * 0.02;
        zoomCamera(pinchDelta);
        pinchStartDist = curDist;
      }

      const panDeltaX = curCenter.x - pinchStartCenter.x;
      const panDeltaY = curCenter.y - pinchStartCenter.y;
      panCamera(panDeltaX, panDeltaY);
      pinchStartCenter = curCenter;
      isFlying = false;
      return;
    }

    const deltaX = e.clientX - previousPointerPos.x;
    const deltaY = e.clientY - previousPointerPos.y;

    if (dragMode === 'pan') {
      panCamera(deltaX, deltaY);
    } else {
      rotateGlobe(deltaX, deltaY);
    }

    isFlying = false;
    previousPointerPos = { x: e.clientX, y: e.clientY };
  });

  const handlePointerEnd = (e) => {
    if (!isDragging) return;
    const ptrId = typeof e.pointerId !== 'undefined' ? e.pointerId : 0;
    activePointers.delete(ptrId);

    if (activePointers.size === 0) {
      isDragging = false;
      const deltaDist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);

      // Click threshold (<=5px) on left click or touch tap without shift: execute raycast POI selection
      const isLeftOrTouch = pointerButton === 0 || e.pointerType === 'touch' || e.pointerType === 'pen';
      if (deltaDist <= 5 && isLeftOrTouch && !e.shiftKey) {
        let hit = layers3D.handleRaycast(e, camera, window.innerWidth, window.innerHeight);
        if (!hit && sarTasking?.getSarPickableObjects && sarTasking.getSarTaskingVisibility()) {
          const sarPickables = sarTasking.getSarPickableObjects();
          if (sarPickables.length > 0 && camera) {
            const w = window.innerWidth || 1;
            const h = window.innerHeight || 1;
            const ndc = new THREE.Vector2((e.clientX / w) * 2 - 1, -(e.clientY / h) * 2 + 1);
            const raycaster = new THREE.Raycaster();
            raycaster.setFromCamera(ndc, camera);
            const hits = raycaster.intersectObjects(sarPickables, true);
            for (const cand of hits) {
              const worldPt = cand.point;
              if (layers3D?.isFrontFacing && !layers3D.isFrontFacing(worldPt, new THREE.Vector3(0, 0, 0), camera.position)) {
                continue;
              }
              let obj = cand.object;
              while (obj && (!obj.userData || !obj.userData.type)) {
                obj = obj.parent;
              }
              if (obj && obj.userData) {
                const payload = obj.userData.data ? { ...obj.userData.data, type: obj.userData.type } : obj.userData;
                hit = {
                  object: obj,
                  point: worldPt,
                  data: payload,
                  screenPos: { x: e.clientX, y: e.clientY }
                };
                break;
              }
            }
          }
        }
        if (!hit && hazardAlerts?.getHazardPickableObjects && hazardAlerts.getHazardAlertsVisibility?.()) {
          const hazardPickables = hazardAlerts.getHazardPickableObjects();
          if (hazardPickables.length > 0 && camera) {
            const w = window.innerWidth || 1;
            const h = window.innerHeight || 1;
            const ndc = new THREE.Vector2((e.clientX / w) * 2 - 1, -(e.clientY / h) * 2 + 1);
            const raycaster = new THREE.Raycaster();
            raycaster.setFromCamera(ndc, camera);
            const hits = raycaster.intersectObjects(hazardPickables, true);
            for (const cand of hits) {
              const worldPt = cand.point;
              if (layers3D?.isFrontFacing && !layers3D.isFrontFacing(worldPt, new THREE.Vector3(0, 0, 0), camera.position)) {
                continue;
              }
              let obj = cand.object;
              while (obj && (!obj.userData || !obj.userData.type)) {
                obj = obj.parent;
              }
              if (obj && obj.userData) {
                const payload = obj.userData.data ? { ...obj.userData.data, type: obj.userData.type } : obj.userData;
                hit = {
                  object: obj,
                  point: worldPt,
                  data: payload,
                  screenPos: { x: e.clientX, y: e.clientY }
                };
                break;
              }
            }
          }
        }
        if (hit && hit.data) {
          uiController.showPopup(hit.data, hit.screenPos);
          isSpinning = false;
          uiController.setSpinState(false);
        } else {
          uiController.hidePopup();
        }
      } else {
        uiController.hidePopup();
      }
    } else if (activePointers.size === 1) {
      // Transition from 2 fingers back to 1 finger smoothly without jumping
      const [remaining] = Array.from(activePointers.values());
      previousPointerPos = { x: remaining.x, y: remaining.y };
      dragMode = 'rotate';
    }
  };

  window.addEventListener('pointerup', handlePointerEnd);
  window.addEventListener('pointercancel', handlePointerEnd);

  // Smooth mouse wheel zoom
  window.addEventListener('wheel', (e) => {
    if (!camera) return;
    const delta = e.deltaY * 0.008;
    zoomCamera(delta);
  }, { passive: true });
}

function setupKeyboardControls() {
  window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA'].includes(e.target?.tagName)) return;

    const panAmount = 35;
    const rotAmount = 0.08;

    if (e.key === 'r' || e.key === 'R' || e.code === 'Space') {
      resetCameraView();
      return;
    }

    if (e.shiftKey) {
      switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
          panCamera(0, panAmount);
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          panCamera(0, -panAmount);
          break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
          panCamera(panAmount, 0);
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          panCamera(-panAmount, 0);
          break;
      }
    } else {
      switch (e.key) {
        case 'ArrowUp':
        case 'w':
        case 'W':
          if (globe) {
            rotateGlobe(0, panAmount * 0.2);
            isFlying = false;
          }
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          if (globe) {
            rotateGlobe(0, -panAmount * 0.2);
            isFlying = false;
          }
          break;
        case 'ArrowLeft':
        case 'a':
        case 'A':
          if (globe) {
            rotateGlobe(-panAmount * 0.2, 0);
            isFlying = false;
          }
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          if (globe) {
            rotateGlobe(panAmount * 0.2, 0);
            isFlying = false;
          }
          break;
        case 'e':
        case 'E':
        case '+':
        case '=':
          zoomCamera(-0.8);
          break;
        case 'q':
        case 'Q':
        case '-':
        case '_':
          zoomCamera(0.8);
          break;
      }
    }
  });
}

// =============================================================================
// 4. ATMOSPHERIC TEXTURE & TOPOGRAPHIC RELIEF CONTROLS
// =============================================================================

export function setReliefState(active) {
  isReliefActive = Boolean(active);
  if (globe && globe.material) {
    globe.material.bumpScale = isReliefActive ? bumpScaleValue : 0.0;
    if (globe.material.normalScale) {
      globe.material.normalScale.set(
        isReliefActive ? normalScaleValue : 0.0,
        isReliefActive ? normalScaleValue : 0.0
      );
    }
    globe.material.needsUpdate = true;
  }
  if (uiController?.setReliefState && uiController.getReliefState() !== isReliefActive) {
    uiController.setReliefState(isReliefActive);
  }
}

export function getReliefState() {
  return (typeof uiController?.getReliefState === 'function')
    ? uiController.getReliefState()
    : isReliefActive;
}

export function setSpinState(spinning) {
  isSpinning = Boolean(spinning);
  if (uiController?.setSpinState && uiController.getSpinState() !== isSpinning) {
    uiController.setSpinState(isSpinning);
  }
}

export function getSpinState() {
  return (typeof uiController?.getSpinState === 'function')
    ? uiController.getSpinState()
    : isSpinning;
}

export function setBaseTexture(mode) {
  const norm = String(mode || 'sat').toLowerCase();
  let nextTex = satTex;
  const isSat = norm === 'sat' || norm === 'satellite';
  if (norm === 't2m') {
    currentTextureName = 'earth_t2m.jpg';
    nextTex = t2mTex;
  } else if (norm === 'tend' || norm === 'tendency') {
    currentTextureName = 'earth_tendency.jpg';
    nextTex = tendTex;
  } else {
    currentTextureName = 'earth_satellite_8k.jpg';
    nextTex = satTex;
  }

  if (globe && globe.material) {
    globe.material.map = nextTex;
    // Preserve bumpScale & normalScale across texture swaps per Item 1 & T3.5
    const reliefActive = getReliefState();
    globe.material.bumpScale = reliefActive ? bumpScaleValue : 0.0;
    if (globe.material.normalScale) {
      globe.material.normalScale.set(
        reliefActive ? normalScaleValue : 0.0,
        reliefActive ? normalScaleValue : 0.0
      );
    }
    globe.material.emissiveIntensity = isSat ? 0.55 : 0.0;
    globe.material.needsUpdate = true;
  }
  tiledEarth.setSatelliteModeActive(isSat);

  if (typeof document !== 'undefined') {
    const btnSat = document.getElementById('layer-sat');
    const btnT2m = document.getElementById('layer-t2m');
    const btnTend = document.getElementById('layer-tend');
    if (btnSat) btnSat.classList.toggle('active-btn', norm === 'sat' || norm === 'satellite');
    if (btnT2m) btnT2m.classList.toggle('active-btn', norm === 't2m');
    if (btnTend) btnTend.classList.toggle('active-btn', norm === 'tend' || norm === 'tendency');
  }
  uiController?.updateLegend?.(norm === 'sat' ? 'sat' : (norm === 't2m' ? 't2m' : 'tendency'));
}

function setupAtmosphereLayerButtons() {
  const btnSat = document.getElementById('layer-sat');
  const btnT2m = document.getElementById('layer-t2m');
  const btnTend = document.getElementById('layer-tend');

  if (btnSat) {
    btnSat.addEventListener('click', () => setBaseTexture('sat'));
  }

  if (btnT2m) {
    btnT2m.addEventListener('click', () => setBaseTexture('t2m'));
  }

  if (btnTend) {
    btnTend.addEventListener('click', () => setBaseTexture('tend'));
  }

  const btnClouds = document.getElementById('layer-clouds');
  if (btnClouds) {
    btnClouds.addEventListener('click', () => {
      isCloudsVisible = btnClouds.classList.toggle('active-btn');
      if (cloudMesh) {
        cloudMesh.visible = isCloudsVisible;
      }
    });
  }

  const btnSentinelLod = document.getElementById('layer-sentinel-lod');
  if (btnSentinelLod) {
    btnSentinelLod.addEventListener('click', () => {
      const enabled = btnSentinelLod.classList.toggle('active-btn');
      tiledEarth.setTiledEarthEnabled(enabled);
    });
  }
}

// =============================================================================
// 5. CAMERA NAVIGATION & BORESIGHT ROTATION
// =============================================================================

export function flyToLatLon(lat, lon, distance = 8.5) {
  const { rotX, rotY } = layers3D.boresightRotation(lat, lon);
  targetGlobeRot = { x: rotX, y: rotY };
  targetCameraPos = { x: 0, y: 0, z: distance };
  targetCameraTarget = new THREE.Vector3(0, 0, 0);
  isFlying = true;
}

export function flyTo(x, y, z) {
  targetCameraPos = { x, y, z };
  targetCameraTarget = new THREE.Vector3(0, 0, 0);
  targetGlobeRot = { x: 0, y: targetGlobeRot ? targetGlobeRot.y : (globe ? globe.rotation.y : 0) };
  isFlying = true;
}

function setupNavigationButtons() {
  const btnGlobal = document.getElementById('fly-global');
  const btnItaly = document.getElementById('fly-italy');
  const btnJapan = document.getElementById('fly-japan');
  const btnAmericas = document.getElementById('fly-americas');
  const btnArctic = document.getElementById('fly-arctic');
  const btnAntarctic = document.getElementById('fly-antarctic');
  const btnResetHud = document.getElementById('btn-camera-reset-hud');

  if (btnGlobal) {
    btnGlobal.addEventListener('click', () => {
      isSpinning = false;
      uiController.setSpinState(false);
      flyToLatLon(0.0, 0.0, 14.0);
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

  if (btnAmericas) {
    btnAmericas.addEventListener('click', () => {
      isSpinning = false;
      uiController.setSpinState(false);
      flyToLatLon(38.0, -97.0, 8.5);
    });
  }

  if (btnArctic) {
    btnArctic.addEventListener('click', () => {
      isSpinning = false;
      uiController.setSpinState(false);
      flyToLatLon(88.0, 0.0, 10.0);
    });
  }

  if (btnAntarctic) {
    btnAntarctic.addEventListener('click', () => {
      isSpinning = false;
      uiController.setSpinState(false);
      flyToLatLon(-88.0, 0.0, 10.0);
    });
  }

  if (btnResetHud) {
    btnResetHud.addEventListener('click', resetCameraView);
  }
}

function setupCameraControlButtons() {
  const btnReset = document.getElementById('btn-camera-reset');
  const btnRecenter = document.getElementById('cam-recenter');
  const btnPanUp = document.getElementById('cam-pan-up');
  const btnPanDown = document.getElementById('cam-pan-down');
  const btnPanLeft = document.getElementById('cam-pan-left');
  const btnPanRight = document.getElementById('cam-pan-right');

  const btnZoomIn = document.getElementById('cam-zoom-in');
  const btnZoomOut = document.getElementById('cam-zoom-out');
  const btnRotLeft = document.getElementById('cam-rot-left');
  const btnRotRight = document.getElementById('cam-rot-right');

  const btnViewArctic = document.getElementById('cam-view-arctic');
  const btnViewAntarctic = document.getElementById('cam-view-antarctic');

  if (btnReset) btnReset.addEventListener('click', resetCameraView);
  if (btnRecenter) btnRecenter.addEventListener('click', recenterCameraTarget);

  if (btnPanUp) btnPanUp.addEventListener('click', () => panCamera(0, 35));
  if (btnPanDown) btnPanDown.addEventListener('click', () => panCamera(0, -35));
  if (btnPanLeft) btnPanLeft.addEventListener('click', () => panCamera(35, 0));
  if (btnPanRight) btnPanRight.addEventListener('click', () => panCamera(-35, 0));

  if (btnZoomIn) btnZoomIn.addEventListener('click', () => zoomCamera(-1.2));
  if (btnZoomOut) btnZoomOut.addEventListener('click', () => zoomCamera(1.2));

  if (btnRotLeft) btnRotLeft.addEventListener('click', () => {
    if (globe) globe.rotation.y -= 0.15;
    isFlying = false;
  });
  if (btnRotRight) btnRotRight.addEventListener('click', () => {
    if (globe) globe.rotation.y += 0.15;
    isFlying = false;
  });

  if (btnViewArctic) btnViewArctic.addEventListener('click', () => {
    isSpinning = false;
    uiController.setSpinState(false);
    flyToLatLon(88.0, 0.0, 10.0);
  });

  if (btnViewAntarctic) btnViewAntarctic.addEventListener('click', () => {
    isSpinning = false;
    uiController.setSpinState(false);
    flyToLatLon(-88.0, 0.0, 10.0);
  });
}

// =============================================================================
// 6. ANIMATION & RENDER LOOP
// =============================================================================

export function onWindowResize() {
  if (!camera || !renderer) return;
  const w = (typeof window !== 'undefined' ? window.innerWidth : 1920) || 1;
  const h = (typeof window !== 'undefined' ? window.innerHeight : 1080) || 1;
  camera.aspect = (w > 0 && h > 0) ? (w / h) : 1.0;
  camera.updateProjectionMatrix();
  renderer.setSize(Math.max(1, w), Math.max(1, h));
  if (uiController?.updatePopupPosition) {
    uiController.updatePopupPosition(camera, w, h);
  }
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

    // Lerp camera target if defined
    if (targetCameraTarget && cameraTarget) {
      cameraTarget.x += (targetCameraTarget.x - cameraTarget.x) * 0.08;
      cameraTarget.y += (targetCameraTarget.y - cameraTarget.y) * 0.08;
      cameraTarget.z += (targetCameraTarget.z - cameraTarget.z) * 0.08;
    }

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
      if (targetCameraTarget && cameraTarget) {
        cameraTarget.copy(targetCameraTarget);
        targetCameraTarget = null;
      }
      globe.rotation.set(targetGlobeRot.x, targetGlobeRot.y, 0);
      isFlying = false;
    }
  }

  // Camera orientation always tracks focus target
  if (camera && cameraTarget) {
    camera.lookAt(cameraTarget.x, cameraTarget.y, cameraTarget.z);
  }

  // 2. Earth Constant Auto-Rotation (F13.3) & Gentle Optical Cloud Drift
  if (isSpinning && globe && !isDragging && !isFlying) {
    globe.rotation.y += 0.0018;
  }
  if (cloudMesh && isCloudsVisible) {
    cloudMesh.rotation.y += 0.00018;
  }

  // 3. Update 3D Scientific Layers (Pulsing Beacons, Plasma Shaders)
  layers3D.updateLayers(elapsedTime, camera);

  // 3b. Update Wind Particles Advection, Hazard Alert Pulses, GEOINT SAR Orbits & 16K-131K Tiled LOD
  windParticles.updateWindParticles(0.016);
  hazardAlerts.updateHazardAlerts(elapsedTime);
  sarTasking.updateSarTasking(elapsedTime);
  tiledEarth.updateTiledEarth(camera, globe, renderer);

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
  flyTo,
  panCamera,
  zoomCamera,
  rotateGlobe,
  resetCameraView,
  recenterCameraTarget,
  setReliefState,
  getReliefState,
  setSpinState,
  getSpinState,
  onWindowResize
};
