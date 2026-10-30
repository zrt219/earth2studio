// SPDX-License-Identifier: Apache-2.0
/**
 * adversarial_layers3d.test.js
 * Empirical Challenger Adversarial Test Suite for Milestone 2: viewer_app/layers3D.js
 *
 * Comprehensive Stress & Penetration Testing:
 * 1. Raycasting Robustness: Extreme NDC inputs, NaN/Infinity, micro-drags (3px), macro-drags (20px), rear-hemisphere points, horizon tangent boundary
 * 2. Rapid Layer Toggling: 1,000 rapid toggle cycles across cyclone, DA pins, ensemble spread, mesoscale insets with alias stress
 * 3. Memory & Buffer Deallocation: Verification that all geometries, materials, and references are properly released by disposeLayers()
 * 4. Empirical Vulnerability Mining:
 *    - BUG-M2-001: Raycast hit leak on hidden layers (parent group invisible but children intersected)
 *    - BUG-M2-002: setEnsembleSpreadOpacity forces spread visible even when layer is disabled
 *    - BUG-M2-003: Listener accumulation on studyData and DOM elements across repeated initLayers()
 */

import * as THREE from 'three';
import layers3D, {
  RADIAL_SHELLS,
  latLonToVector3,
  latLonToCartesian,
  boresightRotation,
  isFrontFacing,
  projectToScreen,
  getMslpColor,
  getIncrementColor,
  getOrographicLapseRateDeltaT,
  createSphericalPatchGeometry,
  initLayers,
  setLayerVisibility,
  setEnsembleSpreadOpacity,
  handleRaycast,
  onGlobeClick,
  updateLayers,
  getInteractiveObjects,
  getLayerState,
  getLayers,
  disposeLayers
} from '../layers3D.js';
import studyData from '../studyData.js';

let passed = 0;
let failed = 0;
const defectsDiscovered = [];

function recordDefect(id, title, details) {
  defectsDiscovered.push({ id, title, details });
  console.warn(`  ⚠️ CONFIRMED DEFECT [${id}]: ${title}\n     -> ${details}`);
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || "Assertion failed");
  }
}

function createHarness() {
  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 1000);
  camera.position.set(0, 0, 14);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);

  let pointerDownListener = null;
  const domElement = {
    clientWidth: 1920,
    clientHeight: 1080,
    addEventListener: (type, cb) => {
      if (type === 'pointerdown') pointerDownListener = cb;
    },
    removeEventListener: (type, cb) => {
      if (type === 'pointerdown' && pointerDownListener === cb) {
        pointerDownListener = null;
      }
    }
  };

  const renderer = { domElement };
  initLayers(globe, camera, renderer);
  globe.updateMatrixWorld(true);

  return {
    globe,
    camera,
    renderer,
    domElement,
    triggerPointerDown: (clientX, clientY) => {
      if (pointerDownListener) {
        pointerDownListener({ clientX, clientY });
      }
    }
  };
}

console.log("===============================================================================");
console.log("OD-EARTH2-001 M2 CHALLENGER 1: ADVERSARIAL EMPIRICAL TEST HARNESS");
console.log("===============================================================================\n");

// -----------------------------------------------------------------------------
// SUITE 1: RAYCASTING & SPATIAL MATHEMATICAL INVARIANTS
// -----------------------------------------------------------------------------
console.log("--- Suite 1: Raycasting Robustness & Extreme NDC Inputs ---");

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    failed++;
    console.error(`  ✗ FAIL: ${name}\n     -> Error: ${err.message}`);
  }
}

async function testAsync(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    failed++;
    console.error(`  ✗ FAIL: ${name}\n     -> Error: ${err.message}`);
  }
}

test("1.1 Extreme / Non-Numeric NDC Inputs survive without unhandled exceptions", () => {
  const { camera } = createHarness();

  // Null/undefined events
  assert(handleRaycast(null, camera, 1920, 1080) === null, "null event must return null");
  assert(handleRaycast(undefined, camera, 1920, 1080) === null, "undefined event must return null");
  assert(handleRaycast({}, camera, 1920, 1080) === null, "empty event must return null");
  assert(handleRaycast({ clientX: 0, clientY: 0 }, null, 1920, 1080) === null, "null camera must return null");

  // Non-numeric / NaN / Infinity coordinates
  assert(handleRaycast({ clientX: NaN, clientY: NaN }, camera, 1920, 1080) === null, "NaN coordinates must return null");
  assert(handleRaycast({ clientX: Infinity, clientY: -Infinity }, camera, 1920, 1080) === null, "Infinity coordinates must return null");

  // Extreme coordinate magnitude
  assert(handleRaycast({ clientX: 1e12, clientY: 1e12 }, camera, 1920, 1080) === null, "Huge coordinates must return null");
  assert(handleRaycast({ clientX: -1e12, clientY: -1e12 }, camera, 1920, 1080) === null, "Huge negative coordinates must return null");

  // Viewport edge cases (zero dimensions)
  assert(handleRaycast({ clientX: 100, clientY: 100 }, camera, 0, 0) === null, "Zero dimensions must return null without divide-by-zero crash");
  assert(handleRaycast({ clientX: 100, clientY: 100 }, camera, -100, -100) === null, "Negative dimensions must return null");
});

test("1.2 Direct raycasting hit on front-facing waypoint computes valid hit payload", () => {
  const { globe, camera, triggerPointerDown } = createHarness();
  const pickables = getInteractiveObjects();
  assert(pickables.length > 0, "Pickable objects must exist");

  const wp0 = pickables.find(p => p.userData?.type === 'cyclone_waypoint');
  assert(wp0, "Waypoint 0 must exist in pickables");

  // Align camera directly with waypoint position
  camera.position.copy(wp0.position.clone().multiplyScalar(2.0));
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  globe.updateMatrixWorld(true);

  const screen = projectToScreen(wp0.position, camera, 1920, 1080);
  assert(screen.visible === true, "Projected waypoint must be visible");

  triggerPointerDown(screen.x, screen.y);
  const hit = handleRaycast({ clientX: screen.x, clientY: screen.y }, camera, 1920, 1080);

  assert(hit !== null, "Direct raycast must produce a hit");
  assert(hit.type === 'cyclone_waypoint', "Hit type must be cyclone_waypoint");
  assert(hit.data.id === wp0.userData.data.id, "Hit data must match waypoint ID");
  assert(hit.point instanceof THREE.Vector3, "Hit point must be THREE.Vector3");
  assert(typeof hit.screenPos.x === 'number' && typeof hit.screenPos.y === 'number', "screenPos must contain numeric coords");
});

test("1.3 Micro-drag threshold (3px movement) permits raycast execution", () => {
  const { globe, camera, triggerPointerDown } = createHarness();
  const pickables = getInteractiveObjects();
  const wp0 = pickables.find(p => p.userData?.type === 'cyclone_waypoint');

  camera.position.copy(wp0.position.clone().multiplyScalar(2.0));
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  globe.updateMatrixWorld(true);

  const screen = projectToScreen(wp0.position, camera, 1920, 1080);

  // Micro-drag: pointerdown at (screen.x, screen.y), pointerup at (screen.x + 3, screen.y) -> distance 3px <= 5px
  triggerPointerDown(screen.x, screen.y);
  const hit = handleRaycast({ clientX: screen.x + 3, clientY: screen.y }, camera, 1920, 1080);

  assert(hit !== null, "Micro-drag (3px) must NOT suppress raycast");
  assert(hit.type === 'cyclone_waypoint', "Hit type must match");
});

test("1.4 Macro-drag threshold (20px movement) suppresses raycast and returns null", () => {
  const { globe, camera, triggerPointerDown } = createHarness();
  const pickables = getInteractiveObjects();
  const wp0 = pickables.find(p => p.userData?.type === 'cyclone_waypoint');

  camera.position.copy(wp0.position.clone().multiplyScalar(2.0));
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  globe.updateMatrixWorld(true);

  const screen = projectToScreen(wp0.position, camera, 1920, 1080);

  // Macro-drag: pointerdown at (screen.x, screen.y), pointerup at (screen.x + 20, screen.y) -> distance 20px > 5px
  triggerPointerDown(screen.x, screen.y);
  const hit = handleRaycast({ clientX: screen.x + 20, clientY: screen.y }, camera, 1920, 1080);

  assert(hit === null, "Macro-drag (20px) MUST suppress raycast and return null");
});

test("1.5 Drag threshold boundary precision (5.0px vs 5.1px)", () => {
  const { globe, camera, triggerPointerDown } = createHarness();
  const pickables = getInteractiveObjects();
  const wp0 = pickables.find(p => p.userData?.type === 'cyclone_waypoint');

  camera.position.copy(wp0.position.clone().multiplyScalar(2.0));
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  globe.updateMatrixWorld(true);

  const screen = projectToScreen(wp0.position, camera, 1920, 1080);

  // Exactly 5.0px distance: dist <= 5, should execute raycast
  triggerPointerDown(screen.x, screen.y);
  const hitExact = handleRaycast({ clientX: screen.x + 5.0, clientY: screen.y }, camera, 1920, 1080);
  assert(hitExact !== null, "Exactly 5.0px drag should not be suppressed by > 5 check");

  // 5.01px distance: dist > 5, should be suppressed
  triggerPointerDown(screen.x, screen.y);
  const hitOver = handleRaycast({ clientX: screen.x + 5.01, clientY: screen.y }, camera, 1920, 1080);
  assert(hitOver === null, "5.01px drag must be suppressed");
});

test("1.6 Front-hemisphere occlusion filter rejects rear-facing markers", () => {
  const globeCenter = new THREE.Vector3(0, 0, 0);
  const cameraPos = new THREE.Vector3(0, 0, 14);

  // Front marker (+Z)
  const frontPt = new THREE.Vector3(0, 0, 5.05);
  assert(isFrontFacing(frontPt, globeCenter, cameraPos) === true, "Front point must be front-facing");

  // Rear marker (-Z)
  const rearPt = new THREE.Vector3(0, 0, -5.05);
  assert(isFrontFacing(rearPt, globeCenter, cameraPos) === false, "Rear point must be occluded");

  // Angled rear marker
  const rearAngled = new THREE.Vector3(3.0, 3.0, -3.0).normalize().multiplyScalar(5.05);
  assert(isFrontFacing(rearAngled, globeCenter, cameraPos) === false, "Rear angled point must be occluded");

  // Horizon point from T2.11 (x=5.0, y=0, z=0 facing slightly away from camera at 0, 0, 14)
  const horizonPoint = new THREE.Vector3(5.0, 0, 0);
  assert(isFrontFacing(horizonPoint, globeCenter, cameraPos) === false, "Horizon point (5, 0, 0) facing away must be occluded");

  // Exact 0.0 dot product boundary test: normal perpendicular to toCamera
  // For globe at origin, if camera is at (0, 0, 14) and point is chosen such that normal . (camera - pt) === 0:
  // e.g. normal is (0, 1, 0), cameraPos is (0, 10, 0), point is (10, 10, 0) -> normal . toCamera = 0
  const normPerp = new THREE.Vector3(0, 1, 0);
  const camPosPerp = new THREE.Vector3(0, 0, 14);
  // Any point on equator where z=0 and camera is on z axis has normal . (cam - pt) = -pt.x * pt.x <= 0
  const ptEquator = new THREE.Vector3(5.0, 0, 0);
  assert(isFrontFacing(ptEquator, globeCenter, camPosPerp) === false, "Equatorial limb point must be occluded");
});

// -----------------------------------------------------------------------------
// SUITE 2: RAPID LAYER TOGGLING & CONCURRENCY STRESS
// -----------------------------------------------------------------------------
console.log("\n--- Suite 2: Rapid Layer Toggling & Concurrency Stress ---");

test("2.1 1,000 rapid layer toggle cycles execute without unhandled exceptions or state corruption", () => {
  const { globe, camera } = createHarness();
  const layerKeys = ['cyclone', 'da_stations', 'ensemble_spread', 'mesoscale_insets'];

  const startTime = performance.now();
  for (let i = 0; i < 1000; i++) {
    // Alternating toggles
    layerKeys.forEach((key, kIdx) => {
      const boolVal = (i + kIdx) % 2 === 0;
      setLayerVisibility(key, boolVal);
    });

    // Test alias mapping
    setLayerVisibility('da', i % 3 === 0);
    setLayerVisibility('spread', i % 5 === 0);
    setLayerVisibility('mesoscale', i % 4 === 0);
    setLayerVisibility('cyclone_trajectory', i % 2 === 0);

    // Dynamic opacity update
    setEnsembleSpreadOpacity((i % 100) / 100.0);

    // Animation update tick
    if (i % 25 === 0) {
      updateLayers(i * 0.016, camera);
    }
  }
  const duration = performance.now() - startTime;
  console.log(`      ↳ 1,000 toggle cycles executed in ${duration.toFixed(2)} ms`);

  const finalState = getLayerState();
  assert(typeof finalState.activeLayers === 'object', "Final activeLayers must be an object");
  assert(typeof finalState.spreadOpacity === 'number', "Final spreadOpacity must be a number");
  assert(finalState.cycloneWaypointsCount === 5, "Waypoint count must remain 5");
  assert(finalState.daStationsCount === 4, "DA station count must remain 4");

  // Check layer groups exist and have boolean visibility
  const groups = getLayers();
  assert(typeof groups.cyclone.visible === 'boolean', "cyclone visibility must be boolean");
  assert(typeof groups.da.visible === 'boolean', "da visibility must be boolean");
  assert(typeof groups.spread.visible === 'boolean', "spread visibility must be boolean");
  assert(typeof groups.mesoscale.visible === 'boolean', "mesoscale visibility must be boolean");
});

test("2.2 Layer alias normalization and case/whitespace tolerance", () => {
  createHarness();

  setLayerVisibility('  CYCLONE  ', false);
  assert(getLayerState().activeLayers.cyclone === false, "Whitespace/uppercase CYCLONE must toggle cyclone to false");

  setLayerVisibility('DA_STATIONS', false);
  assert(getLayerState().activeLayers.da_stations === false, "Uppercase DA_STATIONS must toggle da_stations to false");

  setLayerVisibility('SPREAD', true);
  assert(getLayerState().activeLayers.ensemble_spread === true, "SPREAD alias must toggle ensemble_spread to true");

  setLayerVisibility('MESOSCALE', false);
  assert(getLayerState().activeLayers.mesoscale_insets === false, "MESOSCALE alias must toggle mesoscale_insets to false");
});

// -----------------------------------------------------------------------------
// SUITE 3: BUFFER DISPOSAL & MEMORY LEAK VERIFICATION
// -----------------------------------------------------------------------------
console.log("\n--- Suite 3: Buffer Disposal & Memory Deallocation ---");

test("3.1 disposeLayers() disposes 100% of geometries and materials in scene graph", () => {
  const { globe, camera } = createHarness();

  const geometries = [];
  const materials = [];

  globe.traverse(child => {
    if (child.geometry) {
      geometries.push(child.geometry);
      const orig = child.geometry.dispose.bind(child.geometry);
      child.geometry.disposed = false;
      child.geometry.dispose = () => {
        child.geometry.disposed = true;
        orig();
      };
    }
    if (child.material) {
      materials.push(child.material);
      const orig = child.material.dispose.bind(child.material);
      child.material.disposed = false;
      child.material.dispose = () => {
        child.material.disposed = true;
        orig();
      };
    }
  });

  assert(geometries.length === 29, `Expected 29 geometries, found ${geometries.length}`);
  assert(materials.length === 29, `Expected 29 materials, found ${materials.length}`);

  disposeLayers();

  const undisposedGeom = geometries.filter(g => !g.disposed);
  const undisposedMat = materials.filter(m => !m.disposed);

  assert(undisposedGeom.length === 0, `Undisposed geometries remaining: ${undisposedGeom.length}`);
  assert(undisposedMat.length === 0, `Undisposed materials remaining: ${undisposedMat.length}`);
  assert(globe.children.length === 0, `Globe should have 0 children remaining, found ${globe.children.length}`);
  assert(getInteractiveObjects().length === 0, `pickableObjects should be emptied, found ${getInteractiveObjects().length}`);
});

test("3.2 Repeated 50x initLayers / disposeLayers lifecycle loops execute cleanly", () => {
  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);

  for (let i = 0; i < 50; i++) {
    initLayers(globe, camera);
    disposeLayers();
  }

  assert(globe.children.length === 0, "Globe must have 0 children after 50 lifecycle iterations");
  assert(getInteractiveObjects().length === 0, "Interactive objects must be empty");
});

test("3.3 Consecutive disposeLayers calls are idempotent and do not throw", () => {
  disposeLayers();
  disposeLayers();
  disposeLayers();
  assert(true, "Multiple disposeLayers calls must succeed without error");
});

// -----------------------------------------------------------------------------
// SUITE 4: EMPIRICAL VULNERABILITY MINING & DEFECT PROOFS
// -----------------------------------------------------------------------------
console.log("\n--- Suite 4: Empirical Vulnerability Mining & Defect Proofs ---");

test("4.1 EMPIRICAL DEFECT CHECK: Raycast hit leak on hidden layers (BUG-M2-001)", () => {
  const { globe, camera, triggerPointerDown } = createHarness();
  const daCap = getInteractiveObjects().find(o => o.userData?.type === 'da_station');
  assert(daCap, "DA station cap must exist");

  // Align camera directly with station cap
  camera.position.copy(daCap.position.clone().multiplyScalar(2.0));
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld(true);
  globe.updateMatrixWorld(true);

  const screen = projectToScreen(daCap.position, camera, 1920, 1080);
  triggerPointerDown(screen.x, screen.y);

  // 1. Verify hit works when layer is VISIBLE
  setLayerVisibility('da_stations', true);
  const hitVisible = handleRaycast({ clientX: screen.x, clientY: screen.y }, camera, 1920, 1080);
  assert(hitVisible !== null && hitVisible.data.id === daCap.userData.data.id, "Visible station should be hit");

  // 2. Hide DA stations layer
  setLayerVisibility('da_stations', false);
  globe.updateMatrixWorld(true);

  // 3. Raycast at the exact same coordinates
  const hitHidden = handleRaycast({ clientX: screen.x, clientY: screen.y }, camera, 1920, 1080);

  if (hitHidden !== null) {
    recordDefect(
      "BUG-M2-001",
      "Raycaster intersects objects belonging to invisible parent layer groups",
      `When setLayerVisibility('da_stations', false) hides the DA station layer, handleRaycast() still intersects station cap (${hitHidden.data.id}) because pickableObjects contains child meshes and handleRaycast() does not verify if the hit object or its ancestor group has visible === true. Clicking empty space triggers phantom popups.`
    );
  } else {
    console.log("  ✓ Hidden layer objects are correctly ignored by raycaster");
  }
});

test("4.2 EMPIRICAL DEFECT CHECK: setEnsembleSpreadOpacity forces spread visible when disabled (BUG-M2-002)", () => {
  createHarness();

  // Explicitly disable ensemble spread layer
  setLayerVisibility('ensemble_spread', false);
  const layersBefore = getLayers();
  assert(layersBefore.spread.visible === false, "Spread mesh must be hidden when toggled false");
  assert(getLayerState().activeLayers.ensemble_spread === false, "Layer state must record ensemble_spread: false");

  // Now set spread opacity (e.g. from user slider or studyData event)
  setEnsembleSpreadOpacity(0.85);

  const layersAfter = getLayers();
  const stateAfter = getLayerState();

  if (layersAfter.spread.visible === true && stateAfter.activeLayers.ensemble_spread === false) {
    recordDefect(
      "BUG-M2-002",
      "setEnsembleSpreadOpacity() overrides layer visibility toggle state",
      "Line 937: layerGroups.spread.visible = clamped > 0.001; forces spread.visible to true regardless of whether layerState.ensemble_spread is false. Adjusting the opacity slider or receiving a spread-opacity-changed event visually un-mutes a layer that was explicitly disabled by the user."
    );
  } else {
    console.log("  ✓ setEnsembleSpreadOpacity respects layer visibility state");
  }
});

await testAsync("4.3 EMPIRICAL DEFECT CHECK: Event listener accumulation on repeated initLayers() (BUG-M2-003)", async () => {
  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);

  let warningEmitted = false;
  let warningMessage = '';
  const warningHandler = (w) => {
    if (w.name === 'MaxListenersExceededWarning') {
      warningEmitted = true;
      warningMessage = w.message;
    }
  };
  process.on('warning', warningHandler);

  for (let i = 0; i < 20; i++) {
    initLayers(globe, camera);
    disposeLayers();
  }

  // Allow Node process warning tick to resolve
  await new Promise(resolve => setTimeout(resolve, 50));
  process.off('warning', warningHandler);

  if (warningEmitted) {
    recordDefect(
      "BUG-M2-003",
      "Event listeners attached to studyData and DOM are not unsubscribed in disposeLayers()",
      `Lines 855-871: initLayers() registers anonymous event listeners with studyData.on('layer-toggled', ...), studyData.on('spread-opacity-changed', ...), and studyData.on('study-version-changed', ...). disposeLayers() does not call studyData.off() or removeEventListener. Repeated initialization leaks event listeners, triggering Node warning: "${warningMessage}".`
    );
  } else {
    console.log("  ✓ No event listener accumulation detected");
  }
});

// -----------------------------------------------------------------------------
// SUMMARY & VERDICT
// -----------------------------------------------------------------------------
console.log("\n===============================================================================");
console.log("ADVERSARIAL TEST SUMMARY");
console.log("===============================================================================");
console.log(`Passed:  ${passed}`);
console.log(`Failed:  ${failed}`);
console.log(`Defects Confirmed: ${defectsDiscovered.length}`);

if (defectsDiscovered.length > 0) {
  console.log("\nDiscovered Defects Summary Table:");
  defectsDiscovered.forEach((d, idx) => {
    console.log(`  ${idx + 1}. [${d.id}] ${d.title}`);
  });
}

console.log("===============================================================================\n");

if (failed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
