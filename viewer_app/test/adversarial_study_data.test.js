// SPDX-License-Identifier: Apache-2.0
/**
 * adversarial_study_data.test.js
 * Empirical Challenger Adversarial Test Suite for Milestone 1: viewer_app/studyData.js
 *
 * Comprehensive Stress & Penetration Testing:
 * 1. Deep Immutability & Mutation Defense (Strict mode object tampering)
 * 2. EventTarget Reactive Event System (High throughput, memory leaks, unsubscription contracts)
 * 3. State Transitions & Auto-Promotion Layer Presets (Bidirectional consistency)
 * 4. Input Boundary, Clamping & Fuzzing (Extreme / non-numeric / malformed inputs)
 * 5. Scientific Metric & Geospatial Mathematical Verification
 */

import studyData, {
  latLonToCartesian,
  deepFreeze,
  STUDY_VERSIONS,
  ENSEMBLE_METADATA,
  CYCLONE_TRAJECTORY_DATA,
  CYCLONE_WAYPOINTS,
  MULTI_SOURCE_INGESTION,
  INGESTION_SOURCES,
  PROGNOSTIC_BENCHMARK,
  MESOSCALE_DOMAINS,
  DA_STATIONS,
  DATA_ASSIMILATION_METADATA,
  DIGITAL_TWIN_METADATA,
  DOMAINS_MAP,
  COMPARISON_MATRIX,
  getState,
  getActiveVersion,
  getActiveVersionId,
  setActiveVersion,
  setLayerVisibility,
  toggleLayer,
  setActiveDomain,
  setActiveTimeStep,
  selectStation,
  setSelectedStation,
  setSpreadOpacity,
  on,
  off,
  addEventListener,
  removeEventListener,
  dispatchEvent,
  getStudyVersions,
  getStudyVersion,
  getCycloneWaypoints,
  getCycloneTrajectoryMetadata,
  getDAStations,
  getDAStationById,
  getDAStationByCode,
  getMesoscaleDomains,
  getDomainById,
  getEnsembleMetadata,
  getPrognosticBenchmark,
  getMultiSourceIngestion,
  getIngestionSources,
  getDigitalTwinMetadata,
  getComparisonMatrix,
  validateStudyData
} from '../studyData.js';

let passed = 0;
let failed = 0;
const defectsDiscovered = [];

function resetState() {
  setActiveVersion("V3");
  setActiveDomain("GLOBAL");
  setActiveTimeStep(0);
  selectStation(null);
  setSpreadOpacity(0.65);
}

function test(name, fn) {
  resetState();
  try {
    fn();
    passed++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    failed++;
    console.error(`  ✗ FAIL: ${name}\n     -> Error: ${err.message}`);
  }
}

function recordDefect(id, title, details) {
  defectsDiscovered.push({ id, title, details });
  console.warn(`  ⚠️ CONFIRMED DEFECT [${id}]: ${title}\n     -> ${details}`);
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || "Assertion failed");
  }
}

function assertThrows(fn, message) {
  let threw = false;
  try {
    fn();
  } catch {
    threw = true;
  }
  if (!threw) {
    throw new Error(message || `Expected function to throw in strict mode, but it succeeded.`);
  }
}

console.log("===============================================================================");
console.log("OD-EARTH2-001 M1 CHALLENGER 1: ADVERSARIAL STRESS TEST HARNESS");
console.log("===============================================================================\n");

// -----------------------------------------------------------------------------
// SUITE 1: IMMUTABILITY & MUTATION ATTACKS
// -----------------------------------------------------------------------------
console.log("--- Suite 1: Deep Immutability & Mutation Defense ---");

test("1.1 Mutating nested metrics in getStudyVersions().V1 throws (e.g. rmse = 999.0)", () => {
  const versions = getStudyVersions();
  assert(Object.isFrozen(versions), "versions must be frozen");
  assert(Object.isFrozen(versions.V1), "V1 must be frozen");
  assert(Object.isFrozen(versions.V1.metrics), "V1.metrics must be frozen");

  // Attempting to inject new property 'rmse' as described in dispatch
  assertThrows(() => {
    versions.V1.metrics.rmse = 999.0;
  }, "Assigning new property 'rmse' to frozen metrics must throw");

  // Attempting to alter existing property 'rmseWeightedK'
  assertThrows(() => {
    versions.V1.metrics.rmseWeightedK = 999.0;
  }, "Mutating 'rmseWeightedK' must throw");

  assert(versions.V1.metrics.rmseWeightedK === 0.747, "Value must remain untampered at 0.747");
});

test("1.2 Mutating V1 defects array throws", () => {
  const versions = getStudyVersions();
  assertThrows(() => {
    versions.V1.defects.push({ id: 8, name: "Tampered Defect" });
  }, "Pushing to defects array must throw");

  assertThrows(() => {
    versions.V1.defects[0].name = "Tampered Name";
  }, "Mutating defect object must throw");

  assert(versions.V1.defects.length === 7, "Defects count must remain 7");
});

test("1.3 Mutating V2 metrics & antiLeakageInvariants throws", () => {
  const versions = getStudyVersions();
  assertThrows(() => {
    versions.V2.metrics.rmseWeightedK = 0.0;
  }, "Mutating V2 rmseWeightedK must throw");

  assertThrows(() => {
    versions.V2.antiLeakageInvariants.pop();
  }, "Popping from antiLeakageInvariants must throw");

  assert(versions.V2.metrics.rmseWeightedK === 2.1290, "V2 RMSE must remain 2.1290");
  assert(versions.V2.antiLeakageInvariants.length === 6, "Invariants count must remain 6");
});

test("1.4 Mutating V3 pillarsSummary throws", () => {
  const versions = getStudyVersions();
  assertThrows(() => {
    versions.V3.pillarsSummary[0].metric = "Hacked";
  }, "Mutating V3 pillarsSummary must throw");
  assert(versions.V3.pillarsSummary.length === 7, "Pillars count must remain 7");
});

test("1.5 Mutating getCycloneWaypoints() and deep coordinates throws", () => {
  const wps = getCycloneWaypoints();
  assert(Array.isArray(wps), "Waypoints must be array");
  assert(Object.isFrozen(wps), "Waypoints array must be frozen");
  assert(Object.isFrozen(wps[0]), "Waypoint 0 must be frozen");
  assert(Object.isFrozen(wps[0].cartesianPos), "Waypoint cartesianPos must be frozen");

  assertThrows(() => {
    wps[0].lat = 999.0;
  }, "Mutating lat must throw");

  assertThrows(() => {
    wps[0].cartesianPos.x = 999.0;
  }, "Mutating cartesianPos.x must throw");

  assertThrows(() => {
    wps.splice(0, 1);
  }, "Splice must throw");

  assert(wps[0].lat === 30.0, "Lat must remain 30.0");
  assert(wps.length === 5, "Waypoints length must remain 5");
});

test("1.6 Mutating getDAStations() and deep coordinates throws", () => {
  const stations = getDAStations();
  assert(Object.isFrozen(stations), "DA stations must be frozen");
  assert(Object.isFrozen(stations[0]), "Station must be frozen");
  assert(Object.isFrozen(stations[0].cartesianCap), "cartesianCap must be frozen");

  assertThrows(() => {
    stations[0].obsVal = 999.0;
  }, "Mutating station obsVal must throw");

  assertThrows(() => {
    stations[0].cartesianCap.y = 999.0;
  }, "Mutating cartesianCap.y must throw");

  assert(stations[0].obsVal === 291.50, "obsVal must remain 291.50");
});

test("1.7 Mutating getMesoscaleDomains() bounds and coordinates throws", () => {
  const domains = getMesoscaleDomains();
  assert(Object.isFrozen(domains), "Domains must be frozen");
  assert(Object.isFrozen(domains[0]), "Domain 0 must be frozen");
  assert(Object.isFrozen(domains[0].bounds), "bounds array must be frozen");
  assert(Object.isFrozen(domains[0].cornersCartesian.nw), "cornersCartesian must be frozen");

  assertThrows(() => {
    domains[0].bounds[0] = 999.0;
  }, "Mutating bounds array must throw");

  assertThrows(() => {
    domains[0].cornersCartesian.nw.x = 999.0;
  }, "Mutating corner coordinate must throw");

  assert(domains[0].bounds[0] === 44.0, "Bounds[0] must remain 44.0");
});

test("1.8 Mutating getEnsembleMetadata() throws", () => {
  const meta = getEnsembleMetadata();
  assert(Object.isFrozen(meta), "Ensemble metadata must be frozen");
  assertThrows(() => {
    meta.members = 100;
  }, "Mutating members count must throw");
  assert(meta.members === 25, "Members must remain 25");
});

test("1.9 Mutating getPrognosticBenchmark() models throws", () => {
  const bench = getPrognosticBenchmark();
  assert(Object.isFrozen(bench), "Benchmark must be frozen");
  assert(Object.isFrozen(bench.models), "Models array must be frozen");
  assert(Object.isFrozen(bench.models[0]), "Model 0 must be frozen");

  assertThrows(() => {
    bench.models[0].rmseK = 999.0;
  }, "Mutating model rmseK must throw");
  assert(bench.models[0].rmseK === 1.7629, "Model RMSE must remain 1.7629");
});

test("1.10 Mutating getComparisonMatrix() throws", () => {
  const matrix = getComparisonMatrix();
  assert(Object.isFrozen(matrix), "Matrix must be frozen");
  assert(Object.isFrozen(matrix[0]), "Row 0 must be frozen");

  assertThrows(() => {
    matrix[0].v1 = "Tampered";
  }, "Mutating matrix row must throw");
});

test("1.11 getState() returns deeply frozen snapshot that defends internal state", () => {
  const s = getState();
  assert(Object.isFrozen(s), "getState() snapshot must be frozen");
  assert(Object.isFrozen(s.activeLayers), "getState().activeLayers must be frozen");

  assertThrows(() => {
    s.activeLayers.cyclone = !s.activeLayers.cyclone;
  }, "Mutating s.activeLayers must throw");

  assertThrows(() => {
    s.activeVersionId = "HACKED";
  }, "Mutating s.activeVersionId must throw");

  assert(getActiveVersionId() === "V3", "Internal activeVersionId must not be altered");
});

test("1.12 getCycloneTrajectoryMetadata() returns independent object that protects CYCLONE_TRAJECTORY_DATA", () => {
  const traj = getCycloneTrajectoryMetadata();
  traj.stormId = "HACKED_STORM";
  assert(CYCLONE_TRAJECTORY_DATA.stormId === "WPAC_TYPHOON_SIM", "Internal stormId must not change");
});

// -----------------------------------------------------------------------------
// SUITE 2: EVENTTARGET REACTIVE EVENT SYSTEM STRESS TEST
// -----------------------------------------------------------------------------
console.log("\n--- Suite 2: EventTarget Reactive Event System Stress Test ---");

test("2.1 Rapid version toggles (1,000 cycles = 3,000 transitions) maintain consistency", () => {
  let versionChangeEvents = 0;
  const unsub = on("study-version-changed", () => {
    versionChangeEvents++;
  });

  for (let i = 0; i < 1000; i++) {
    setActiveVersion("V1");
    setActiveVersion("V2");
    setActiveVersion("V3");
  }

  unsub();
  assert(versionChangeEvents === 3000, `Expected 3000 events, got ${versionChangeEvents}`);
  assert(getActiveVersionId() === "V3", "Active version must end on V3");
  const s = getState();
  assert(s.activeLayers.cyclone === true, "V3 must have cyclone active");
  assert(s.activeLayers.da_stations === true, "V3 must have da_stations active");
  assert(s.activeLayers.mesoscale_insets === true, "V3 must have mesoscale_insets active");
});

test("2.2 on() returns an unsubscribe function that reliably halts event delivery", () => {
  let count = 0;
  const unsub = on("layer-toggled", () => {
    count++;
  });

  setLayerVisibility("cyclone", false);
  setLayerVisibility("cyclone", true);
  assert(count === 2, `Expected 2 layer-toggled events, got ${count}`);

  unsub(); // unsubscribe via returned closure
  setLayerVisibility("cyclone", false);
  setLayerVisibility("cyclone", true);
  assert(count === 2, `Count should remain 2 after unsubscribe, got ${count}`);
});

test("2.3 EMPIRICAL DEFECT CHECK: off(eventName, handler) unsubscription contract", () => {
  let count = 0;
  const myHandler = () => {
    count++;
  };

  const unsub = on("study-version-changed", myHandler);
  setActiveVersion("V1");
  assert(count === 1, "Handler should have been called once");

  // Call exported off(eventName, handler)
  off("study-version-changed", myHandler);
  setActiveVersion("V2");

  if (count === 2) {
    recordDefect(
      "BUG-E2S-001",
      "Broken off(eventName, handler) unsubscription in EventTarget dispatcher",
      "Lines 1068-1081: on() creates an anonymous wrapper `listener = (event) => handler(event.detail)` and attaches it to eventBus. addEventListener, but off() passes `handler` directly to eventBus.removeEventListener. Since handler !== listener, removeEventListener is a no-op and the event handler is permanently retained."
    );
    // Clean up using the closure
    unsub();
    setActiveVersion("V3");
  } else {
    unsub();
  }
});

test("2.4 Rapid add and remove of 1,000 distinct listeners runs without leak", () => {
  const unsubs = [];
  let totalCalls = 0;

  for (let i = 0; i < 1000; i++) {
    unsubs.push(on("domain-focused", () => {
      totalCalls++;
    }));
  }

  setActiveDomain("ITALY");
  assert(totalCalls === 1000, `Expected 1000 calls, got ${totalCalls}`);

  // Unsubscribe all
  for (const unsub of unsubs) {
    unsub();
  }

  totalCalls = 0;
  setActiveDomain("JAPAN");
  assert(totalCalls === 0, `Expected 0 calls after unsubscriptions, got ${totalCalls}`);
});

test("2.5 Invalid version IDs return false, leave state unchanged, and do not emit events", () => {
  let eventFired = false;
  const unsub = on("study-version-changed", () => {
    eventFired = true;
  });

  const initialVersion = getActiveVersionId();
  assert(initialVersion === "V3", "Initial version should be V3");

  assert(setActiveVersion("V4") === false, "V4 must return false");
  assert(setActiveVersion("") === false, "Empty string must return false");
  assert(setActiveVersion(null) === false, "null must return false");
  assert(setActiveVersion(undefined) === false, "undefined must return false");
  assert(setActiveVersion(123) === false, "Number must return false");
  assert(setActiveVersion({}) === false, "Object must return false");
  assert(setActiveVersion("UNKNOWN") === false, "UNKNOWN must return false");

  assert(!eventFired, "No study-version-changed event should be fired for invalid versions");
  assert(getActiveVersionId() === "V3", "Active version must remain V3");
  unsub();
});

test("2.6 Case insensitivity and whitespace trimming for version IDs", () => {
  assert(setActiveVersion("v1") === true, "'v1' should be accepted");
  assert(getActiveVersionId() === "V1", "Should normalize to 'V1'");

  assert(setActiveVersion("  v2  ") === true, "'  v2  ' should be accepted");
  assert(getActiveVersionId() === "V2", "Should normalize to 'V2'");

  assert(setActiveVersion("V3") === true, "'V3' should be accepted");
  assert(getActiveVersionId() === "V3", "Should be 'V3'");
});

// -----------------------------------------------------------------------------
// SUITE 3: STATE TRANSITIONS & AUTO-PROMOTION
// -----------------------------------------------------------------------------
console.log("\n--- Suite 3: State Transitions & Layer Presets ---");

test("3.1 Transition V3 -> V1 clears advanced layers and preserves baseline layers", () => {
  setActiveVersion("V3");
  let s = getState();
  assert(s.activeLayers.cyclone === true, "V3 cyclone should be true");
  assert(s.activeLayers.da_stations === true, "V3 da_stations should be true");
  assert(s.activeLayers.mesoscale_insets === true, "V3 mesoscale_insets should be true");

  setActiveVersion("V1");
  s = getState();
  assert(s.activeVersionId === "V1", "activeVersionId should be V1");
  assert(s.activeLayers.cyclone === false, "V1 cyclone should be false");
  assert(s.activeLayers.da_stations === false, "V1 da_stations should be false");
  assert(s.activeLayers.ensemble_spread === false, "V1 ensemble_spread should be false");
  assert(s.activeLayers.mesoscale_insets === false, "V1 mesoscale_insets should be false");
  assert(s.activeLayers.surface_temp === true, "V1 surface_temp should remain true");
  assert(s.activeLayers.rotation === true, "V1 rotation should remain true");
});

test("3.2 Transition V1 -> V2 keeps advanced layers disabled", () => {
  setActiveVersion("V1");
  setActiveVersion("V2");
  const s = getState();
  assert(s.activeVersionId === "V2", "activeVersionId should be V2");
  assert(s.activeLayers.cyclone === false, "V2 cyclone should be false");
  assert(s.activeLayers.da_stations === false, "V2 da_stations should be false");
  assert(s.activeLayers.ensemble_spread === false, "V2 ensemble_spread should be false");
  assert(s.activeLayers.mesoscale_insets === false, "V2 mesoscale_insets should be false");
});

test("3.3 Transition V2 -> V3 restores advanced layers", () => {
  setActiveVersion("V2");
  setActiveVersion("V3");
  const s = getState();
  assert(s.activeVersionId === "V3", "activeVersionId should be V3");
  assert(s.activeLayers.cyclone === true, "V3 cyclone should be true");
  assert(s.activeLayers.da_stations === true, "V3 da_stations should be true");
  assert(s.activeLayers.mesoscale_insets === true, "V3 mesoscale_insets should be true");
});

test("3.4 Enabling advanced layer while in V1 automatically promotes version to V3", () => {
  setActiveVersion("V1");
  assert(getActiveVersionId() === "V1", "Should be in V1");

  const events = [];
  const unsub1 = on("study-version-changed", (d) => events.push({ type: "version", detail: d }));
  const unsub2 = on("layer-toggled", (d) => events.push({ type: "layer", detail: d }));

  setLayerVisibility("cyclone", true);

  unsub1();
  unsub2();

  assert(getActiveVersionId() === "V3", "Enabling cyclone while in V1 must auto-promote to V3");
  assert(getState().activeLayers.cyclone === true, "cyclone layer must be visible");

  // Verify event sequence: version change should happen, then layer toggle
  assert(events.some(e => e.type === "version" && e.detail.versionId === "V3"), "Must emit study-version-changed to V3");
  assert(events.some(e => e.type === "layer" && e.detail.layerId === "cyclone" && e.detail.visible === true), "Must emit layer-toggled");
});

test("3.5 Enabling non-advanced layer while in V1 does NOT promote to V3", () => {
  setActiveVersion("V1");
  assert(getActiveVersionId() === "V1", "Should be in V1");

  setLayerVisibility("tendency", true);
  assert(getActiveVersionId() === "V1", "Enabling tendency must NOT promote to V3");
  assert(getState().activeLayers.tendency === true, "tendency layer must be visible");

  // Toggle back
  setLayerVisibility("tendency", false);
  assert(getState().activeLayers.tendency === false, "tendency layer must be false");
});

test("3.6 toggleLayer() correctly toggles layer and returns new state", () => {
  setActiveVersion("V3");
  const initial = getState().activeLayers.rotation;
  const toggled = toggleLayer("rotation");
  assert(toggled === !initial, "toggleLayer must return inverted value");
  assert(getState().activeLayers.rotation === !initial, "getState() must reflect toggled value");

  const toggledBack = toggleLayer("rotation");
  assert(toggledBack === initial, "toggleLayer must restore original value");
  assert(getState().activeLayers.rotation === initial, "getState() must reflect restored value");
});

// -----------------------------------------------------------------------------
// SUITE 4: INPUT BOUNDARY, CLAMPING & FUZZING
// -----------------------------------------------------------------------------
console.log("\n--- Suite 4: Input Boundary, Clamping & Fuzzing ---");

test("4.1 EMPIRICAL DEFECT CHECK: setActiveTimeStep with non-numeric inputs", () => {
  setActiveTimeStep(0);
  assert(getState().activeTimeStep === 0, "TimeStep 0 ok");

  setActiveTimeStep(4);
  assert(getState().activeTimeStep === 4, "TimeStep 4 ok");

  setActiveTimeStep(-100);
  assert(getState().activeTimeStep === 0, "Negative step clamped to 0");

  setActiveTimeStep(999);
  assert(getState().activeTimeStep === 4, "Excessive step clamped to 4");

  setActiveTimeStep(2.7);
  assert(getState().activeTimeStep === 2, "Float step floored to 2");

  // String number
  setActiveTimeStep("3");
  assert(getState().activeTimeStep === 3, "String '3' parsed as 3");

  // Fuzzing with non-numeric string "step_alpha"
  setActiveTimeStep("step_alpha");
  const stepAfterInvalid = getState().activeTimeStep;

  if (Number.isNaN(stepAfterInvalid)) {
    recordDefect(
      "BUG-E2S-002",
      "setActiveTimeStep('abc') propagates NaN into reactive state and events",
      "Line 1248: `const clamped = Math.max(0, Math.min(4, Math.floor(step || 0)));` When `step` is a non-empty non-numeric string (e.g. 'step_alpha'), `step || 0` evaluates to the string itself. `Math.floor('step_alpha')` evaluates to NaN, causing Math.min and Math.max to propagate NaN into `state.activeTimeStep` and dispatch `{ step: NaN }` event. Recommended fix: `Math.floor(Number(step) || 0)`."
    );
  }
});

test("4.2 setSpreadOpacity clamps to [0.0, 1.0] and handles invalid inputs", () => {
  setSpreadOpacity(0.5);
  assert(getState().spreadOpacity === 0.5, "0.5 opacity ok");

  setSpreadOpacity(-1.5);
  assert(getState().spreadOpacity === 0.0, "Negative opacity clamped to 0.0");

  setSpreadOpacity(2.5);
  assert(getState().spreadOpacity === 1.0, "Excessive opacity clamped to 1.0");

  setSpreadOpacity("0.85");
  assert(getState().spreadOpacity === 0.85, "String '0.85' parsed as 0.85");

  setSpreadOpacity("invalid");
  assert(getState().spreadOpacity === 0.0, "Invalid string falls back to 0.0");

  setSpreadOpacity(NaN);
  assert(getState().spreadOpacity === 0.0, "NaN falls back to 0.0");
});

test("4.3 setActiveDomain handles known and unknown domains", () => {
  setActiveDomain("ITALY");
  assert(getState().activeDomain === "ITALY", "Known domain ITALY set");

  let eventDetail = null;
  const unsub = on("domain-focused", (d) => { eventDetail = d; });

  setActiveDomain("UNKNOWN_SPACE");
  unsub();

  assert(eventDetail !== null, "domain-focused event must fire");
  assert(eventDetail.domainInfo === DOMAINS_MAP.GLOBAL, "Unknown domain must fall back to GLOBAL in domainInfo");
});

test("4.4 selectStation handles valid IDs, WMO IDs, unknown IDs, and null/empty", () => {
  let stationEvent = null;
  const unsub = on("station-selected", (d) => { stationEvent = d; });

  // Valid ID
  selectStation("LIMC");
  assert(getState().selectedStationId === "LIMC", "Station LIMC selected");
  assert(stationEvent.stationData && stationEvent.stationData.name === "Milan Malpensa", "Milan station payload received");

  // WMO ID
  selectStation("16242"); // Rome
  assert(getState().selectedStationId === "LIRF", "Station 16242 resolved to LIRF");
  assert(stationEvent.stationData && stationEvent.stationData.name === "Rome Fiumicino", "Rome station payload received");

  // Unknown station
  selectStation("NON_EXISTENT");
  assert(getState().selectedStationId === null, "Unknown station sets id to null");
  assert(stationEvent.stationData === null, "Unknown station payload is null");

  // Null / Deselect
  selectStation(null);
  assert(getState().selectedStationId === null, "Deselect sets id to null");
  assert(stationEvent.stationData === null, "Deselected payload is null");

  unsub();
});

// -----------------------------------------------------------------------------
// SUITE 5: MATHEMATICAL, GEOSPATIAL & SCIENTIFIC INTEGRITY CHECKS
// -----------------------------------------------------------------------------
console.log("\n--- Suite 5: Scientific Integrity & Geospatial Math ---");

test("5.1 latLonToCartesian aligns with Three.js sphere UV conventions", () => {
  const R = 5.0;
  // Equator, Greenwich (lat 0, lon 0) -> x = -R, y = 0, z = 0
  const p0 = latLonToCartesian(0, 0, R);
  assert(Math.abs(p0.x - (-R)) < 1e-6, `x at (0,0) should be -${R}, got ${p0.x}`);
  assert(Math.abs(p0.y - 0) < 1e-6, `y at (0,0) should be 0, got ${p0.y}`);
  assert(Math.abs(p0.z - 0) < 1e-6, `z at (0,0) should be 0, got ${p0.z}`);

  // North Pole (lat +90, lon 0) -> x = 0, y = +R, z = 0
  const pNP = latLonToCartesian(90, 0, R);
  assert(Math.abs(pNP.x - 0) < 1e-6, `x at NP should be 0, got ${pNP.x}`);
  assert(Math.abs(pNP.y - R) < 1e-6, `y at NP should be ${R}, got ${pNP.y}`);
  assert(Math.abs(pNP.z - 0) < 1e-6, `z at NP should be 0, got ${pNP.z}`);

  // South Pole (lat -90, lon 0) -> x = 0, y = -R, z = 0
  const pSP = latLonToCartesian(-90, 0, R);
  assert(Math.abs(pSP.y - (-R)) < 1e-6, `y at SP should be -${R}, got ${pSP.y}`);

  // 90°E (lat 0, lon 90) -> x = 0, y = 0, z = +R
  const p90E = latLonToCartesian(0, 90, R);
  assert(Math.abs(p90E.x - 0) < 1e-6, `x at 90E should be 0, got ${p90E.x}`);
  assert(Math.abs(p90E.z - R) < 1e-6, `z at 90E should be ${R}, got ${p90E.z}`);

  // 90°W (lat 0, lon -90 or 270) -> x = 0, y = 0, z = -R
  const p90W = latLonToCartesian(0, -90, R);
  assert(Math.abs(p90W.x - 0) < 1e-6, `x at 90W should be 0, got ${p90W.x}`);
  assert(Math.abs(p90W.z - (-R)) < 1e-6, `z at 90W should be -${R}, got ${p90W.z}`);
});

test("5.2 validateStudyData() reports 100% pass rate (47/47 assertions)", () => {
  const result = validateStudyData();
  assert(result.valid === true, `validateStudyData failed with errors: ${result.errors.join(", ")}`);
  assert(result.total === 47, `Expected 47 assertions, got ${result.total}`);
  assert(result.passed === 47, `Expected 47 passed, got ${result.passed}`);
});

test("5.3 Rule e2s-014 invariants are mathematically preserved", () => {
  const v2 = getStudyVersion("V2");
  assert(v2.metrics.tac === 0.0000, "V2 TAC must be 0.0000");
  assert(v2.metrics.acc === null, "V2 ACC must be null");
  assert(v2.cycle.neuralStatus.includes("HARDWARE BLOCKER"), "Hardware blocker must be declared");

  const v1 = getStudyVersion("V1");
  assert(v1.metrics.rmseWeightedK === 0.747, "V1 RMSE must be 0.747");
  assert(v1.statusBadge === "QUARANTINED TARGET LEAKAGE", "V1 status badge must be quarantined");
});

// -----------------------------------------------------------------------------
// SUMMARY & VERDICT GENERATION
// -----------------------------------------------------------------------------
console.log("\n===============================================================================");
console.log(`TEST SUMMARY: Total Tests: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log(`CONFIRMED DEFECTS DISCOVERED: ${defectsDiscovered.length}`);
for (const d of defectsDiscovered) {
  console.log(`  * ${d.id}: ${d.title}`);
}
console.log("===============================================================================");

if (defectsDiscovered.length > 0) {
  console.log("\nEMPIRICAL VERDICT: DEFECTS CONFIRMED (SEE REPORT)");
} else {
  console.log("\nEMPIRICAL VERDICT: ALL PASS");
}
