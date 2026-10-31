/**
 * empirical_numerical_challenge.test.js
 *
 * EMPIRICAL ADVERSARIAL CHALLENGER SUITE (Challenger 2, Milestone 1)
 * OD-EARTH2-001 / EO-OBSCURA 3D WebGL Digital Twin
 *
 * Adversarially challenges:
 * 1. Target leakage error propagation formula & Monte Carlo convergence
 * 2. Great-circle distance calculations & spherical geometry for Typhoon waypoints
 * 3. Geographic coordinates validity, bounding boxes, & Cartesian norms
 * 4. Analysis increment bounds, Optimal Interpolation shrinkage & Kalman gain
 * 5. Radial shell hierarchy monotonicity & z-fighting margin defense
 * 6. Immutability defenses & deep-freeze mutation attacks
 * 7. Reactive state machine transitions & auto-promotion invariants
 */

import studyData, {
  latLonToCartesian,
  deepFreeze,
  validateStudyData,
  getStudyVersions,
  STUDY_VERSIONS,
  CYCLONE_TRAJECTORY_DATA,
  CYCLONE_WAYPOINTS,
  DA_STATIONS,
  DATA_ASSIMILATION_METADATA,
  MESOSCALE_DOMAINS,
  DOMAINS_MAP,
  PROGNOSTIC_BENCHMARK,
  ENSEMBLE_METADATA,
  DIGITAL_TWIN_METADATA,
  getState,
  setActiveVersion,
  setLayerVisibility,
  setActiveDomain,
  setActiveTimeStep,
  selectStation,
  setSpreadOpacity
} from '../studyData.js';

let passed = 0;
let failed = 0;
const failures = [];

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    failed++;
    failures.push({ name, error: err });
    console.error(`  ✗ FAIL: ${name}`);
    console.error(`    ${err.message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function assertCloseTo(actual, expected, tolerance, message) {
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    throw new Error(`${message || 'assertCloseTo failed'}: expected ${expected}, got ${actual} (diff: ${diff} > tol: ${tolerance})`);
  }
}

console.log('\n======================================================================');
console.log('  CHALLENGER 2: EMPIRICAL NUMERICAL & MATHEMATICAL INTEGRITY HARNESS');
console.log('======================================================================\n');

// -----------------------------------------------------------------------------
// 1. TARGET LEAKAGE ERROR PROPAGATION FORMULA
// -----------------------------------------------------------------------------
console.log('▸ Challenge Suite 1: Target Leakage Error Propagation Formula');

test('Analytical Error Propagation: sqrt((0.28 * 2.129)^2 + 0.45^2) == 0.74690 K', () => {
  const sigma_pers = 2.129;
  const alpha = 0.72;
  const residual = 1.0 - alpha; // 0.28
  const sigma_eps = 0.45;

  const deterministicRms = residual * sigma_pers; // 0.28 * 2.129 = 0.59612
  assertCloseTo(deterministicRms, 0.59612, 1e-5, 'Deterministic error RMS');

  const deterministicVariance = deterministicRms * deterministicRms; // 0.3553590544
  assertCloseTo(deterministicVariance, 0.3553590544, 1e-8, 'Deterministic variance');

  const noiseVariance = sigma_eps * sigma_eps; // 0.2025
  assertCloseTo(noiseVariance, 0.2025, 1e-8, 'Noise variance');

  const totalExpectedMse = deterministicVariance + noiseVariance; // 0.5578590544
  assertCloseTo(totalExpectedMse, 0.5578590544, 1e-8, 'Total expected MSE');

  const expectedRmse = Math.sqrt(totalExpectedMse); // 0.746899628
  assertCloseTo(expectedRmse, 0.74690, 1e-4, 'Expected RMSE');

  // Check stored values in V1 proof metadata
  const proof = STUDY_VERSIONS.V1.mathematicalProof;
  assert(proof !== undefined, 'V1.mathematicalProof must exist');
  assertCloseTo(proof.persistenceRmseK, sigma_pers, 1e-4, 'proof.persistenceRmseK');
  assertCloseTo(proof.alphaFactor, alpha, 1e-4, 'proof.alphaFactor');
  assertCloseTo(proof.residualFactor, residual, 1e-4, 'proof.residualFactor');
  assertCloseTo(proof.deterministicRmsK, deterministicRms, 1e-4, 'proof.deterministicRmsK');
  assertCloseTo(proof.noiseStdK, sigma_eps, 1e-4, 'proof.noiseStdK');
  assertCloseTo(proof.noiseVarianceK2, noiseVariance, 1e-4, 'proof.noiseVarianceK2');
  assertCloseTo(proof.expectedMseK2, totalExpectedMse, 1e-4, 'proof.expectedMseK2');
  assertCloseTo(proof.expectedRmseK, expectedRmse, 1e-4, 'proof.expectedRmseK');

  // Verify rounded report in V1 metrics
  const v1Metrics = STUDY_VERSIONS.V1.metrics;
  assertCloseTo(v1Metrics.rmseWeightedK, 0.747, 1e-3, 'V1 metrics.rmseWeightedK matches 0.747 K');

  // Skill Score vs Persistence
  const skill = (1.0 - expectedRmse / sigma_pers) * 100.0; // 64.9178%
  assertCloseTo(skill, 64.92, 0.05, 'Manufactured skill score percentage');
  assertCloseTo(proof.manufacturedSkillPct, 64.92, 0.05, 'proof.manufacturedSkillPct');
  assertCloseTo(v1Metrics.skillScorePct, 64.9, 0.1, 'v1Metrics.skillScorePct');
});

test('Monte Carlo Empirical Simulation (N=1,000,000 samples) converges to 0.7469 K', () => {
  // Box-Muller transform for high quality standard normal samples
  function sampleNormal() {
    let u1 = 0, u2 = 0;
    while (u1 === 0) u1 = Math.random();
    while (u2 === 0) u2 = Math.random();
    return Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  }

  const N = 1000000;
  const sigma_pers = 2.129;
  const alpha = 0.72;
  const sigma_eps = 0.45;

  let sumSquaredError = 0;
  for (let i = 0; i < N; i++) {
    const deltaAtm = sampleNormal() * sigma_pers; // delta = Y - x0
    const eps = sampleNormal() * sigma_eps;
    // Error = y_hat - Y = -(1 - alpha)*delta + eps
    const error = -(1.0 - alpha) * deltaAtm + eps;
    sumSquaredError += error * error;
  }

  const empiricalRmse = Math.sqrt(sumSquaredError / N);
  console.log(`    [Monte Carlo N=${N}] Empirical RMSE = ${empiricalRmse.toFixed(5)} K (Analytical: 0.74690 K)`);
  assertCloseTo(empiricalRmse, 0.74690, 0.005, 'Monte Carlo convergence within 0.005 K');
});

// -----------------------------------------------------------------------------
// 2. GREAT-CIRCLE DISTANCE CALCULATIONS (TYPHOON WAYPOINTS)
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 2: Great-Circle Distance Calculations (Typhoon Track)');

function haversineDistanceKm(lat1, lon1, lat2, lon2, R = 6371.0) {
  const phi1 = (lat1 * Math.PI) / 180.0;
  const phi2 = (lat2 * Math.PI) / 180.0;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180.0;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180.0;

  const a =
    Math.sin(deltaPhi / 2.0) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2.0) ** 2;
  const c = 2.0 * Math.atan2(Math.sqrt(a), Math.sqrt(1.0 - a));
  return R * c;
}

test('Successive Waypoint Leg Great-Circle Distances and Total Track Length', () => {
  const wps = CYCLONE_WAYPOINTS;
  assert(wps.length === 5, 'Must have 5 waypoints');

  let cumulativeDistKm = 0;
  const legDistances = [];

  for (let i = 0; i < wps.length - 1; i++) {
    const d = haversineDistanceKm(wps[i].lat, wps[i].lon, wps[i + 1].lat, wps[i + 1].lon);
    legDistances.push(d);
    cumulativeDistKm += d;
    console.log(`    Leg ${i} -> ${i + 1} (${wps[i].id} to ${wps[i + 1].id}): ${d.toFixed(2)} km`);
  }

  console.log(`    Cumulative Track Length = ${cumulativeDistKm.toFixed(2)} km (Metadata: ${CYCLONE_TRAJECTORY_DATA.totalTrackLengthKm} km)`);
  
  // Verify cumulative distance matches within 0.2%
  assertCloseTo(cumulativeDistKm, CYCLONE_TRAJECTORY_DATA.totalTrackLengthKm, 2.0, 'Cumulative track length matches metadata');

  // Verify direct great-circle chord distance from WP-0 to WP-4
  const directChordKm = haversineDistanceKm(wps[0].lat, wps[0].lon, wps[4].lat, wps[4].lon);
  console.log(`    Direct Great-Circle Chord (WP-0 to WP-4) = ${directChordKm.toFixed(2)} km`);
  assert(directChordKm < cumulativeDistKm, 'Spherical triangle inequality: direct chord < cumulative polyline');
  assertCloseTo(directChordKm, 1339.63, 0.5, 'Direct chord distance matches 1339.63 km');

  // Verify forward motion speed across 48 hours
  const totalHours = 48.0;
  const computedSpeedKmH = CYCLONE_TRAJECTORY_DATA.totalTrackLengthKm / totalHours;
  assertCloseTo(computedSpeedKmH, CYCLONE_TRAJECTORY_DATA.meanSpeedKmH, 0.1, 'Mean speed km/h');
  const computedSpeedKt = computedSpeedKmH / 1.852;
  assertCloseTo(computedSpeedKt, CYCLONE_TRAJECTORY_DATA.meanSpeedKt, 0.1, 'Mean speed knots');

  // Verify monotonic progression in time, lead hours, and latitude
  for (let i = 0; i < wps.length - 1; i++) {
    assert(wps[i + 1].leadHours > wps[i].leadHours, `Waypoint ${i + 1} leadHours must increase`);
    assert(wps[i + 1].lat > wps[i].lat, `Waypoint ${i + 1} lat must progress northward`);
    assert(wps[i + 1].lon > wps[i].lon, `Waypoint ${i + 1} lon must progress eastward`);
    assert(wps[i + 1].mslp >= wps[i].mslp, `Waypoint ${i + 1} MSLP must fill/decay`);
    assert(wps[i + 1].windKt <= wps[i].windKt, `Waypoint ${i + 1} windKt must decrease`);
    assert(wps[i + 1].coneRadiusKm > wps[i].coneRadiusKm, `Uncertainty cone must expand over forecast lead time`);
  }
});

// -----------------------------------------------------------------------------
// 3. GEOGRAPHIC COORDINATES VALIDITY & CARTESIAN TRANSFORMATION
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 3: Geographic Coordinates Validity & Cartesian Norms');

test('All Italian Sounding Stations Lie Strictly Inside Italy Geographic Bounds', () => {
  const italyBounds = DOMAINS_MAP.ITALY.bounds; // [35.0, 48.0, 6.0, 19.0]
  const [minLat, maxLat, minLon, maxLon] = italyBounds;

  assert(DA_STATIONS.length === 4, 'Must have exactly 4 stations');

  for (const st of DA_STATIONS) {
    assert(st.lat >= minLat && st.lat <= maxLat, `Station ${st.id} lat ${st.lat} within [${minLat}, ${maxLat}]`);
    assert(st.lon >= minLon && st.lon <= maxLon, `Station ${st.id} lon ${st.lon} within [${minLon}, ${maxLon}]`);
    assert(st.elevM >= 0, `Station ${st.id} elevation >= 0m`);
    assert(typeof st.wmoId === 'string' && st.wmoId.length === 5, `Station ${st.id} has 5-digit WMO ID`);
  }
});

test('Mesoscale Domain Bounds & Center Coordinates are Internally Consistent', () => {
  for (const dom of MESOSCALE_DOMAINS) {
    const [minLat, maxLat, minLon, maxLon] = dom.bounds;
    assert(minLat < maxLat, `Domain ${dom.id}: minLat (${minLat}) < maxLat (${maxLat})`);
    assert(minLon < maxLon, `Domain ${dom.id}: minLon (${minLon}) < maxLon (${maxLon})`);
    assert(dom.center.lat >= minLat && dom.center.lat <= maxLat, `Domain ${dom.id}: center lat within bounds`);
    assert(dom.center.lon >= minLon && dom.center.lon <= maxLon, `Domain ${dom.id}: center lon within bounds`);
  }
});

test('Geographic to Cartesian Transformation Preserves Exact Sphere Radius Everywhere', () => {
  const testRadii = [5.000, 5.020, 5.035, 5.045, 5.050, 5.080, 5.350];
  const testPoints = [
    { lat: 0, lon: 0 },
    { lat: 90, lon: 0 },
    { lat: -90, lon: 0 },
    { lat: 45, lon: 90 },
    { lat: -30, lon: 180 },
    { lat: 60, lon: 270 },
    { lat: 35.5, lon: -45.5 }, // Negative longitude test
    { lat: -78.2, lon: 450.0 } // Over-360 longitude wrapping test
  ];

  for (const R of testRadii) {
    for (const pt of testPoints) {
      const pos = latLonToCartesian(pt.lat, pt.lon, R);
      const computedR = Math.sqrt(pos.x * pos.x + pos.y * pos.y + pos.z * pos.z);
      assertCloseTo(computedR, R, 1e-12, `Cartesian norm at (${pt.lat}, ${pt.lon}) must equal ${R}`);
    }
  }

  // Verify all pre-computed waypoint positions
  for (const wp of CYCLONE_WAYPOINTS) {
    const norm = Math.sqrt(wp.cartesianPos.x ** 2 + wp.cartesianPos.y ** 2 + wp.cartesianPos.z ** 2);
    assertCloseTo(norm, 5.050, 1e-12, `Waypoint ${wp.id} Cartesian norm`);
  }

  // Verify all pre-computed station positions
  for (const st of DA_STATIONS) {
    const baseNorm = Math.sqrt(st.cartesianBase.x ** 2 + st.cartesianBase.y ** 2 + st.cartesianBase.z ** 2);
    const capNorm = Math.sqrt(st.cartesianCap.x ** 2 + st.cartesianCap.y ** 2 + st.cartesianCap.z ** 2);
    assertCloseTo(baseNorm, 5.000, 1e-12, `Station ${st.id} base norm`);
    assertCloseTo(capNorm, 5.350, 1e-12, `Station ${st.id} cap norm`);
  }
});

// -----------------------------------------------------------------------------
// 4. ANALYSIS INCREMENT & DATA ASSIMILATION BOUNDS
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 4: Analysis Increment & Innovation Bounds');

test('All 4 Italian Stations Have Innovations and Increments Within [+2.0, +8.5] K', () => {
  const minBound = 2.0;
  const maxBound = 8.5;

  assert(DA_STATIONS.length === 4, 'Must have 4 stations');

  for (const st of DA_STATIONS) {
    // Check bounds
    assert(st.innovation >= minBound && st.innovation <= maxBound,
      `Station ${st.id} innovation ${st.innovation} within [${minBound}, ${maxBound}] K`);
    assert(st.increment >= minBound && st.increment <= maxBound,
      `Station ${st.id} increment ${st.increment} within [${minBound}, ${maxBound}] K`);

    // Verify innovation == obsVal - bgVal
    const expectedInnov = +(st.obsVal - st.bgVal).toFixed(2);
    assertCloseTo(st.innovation, expectedInnov, 1e-5, `Station ${st.id} innovation definition`);

    // Optimal Interpolation (OI) shrinkage property:
    // Analysis increment = W * innovation. Because observation error variance > 0, W < 1.
    // Therefore 0 < increment <= innovation
    assert(st.increment > 0, `Station ${st.id} increment must be strictly positive`);
    assert(st.increment <= st.innovation, `Station ${st.id} increment (${st.increment}) <= innovation (${st.innovation})`);

    const shrinkageFactor = st.increment / st.innovation;
    assert(shrinkageFactor >= 0.90 && shrinkageFactor <= 1.00,
      `Station ${st.id} shrinkage factor ${shrinkageFactor.toFixed(4)} within physical range [0.90, 1.00]`);
  }

  // Check metadata summary bounds
  const daMeta = DATA_ASSIMILATION_METADATA;
  assert(daMeta.incrementRangeK[0] >= minBound, 'metadata min increment >= 2.0 K');
  assert(daMeta.incrementRangeK[1] <= maxBound, 'metadata max increment <= 8.5 K');
  assertCloseTo(daMeta.priorBackgroundK, 286.00, 1e-2, 'priorBackgroundK');
});

// -----------------------------------------------------------------------------
// 5. RADIAL SHELL HIERARCHY & Z-FIGHTING DEFENSE
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 5: Radial Shell Hierarchy & Z-Fighting Margin Defense');

test('Concentric Radial Shells are Strictly Monotonic with Non-Zero Separation Margins', () => {
  const rh = DIGITAL_TWIN_METADATA.radialHierarchy;
  
  const shells = [
    { name: 'baseGlobe', r: rh.baseGlobe },
    { name: 'ensembleSpreadShell', r: rh.ensembleSpreadShell },
    { name: 'mesoscaleInsets', r: rh.mesoscaleInsets },
    { name: 'uncertaintyCone', r: rh.uncertaintyCone },
    { name: 'cycloneTrajectorySpline', r: rh.cycloneTrajectorySpline },
    { name: 'daStationBeaconsCap', r: rh.daStationBeacons[1] }
  ];

  for (let i = 0; i < shells.length - 1; i++) {
    const margin = shells[i + 1].r - shells[i].r;
    console.log(`    Margin between ${shells[i].name} (${shells[i].r}) and ${shells[i + 1].name} (${shells[i + 1].r}): ${margin.toFixed(4)} units`);
    assert(margin >= 0.005 - 1e-9, `Radial margin between ${shells[i].name} and ${shells[i + 1].name} must be at least 0.005 units (got ${margin})`);
  }
});

// -----------------------------------------------------------------------------
// 6. IMMUTABILITY STRESS TESTING
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 6: Immutability & Deep-Freeze Mutation Attacks');

test('deepFreeze defends against adversarial mutation attempts on nested objects and arrays', () => {
  // Test 1: Attempt to mutate V1 metrics
  try {
    STUDY_VERSIONS.V1.metrics.rmseWeightedK = 999.9;
  } catch (e) {
    // In strict mode, throws TypeError
  }
  assert(STUDY_VERSIONS.V1.metrics.rmseWeightedK === 0.747, 'V1 metrics.rmseWeightedK cannot be mutated');

  // Test 2: Attempt to push a counterfeit waypoint into CYCLONE_WAYPOINTS
  try {
    CYCLONE_WAYPOINTS.push({ id: 'WP-FAKE' });
  } catch (e) {
    // TypeError expected
  }
  assert(CYCLONE_WAYPOINTS.length === 5, 'CYCLONE_WAYPOINTS array length immutable');

  // Test 3: Attempt to mutate DA station background value
  try {
    DA_STATIONS[0].bgVal = 350.0;
  } catch (e) {
    // TypeError expected
  }
  assert(DA_STATIONS[0].bgVal === 286.00, 'DA_STATIONS properties immutable');

  // Test 4: Attempt to mutate getState() returned snapshot
  const st = getState();
  try {
    st.activeVersionId = 'V1';
  } catch (e) {}
  assert(st.activeVersionId === 'V3', 'getState() return value is deeply frozen');
});

// -----------------------------------------------------------------------------
// 7. REACTIVE STATE MACHINE INVARIANTS & EVENT DISPATCHING
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 7: Reactive State Machine & Transition Rules');

test('State transitions follow layer masking rules and auto-promote to V3 on advanced layer enable', () => {
  // Reset to V3
  setActiveVersion('V3');
  assert(getState().activeVersionId === 'V3', 'Initial state is V3');

  // Transition to V2 -> Advanced layers must be hidden
  setActiveVersion('V2');
  const v2State = getState();
  assert(v2State.activeVersionId === 'V2', 'Active version is V2');
  assert(v2State.activeLayers.cyclone === false, 'Cyclone layer disabled in V2');
  assert(v2State.activeLayers.da_stations === false, 'DA stations layer disabled in V2');
  assert(v2State.activeLayers.ensemble_spread === false, 'Ensemble spread disabled in V2');
  assert(v2State.activeLayers.mesoscale_insets === false, 'Mesoscale insets disabled in V2');

  // Adversarial Action: Enabling an advanced layer (e.g. cyclone) while in V2 MUST auto-promote to V3
  setLayerVisibility('cyclone', true);
  const promotedState = getState();
  assert(promotedState.activeVersionId === 'V3', 'Enabling cyclone auto-promotes version to V3');
  assert(promotedState.activeLayers.cyclone === true, 'Cyclone layer is enabled');

  // Domain focusing
  setActiveDomain('ITALY');
  assert(getState().activeDomain === 'ITALY', 'Active domain is ITALY');

  // Time step clamping
  setActiveTimeStep(99);
  assert(getState().activeTimeStep === 4, 'Timestep clamps to 4');
  setActiveTimeStep(-10);
  assert(getState().activeTimeStep === 0, 'Timestep clamps to 0');

  // Station selection
  selectStation('LIRF');
  assert(getState().selectedStationId === 'LIRF', 'Selected station is LIRF');
  selectStation(null);
  assert(getState().selectedStationId === null, 'Station deselected to null');

  // Spread opacity clamping
  setSpreadOpacity(1.5);
  assertCloseTo(getState().spreadOpacity, 1.0, 1e-4, 'Opacity clamped to 1.0');
  setSpreadOpacity(-0.5);
  assertCloseTo(getState().spreadOpacity, 0.0, 1e-4, 'Opacity clamped to 0.0');
});

// -----------------------------------------------------------------------------
// 8. PROGNOSTIC BENCHMARK SKILL SCORE CONSISTENCY
// -----------------------------------------------------------------------------
console.log('\n▸ Challenge Suite 8: Prognostic Benchmark Mathematical Rigor');

test('All neural benchmark skill scores exactly match Skill = (1 - RMSE/RMSE_pers) * 100%', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  const persModel = models.find((m) => m.id === 'persistence');
  assert(persModel !== undefined, 'Persistence baseline model must exist');
  const persRmse = persModel.rmseK;

  for (const m of models) {
    if (m.id === 'persistence') {
      assert(m.skillPct === 0.0, 'Persistence skill must be 0%');
    } else {
      const expectedSkill = (1.0 - m.rmseK / persRmse) * 100.0;
      assertCloseTo(m.skillPct, expectedSkill, 0.1, `Model ${m.name} skill score`);
    }
  }
});

// -----------------------------------------------------------------------------
// SUMMARY
// -----------------------------------------------------------------------------
console.log('\n======================================================================');
console.log(`CHALLENGER 2 SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('======================================================================\n');

if (failed > 0) {
  console.error('FAILURES DETECTED:');
  for (const f of failures) {
    console.error(`- ${f.name}: ${f.error.message}`);
  }
  process.exit(1);
} else {
  console.log('ALL EMPIRICAL CHALLENGES PASSED WITH ZERO FAILURES.');
  process.exit(0);
}
