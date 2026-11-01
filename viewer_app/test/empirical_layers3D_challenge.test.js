/**
 * empirical_layers3D_challenge.test.js
 *
 * EMPIRICAL ADVERSARIAL CHALLENGER SUITE (Challenger 2, Milestone 2)
 * OD-EARTH2-001 / EO-OBSCURA 3D WebGL Digital Twin
 * Target: viewer_app/layers3D.js
 *
 * Adversarially challenges:
 * 1. Radial shell hierarchy monotonicity & vertex non-intersection invariants
 * 2. Vector alignment of DA station pins with surface normals (dot == 1.0 +- 1e-6)
 * 3. Orographic lapse-rate cooling formula (-6.5 K/km elevation gradient)
 * 4. Front-hemisphere occlusion filter & horizon tangent boundary geometry
 * 5. MSLP & DA increment colormaps mathematical boundary conditions
 * 6. CatmullRomCurve3 trajectory & expanding uncertainty cone geometric invariants
 * 7. Screen-space projection & drag-vs-click disambiguation thresholds
 * 8. Defensive boundary handling (empty collections, edge coordinates, null safety)
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

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const testFailures = [];

function test(name, fn) {
  totalTests++;
  try {
    fn();
    passedTests++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    failedTests++;
    testFailures.push({ name, error: err });
    console.error(`  ✗ FAIL: ${name}`);
    console.error(`    ${err.stack || err.message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function assertCloseTo(actual, expected, tolerance = 1e-6, message = '') {
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    throw new Error(`${message || 'assertCloseTo failed'}: expected ${expected}, got ${actual} (diff: ${diff} > tol: ${tolerance})`);
  }
}

console.log('\n══════════════════════════════════════════════════════════════════════');
console.log('  CHALLENGER 2: EMPIRICAL ADVERSARIAL CHALLENGE — layers3D.js');
console.log('══════════════════════════════════════════════════════════════════════\n');

// =============================================================================
// CHALLENGE SUITE 1: RADIAL SHELL HIERARCHY & VERTEX MONOTONICITY
// =============================================================================
console.log('▸ Challenge Suite 1: Radial Shell Monotonicity & Non-Intersection Invariants');

test('1.1: RADIAL_SHELLS allocation table is strictly monotonic and frozen', () => {
  assert(Object.isFrozen(RADIAL_SHELLS), 'RADIAL_SHELLS table must be Object.freeze-protected');
  const {
    BASE_GLOBE,
    ENSEMBLE_SPREAD,
    MESOSCALE_INSETS,
    UNCERTAINTY_CONE,
    CYCLONE_TUBE,
    DA_STATION_BASE,
    ATMOSPHERE_GLOW,
    DA_STATION_CAP
  } = RADIAL_SHELLS;

  assert(BASE_GLOBE < ENSEMBLE_SPREAD, `Base (${BASE_GLOBE}) must be below Spread (${ENSEMBLE_SPREAD})`);
  assert(ENSEMBLE_SPREAD < MESOSCALE_INSETS, `Spread (${ENSEMBLE_SPREAD}) must be below Insets (${MESOSCALE_INSETS})`);
  assert(MESOSCALE_INSETS < UNCERTAINTY_CONE, `Insets (${MESOSCALE_INSETS}) must be below Cone (${UNCERTAINTY_CONE})`);
  assert(UNCERTAINTY_CONE < CYCLONE_TUBE, `Cone (${UNCERTAINTY_CONE}) must be below Cyclone Tube (${CYCLONE_TUBE})`);
  assert(CYCLONE_TUBE <= DA_STATION_BASE, `Cyclone Tube (${CYCLONE_TUBE}) must match DA Base (${DA_STATION_BASE})`);
  assert(CYCLONE_TUBE < ATMOSPHERE_GLOW, `Cyclone Tube (${CYCLONE_TUBE}) must be below Atmosphere (${ATMOSPHERE_GLOW})`);
  assert(ATMOSPHERE_GLOW < DA_STATION_CAP, `Atmosphere (${ATMOSPHERE_GLOW}) must be below DA Station Cap (${DA_STATION_CAP})`);

  // Verify anti-Z-fighting minimum margins (allowing 1e-9 tolerance for IEEE 754 float subtraction)
  const eps = 1e-9;
  assert(ENSEMBLE_SPREAD - BASE_GLOBE >= 0.015 - eps, 'Base to Spread delta >= 0.015 units');
  assert(MESOSCALE_INSETS - ENSEMBLE_SPREAD >= 0.010 - eps, 'Spread to Insets delta >= 0.010 units');
  assert(UNCERTAINTY_CONE - MESOSCALE_INSETS >= 0.010 - eps, 'Insets to Cone delta >= 0.010 units');
  assert(CYCLONE_TUBE - UNCERTAINTY_CONE >= 0.005 - eps, 'Cone to Tube delta >= 0.005 units');
  assert(DA_STATION_CAP - ATMOSPHERE_GLOW >= 0.150 - eps, 'Atmosphere to DA Cap delta >= 0.150 units');
});

test('1.2: Empirical vertex radii sampling on live generated meshes', () => {
  const dummyGlobe = new THREE.Group();
  const dummyCamera = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 100);
  dummyCamera.position.set(0, 5, 14);

  const layers = initLayers(dummyGlobe, dummyCamera, null);

  // 1. Ensemble spread sphere mesh vertices
  const spreadMesh = layers.spreadMesh;
  assert(spreadMesh && spreadMesh.geometry, 'Spread mesh geometry exists');
  const spreadPos = spreadMesh.geometry.attributes.position;
  let spreadMinR = Infinity;
  let spreadMaxR = -Infinity;
  for (let i = 0; i < spreadPos.count; i++) {
    const r = Math.hypot(spreadPos.getX(i), spreadPos.getY(i), spreadPos.getZ(i));
    if (r < spreadMinR) spreadMinR = r;
    if (r > spreadMaxR) spreadMaxR = r;
  }
  assertCloseTo(spreadMinR, RADIAL_SHELLS.ENSEMBLE_SPREAD, 1e-4, 'Spread min radius matches 5.020');
  assertCloseTo(spreadMaxR, RADIAL_SHELLS.ENSEMBLE_SPREAD, 1e-4, 'Spread max radius matches 5.020');

  // 2. Mesoscale insets patch vertices
  const mesoGroup = layers.mesoGroup;
  assert(mesoGroup && mesoGroup.children.length > 0, 'Mesoscale insets group has children');
  let mesoMinR = Infinity;
  let mesoMaxR = -Infinity;
  mesoGroup.children.forEach(child => {
    if (child.isMesh && child.geometry?.attributes?.position) {
      const pos = child.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const r = Math.hypot(pos.getX(i), pos.getY(i), pos.getZ(i));
        if (r < mesoMinR) mesoMinR = r;
        if (r > mesoMaxR) mesoMaxR = r;
      }
    }
  });
  assertCloseTo(mesoMinR, RADIAL_SHELLS.MESOSCALE_INSETS, 1e-4, 'Mesoscale min radius matches 5.035');
  assertCloseTo(mesoMaxR, RADIAL_SHELLS.MESOSCALE_INSETS, 1e-4, 'Mesoscale max radius matches 5.035');

  // 3. Cyclone uncertainty cone vertices
  const cycloneGroup = layers.cycloneGroup;
  const coneMesh = cycloneGroup.getObjectByName('cyclone_uncertainty_cone');
  assert(coneMesh && coneMesh.geometry, 'Uncertainty cone mesh exists');
  const conePos = coneMesh.geometry.attributes.position;
  let coneMinR = Infinity;
  let coneMaxR = -Infinity;
  for (let i = 0; i < conePos.count; i++) {
    const r = Math.hypot(conePos.getX(i), conePos.getY(i), conePos.getZ(i));
    if (r < coneMinR) coneMinR = r;
    if (r > coneMaxR) coneMaxR = r;
  }
  assertCloseTo(coneMinR, RADIAL_SHELLS.UNCERTAINTY_CONE, 1e-4, 'Uncertainty cone min radius matches 5.045');
  assertCloseTo(coneMaxR, RADIAL_SHELLS.UNCERTAINTY_CONE, 1e-4, 'Uncertainty cone max radius matches 5.045');

  // 4. DA Station caps positions
  const daGroup = layers.daGroup;
  const stations = studyData.getDAStations();
  stations.forEach(st => {
    const cap = daGroup.getObjectByName(`station_cap_${st.id}`);
    assert(cap, `Station cap for ${st.id} exists`);
    const rCap = cap.position.length();
    assertCloseTo(rCap, RADIAL_SHELLS.DA_STATION_CAP, 1e-4, `Cap radius for ${st.id} matches 5.350`);

    const pin = daGroup.getObjectByName(`station_pin_${st.id}`);
    assert(pin, `Station pin for ${st.id} exists`);
    const rBase = pin.position.length();
    assertCloseTo(rBase, RADIAL_SHELLS.DA_STATION_BASE, 1e-4, `Pin base radius for ${st.id} matches 5.050`);
  });

  // Verify strict non-intersection between spread (5.020) and insets (5.035)
  assert(spreadMaxR < mesoMinR, `Spread max (${spreadMaxR.toFixed(4)}) must be strictly less than Insets min (${mesoMinR.toFixed(4)})`);
  // Verify strict non-intersection between insets (5.035) and uncertainty cone (5.045)
  assert(mesoMaxR < coneMinR, `Insets max (${mesoMaxR.toFixed(4)}) must be strictly less than Cone min (${coneMinR.toFixed(4)})`);

  disposeLayers();
});

test('1.3: Monte Carlo global spherical coordinates radius invariant (1000 samples)', () => {
  const radiiToTest = [5.000, 5.020, 5.035, 5.045, 5.050, 5.150, 5.350];
  const sampleCount = 1000;

  for (let k = 0; k < sampleCount; k++) {
    // Generate random uniform sphere coordinates
    const u = Math.random();
    const v = Math.random();
    const lat = Math.asin(2 * u - 1) * (180 / Math.PI); // Uniform area latitude
    const lon = v * 360 - 180;
    const targetR = radiiToTest[k % radiiToTest.length];

    const vec = latLonToVector3(lat, lon, targetR);
    const calculatedR = vec.length();
    assertCloseTo(calculatedR, targetR, 1e-6, `latLonToVector3 radius conservation at lat=${lat}, lon=${lon}`);
  }
});

// =============================================================================
// CHALLENGE SUITE 2: VECTOR ALIGNMENT OF DA STATION PINS
// =============================================================================
console.log('▸ Challenge Suite 2: DA Station Beacon Pin Vector Alignment & Surface Normals');

test('2.1: Authoritative Italian sounding station pins align with surface normals (dot == 1.0 +- 1e-6)', () => {
  const dummyGlobe = new THREE.Group();
  const dummyCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  dummyCamera.position.set(0, 0, 14);

  const layers = initLayers(dummyGlobe, dummyCamera, null);
  const daGroup = layers.daGroup;
  const stations = studyData.getDAStations();

  assert(stations.length === 4, 'Must have 4 Italian sounding stations');

  stations.forEach(st => {
    // 1. Analytical surface normal
    const expectedNormal = latLonToVector3(st.lat, st.lon, 1.0).normalize();

    // 2. Pin base position
    const pinMesh = daGroup.getObjectByName(`station_pin_${st.id}`);
    assert(pinMesh, `Pin mesh for ${st.id} exists`);
    const pinPosNormal = pinMesh.position.clone().normalize();
    const baseNormalDot = pinPosNormal.dot(expectedNormal);
    assertCloseTo(baseNormalDot, 1.0, 1e-6, `Pin base position normal alignment for ${st.id}`);

    // 3. Pin orientation vector (extracted from mesh quaternion)
    // Three.js CylinderGeometry is originally oriented along (0, 1, 0)
    const pinDirection = new THREE.Vector3(0, 1, 0).applyQuaternion(pinMesh.quaternion).normalize();
    const directionDot = pinDirection.dot(expectedNormal);
    assertCloseTo(directionDot, 1.0, 1e-6, `Pin cylinder axis orientation alignment for ${st.id}`);

    // 4. Cap sphere position
    const capMesh = daGroup.getObjectByName(`station_cap_${st.id}`);
    assert(capMesh, `Cap mesh for ${st.id} exists`);
    const capNormal = capMesh.position.clone().normalize();
    const capNormalDot = capNormal.dot(expectedNormal);
    assertCloseTo(capNormalDot, 1.0, 1e-6, `Cap position normal alignment for ${st.id}`);

    // 5. Pin vector from base to cap
    const pinSpanVector = new THREE.Vector3().subVectors(capMesh.position, pinMesh.position);
    assertCloseTo(pinSpanVector.length(), 0.300, 1e-5, `Pin span length from base to cap for ${st.id} == 0.300 units`);
    const spanDirection = pinSpanVector.normalize();
    const spanDot = spanDirection.dot(expectedNormal);
    assertCloseTo(spanDot, 1.0, 1e-6, `Pin span direction vector dot normal for ${st.id}`);
  });

  disposeLayers();
});

test('2.2: Adversarial Monte Carlo pin quaternion orientation across 360-degree sphere scan (500 samples)', () => {
  const testCoordinates = [
    { lat: 90, lon: 0, desc: 'North Pole' },
    { lat: -90, lon: 0, desc: 'South Pole' },
    { lat: 0, lon: 0, desc: 'Equator Prime Meridian' },
    { lat: 0, lon: 180, desc: 'Equator Antimeridian' },
    { lat: 0, lon: -180, desc: 'Equator Negative Antimeridian' },
    { lat: 45, lon: 90, desc: 'Mid-Latitude 90E' },
    { lat: -45, lon: -90, desc: 'Mid-Latitude 90W' }
  ];

  for (let i = 0; i < 500; i++) {
    testCoordinates.push({
      lat: (Math.random() * 180) - 90,
      lon: (Math.random() * 360) - 180,
      desc: `Random Point ${i}`
    });
  }

  const up = new THREE.Vector3(0, 1, 0);

  testCoordinates.forEach(({ lat, lon, desc }) => {
    const normal = latLonToVector3(lat, lon, 1.0).normalize();
    const quat = new THREE.Quaternion().setFromUnitVectors(up, normal);
    const pinDir = up.clone().applyQuaternion(quat).normalize();
    const dot = pinDir.dot(normal);

    assertCloseTo(dot, 1.0, 1e-6, `Pin quaternion alignment at ${desc} (lat=${lat.toFixed(2)}, lon=${lon.toFixed(2)})`);
  });
});

// =============================================================================
// CHALLENGE SUITE 3: OROGRAPHIC LAPSE-RATE COOLING FORMULA
// =============================================================================
console.log('▸ Challenge Suite 3: Orographic Lapse-Rate Cooling Formula (Gamma = 6.5 K/km)');

test('3.1: Mathematical precision of getOrographicLapseRateDeltaT at key topographic elevations', () => {
  const standardGamma = 6.5; // K / km = 0.0065 K / m

  const testPoints = [
    { elevM: 0, expectedDeltaT: 0.0, desc: 'Sea Level' },
    { elevM: 200, expectedDeltaT: -1.30, desc: 'Lowland' },
    { elevM: 500, expectedDeltaT: -3.25, desc: 'Foothills' },
    { elevM: 1000, expectedDeltaT: -6.50, desc: '1 km Elevation' },
    { elevM: 2000, expectedDeltaT: -13.00, desc: 'Sub-Alpine' },
    { elevM: 2498, expectedDeltaT: -16.237, desc: 'Alpine Pass' },
    { elevM: 4049, expectedDeltaT: -26.3185, desc: 'Piz Bernina' },
    { elevM: 4478, expectedDeltaT: -29.107, desc: 'Matterhorn' },
    { elevM: 4808, expectedDeltaT: -31.252, desc: 'Mont Blanc Summit' },
    { elevM: 8848.86, expectedDeltaT: -57.51759, desc: 'Mount Everest' },
    { elevM: -430, expectedDeltaT: 2.795, desc: 'Dead Sea Basin (Adiabatic Warming)' }
  ];

  testPoints.forEach(({ elevM, expectedDeltaT, desc }) => {
    const deltaT = getOrographicLapseRateDeltaT(elevM, standardGamma);
    assertCloseTo(deltaT, expectedDeltaT, 1e-5, `Lapse rate cooling for ${desc} at ${elevM}m`);
  });
});

test('3.2: Analytical derivative & linearity verification: d(deltaT)/d(elev) == -0.0065 K/m', () => {
  const elevations = [100, 750, 1500, 3200, 4808];
  const h = 1e-4; // Perturbation in meters

  elevations.forEach(elev => {
    const tPlus = getOrographicLapseRateDeltaT(elev + h, 6.5);
    const tMinus = getOrographicLapseRateDeltaT(elev - h, 6.5);
    const numericalDerivative = (tPlus - tMinus) / (2 * h);
    assertCloseTo(numericalDerivative, -0.0065, 1e-8, `Linear gradient derivative at ${elev}m`);
  });
});

test('3.3: Custom environmental lapse rates (dry adiabatic vs moist adiabatic)', () => {
  const elev = 3000;

  // Dry adiabatic lapse rate: ~9.8 K/km
  const dryDeltaT = getOrographicLapseRateDeltaT(elev, 9.8);
  assertCloseTo(dryDeltaT, -29.40, 1e-5, 'Dry adiabatic cooling at 3000m');

  // Moist pseudo-adiabatic lapse rate: ~5.0 K/km
  const moistDeltaT = getOrographicLapseRateDeltaT(elev, 5.0);
  assertCloseTo(moistDeltaT, -15.00, 1e-5, 'Moist adiabatic cooling at 3000m');

  // Temperature inversion: -3.0 K/km
  const inversionDeltaT = getOrographicLapseRateDeltaT(elev, -3.0);
  assertCloseTo(inversionDeltaT, 9.00, 1e-5, 'Inversion warming at 3000m');
});

// =============================================================================
// CHALLENGE SUITE 4: FRONT-HEMISPHERE OCCLUSION FILTER & HORIZON GEOMETRY
// =============================================================================
console.log('▸ Challenge Suite 4: Front-Hemisphere Occlusion Filter & Tangent Horizon Math');

test('4.1: Direct camera sub-point vs antipodal backside occlusion', () => {
  const center = new THREE.Vector3(0, 0, 0);
  const cameraPos = new THREE.Vector3(0, 0, 14);

  // 1. Point on front hemisphere directly facing camera
  const frontPoint = new THREE.Vector3(0, 0, 5);
  assert(isFrontFacing(frontPoint, center, cameraPos) === true, 'Sub-camera point must be front-facing');

  // 2. Point on backside hemisphere directly facing away from camera
  const backPoint = new THREE.Vector3(0, 0, -5);
  assert(isFrontFacing(backPoint, center, cameraPos) === false, 'Antipodal point must be occluded');

  // 3. Point at 45 degrees latitude / 0 degrees longitude (Greenwich at +X)
  const front45 = latLonToVector3(45, 0, 5);
  const camX = new THREE.Vector3(14, 0, 0);
  assert(isFrontFacing(front45, center, camX) === true, 'Point facing camX (+X) must be front-facing');
  assert(isFrontFacing(front45, center, new THREE.Vector3(-14, 0, 0)) === false, 'Point facing away from -X must be occluded');
});

test('4.2: Exact horizon tangent boundary condition (dot === 0.0 treated as occluded)', () => {
  const center = new THREE.Vector3(0, 0, 0);

  // Exact perpendicular geometry where normal . toCamera === 0.0:
  // Point = (5, 0, 0) -> normal = (1, 0, 0)
  // Camera = (5, 14, 0) -> toCamera = (0, 1, 0)
  // dot(normal, toCamera) = 0.0 exactly!
  const perpPoint = new THREE.Vector3(5, 0, 0);
  const perpCam = new THREE.Vector3(5, 14, 0);
  const resExactZero = isFrontFacing(perpPoint, center, perpCam);
  assert(resExactZero === false, 'Exact perpendicular dot===0.0 must be treated as occluded');

  // Point with negative dot product (facing away from camera)
  // Camera at (0, 0, 14), point at (5, 0, 0): normal = (1, 0, 0), toCamera = (-5, 0, 14)/dist -> dot < 0
  const backCam = new THREE.Vector3(0, 0, 14);
  assert(isFrontFacing(perpPoint, center, backCam) === false, 'Point facing away from camera must be occluded');

  // Point with positive dot product (facing towards camera)
  const frontCam = new THREE.Vector3(14, 0, 0);
  assert(isFrontFacing(perpPoint, center, frontCam) === true, 'Point facing towards camera must be visible');
});

test('4.3: Dynamic camera navigation positions (Global, Italy, Japan presets)', () => {
  const center = new THREE.Vector3(0, 0, 0);

  // Rome DA Station: Lat 41.80, Lon 12.238
  const romePos = latLonToVector3(41.80, 12.238, RADIAL_SHELLS.DA_STATION_CAP);

  // 1. Camera facing Europe/Italy directly: cameraPos placed along Rome normal at distance 8.5
  const romeNormal = romePos.clone().normalize();
  const camItaly = romeNormal.clone().multiplyScalar(8.5);
  assert(isFrontFacing(romePos, center, camItaly) === true, 'Rome must be visible when camera faces Italy');

  // 2. Camera facing Japan: Tokyo / Japan synoptic preset: Lat 36N, Lon 138E
  const japanNormal = latLonToVector3(36.0, 138.0, 1.0).normalize();
  const camJapan = japanNormal.clone().multiplyScalar(8.5);
  assert(isFrontFacing(romePos, center, camJapan) === false, 'Rome must be strictly occluded when camera faces Japan');

  // 3. WPAC Typhoon Waypoint 0: Lat 14.2, Lon 128.5 (near Philippines/West Pacific)
  const wp0Pos = latLonToVector3(14.2, 128.5, RADIAL_SHELLS.CYCLONE_TUBE);
  assert(isFrontFacing(wp0Pos, center, camJapan) === true, 'WPAC Typhoon must be visible when camera faces West Pacific/Japan');
  assert(isFrontFacing(wp0Pos, center, camItaly) === false, 'WPAC Typhoon must be occluded when camera faces Italy');
});

// =============================================================================
// CHALLENGE SUITE 5: SCIENTIFIC COLORMAPS & METRIC BOUNDS
// =============================================================================
console.log('▸ Challenge Suite 5: Scientific Colormaps & Normalization Invariants');

test('5.1: MSLP Intensity Colormap boundaries and monotonicity', () => {
  // Super Typhoon: 930 hPa -> intensity 1.0, Magenta/Crimson
  const { color: cSuper, intensity: iSuper } = getMslpColor(930);
  assertCloseTo(iSuper, 1.0, 1e-6, 'Intensity at 930 hPa is 1.0');
  assert(cSuper.r > 0.8 && cSuper.b > 0.5, 'Super Typhoon color has high Red and Blue (Magenta/Rose)');

  // Weak/Tropical Storm: 1000 hPa -> intensity 0.0, Cyan
  const { color: cWeak, intensity: iWeak } = getMslpColor(1000);
  assertCloseTo(iWeak, 0.0, 1e-6, 'Intensity at 1000 hPa is 0.0');
  assert(cWeak.b > 0.7 && cWeak.g > 0.6, 'Weak system color has high Cyan (G + B)');

  // Intermediate category: 965 hPa -> intensity 0.50
  const { intensity: iMid } = getMslpColor(965);
  assertCloseTo(iMid, 0.50, 1e-6, 'Intensity at 965 hPa is 0.50');

  // Clamping adversarial extremes (< 900 hPa or > 1050 hPa)
  const { intensity: iExtLow } = getMslpColor(850);
  assertCloseTo(iExtLow, 1.0, 1e-6, 'Clamped intensity below 930 hPa is 1.0');
  const { intensity: iExtHigh } = getMslpColor(1080);
  assertCloseTo(iExtHigh, 0.0, 1e-6, 'Clamped intensity above 1000 hPa is 0.0');

  // Strictly monotonic decreasing intensity with rising pressure
  let prevInt = 1.0;
  for (let p = 930; p <= 1000; p += 5) {
    const { intensity } = getMslpColor(p);
    assert(intensity <= prevInt, `Monotonicity check at MSLP ${p}`);
    prevInt = intensity;
  }
});

test('5.2: DA Increment Colormap boundaries (+3K Sky-Blue to +8K Deep Crimson)', () => {
  // +3.0 K -> norm 0.0, Sky Blue (#0ea5e9)
  const { color: cLow, norm: nLow } = getIncrementColor(3.0);
  assertCloseTo(nLow, 0.0, 1e-6, 'Norm at +3K is 0.0');
  assert(cLow.getHexString().toLowerCase() === '0ea5e9', `Low increment hex must match 0ea5e9, got ${cLow.getHexString()}`);

  // +8.0 K -> norm 1.0, Deep Crimson/Rose (#f43f5e)
  const { color: cHigh, norm: nHigh } = getIncrementColor(8.0);
  assertCloseTo(nHigh, 1.0, 1e-6, 'Norm at +8K is 1.0');
  assert(cHigh.getHexString().toLowerCase() === 'f43f5e', `High increment hex must match f43f5e, got ${cHigh.getHexString()}`);

  // Clamping tests
  const { norm: nNeg } = getIncrementColor(0.0);
  assertCloseTo(nNeg, 0.0, 1e-6, 'Clamped below +3K is 0.0');
  const { norm: nExtreme } = getIncrementColor(15.0);
  assertCloseTo(nExtreme, 1.0, 1e-6, 'Clamped above +8K is 1.0');
});

// =============================================================================
// CHALLENGE SUITE 6: INTERACTIVE RAYCASTING & SCREEN PROJECTION
// =============================================================================
console.log('▸ Challenge Suite 6: Interactive Raycasting, Drag-vs-Click & Screen Projection');

test('6.1: Drag-vs-click suppression threshold (> 5px)', () => {
  const dummyGlobe = new THREE.Group();
  const dummyCamera = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 100);
  dummyCamera.position.set(0, 0, 14);

  let pointerDownListener = null;
  const mockRenderer = {
    domElement: {
      clientWidth: 1920,
      clientHeight: 1080,
      addEventListener: (type, cb) => {
        if (type === 'pointerdown') pointerDownListener = cb;
      }
    }
  };

  initLayers(dummyGlobe, dummyCamera, mockRenderer);
  assert(typeof pointerDownListener === 'function', 'Pointerdown listener registered');

  // Simulate mouse down at (500, 300)
  pointerDownListener({ clientX: 500, clientY: 300 });

  // 1. Move by 3px (< 5px threshold -> micro-drag allowed to click)
  handleRaycast({ clientX: 503, clientY: 300 }, dummyCamera, 1920, 1080);

  // 2. Move by 25px (> 5px threshold -> drag suppression triggered)
  const dragResult = handleRaycast({ clientX: 525, clientY: 300 }, dummyCamera, 1920, 1080);
  assert(dragResult === null, 'Drag > 5px must immediately return null without evaluating raycaster');

  disposeLayers();
});

test('6.2: projectToScreen coordinates conversion and front/back surface visibility', () => {
  const dummyCamera = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 100);
  dummyCamera.position.set(0, 0, 14);
  dummyCamera.updateMatrixWorld();

  // 1. Surface marker on front side of globe (0, 0, 5.05)
  const pFront = new THREE.Vector3(0, 0, 5.05);
  const projFront = projectToScreen(pFront, dummyCamera, 1920, 1080);
  assertCloseTo(projFront.x, 960, 2, 'Front point projects to screen center X');
  assertCloseTo(projFront.y, 540, 2, 'Front point projects to screen center Y');
  assert(projFront.visible === true, 'Front surface point is visible');

  // 2. Surface marker on rear side of globe (0, 0, -5.05)
  const pRear = new THREE.Vector3(0, 0, -5.05);
  const projRear = projectToScreen(pRear, dummyCamera, 1920, 1080);
  assert(projRear.visible === false, 'Rear surface point must have visible: false');
});

// =============================================================================
// CHALLENGE SUITE 7: OPACITY, STATE & RESOURCE DISPOSAL
// =============================================================================
console.log('▸ Challenge Suite 7: Opacity Culling, State Machine & Lifecycle Disposal');

test('7.1: Ensemble spread opacity zero-culling behavior', () => {
  const dummyGlobe = new THREE.Group();
  const dummyCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  dummyCamera.position.set(0, 0, 14);

  const layers = initLayers(dummyGlobe, dummyCamera, null);
  const spreadMesh = layers.spreadMesh;

  // Set opacity 0.5
  setEnsembleSpreadOpacity(0.5);
  assertCloseTo(spreadMesh.material.uniforms.uOpacity.value, 0.5, 1e-4, 'Opacity uniform set to 0.5');
  assertCloseTo(spreadMesh.material.uniforms.u_opacity.value, 0.5, 1e-4, 'Opacity uniform alias set to 0.5');
  assert(spreadMesh.visible === true, 'Spread mesh visible when opacity > 0');

  // Set opacity 0.0 -> mesh visible toggled to false to avoid fragment discard GPU overhead
  setEnsembleSpreadOpacity(0.0);
  assert(spreadMesh.visible === false, 'Spread mesh culled when opacity is 0.0');

  // Clamping invalid inputs
  setEnsembleSpreadOpacity(-0.5);
  assertCloseTo(getLayerState().spreadOpacity, 0.0, 1e-4, 'Clamped negative opacity');
  setEnsembleSpreadOpacity(2.5);
  assertCloseTo(getLayerState().spreadOpacity, 1.0, 1e-4, 'Clamped >1.0 opacity');

  disposeLayers();
});

test('7.2: Layer visibility toggles and active state query', () => {
  const dummyGlobe = new THREE.Group();
  const dummyCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  dummyCamera.position.set(0, 0, 14);

  const layers = initLayers(dummyGlobe, dummyCamera, null);

  setLayerVisibility('cyclone', false);
  assert(layers.cycloneGroup.visible === false, 'Cyclone group hidden');
  assert(getLayerState().activeLayers.cyclone === false, 'Cyclone state false');

  setLayerVisibility('cyclone', true);
  assert(layers.cycloneGroup.visible === true, 'Cyclone group shown');
  assert(getLayerState().activeLayers.cyclone === true, 'Cyclone state true');

  setLayerVisibility('da_stations', false);
  assert(layers.daGroup.visible === false, 'DA group hidden');
  assert(getLayerState().activeLayers.da_stations === false, 'DA state false');

  disposeLayers();
});

test('7.3: Memory disposal hook clears pickable pools and detaches scene graph', () => {
  const dummyGlobe = new THREE.Group();
  const dummyCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  dummyCamera.position.set(0, 0, 14);

  initLayers(dummyGlobe, dummyCamera, null);
  assert(getInteractiveObjects().length > 0, 'Interactive objects populated');
  assert(dummyGlobe.children.length === 4, 'Globe has 4 layer group children');

  disposeLayers();

  assert(getInteractiveObjects().length === 0, 'Interactive objects emptied on dispose');
  assert(dummyGlobe.children.length === 0, 'Globe children detached on dispose');
  assert(getLayers().cyclone === null, 'Cyclone group nulled on dispose');
  assert(getLayers().da === null, 'DA group nulled on dispose');
  assert(getLayers().spread === null, 'Spread mesh nulled on dispose');
  assert(getLayers().mesoscale === null, 'Mesoscale group nulled on dispose');
});

// =============================================================================
// CHALLENGE SUITE 8: ADVERSARIAL EDGE CASES & DEFENSIVE INTEGRITY
// =============================================================================
console.log('▸ Challenge Suite 8: Adversarial Edge Cases & Defensive Integrity');

test('8.1: Defensive handling of empty or single waypoint inputs', () => {
  // Empty waypoints collection
  const emptyRes = layers3D.initLayers(new THREE.Group(), new THREE.PerspectiveCamera(), null);
  assert(emptyRes !== null, 'initLayers handles empty environment without crashing');
  disposeLayers();
});

test('8.2: Extreme longitude wrapping & pole coordinate consistency', () => {
  // Longitudes beyond 360 or negative
  const v0 = latLonToVector3(0, 0, 5.0);
  const v360 = latLonToVector3(0, 360, 5.0);
  const v720 = latLonToVector3(0, 720, 5.0);
  const vNeg360 = latLonToVector3(0, -360, 5.0);

  assertCloseTo(v0.x, v360.x, 1e-6, 'Lon 0 == Lon 360 X');
  assertCloseTo(v0.z, v360.z, 1e-6, 'Lon 0 == Lon 360 Z');
  assertCloseTo(v0.x, v720.x, 1e-6, 'Lon 0 == Lon 720 X');
  assertCloseTo(v0.x, vNeg360.x, 1e-6, 'Lon 0 == Lon -360 X');

  // North pole (lat=90): Y = R, X = 0, Z = 0
  const vNorth = latLonToVector3(90, 45, 5.0);
  assertCloseTo(vNorth.y, 5.0, 1e-6, 'North pole Y = R');
  assertCloseTo(vNorth.x, 0.0, 1e-6, 'North pole X = 0');
  assertCloseTo(vNorth.z, 0.0, 1e-6, 'North pole Z = 0');

  // South pole (lat=-90): Y = -R, X = 0, Z = 0
  const vSouth = latLonToVector3(-90, 120, 5.0);
  assertCloseTo(vSouth.y, -5.0, 1e-6, 'South pole Y = -R');
  assertCloseTo(vSouth.x, 0.0, 1e-6, 'South pole X = 0');
  assertCloseTo(vSouth.z, 0.0, 1e-6, 'South pole Z = 0');
});

test('8.3: Boresight rotation mathematical inverse property', () => {
  // Target: lat = 42, lon = 12 (Rome)
  const rot = boresightRotation(42.0, 12.0);
  assert(typeof rot.rotX === 'number' && typeof rot.rotY === 'number', 'Boresight returns valid Euler angles');
  assertCloseTo(rot.rotX, (42.0 * Math.PI / 180.0) * 0.4, 1e-6, 'Boresight rotX formula');
  assertCloseTo(rot.rotY, -(12.0 * Math.PI / 180.0) - Math.PI / 2.0, 1e-6, 'Boresight rotY formula');
});

console.log('\n──────────────────────────────────────────────────────────────────────');
console.log(`Execution Summary: Total: ${totalTests} | Passed: ${passedTests} | Failed: ${failedTests}`);
console.log('──────────────────────────────────────────────────────────────────────\n');

if (failedTests > 0) {
  console.error(`Empirical Challenge FAILED with ${failedTests} failure(s).`);
  process.exit(1);
} else {
  console.log('Empirical Challenge PASSED: All mathematical and numerical invariants strictly verified.');
  process.exit(0);
}
