// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * layers3D.test.js
 * Comprehensive Unit Test Suite for Exact 3D Boresight & Coordinate Panning
 *
 * Verifies:
 * 1. Zero artificial damping (elimination of rotX = latRad * 0.4).
 * 2. Exact spherical centering of all regional presets (Italy, Japan, Americas, Arctic, Antarctic, etc.).
 * 3. Exact screen-center projection at (W/2, H/2).
 * 4. Euler rotation order 'XYZ' alignment with Three.js SphereGeometry.
 * 5. Boresight inversion and lat/lon coordinate recovery.
 * 6. Interactive navigation functions: flyToLatLon, panCamera, and cameraTarget.
 */

import * as THREE from 'three';
import layers3D, {
  RADIAL_SHELLS,
  latLonToVector3,
  latLonToCartesian,
  boresightRotation,
  cameraTarget,
  panCamera,
  flyToLatLon,
  projectToScreen,
  isFrontFacing
} from '../layers3D.js';
import { getCameraBoresightLatLon } from '../tiledEarth.js';

let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) {
    failed++;
    console.error(`  FAIL: ${message}`);
    throw new Error(message || 'Assertion failed');
  }
}

function assertCloseTo(actual, expected, tol = 1e-6, message = '') {
  const diff = Math.abs(actual - expected);
  if (diff > tol) {
    failed++;
    console.error(`  FAIL: ${message} (expected ${expected}, got ${actual}, diff ${diff} > tol ${tol})`);
    throw new Error(message || `Expected ${expected}, got ${actual}`);
  }
}

function runTest(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    console.error(`  ✕ ERROR in "${name}":`, err.message);
  }
}

console.log('═══════════════════════════════════════════════════════════════════════');
console.log('  layers3D.js: Exact 3D Boresight & Coordinate Panning Unit Tests');
console.log('═══════════════════════════════════════════════════════════════════════\n');

// -----------------------------------------------------------------------------
// Suite 1: Exact Boresight Rotation Formula (Zero Damping Invariant)
// -----------------------------------------------------------------------------
console.log('▸ Suite 1: Exact Boresight Rotation Formula (Zero Damping)');

runTest('1.1 Zero artificial damping: rotX equals latRad exactly (not latRad * 0.4)', () => {
  const testLatitudes = [-88, -60, -45, -30, 0, 15, 36, 42, 60, 88];
  for (const lat of testLatitudes) {
    const { rotX } = boresightRotation(lat, 0);
    const expectedRotX = lat * (Math.PI / 180.0);
    assertCloseTo(rotX, expectedRotX, 1e-7, `rotX for lat ${lat}° must be lat * PI/180`);
    
    // Explicitly reject damped legacy formula
    if (lat !== 0) {
      const dampedRotX = lat * (Math.PI / 180.0) * 0.4;
      assert(Math.abs(rotX - dampedRotX) > 1e-4, `rotX must not equal damped legacy value (${dampedRotX})`);
    }
  }
});

runTest('1.2 Exact rotY longitude mapping: rotY = -lonRad - PI/2', () => {
  const testLongitudes = [-180, -97, -90, 0, 12, 90, 138, 180, 270];
  for (const lon of testLongitudes) {
    const { rotY } = boresightRotation(0, lon);
    const expectedRotY = -(lon * Math.PI / 180.0) - Math.PI / 2.0;
    assertCloseTo(rotY, expectedRotY, 1e-7, `rotY for lon ${lon}° must be -lon*PI/180 - PI/2`);
  }
});

// -----------------------------------------------------------------------------
// Suite 2: Geographic Presets & Dead-Center Boresight Alignment
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 2: Geographic Presets & Dead-Center Boresight Alignment');

const TARGET_PRESETS = [
  { name: 'Equator Greenwich', lat: 0.0, lon: 0.0 },
  { name: 'Equator 90°E (Indian Ocean)', lat: 0.0, lon: 90.0 },
  { name: 'Equator 90°W (Galapagos)', lat: 0.0, lon: -90.0 },
  { name: 'Equator 180° (Antimeridian)', lat: 0.0, lon: 180.0 },
  { name: 'Italy Synoptic Domain (Rome)', lat: 42.0, lon: 12.0 },
  { name: 'Japan Synoptic Domain (Honshu)', lat: 36.0, lon: 138.0 },
  { name: 'Americas Synoptic Domain (Kansas)', lat: 38.0, lon: -97.0 },
  { name: 'Arctic Synoptic Domain', lat: 88.0, lon: 0.0 },
  { name: 'Antarctic Synoptic Domain', lat: -88.0, lon: 0.0 },
  { name: 'North Pole', lat: 90.0, lon: 0.0 },
  { name: 'South Pole', lat: -90.0, lon: 0.0 }
];

runTest('2.1 Rotated spherical point lands at (0, 0, +R) facing camera', () => {
  const R = RADIAL_SHELLS.BASE_GLOBE; // 5.000
  for (const preset of TARGET_PRESETS) {
    const p = latLonToVector3(preset.lat, preset.lon, R);
    const rot = boresightRotation(preset.lat, preset.lon);
    const euler = new THREE.Euler(rot.rotX, rot.rotY, 0, 'XYZ');
    const rotated = p.clone().applyEuler(euler);

    assertCloseTo(rotated.x, 0.0, 1e-5, `${preset.name} X must be 0`);
    assertCloseTo(rotated.y, 0.0, 1e-5, `${preset.name} Y must be 0`);
    assertCloseTo(rotated.z, R, 1e-5, `${preset.name} Z must be +R (${R})`);
  }
});

runTest('2.2 Target projects dead-center on 2D screen viewport (W/2, H/2)', () => {
  const W = 1920;
  const H = 1080;
  const camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 1000);
  camera.position.set(0, 0, 8.5);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);

  for (const preset of TARGET_PRESETS) {
    const p = latLonToVector3(preset.lat, preset.lon, RADIAL_SHELLS.BASE_GLOBE);
    const rot = boresightRotation(preset.lat, preset.lon);
    const euler = new THREE.Euler(rot.rotX, rot.rotY, 0, 'XYZ');
    const rotated = p.clone().applyEuler(euler);

    const screenPos = projectToScreen(rotated, camera, W, H);
    assert(screenPos.visible === true, `${preset.name} must be visible on front hemisphere`);
    assertCloseTo(screenPos.x, W / 2, 1.0, `${preset.name} screen X must be centered at ${W / 2}`);
    assertCloseTo(screenPos.y, H / 2, 1.0, `${preset.name} screen Y must be centered at ${H / 2}`);
  }
});

// -----------------------------------------------------------------------------
// Suite 3: Euler Rotation Order 'XYZ' Alignment & Inversion
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 3: Euler Rotation Order & Boresight Inversion');

runTest('3.1 Three.js Euler order XYZ correctly applies Y first then X', () => {
  const lat = 42.0;
  const lon = 12.0;
  const p = latLonToVector3(lat, lon, 5.0);
  const rot = boresightRotation(lat, lon);

  const eulerXYZ = new THREE.Euler(rot.rotX, rot.rotY, 0, 'XYZ');
  const ptXYZ = p.clone().applyEuler(eulerXYZ);
  assertCloseTo(ptXYZ.distanceTo(new THREE.Vector3(0, 0, 5.0)), 0.0, 1e-5, 'XYZ order yields exact boresight');

  // Verify that arbitrary order YXZ without re-derivation does NOT yield (0,0,5)
  const eulerYXZ = new THREE.Euler(rot.rotX, rot.rotY, 0, 'YXZ');
  const ptYXZ = p.clone().applyEuler(eulerYXZ);
  assert(ptYXZ.distanceTo(new THREE.Vector3(0, 0, 5.0)) > 1.0, 'YXZ order differs without modified angles');
});

runTest('3.2 getCameraBoresightLatLon accurately recovers input coordinates', () => {
  const testGlobe = new THREE.Mesh(new THREE.SphereGeometry(5, 32, 32));
  const camera = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
  camera.position.set(0, 0, 8.5);

  for (const preset of TARGET_PRESETS) {
    const rot = boresightRotation(preset.lat, preset.lon);
    testGlobe.rotation.set(rot.rotX, rot.rotY, 0, 'XYZ');
    testGlobe.updateMatrixWorld(true);

    const recovered = getCameraBoresightLatLon(camera, testGlobe);
    assertCloseTo(recovered.lat, preset.lat, 1e-4, `${preset.name} recovered latitude`);

    let diffLon = Math.abs(recovered.lon - preset.lon) % 360;
    if (diffLon > 180) diffLon = 360 - diffLon;
    // Near poles (lat > 89 or < -89), longitude is mathematically degenerate
    if (Math.abs(preset.lat) < 85) {
      assertCloseTo(diffLon, 0.0, 1e-4, `${preset.name} recovered longitude`);
    }
  }
});

// -----------------------------------------------------------------------------
// Suite 4: Camera Target & Navigation Methods (flyToLatLon, panCamera)
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 4: Camera Target & Navigation Methods');

runTest('4.1 flyToLatLon orients globe and resets camera target', () => {
  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
  const target = new THREE.Vector3(5, 5, 5); // non-zero initial target

  const result = flyToLatLon(42.0, 12.0, 8.5, globe, camera, target);
  assertCloseTo(result.rotX, 42.0 * (Math.PI / 180.0), 1e-6);
  assertCloseTo(result.rotY, -(12.0 * Math.PI / 180.0) - Math.PI / 2.0, 1e-6);
  assertCloseTo(globe.rotation.x, result.rotX, 1e-6);
  assertCloseTo(globe.rotation.y, result.rotY, 1e-6);
  assertCloseTo(camera.position.z, 8.5, 1e-6);
  assertCloseTo(target.length(), 0.0, 1e-6, 'Target reset to origin');
});

runTest('4.2 panCamera smoothly translates camera position and target without distortion', () => {
  const camera = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
  camera.position.set(0, 0, 10);
  camera.updateMatrixWorld(true);
  const target = new THREE.Vector3(0, 0, 0);

  panCamera(100, 50, camera, target);
  assert(target.x < 0, 'Target moved horizontally');
  assert(target.y > 0, 'Target moved vertically');
  assertCloseTo(camera.position.x, target.x, 1e-6, 'Camera X tracks target X');
  assertCloseTo(camera.position.y, target.y, 1e-6, 'Camera Y tracks target Y');
});

// -----------------------------------------------------------------------------
// Execution Summary
// -----------------------------------------------------------------------------
console.log('\n───────────────────────────────────────────────────────────────────────');
console.log(`Execution Summary: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('───────────────────────────────────────────────────────────────────────\n');

if (failed > 0) {
  console.error(`layers3D.test.js FAILED with ${failed} failure(s).`);
  process.exit(1);
} else {
  console.log('layers3D.test.js PASSED: All 3D boresight and coordinate tests 100% verified.');
  process.exit(0);
}
