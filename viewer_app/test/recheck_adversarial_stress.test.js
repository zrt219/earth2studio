/**
 * OD-EARTH2-001 M1 CHALLENGER RECHECK: ADVERSARIAL STRESS TEST HARNESS
 *
 * Exhaustive empirical verification of:
 * 1. BUG-E2S-001: off(eventName, handler) unsubscription contract & edge cases
 * 2. BUG-E2S-002: setActiveTimeStep(step) input coercion, non-numeric fuzzing & bounds
 */

import * as studyData from "../studyData.js";

let totalTests = 0;
let passedTests = 0;
let failedTests = 0;
const defects = [];

function assert(condition, message) {
  totalTests++;
  if (condition) {
    passedTests++;
    console.log(`  ✓ PASS: ${message}`);
  } else {
    failedTests++;
    console.error(`  ✗ FAIL: ${message}`);
    defects.push(message);
  }
}

console.log("===============================================================================");
console.log("OD-EARTH2-001 M1 CHALLENGER RECHECK: EMPIRICAL VERIFICATION HARNESS");
console.log("===============================================================================\n");

// ============================================================================
// SUITE 1: BUG-E2S-001 - EVENT SUBSCRIPTION & UNATTACHMENT ROBUSTNESS
// ============================================================================
console.log("--- Suite 1: BUG-E2S-001 Event Unsubscription Stress Tests ---");

// Test 1.1: Core off(eventName, handler) contract
{
  let count = 0;
  const handler = () => { count++; };
  studyData.on("study-version-changed", handler);
  studyData.setActiveVersion("V1");
  const countAfterFirst = count;
  studyData.off("study-version-changed", handler);
  studyData.setActiveVersion("V2");
  
  assert(
    countAfterFirst >= 1 && count === countAfterFirst,
    "1.1 off(eventName, handler) successfully deregisters listener and prevents subsequent invocations"
  );
}

// Test 1.2: Double off() call safety (idempotent unsubscription)
{
  let threw = false;
  const dummyHandler = () => {};
  try {
    studyData.on("study-version-changed", dummyHandler);
    studyData.off("study-version-changed", dummyHandler);
    studyData.off("study-version-changed", dummyHandler); // second off
  } catch (e) {
    threw = true;
  }
  assert(!threw, "1.2 Calling off() repeatedly for the same handler does not throw or corrupt state");
}

// Test 1.3: Unsubscribe returned closure followed by off()
{
  let threw = false;
  const handler = () => {};
  try {
    const unsub = studyData.on("study-version-changed", handler);
    unsub();
    studyData.off("study-version-changed", handler);
  } catch (e) {
    threw = true;
  }
  assert(!threw, "1.3 Calling unsub() closure followed by off() handles missing mapping gracefully");
}

// Test 1.4: Calling off() followed by unsub() closure
{
  let threw = false;
  const handler = () => {};
  try {
    const unsub = studyData.on("study-version-changed", handler);
    studyData.off("study-version-changed", handler);
    unsub();
  } catch (e) {
    threw = true;
  }
  assert(!threw, "1.4 Calling off() followed by unsub() closure handles already-deleted mapping gracefully");
}

// Test 1.5: Selective unsubscription among multiple listeners
{
  let callsA = 0;
  let callsB = 0;
  let callsC = 0;
  const handlerA = () => { callsA++; };
  const handlerB = () => { callsB++; };
  const handlerC = () => { callsC++; };

  studyData.on("study-version-changed", handlerA);
  studyData.on("study-version-changed", handlerB);
  studyData.on("study-version-changed", handlerC);

  studyData.setActiveVersion("V3");
  const initialA = callsA;
  const initialB = callsB;
  const initialC = callsC;

  // Unsubscribe only B
  studyData.off("study-version-changed", handlerB);
  studyData.setActiveVersion("V1");

  assert(
    callsA > initialA && callsC > initialC && callsB === initialB,
    "1.5 Unsubscribing handlerB leaves handlerA and handlerC active and firing"
  );

  // Clean up
  studyData.off("study-version-changed", handlerA);
  studyData.off("study-version-changed", handlerC);
}

// Test 1.6: Same handler subscribed to two distinct events
{
  let count = 0;
  const dualHandler = () => { count++; };

  studyData.on("study-version-changed", dualHandler);
  studyData.on("timestep-changed", dualHandler);

  studyData.setActiveVersion("V2"); // count = 1
  const afterVersion = count;
  studyData.setActiveTimeStep(1); // count = 2
  const afterStep = count;

  // Unsubscribe from version only
  studyData.off("study-version-changed", dualHandler);
  studyData.setActiveVersion("V3"); // should not increment
  const afterSecondVersion = count;

  studyData.setActiveTimeStep(2); // should increment
  const afterSecondStep = count;

  assert(
    afterVersion === 1 &&
    afterStep === 2 &&
    afterSecondVersion === 2 &&
    afterSecondStep === 3,
    "1.6 Unsubscribing handler from event X does NOT affect its subscription to event Y"
  );

  studyData.off("timestep-changed", dualHandler);
}

// Test 1.7: Re-subscribing previously unsubscribed handler
{
  let count = 0;
  const handler = () => { count++; };

  studyData.on("study-version-changed", handler);
  studyData.setActiveVersion("V1"); // 1
  studyData.off("study-version-changed", handler);
  studyData.setActiveVersion("V2"); // still 1

  // Re-subscribe
  studyData.on("study-version-changed", handler);
  studyData.setActiveVersion("V3"); // 2

  assert(count === 2, "1.7 A previously unsubscribed handler can be cleanly re-subscribed and works as expected");
  studyData.off("study-version-changed", handler);
}

// Test 1.8: Calling off() with unregistered event or unregistered handler
{
  let threw = false;
  try {
    studyData.off("completely-nonexistent-event", () => {});
    studyData.off("study-version-changed", () => {});
  } catch (e) {
    threw = true;
  }
  assert(!threw, "1.8 off() handles non-existent events and unregistered handlers without throwing");
}

// Test 1.9: Calling off() with null or undefined handler
{
  let threw = false;
  try {
    studyData.off("study-version-changed", null);
    studyData.off("study-version-changed", undefined);
    studyData.off(null, () => {});
  } catch (e) {
    threw = true;
  }
  assert(!threw, "1.9 off() handles null or undefined arguments safely without crashing");
}

// Test 1.10: Unsubscribing self from within the event listener
{
  let runCount = 0;
  let selfUnsubCalled = false;
  const selfUnsubHandler = () => {
    runCount++;
    studyData.off("study-version-changed", selfUnsubHandler);
    selfUnsubCalled = true;
  };

  studyData.on("study-version-changed", selfUnsubHandler);
  studyData.setActiveVersion("V1");
  studyData.setActiveVersion("V2");
  studyData.setActiveVersion("V3");

  assert(
    runCount === 1 && selfUnsubCalled,
    "1.10 Listener can safely unsubscribe itself during execution without throwing or duplicate runs"
  );
}

console.log("\n--- Suite 2: BUG-E2S-002 setActiveTimeStep Fuzzing & Boundary Stress Tests ---");

// Test 2.1: Non-numeric strings default safely to 0 without NaN
{
  const adversarialStrings = [
    "invalid",
    "step_alpha",
    "undefined",
    "null",
    "NaN",
    "",
    "   ",
    "step 3",
    "0xZZ",
    "true",
    "false"
  ];

  let anyNaN = false;
  let allZero = true;

  for (const str of adversarialStrings) {
    studyData.setActiveTimeStep(str);
    const step = studyData.getState().activeTimeStep;
    if (Number.isNaN(step)) {
      anyNaN = true;
    }
    // "true" and "false" in JS Number("true") is NaN -> clamped to 0
    if (step !== 0) {
      allZero = false;
    }
  }

  assert(
    !anyNaN && allZero,
    "2.1 All invalid/non-numeric strings safely default to 0 without NaN propagation"
  );
}

// Test 2.2: Numeric string inputs correctly parse and clamp
{
  studyData.setActiveTimeStep("0");
  const s0 = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep("3");
  const s3 = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep("4");
  const s4 = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(" 2 ");
  const s2 = studyData.getState().activeTimeStep;

  assert(
    s0 === 0 && s3 === 3 && s4 === 4 && s2 === 2,
    "2.2 Valid numeric strings ('0', '3', '4', ' 2 ') parse to corresponding integers"
  );
}

// Test 2.3: Floating point numbers and numeric strings
{
  studyData.setActiveTimeStep(2.999);
  const s2 = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep("3.7");
  const s3 = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(0.0001);
  const s0 = studyData.getState().activeTimeStep;

  assert(
    s2 === 2 && s3 === 3 && s0 === 0,
    "2.3 Floating point numbers are properly floored to integer step indices"
  );
}

// Test 2.4: Out-of-bounds numbers and extreme values
{
  studyData.setActiveTimeStep(-100);
  const sNeg = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(100);
  const sPos = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(-Infinity);
  const sNegInf = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(Infinity);
  const sPosInf = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(Number.MAX_SAFE_INTEGER);
  const sMaxSafe = studyData.getState().activeTimeStep;
  studyData.setActiveTimeStep(Number.MIN_SAFE_INTEGER);
  const sMinSafe = studyData.getState().activeTimeStep;

  assert(
    sNeg === 0 && sPos === 4 && sNegInf === 0 && sPosInf === 0 && sMaxSafe === 4 && sMinSafe === 0,
    "2.4 Extreme negative, positive, and infinite values clamp strictly within [0, 4] (Infinity defaults to 0 via isFinite)"
  );
}

// Test 2.5: Complex object, array, null, undefined, NaN inputs
{
  const complexInputs = [
    { input: null, expected: 0 },
    { input: undefined, expected: 0 },
    { input: NaN, expected: 0 },
    { input: {}, expected: 0 },
    { input: [], expected: 0 },
    { input: [3], expected: 3 }, // Number([3]) === 3
    { input: [1, 2], expected: 0 } // Number([1, 2]) === NaN -> 0
  ];

  let passed = true;
  for (const { input, expected } of complexInputs) {
    studyData.setActiveTimeStep(input);
    const step = studyData.getState().activeTimeStep;
    if (step !== expected || Number.isNaN(step)) {
      passed = false;
      console.error(`    Mismatch for input:`, input, `got:`, step, `expected:`, expected);
    }
  }

  assert(
    passed,
    "2.5 Objects, arrays, null, undefined, and NaN resolve safely to valid clamped integers without NaN"
  );
}

// Test 2.6: Event emission verification for timestep-changed
{
  let lastEvent = null;
  const listener = (detail) => {
    lastEvent = detail;
  };

  studyData.on("timestep-changed", listener);

  studyData.setActiveTimeStep(3);
  const e3 = { ...lastEvent };

  studyData.setActiveTimeStep("invalid");
  const eInvalid = { ...lastEvent };

  studyData.setActiveTimeStep(999);
  const eMax = { ...lastEvent };

  studyData.off("timestep-changed", listener);

  const e3Valid = e3.step === 3 && e3.leadHours === 36 && e3.waypoint && e3.waypoint.step === 3;
  const eInvValid = eInvalid.step === 0 && eInvalid.leadHours === 0 && eInvalid.waypoint && eInvalid.waypoint.step === 0;
  const eMaxValid = eMax.step === 4 && eMax.leadHours === 48 && eMax.waypoint && eMax.waypoint.step === 4;

  assert(
    e3Valid && eInvValid && eMaxValid,
    "2.6 'timestep-changed' dispatches consistent detail payload { step, leadHours, waypoint } with 0 NaN"
  );
}

console.log("\n===============================================================================");
console.log(`TEST SUMMARY: Total: ${totalTests} | Passed: ${passedTests} | Failed: ${failedTests}`);
console.log(`CONFIRMED DEFECTS DISCOVERED: ${defects.length}`);
console.log("===============================================================================\n");

if (failedTests > 0 || defects.length > 0) {
  console.error("EMPIRICAL VERDICT: DEFECTS DETECTED (REQUEST_CHANGES)");
  process.exit(1);
} else {
  console.log("EMPIRICAL VERDICT: ALL PASS (APPROVE)");
  process.exit(0);
}
