/**
 * test_framework.js
 * Lightweight, zero-dependency test runner and assertion library
 * Designed for OD-EARTH2-001 / EO-OBSCURA 3D WebGL Digital Twin E2E Testing.
 */

// ANSI Color Codes
const ANSI = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  gray: '\x1b[90m',
};

// Deep equality check helper
function deepEqualHelper(a, b) {
  if (Object.is(a, b)) return true;
  if (typeof a !== 'object' || a === null || typeof b !== 'object' || b === null) return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;

  const keysA = Reflect.ownKeys(a);
  const keysB = Reflect.ownKeys(b);
  if (keysA.length !== keysB.length) return false;

  for (const key of keysA) {
    if (!Reflect.has(b, key) || !deepEqualHelper(a[key], b[key])) return false;
  }
  return true;
}

export const assert = {
  equal(actual, expected, message) {
    if (actual != expected) {
      throw new Error(message || `AssertionError: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    }
  },

  strictEqual(actual, expected, message) {
    if (!Object.is(actual, expected)) {
      throw new Error(message || `AssertionError: expected strict equal ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
    }
  },

  notStrictEqual(actual, expected, message) {
    if (Object.is(actual, expected)) {
      throw new Error(message || `AssertionError: expected not strict equal, but both are ${JSON.stringify(actual)}`);
    }
  },

  deepEqual(actual, expected, message) {
    if (!deepEqualHelper(actual, expected)) {
      throw new Error(message || `AssertionError: deepEqual mismatch.\nExpected: ${JSON.stringify(expected, null, 2)}\nActual:   ${JSON.stringify(actual, null, 2)}`);
    }
  },

  ok(value, message) {
    if (!value) {
      throw new Error(message || `AssertionError: expected truthy value, got ${JSON.stringify(value)}`);
    }
  },

  notOk(value, message) {
    if (value) {
      throw new Error(message || `AssertionError: expected falsy value, got ${JSON.stringify(value)}`);
    }
  },

  closeTo(actual, expected, delta = 1e-4, message) {
    if (typeof actual !== 'number' || typeof expected !== 'number' || isNaN(actual) || isNaN(expected)) {
      throw new Error(message || `AssertionError: closeTo operands must be numbers. Got actual=${actual}, expected=${expected}`);
    }
    const diff = Math.abs(actual - expected);
    if (diff > delta) {
      throw new Error(message || `AssertionError: expected ${actual} to be close to ${expected} within delta ${delta} (diff was ${diff})`);
    }
  },

  greaterThan(actual, expected, message) {
    if (!(actual > expected)) {
      throw new Error(message || `AssertionError: expected ${actual} > ${expected}`);
    }
  },

  lessThan(actual, expected, message) {
    if (!(actual < expected)) {
      throw new Error(message || `AssertionError: expected ${actual} < ${expected}`);
    }
  },

  includes(collection, item, message) {
    if (typeof collection === 'string') {
      if (!collection.includes(item)) {
        throw new Error(message || `AssertionError: expected string to include "${item}". String was "${collection}"`);
      }
    } else if (Array.isArray(collection)) {
      if (!collection.includes(item)) {
        throw new Error(message || `AssertionError: expected array to include ${JSON.stringify(item)}`);
      }
    } else if (collection && typeof collection === 'object') {
      if (!Object.values(collection).includes(item)) {
        throw new Error(message || `AssertionError: expected object values to include ${JSON.stringify(item)}`);
      }
    } else {
      throw new Error(message || `AssertionError: invalid collection passed to assert.includes`);
    }
  },

  matches(str, regex, message) {
    if (typeof str !== 'string' || !regex.test(str)) {
      throw new Error(message || `AssertionError: expected string "${str}" to match regex ${regex}`);
    }
  },

  throws(fn, expectedRegexOrMessage, message) {
    let threw = false;
    let actualError = null;
    try {
      fn();
    } catch (err) {
      threw = true;
      actualError = err;
    }
    if (!threw) {
      throw new Error(message || `AssertionError: expected function to throw, but it did not`);
    }
    if (expectedRegexOrMessage) {
      if (expectedRegexOrMessage instanceof RegExp) {
        if (!expectedRegexOrMessage.test(actualError.message)) {
          throw new Error(`AssertionError: expected error message matching ${expectedRegexOrMessage}, got "${actualError.message}"`);
        }
      } else if (typeof expectedRegexOrMessage === 'string') {
        if (!actualError.message.includes(expectedRegexOrMessage)) {
          throw new Error(`AssertionError: expected error message containing "${expectedRegexOrMessage}", got "${actualError.message}"`);
        }
      }
    }
  },

  doesNotThrow(fn, message) {
    try {
      fn();
    } catch (err) {
      throw new Error(message || `AssertionError: expected function not to throw, but caught error: ${err.message}`);
    }
  }
};

// Test Suite Collector
class TestRunner {
  constructor() {
    this.suites = [];
    this.currentSuite = null;
    this.currentBeforeEach = [];
    this.currentAfterEach = [];
    this.stats = {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      startTime: 0,
      endTime: 0
    };
  }

  describe(name, fn) {
    const parentSuite = this.currentSuite;
    const parentBeforeEach = [...this.currentBeforeEach];
    const parentAfterEach = [...this.currentAfterEach];

    const suite = {
      name,
      tests: [],
      subSuites: [],
      parent: parentSuite,
      beforeEach: [...this.currentBeforeEach],
      afterEach: [...this.currentAfterEach]
    };

    if (parentSuite) {
      parentSuite.subSuites.push(suite);
    } else {
      this.suites.push(suite);
    }

    this.currentSuite = suite;
    fn();
    this.currentSuite = parentSuite;
    this.currentBeforeEach = parentBeforeEach;
    this.currentAfterEach = parentAfterEach;
  }

  test(name, fn, options = {}) {
    if (!this.currentSuite) {
      this.describe('Default Suite', () => {
        this.test(name, fn, options);
      });
      return;
    }

    this.currentSuite.tests.push({
      name,
      fn,
      skip: options.skip || false,
      beforeEach: [...this.currentBeforeEach],
      afterEach: [...this.currentAfterEach]
    });
  }

  it(name, fn, options = {}) {
    this.test(name, fn, options);
  }

  beforeEach(fn) {
    this.currentBeforeEach.push(fn);
  }

  afterEach(fn) {
    this.currentAfterEach.push(fn);
  }

  async runSuite(suite, depth = 0) {
    const indent = '  '.repeat(depth);
    console.log(`${indent}${ANSI.bold}${ANSI.cyan}▸ ${suite.name}${ANSI.reset}`);

    for (const testCase of suite.tests) {
      this.stats.total++;
      const testIndent = '  '.repeat(depth + 1);

      if (testCase.skip) {
        this.stats.skipped++;
        console.log(`${testIndent}${ANSI.yellow}○ [SKIP] ${testCase.name}${ANSI.reset}`);
        continue;
      }

      const t0 = performance.now();
      try {
        // Run beforeEach hooks
        for (const hook of testCase.beforeEach) {
          await hook();
        }

        // Run test
        await testCase.fn();

        // Run afterEach hooks
        for (const hook of testCase.afterEach) {
          await hook();
        }

        const duration = (performance.now() - t0).toFixed(2);
        this.stats.passed++;
        console.log(`${testIndent}${ANSI.green}✓ ${testCase.name}${ANSI.reset} ${ANSI.gray}(${duration}ms)${ANSI.reset}`);
      } catch (err) {
        const duration = (performance.now() - t0).toFixed(2);
        this.stats.failed++;
        console.log(`${testIndent}${ANSI.red}✗ ${testCase.name}${ANSI.reset} ${ANSI.gray}(${duration}ms)${ANSI.reset}`);
        console.log(`${testIndent}  ${ANSI.red}${err.message}${ANSI.reset}`);
        if (err.stack) {
          const stackLines = err.stack.split('\n').slice(1, 4);
          for (const line of stackLines) {
            console.log(`${testIndent}  ${ANSI.gray}${line.trim()}${ANSI.reset}`);
          }
        }
      }
    }

    for (const sub of suite.subSuites) {
      await this.runSuite(sub, depth + 1);
    }
  }

  async run() {
    this.stats.startTime = performance.now();
    console.log(`\n${ANSI.bold}${ANSI.blue}═══════════════════════════════════════════════════════════════════════${ANSI.reset}`);
    console.log(`${ANSI.bold}  OD-EARTH2-001 / EO-OBSCURA 3D Digital Twin E2E Test Suite${ANSI.reset}`);
    console.log(`${ANSI.bold}${ANSI.blue}═══════════════════════════════════════════════════════════════════════${ANSI.reset}\n`);

    for (const suite of this.suites) {
      await this.runSuite(suite, 0);
      console.log('');
    }

    this.stats.endTime = performance.now();
    const totalTime = ((this.stats.endTime - this.stats.startTime) / 1000).toFixed(3);

    console.log(`${ANSI.bold}${ANSI.blue}───────────────────────────────────────────────────────────────────────${ANSI.reset}`);
    console.log(`${ANSI.bold}Test Execution Summary:${ANSI.reset}`);
    console.log(`  Total:   ${this.stats.total}`);
    console.log(`  Passed:  ${ANSI.green}${this.stats.passed}${ANSI.reset}`);
    console.log(`  Failed:  ${this.stats.failed > 0 ? ANSI.red + this.stats.failed + ANSI.reset : this.stats.failed}`);
    console.log(`  Skipped: ${this.stats.skipped}`);
    console.log(`  Elapsed: ${totalTime}s`);
    console.log(`${ANSI.bold}${ANSI.blue}───────────────────────────────────────────────────────────────────────${ANSI.reset}\n`);

    return this.stats;
  }
}

// Global default runner instance
export const runner = new TestRunner();
export const describe = runner.describe.bind(runner);
export const test = runner.test.bind(runner);
export const it = runner.it.bind(runner);
export const beforeEach = runner.beforeEach.bind(runner);
export const afterEach = runner.afterEach.bind(runner);
