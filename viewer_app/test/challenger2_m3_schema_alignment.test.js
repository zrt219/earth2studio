// SPDX-License-Identifier: Apache-2.0
/**
 * challenger2_m3_schema_alignment.test.js
 * Empirical Challenger 2 Adversarial Test Suite for Milestone 3.
 *
 * Focus:
 * 1. Web App Schema Stress:
 *    - PROGNOSTIC_BENCHMARK.models completeness (5 models + multimodel ensemble)
 *    - Skill formula: Skill = (1 - RMSE / RMSE_pers) * 100% within 0.1% tolerance
 *    - Strict typing of paramCountM, latencyMsCpu, memoryMb, empiricalProxy
 *    - ENSEMBLE_METADATA Pillar A verification metrics (crps, ssr, edi_wind_20ms, sedi_wind_20ms, sedi_precip_10mm)
 *    - Immutability and mutation defense
 *    - Non-negativity, finiteness, absence of NaN/Infinity
 */

import studyData, {
  PROGNOSTIC_BENCHMARK,
  ENSEMBLE_METADATA,
  STUDY_DATA,
  getPrognosticBenchmark,
  getEnsembleMetadata,
} from '../studyData.js';

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const failureDetails = [];

function test(name, fn) {
  totalTests++;
  try {
    fn();
    passedTests++;
    console.log(`  ✓ PASS: ${name}`);
  } catch (err) {
    failedTests++;
    failureDetails.push({ name, error: err.message, stack: err.stack });
    console.error(`  ✗ FAIL: ${name}\n     -> Error: ${err.message}`);
  }
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

function assertCloseTo(actual, expected, tolerance, label) {
  const diff = Math.abs(actual - expected);
  if (diff > tolerance) {
    throw new Error(
      `${label}: expected ${expected} ± ${tolerance}, but received ${actual} (diff: ${diff.toFixed(6)})`
    );
  }
}

console.log('======================================================================');
console.log('  CHALLENGER 2: MILESTONE 3 WEB APP SCHEMA STRESS TEST HARNESS');
console.log('======================================================================\n');

// -----------------------------------------------------------------------------
// SUITE 1: PROGNOSTIC_BENCHMARK.models Completeness & Typing
// -----------------------------------------------------------------------------
console.log('▸ Suite 1: Prognostic Benchmark Model Roster & Resource Profiles');

test('All 5 core models and multimodel ensemble are present', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  assert(Array.isArray(models), 'PROGNOSTIC_BENCHMARK.models must be an array');
  assert(models.length >= 6, `Expected at least 6 models, got ${models.length}`);

  const requiredIds = ['persistence', 'sfno', 'graphcast', 'pangu', 'climax'];
  for (const id of requiredIds) {
    const found = models.find((m) => m.id === id);
    assert(found !== undefined, `Required model '${id}' must be present in models array`);
  }

  // Check multimodel ensemble presence
  const multi = models.find((m) => m.id === 'multimodel' || m.id === 'multi_model_ensemble');
  assert(multi !== undefined, "Multimodel ensemble ('multimodel' or 'multi_model_ensemble') must be present");
});

test('Persistence model baseline is well-formed and valid', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  const pers = models.find((m) => m.id === 'persistence');
  assert(pers !== undefined, 'Persistence model must exist');

  assert(typeof pers.rmseK === 'number' && Number.isFinite(pers.rmseK) && pers.rmseK > 0, 'Persistence rmseK must be positive finite number');
  assert(typeof pers.maeK === 'number' && Number.isFinite(pers.maeK) && pers.maeK > 0, 'Persistence maeK must be positive finite number');
  assert(typeof pers.biasK === 'number' && Number.isFinite(pers.biasK), 'Persistence biasK must be finite number');
  assert(pers.skillPct === 0.0, `Persistence skillPct must be exactly 0.0, got ${pers.skillPct}`);
  assert(pers.tac === 0.0, `Persistence TAC must be 0.0 (Rule e2s-014), got ${pers.tac}`);
  assert(pers.empiricalProxy === false, 'Persistence empiricalProxy must be false');
  assert(pers.paramCountM === 0.0, 'Persistence paramCountM must be 0.0');
});

test('Resource profiles (paramCountM, latencyMsCpu, memoryMb, empiricalProxy) are strictly defined and typed', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  for (const m of models) {
    // paramCountM
    assert(typeof m.paramCountM === 'number', `Model ${m.id} paramCountM must be a number, got ${typeof m.paramCountM}`);
    assert(Number.isFinite(m.paramCountM), `Model ${m.id} paramCountM must be finite`);
    assert(m.paramCountM >= 0, `Model ${m.id} paramCountM must be non-negative, got ${m.paramCountM}`);

    // latencyMsCpu
    assert(typeof m.latencyMsCpu === 'number', `Model ${m.id} latencyMsCpu must be a number, got ${typeof m.latencyMsCpu}`);
    assert(Number.isFinite(m.latencyMsCpu), `Model ${m.id} latencyMsCpu must be finite`);
    assert(m.latencyMsCpu > 0, `Model ${m.id} latencyMsCpu must be strictly positive, got ${m.latencyMsCpu}`);

    // memoryMb
    assert(typeof m.memoryMb === 'number', `Model ${m.id} memoryMb must be a number, got ${typeof m.memoryMb}`);
    assert(Number.isFinite(m.memoryMb), `Model ${m.id} memoryMb must be finite`);
    assert(m.memoryMb > 0, `Model ${m.id} memoryMb must be strictly positive, got ${m.memoryMb}`);

    // empiricalProxy
    assert(typeof m.empiricalProxy === 'boolean', `Model ${m.id} empiricalProxy must be a boolean, got ${typeof m.empiricalProxy}`);
  }
});

// -----------------------------------------------------------------------------
// SUITE 2: Skill Score Mathematical Integrity
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 2: Skill Score Mathematical Integrity & Tolerance Stress');

test('Every model skillPct satisfies Skill = (1 - RMSE / RMSE_pers) * 100% within 0.1% tolerance', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  const persModel = models.find((m) => m.id === 'persistence');
  assert(persModel !== undefined, 'Persistence baseline model must exist');
  const persRmse = persModel.rmseK;
  assert(persRmse > 0, 'Persistence RMSE must be > 0');

  for (const m of models) {
    const expectedSkill = (1.0 - m.rmseK / persRmse) * 100.0;
    assertCloseTo(
      m.skillPct,
      expectedSkill,
      0.1,
      `Model '${m.id}' (${m.name}) skillPct`
    );
  }
});

test('No model exhibits negative skillPct or unphysical skillPct > 100%', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  for (const m of models) {
    assert(m.skillPct >= 0.0, `Model ${m.id} skillPct must be non-negative, got ${m.skillPct}`);
    assert(m.skillPct <= 100.0, `Model ${m.id} skillPct must be <= 100.0%, got ${m.skillPct}`);
  }
});

test('Error metrics (rmseK, maeK) are strictly positive and bounded: RMSE >= MAE', () => {
  const models = PROGNOSTIC_BENCHMARK.models;
  for (const m of models) {
    assert(m.rmseK > 0, `Model ${m.id} rmseK must be > 0`);
    assert(m.maeK > 0, `Model ${m.id} maeK must be > 0`);
    // Mathematical Cauchy-Schwarz invariant: RMSE >= MAE
    assert(
      m.rmseK >= m.maeK - 1e-4,
      `Model ${m.id} violates Cauchy-Schwarz: RMSE (${m.rmseK}) must be >= MAE (${m.maeK})`
    );
  }
});

// -----------------------------------------------------------------------------
// SUITE 3: ENSEMBLE_METADATA Pillar A Verification Metrics Stress
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 3: ENSEMBLE_METADATA Pillar A Operational Verification Metrics');

test('ENSEMBLE_METADATA contains required verification properties', () => {
  assert(typeof ENSEMBLE_METADATA === 'object' && ENSEMBLE_METADATA !== null, 'ENSEMBLE_METADATA must be an object');

  const requiredProps = [
    'crps',
    'ssr',
    'edi_wind_20ms',
    'sedi_wind_20ms',
    'sedi_precip_10mm',
  ];

  for (const prop of requiredProps) {
    assert(prop in ENSEMBLE_METADATA, `ENSEMBLE_METADATA must contain '${prop}'`);
    const val = ENSEMBLE_METADATA[prop];
    assert(typeof val === 'number', `ENSEMBLE_METADATA.${prop} must be a number, got ${typeof val}`);
    assert(Number.isFinite(val), `ENSEMBLE_METADATA.${prop} must be finite`);
    assert(val >= 0, `ENSEMBLE_METADATA.${prop} must be non-negative, got ${val}`);
  }
});

test('ENSEMBLE_METADATA verification values match operational Pillar A benchmark targets', () => {
  assertCloseTo(ENSEMBLE_METADATA.crps, 0.312, 1e-3, 'crps target');
  assertCloseTo(ENSEMBLE_METADATA.ssr, 0.985, 1e-3, 'ssr target');
  assertCloseTo(ENSEMBLE_METADATA.edi_wind_20ms, 0.764, 1e-3, 'edi_wind_20ms target');
  assertCloseTo(ENSEMBLE_METADATA.sedi_wind_20ms, 0.789, 1e-3, 'sedi_wind_20ms target');
  assertCloseTo(ENSEMBLE_METADATA.sedi_precip_10mm, 0.712, 1e-3, 'sedi_precip_10mm target');
});

test('ENSEMBLE_METADATA nested verification dictionary is synchronized', () => {
  const ver = ENSEMBLE_METADATA.verification;
  assert(typeof ver === 'object' && ver !== null, 'ENSEMBLE_METADATA.verification must be an object');

  assertCloseTo(ver.crps, ENSEMBLE_METADATA.crps, 1e-6, 'verification.crps sync');
  assertCloseTo(ver.ssr, ENSEMBLE_METADATA.ssr, 1e-6, 'verification.ssr sync');
  assertCloseTo(ver.edi_wind_20ms, ENSEMBLE_METADATA.edi_wind_20ms, 1e-6, 'verification.edi_wind_20ms sync');
  assertCloseTo(ver.sedi_wind_20ms, ENSEMBLE_METADATA.sedi_wind_20ms, 1e-6, 'verification.sedi_wind_20ms sync');
  assertCloseTo(ver.sedi_precip_10mm, ENSEMBLE_METADATA.sedi_precip_10mm, 1e-6, 'verification.sedi_precip_10mm sync');
});

// -----------------------------------------------------------------------------
// SUITE 4: Adversarial Immutability & Tampering Defense
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 4: Adversarial Immutability & Anti-Tampering Defense');

test('PROGNOSTIC_BENCHMARK cannot be mutated or injected with fake models', () => {
  const bench = getPrognosticBenchmark();

  // Attempt to overwrite property
  try {
    bench.leadTimeHours = 999;
  } catch (e) {
    // Strict mode throw expected
  }
  assert(bench.leadTimeHours === 24, 'leadTimeHours must not be overwritten');

  // Attempt to push to models array
  try {
    bench.models.push({ id: 'fake_model', name: 'Malicious Injected Model', skillPct: 99.9 });
  } catch (e) {
    // Expected to throw
  }
  const fake = bench.models.find((m) => m.id === 'fake_model');
  assert(fake === undefined, 'Injected fake model must not be present');

  // Attempt to mutate individual model skillPct
  try {
    bench.models[0].skillPct = 100.0;
  } catch (e) {
    // Expected to throw
  }
  assert(bench.models[0].skillPct !== 100.0 || bench.models[0].id === 'fake_model', 'Individual model properties must remain immutable');
});

test('ENSEMBLE_METADATA cannot be mutated or falsified', () => {
  const meta = getEnsembleMetadata();

  try {
    meta.crps = -999.0;
  } catch (e) {
    // Expected
  }
  assert(meta.crps === 0.312, 'crps must remain 0.312');

  try {
    meta.ssr = 0.0;
  } catch (e) {
    // Expected
  }
  assert(meta.ssr === 0.985, 'ssr must remain 0.985');
});

// -----------------------------------------------------------------------------
// SUITE 5: Deep Sanity Checks on STUDY_DATA.V3 and Helper Methods
// -----------------------------------------------------------------------------
console.log('\n▸ Suite 5: Full Deep Sanity on Exported Structures');

test('STUDY_DATA.V3 contains verified prognosticBenchmark matching export', () => {
  assert(STUDY_DATA.V3 !== undefined, 'STUDY_DATA.V3 must exist');
  assert(STUDY_DATA.V3.prognosticBenchmark === PROGNOSTIC_BENCHMARK, 'STUDY_DATA.V3.prognosticBenchmark must strictly match PROGNOSTIC_BENCHMARK');
  assert(STUDY_DATA.V3.models === PROGNOSTIC_BENCHMARK.models, 'STUDY_DATA.V3.models must strictly match PROGNOSTIC_BENCHMARK.models');
});

console.log('\n======================================================================');
console.log(`CHALLENGER 2 SUMMARY: Total: ${totalTests} | Passed: ${passedTests} | Failed: ${failedTests}`);
console.log('======================================================================\n');

if (failedTests > 0) {
  console.error('CHALLENGER 2 DETECTED FAILURES:');
  for (const f of failureDetails) {
    console.error(`- ${f.name}: ${f.error}`);
  }
  process.exit(1);
} else {
  console.log('ALL CHALLENGER 2 WEB APP SCHEMA STRESS TESTS PASSED.');
  process.exit(0);
}
