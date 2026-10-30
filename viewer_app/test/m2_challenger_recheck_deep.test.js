/**
 * m2_challenger_recheck_deep.test.js
 *
 * EMPIRICAL ADVERSARIAL CHALLENGER RECHECK SUITE (Milestone 2)
 * OD-EARTH2-001 / EO-OBSCURA 3D WebGL Digital Twin
 *
 * Exhaustive independent re-verification of:
 * 1. Coordinate Transformation Signs & Camera Navigation (Italy, Japan, WPAC, Prime Meridian, Equator, Poles)
 * 2. Raycasting on Invisible Layers (BUG-M2-001 regression tests, ancestor visibility traversal)
 * 3. Spread Opacity State Invariance (BUG-M2-002 regression tests, zero-culling, event preservation)
 * 4. Clean Lifecycle Disposal & Listener Leak Immunity (BUG-M2-003 regression tests, 50x loops)
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

let totalAssertions = 0;
let passedAssertions = 0;
let failedAssertions = 0;
const failures = [];

function assert(condition, message) {
  totalAssertions++;
  if (condition) {
    passedAssertions++;
    console.log(`    ✓ ${message}`);
  } else {
    failedAssertions++;
    failures.push(message);
    console.error(`    ✗ FAIL: ${message}`);
  }
}

function assertCloseTo(actual, expected, tolerance = 1e-4, message = '') {
  totalAssertions++;
  const diff = Math.abs(actual - expected);
  if (diff <= tolerance) {
    passedAssertions++;
    console.log(`    ✓ ${message} (${actual.toFixed(4)} ≈ ${expected.toFixed(4)})`);
  } else {
    failedAssertions++;
    const desc = `${message}: expected ${expected}, got ${actual} (diff ${diff} > tol ${tolerance})`;
    failures.push(desc);
    console.error(`    ✗ FAIL: ${desc}`);
  }
}

console.log('════════════════════════════════════════════════════════════════════════════════');
console.log('  OD-EARTH2-001 MILESTONE 2: CHALLENGER RECHECK ADVERSARIAL HARNESS');
console.log('════════════════════════════════════════════════════════════════════════════════\n');

// =============================================================================
// SUITE 1: COORDINATE TRANSFORMATION SIGNS & CAMERA NAVIGATION
// =============================================================================
console.log('▸ Suite 1: Coordinate Transformation Signs & Camera Navigation');

// 1.1 Canonical Reference Points (Prime Meridian, Equator, Poles, Antimeridian)
{
  console.log('  Subsuite 1.1: Canonical Texture Map Coordinates');
  const R = 5.0;

  // Prime Meridian at Equator (0°N, 0°E) -> u = 0.50 -> x = +R, y = 0, z = 0
  const pGreenwich = latLonToVector3(0, 0, R);
  assertCloseTo(pGreenwich.x, R, 1e-5, '0°N, 0°E (Greenwich) has x = +R');
  assertCloseTo(pGreenwich.y, 0.0, 1e-5, '0°N, 0°E (Greenwich) has y = 0');
  assertCloseTo(pGreenwich.z, 0.0, 1e-5, '0°N, 0°E (Greenwich) has z = 0');

  // 90°E at Equator -> u = 0.75 -> x = 0, y = 0, z = -R
  const p90E = latLonToVector3(0, 90, R);
  assertCloseTo(p90E.x, 0.0, 1e-5, '0°N, 90°E (Indian Ocean) has x = 0');
  assertCloseTo(p90E.y, 0.0, 1e-5, '0°N, 90°E (Indian Ocean) has y = 0');
  assertCloseTo(p90E.z, -R, 1e-5, '0°N, 90°E (Indian Ocean) has z = -R');

  // 180°E at Equator -> u = 1.00 / 0.00 -> x = -R, y = 0, z = 0
  const p180 = latLonToVector3(0, 180, R);
  assertCloseTo(p180.x, -R, 1e-5, '0°N, 180°E (Antimeridian) has x = -R');
  assertCloseTo(p180.y, 0.0, 1e-5, '0°N, 180°E (Antimeridian) has y = 0');
  assertCloseTo(p180.z, 0.0, 1e-5, '0°N, 180°E (Antimeridian) has z = 0');

  // 90°W at Equator -> u = 0.25 -> x = 0, y = 0, z = +R
  const p90W = latLonToVector3(0, -90, R);
  assertCloseTo(p90W.x, 0.0, 1e-5, '0°N, 90°W (Galapagos) has x = 0');
  assertCloseTo(p90W.y, 0.0, 1e-5, '0°N, 90°W (Galapagos) has y = 0');
  assertCloseTo(p90W.z, R, 1e-5, '0°N, 90°W (Galapagos) has z = +R');

  // North Pole (90°N) -> y = +R, x = 0, z = 0
  const pNorth = latLonToVector3(90, 0, R);
  assertCloseTo(pNorth.x, 0.0, 1e-5, '90°N (North Pole) has x = 0');
  assertCloseTo(pNorth.y, R, 1e-5, '90°N (North Pole) has y = +R');
  assertCloseTo(pNorth.z, 0.0, 1e-5, '90°N (North Pole) has z = 0');

  // South Pole (-90°N) -> y = -R, x = 0, z = 0
  const pSouth = latLonToVector3(-90, 0, R);
  assertCloseTo(pSouth.x, 0.0, 1e-5, '-90°N (South Pole) has x = 0');
  assertCloseTo(pSouth.y, -R, 1e-5, '-90°N (South Pole) has y = -R');
  assertCloseTo(pSouth.z, 0.0, 1e-5, '-90°N (South Pole) has z = 0');
}

// 1.2 Italy Navigation Rotation & Sounding Stations Front-Hemisphere Verification
{
  console.log('  Subsuite 1.2: Italy Synoptic Preset Navigation & Sounding Stations');
  const latItaly = 42;
  const lonItaly = 12;
  const camPos = new THREE.Vector3(0, 1.5, 8.5);
  const globeCenter = new THREE.Vector3(0, 0, 0);

  // Boresight rotation math from main.js / layers3D.js
  const rot = boresightRotation(latItaly, lonItaly);
  const expectedRotX = latItaly * (Math.PI / 180.0) * 0.4;
  const expectedRotY = -lonItaly * (Math.PI / 180.0) - Math.PI / 2.0;
  assertCloseTo(rot.rotX, expectedRotX, 1e-6, 'rotX equals lat * (PI/180) * 0.4');
  assertCloseTo(rot.rotY, expectedRotY, 1e-6, 'rotY equals -lon * (PI/180) - PI/2');

  const euler = new THREE.Euler(rot.rotX, rot.rotY, 0, 'XYZ');

  const stations = studyData.getDAStations();
  assert(stations.length === 4, 'StudyData provides 4 Italian DA stations');

  for (const st of stations) {
    const unrotated = latLonToVector3(st.lat, st.lon, RADIAL_SHELLS.DA_STATION_CAP);
    const rotated = unrotated.clone().applyEuler(euler);

    // Front hemisphere verification
    assert(rotated.z > 0, `${st.id} (${st.name}) has Z > 0 after Italy rotation (${rotated.z.toFixed(2)})`);
    
    // Dot product with outward normal to camera vector
    const outwardNormal = rotated.clone().normalize();
    const toCamera = camPos.clone().sub(rotated).normalize();
    const dot = outwardNormal.dot(toCamera);
    assert(dot > 0, `${st.id} outward normal dots positively with camera vector (dot = ${dot.toFixed(3)})`);

    const frontFacing = isFrontFacing(rotated, globeCenter, camPos);
    assert(frontFacing === true, `${st.id} evaluates isFrontFacing === true`);
  }
}

// 1.3 Japan Preset Navigation & Typhoon Waypoints Front-Hemisphere Verification
{
  console.log('  Subsuite 1.3: Japan Preset Navigation & WPAC Storm Waypoints');
  const latJapan = 36;
  const lonJapan = 138;
  const camPos = new THREE.Vector3(0, 1.5, 8.5);
  const globeCenter = new THREE.Vector3(0, 0, 0);

  const rot = boresightRotation(latJapan, lonJapan);
  const euler = new THREE.Euler(rot.rotX, rot.rotY, 0, 'XYZ');

  const waypoints = studyData.getCycloneWaypoints();
  assert(waypoints.length === 5, 'StudyData provides 5 cyclone waypoints');

  // Terminal waypoint WP-4 (landfall in Honshu, 35.8°N, 139.7°E)
  const wp4 = waypoints.find(w => w.id === 'WP-4');
  assert(Boolean(wp4), 'WP-4 waypoint exists');

  const unrotatedWp4 = latLonToVector3(wp4.lat, wp4.lon, RADIAL_SHELLS.CYCLONE_TUBE);
  const rotatedWp4 = unrotatedWp4.clone().applyEuler(euler);

  assert(rotatedWp4.z > 0, `WP-4 rotated to Japan has Z > 0 (${rotatedWp4.z.toFixed(2)})`);
  const frontFacingWp4 = isFrontFacing(rotatedWp4, globeCenter, camPos);
  assert(frontFacingWp4 === true, 'WP-4 evaluates isFrontFacing === true under Japan view');

  // Check initial waypoint WP-0 (genesis at 12.5°N, 144.8°E)
  const wp0 = waypoints.find(w => w.id === 'WP-0');
  const unrotatedWp0 = latLonToVector3(wp0.lat, wp0.lon, RADIAL_SHELLS.CYCLONE_TUBE);
  const rotatedWp0 = unrotatedWp0.clone().applyEuler(euler);
  assert(rotatedWp0.z > 0, `WP-0 rotated to Japan has Z > 0 (${rotatedWp0.z.toFixed(2)})`);
  assert(isFrontFacing(rotatedWp0, globeCenter, camPos) === true, 'WP-0 is front-facing under Japan synoptic view');
}

// =============================================================================
// SUITE 2: RAYCASTING ON INVISIBLE LAYERS (BUG-M2-001 REGRESSION)
// =============================================================================
console.log('\n▸ Suite 2: Raycasting on Invisible Layers (BUG-M2-001 Regression)');

{
  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 100);
  camera.position.set(0, 1.5, 8.5);
  camera.updateMatrixWorld(true);

  const mockRenderer = {
    domElement: {
      clientWidth: 1920,
      clientHeight: 1080,
      addEventListener: () => {},
      removeEventListener: () => {}
    }
  };

  const layersObj = initLayers(globe, camera, mockRenderer);
  const W = 1920;
  const H = 1080;

  // Rotate globe to Italy so DA stations are directly in front
  const rotItaly = boresightRotation(42, 12);
  globe.rotation.x = rotItaly.rotX;
  globe.rotation.y = rotItaly.rotY;
  globe.updateMatrixWorld(true);

  // 2.1 Raycast when da_stations layer is VISIBLE
  setLayerVisibility('da_stations', true);
  
  // Calculate Rome screen coordinates
  const romePos = latLonToVector3(41.8003, 12.2389, RADIAL_SHELLS.DA_STATION_CAP);
  romePos.applyEuler(new THREE.Euler(rotItaly.rotX, rotItaly.rotY, 0, 'XYZ'));
  const romeScreen = projectToScreen(romePos, camera, W, H);

  assert(romeScreen.visible === true, `Rome screen coordinate is visible on front hemisphere (${romeScreen.x}, ${romeScreen.y})`);

  const hitRomeVis = handleRaycast({ clientX: romeScreen.x, clientY: romeScreen.y }, camera, W, H);
  assert(Boolean(hitRomeVis), 'Raycast hits Rome sounding station when da_stations is visible');
  assert(hitRomeVis?.data?.id === 'LIRF', `Hit target corresponds to Rome Fiumicino (LIRF), got ${hitRomeVis?.data?.id}`);

  // 2.2 Raycast when da_stations layer is INVISIBLE
  setLayerVisibility('da_stations', false);
  const hitRomeInvis = handleRaycast({ clientX: romeScreen.x, clientY: romeScreen.y }, camera, W, H);
  assert(hitRomeInvis === null, 'Raycast returns NULL on Rome screen coordinate when da_stations is false');

  // Check all 4 Italian stations when invisible
  const stations = studyData.getDAStations();
  let allHiddenNull = true;
  for (const st of stations) {
    const p = latLonToVector3(st.lat, st.lon, RADIAL_SHELLS.DA_STATION_CAP);
    p.applyEuler(new THREE.Euler(rotItaly.rotX, rotItaly.rotY, 0, 'XYZ'));
    const scr = projectToScreen(p, camera, W, H);
    if (scr.visible) {
      const hit = handleRaycast({ clientX: scr.x, clientY: scr.y }, camera, W, H);
      if (hit !== null) allHiddenNull = false;
    }
  }
  assert(allHiddenNull, 'All 4 Italian stations return null when da_stations layer is hidden');

  // Re-enable da_stations and verify raycasting works again
  setLayerVisibility('da_stations', true);
  const hitRomeRestored = handleRaycast({ clientX: romeScreen.x, clientY: romeScreen.y }, camera, W, H);
  assert(hitRomeRestored?.data?.id === 'LIRF', 'Raycasting on Rome station works again after re-enabling da_stations');

  // 2.3 Cyclone layer visibility raycasting
  // Rotate to Japan for WP-4
  const rotJapan = boresightRotation(36, 138);
  globe.rotation.x = rotJapan.rotX;
  globe.rotation.y = rotJapan.rotY;
  globe.updateMatrixWorld(true);

  const wp4 = studyData.getCycloneWaypoints().find(w => w.id === 'WP-4');
  const wp4Pos = latLonToVector3(wp4.lat, wp4.lon, RADIAL_SHELLS.CYCLONE_TUBE);
  wp4Pos.applyEuler(new THREE.Euler(rotJapan.rotX, rotJapan.rotY, 0, 'XYZ'));
  const wp4Screen = projectToScreen(wp4Pos, camera, W, H);

  // With cyclone visible
  setLayerVisibility('cyclone', true);
  const hitWp4Vis = handleRaycast({ clientX: wp4Screen.x, clientY: wp4Screen.y }, camera, W, H);
  assert(Boolean(hitWp4Vis), 'Raycast hits WP-4 waypoint beacon when cyclone is visible');
  assert(hitWp4Vis?.data?.id === 'WP-4', `Hit target is WP-4, got ${hitWp4Vis?.data?.id}`);

  // With cyclone hidden
  setLayerVisibility('cyclone', false);
  const hitWp4Invis = handleRaycast({ clientX: wp4Screen.x, clientY: wp4Screen.y }, camera, W, H);
  assert(hitWp4Invis === null, 'Raycast returns NULL on WP-4 screen coordinate when cyclone is false');

  // Cleanup
  disposeLayers();
}

// =============================================================================
// SUITE 3: SPREAD OPACITY & VISIBILITY STATE (BUG-M2-002 REGRESSION)
// =============================================================================
console.log('\n▸ Suite 3: Ensemble Spread Opacity State (BUG-M2-002 Regression)');

{
  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  const layersObj = initLayers(globe, camera);
  const spreadMesh = layersObj.spreadMesh;

  // 3.1 Initial state with spread toggled OFF
  setLayerVisibility('ensemble_spread', false);
  assert(spreadMesh.visible === false, 'spreadMesh.visible is false when ensemble_spread is false');
  assert(getLayerState().activeLayers.ensemble_spread === false, 'getLayerState reports ensemble_spread: false');

  // 3.2 Change opacity while spread layer is disabled
  setEnsembleSpreadOpacity(0.85);
  assert(spreadMesh.visible === false, 'spreadMesh.visible remains FALSE after setEnsembleSpreadOpacity(0.85)');
  assert(getLayerState().spreadOpacity === 0.85, 'spreadOpacity uniform value updated to 0.85');
  assert(spreadMesh.material.uniforms.uOpacity.value === 0.85, 'Shader uniform uOpacity set to 0.85');

  // 3.3 Event bus emission of spread-opacity-changed while layer is disabled
  studyData.setSpreadOpacity(0.95);
  assert(spreadMesh.visible === false, 'spreadMesh.visible remains FALSE after studyData spread-opacity-changed event');
  assert(getLayerState().spreadOpacity === 0.95, 'spreadOpacity updated to 0.95 via event');

  // 3.4 Enable spread layer with positive opacity
  setLayerVisibility('ensemble_spread', true);
  assert(spreadMesh.visible === true, 'spreadMesh.visible becomes TRUE when ensemble_spread is enabled with opacity > 0');

  // 3.5 Zero opacity culling: opacity == 0 hides mesh even when layer is enabled
  setEnsembleSpreadOpacity(0.0);
  assert(spreadMesh.visible === false, 'spreadMesh.visible is FALSE when opacity is clamped to 0.0 (zero-culling)');

  // 3.6 Non-zero opacity restores visibility when layer is enabled
  setEnsembleSpreadOpacity(0.5);
  assert(spreadMesh.visible === true, 'spreadMesh.visible is restored to TRUE when opacity > 0.001');

  // 3.7 Study version change event maintaining spread state
  studyData.setActiveVersion('V2');
  assert(spreadMesh.visible === false, 'spreadMesh.visible is FALSE after study-version-changed sets activeLayers.ensemble_spread = false');

  // Cleanup
  disposeLayers();
}

// =============================================================================
// SUITE 4: CLEAN DISPOSAL & EVENT UNBINDING (BUG-M2-003 REGRESSION)
// =============================================================================
console.log('\n▸ Suite 4: Clean Disposal & Lifecycle Leak Immunity (BUG-M2-003 Regression)');

{
  let listenersAdded = 0;
  let listenersRemoved = 0;

  const mockRenderer = {
    domElement: {
      clientWidth: 1920,
      clientHeight: 1080,
      addEventListener: (type, handler) => {
        if (type === 'pointerdown') listenersAdded++;
      },
      removeEventListener: (type, handler) => {
        if (type === 'pointerdown') listenersRemoved++;
      }
    }
  };

  const globe = new THREE.Group();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);

  // 4.1 Single lifecycle verification
  initLayers(globe, camera, mockRenderer);
  assert(listenersAdded === 1, 'pointerdown listener added to renderer.domElement on initLayers');

  disposeLayers();
  assert(listenersRemoved === 1, 'pointerdown listener removed from renderer.domElement on disposeLayers');
  assert(getInteractiveObjects().length === 0, 'pickableObjects array cleared on disposeLayers');
  const layersAfterDispose = getLayers();
  assert(layersAfterDispose.cyclone === null && layersAfterDispose.da === null, 'Layer group references set to null on dispose');

  // 4.2 Idempotent double-dispose
  let doubleDisposeThrew = false;
  try {
    disposeLayers();
    disposeLayers();
  } catch (err) {
    doubleDisposeThrew = true;
  }
  assert(!doubleDisposeThrew, 'Consecutive disposeLayers calls are idempotent and do not throw');

  // 4.3 50x repeated init/dispose loop without Node MaxListeners warnings
  const warnings = [];
  const origEmitWarning = process.emitWarning;
  process.emitWarning = (warning, ...args) => {
    warnings.push(typeof warning === 'string' ? warning : warning?.message);
    return origEmitWarning.call(process, warning, ...args);
  };

  listenersAdded = 0;
  listenersRemoved = 0;

  for (let i = 0; i < 50; i++) {
    const loopGlobe = new THREE.Group();
    initLayers(loopGlobe, camera, mockRenderer);
    disposeLayers();
  }

  process.emitWarning = origEmitWarning;

  assert(listenersAdded === 50, '50 pointerdown listeners added across 50 iterations');
  assert(listenersRemoved === 50, '50 pointerdown listeners removed across 50 iterations (0 net leak)');
  assert(warnings.length === 0, `Zero Node MaxListeners warnings emitted during 50 iterations (got ${warnings.length})`);

  // 4.4 Functional re-initialization after 50 dispose cycles
  const finalGlobe = new THREE.Group();
  const finalLayers = initLayers(finalGlobe, camera, mockRenderer);
  assert(Boolean(finalLayers.cycloneGroup), 'Cyclone group created successfully on post-stress initLayers');
  assert(Boolean(finalLayers.daGroup), 'DA group created successfully on post-stress initLayers');
  assert(getInteractiveObjects().length === 9, 'Interactive objects pool populated with 9 items (5 waypoints + 4 station caps)');

  disposeLayers();
  assert(getInteractiveObjects().length === 0, 'Interactive objects pool cleared after final disposal');
}

// =============================================================================
// SUMMARY REPORT
// =============================================================================
console.log('\n════════════════════════════════════════════════════════════════════════════════');
console.log('  CHALLENGER RECHECK ADVERSARIAL HARNESS RESULTS');
console.log('════════════════════════════════════════════════════════════════════════════════');
console.log(`  Total Assertions:  ${totalAssertions}`);
console.log(`  Passed:            ${passedAssertions}`);
console.log(`  Failed:            ${failedAssertions}`);

if (failedAssertions > 0) {
  console.error('\n  FAILURES ENCOUNTERED:');
  failures.forEach((f, idx) => console.error(`    [${idx + 1}] ${f}`));
  process.exit(1);
} else {
  console.log('\n  ALL ADVERSARIAL RECHECK ASSERTIONS PASSED CLEANLY.');
  process.exit(0);
}
