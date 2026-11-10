// Automated Headless Browser Verifier for Earth-2 SAR & InSAR Mission Twin
// Uses native Node.js v24 global WebSocket and fetch with Chrome DevTools Protocol (CDP)
// Target environments: Local Build Preview (http://127.0.0.1:4173) and Production (https://earth2-sar-insar.vercel.app)

import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const VIEWER_APP_DIR = path.resolve(__dirname, '..');

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const LOCAL_PREVIEW_PORT = 4173;
const LOCAL_PREVIEW_URL = `http://127.0.0.1:${LOCAL_PREVIEW_PORT}`;
const PROD_URL = 'https://earth2-sar-insar.vercel.app';

// Assets to verify directly
const ASSETS_TO_CHECK = [
  '/',
  '/favicon.svg',
  '/favicon.ico',
  '/reports/EARTH2_X_BAND_SAR_INSAR_ENGINEERING_REPORT.pdf',
  '/textures/earth_satellite_8k.jpg',
  '/textures/earth_normal_4k.jpg',
  '/textures/earth_citylights_4k.jpg',
  '/textures/earth_clouds_4k.jpg',
  '/textures/earth_roughness.jpg',
  '/textures/earth_t2m.jpg',
  '/textures/earth_elevation.jpg',
  '/textures/earth_tendency.jpg',
  '/01_probabilistic_ensemble_spread.png',
  '/02_cyclone_tracking_trajectory.png',
  '/03_prognostic_model_benchmark.png',
  '/04_mesoscale_super_resolution.png',
  '/05_data_assimilation_increment.png',
  '/06_geoint_sar_aps_trifecta.png'
];

async function verifyAssets(baseUrl, label) {
  console.log(`\n--- [Asset Health Check] ${label} (${baseUrl}) ---`);
  const results = [];
  for (const assetPath of ASSETS_TO_CHECK) {
    const fullUrl = `${baseUrl.replace(/\/$/, '')}${assetPath}`;
    try {
      const res = await fetch(fullUrl, { method: 'HEAD' });
      const status = res.status;
      const contentType = res.headers.get('content-type') || 'unknown';
      const contentLength = res.headers.get('content-length') || 'unknown';
      const passed = status === 200;
      results.push({ assetPath, fullUrl, status, contentType, contentLength, passed });
      console.log(`  [${passed ? 'PASS' : 'FAIL'}] HTTP ${status} | ${contentType} | ${contentLength} bytes | ${assetPath}`);
    } catch (err) {
      results.push({ assetPath, fullUrl, status: 'ERROR', error: err.message, passed: false });
      console.log(`  [FAIL] Error fetching ${fullUrl}: ${err.message}`);
    }
  }
  const failed = results.filter(r => !r.passed);
  return { results, failedCount: failed.length };
}

function startVitePreview() {
  console.log(`\n--- Starting Vite Preview Server on port ${LOCAL_PREVIEW_PORT} ---`);
  const isWindows = process.platform === 'win32';
  const proc = isWindows
    ? spawn('cmd.exe', ['/c', 'npx', 'vite', 'preview', '--port', String(LOCAL_PREVIEW_PORT), '--host', '127.0.0.1'], {
        cwd: VIEWER_APP_DIR,
        stdio: 'pipe'
      })
    : spawn('npx', ['vite', 'preview', '--port', String(LOCAL_PREVIEW_PORT), '--host', '127.0.0.1'], {
        cwd: VIEWER_APP_DIR,
        stdio: 'pipe'
      });

  proc.stdout.on('data', d => {
    // console.log(`[vite preview stdout] ${d}`);
  });
  proc.stderr.on('data', d => {
    // console.error(`[vite preview stderr] ${d}`);
  });

  return proc;
}

function killProcessTree(proc) {
  if (!proc || !proc.pid) return;
  if (process.platform === 'win32') {
    try {
      spawn('taskkill.exe', ['/F', '/T', '/PID', String(proc.pid)], { stdio: 'ignore' });
    } catch (e) {}
  } else {
    try {
      proc.kill('SIGKILL');
    } catch (e) {}
  }
}

async function waitForServer(url, maxAttempts = 30, intervalMs = 300) {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const res = await fetch(url, { method: 'HEAD' });
      if (res.ok) return true;
    } catch (e) {
      // ignore
    }
    await new Promise(r => setTimeout(r, intervalMs));
  }
  return false;
}

async function runCdpSession(targetUrl, suiteLabel, cdpPort) {
  console.log(`\n======================================================`);
  console.log(`  CDP TEST SUITE: ${suiteLabel}`);
  console.log(`  Target: ${targetUrl}`);
  console.log(`======================================================`);

  const tmpUserDataDir = path.join(os.tmpdir(), `chrome_cdp_${cdpPort}_${Date.now()}`);
  fs.mkdirSync(tmpUserDataDir, { recursive: true });

  const chrome = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${cdpPort}`,
    `--user-data-dir=${tmpUserDataDir}`,
    '--use-gl=angle',
    '--use-angle=swiftshader',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-gpu-sandbox',
    '--window-size=1920,1080'
  ]);

  const testReport = {
    suiteLabel,
    targetUrl,
    tests: [],
    consoleErrors: [],
    consoleWarnings: [],
    runtimeExceptions: [],
    networkFailures: [],
    passed: true
  };

  try {
    // Wait for Chrome CDP port
    let connected = false;
    for (let i = 0; i < 25; i++) {
      await new Promise(r => setTimeout(r, 200));
      try {
        const res = await fetch(`http://127.0.0.1:${cdpPort}/json/version`);
        if (res.ok) {
          connected = true;
          break;
        }
      } catch (e) {}
    }
    if (!connected) {
      throw new Error(`Chrome failed to start CDP listener on port ${cdpPort}`);
    }

    // Open target tab
    const newTabRes = await fetch(`http://127.0.0.1:${cdpPort}/json/new?${targetUrl}`, { method: 'PUT' });
    const tab = await newTabRes.json();
    const ws = new WebSocket(tab.webSocketDebuggerUrl);

    let msgId = 1;
    const pendingCallbacks = new Map();

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && pendingCallbacks.has(msg.id)) {
        pendingCallbacks.get(msg.id)(msg.result || msg.error);
        pendingCallbacks.delete(msg.id);
      }
      if (msg.method === 'Runtime.consoleAPICalled') {
        const type = msg.params.type;
        const text = msg.params.args.map(a => a.value !== undefined ? String(a.value) : JSON.stringify(a)).join(' ');
        if (type === 'error') {
          console.error(`  [CONSOLE ERROR] ${text}`);
          testReport.consoleErrors.push(text);
        } else if (type === 'warning') {
          testReport.consoleWarnings.push(text);
        }
      }
      if (msg.method === 'Runtime.exceptionThrown') {
        const details = msg.params.exceptionDetails;
        const desc = details.exception?.description || details.text;
        console.error(`  [UNCAUGHT EXCEPTION] ${desc}`);
        testReport.runtimeExceptions.push(desc);
      }
      if (msg.method === 'Network.responseReceived') {
        const resp = msg.params.response;
        if (resp.status >= 400) {
          const failureDesc = `${resp.status} ${resp.statusText}: ${resp.url}`;
          console.warn(`  [NETWORK RESPONSE >= 400] ${failureDesc}`);
          testReport.networkFailures.push(failureDesc);
        }
      }
      if (msg.method === 'Network.loadingFailed') {
        const failText = `Failed loading ${msg.params.errorText || 'unknown'} (type: ${msg.params.type}): requestId ${msg.params.requestId}`;
        console.warn(`  [NETWORK LOADING FAILED] ${failText}`);
        testReport.networkFailures.push(failText);
      }
    };

    function send(method, params = {}) {
      return new Promise((resolve) => {
        const id = msgId++;
        pendingCallbacks.set(id, resolve);
        ws.send(JSON.stringify({ id, method, params }));
      });
    }

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });

    await send('Page.enable');
    await send('Runtime.enable');
    await send('Network.enable');

    console.log('  Waiting 4.5s for WebGL scene, shaders, and textures to initialize...');
    await new Promise(r => setTimeout(r, 4500));

    // -------------------------------------------------------------------------
    // TEST 1: Desktop Viewport (1920x1080)
    // -------------------------------------------------------------------------
    console.log('\n  --- Test 1: Desktop Viewport (1920x1080, scale 1.0) ---');
    await send('Emulation.setDeviceMetricsOverride', {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1,
      mobile: false
    });
    await send('Runtime.evaluate', { expression: 'window.dispatchEvent(new Event("resize"))' });
    await new Promise(r => setTimeout(r, 600));

    const desktopEval = await send('Runtime.evaluate', {
      expression: `(() => {
        const canvas = document.querySelector('#canvas-container canvas') || document.querySelector('canvas');
        const hud = document.querySelector('.hud-panel');
        const cam = document.querySelector('.camera-widget');
        const timeline = document.querySelector('.timeline-bar');
        const gl = canvas ? (canvas.getContext('webgl2') || canvas.getContext('webgl')) : null;

        return {
          title: document.title,
          h1: document.querySelector('h1')?.innerText,
          hasCanvas: !!canvas,
          canvasClientWidth: canvas?.clientWidth,
          canvasClientHeight: canvas?.clientHeight,
          canvasWidth: canvas?.width,
          canvasHeight: canvas?.height,
          webglContextLost: gl ? gl.isContextLost() : true,
          webglRenderer: gl ? gl.getParameter(gl.RENDERER) : null,
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          noOverflow: document.documentElement.scrollWidth <= window.innerWidth,
          hudRect: hud ? hud.getBoundingClientRect().toJSON() : null,
          hudVisible: hud ? window.getComputedStyle(hud).display !== 'none' : false,
          camRect: cam ? cam.getBoundingClientRect().toJSON() : null,
          camVisible: cam ? window.getComputedStyle(cam).display !== 'none' : false,
          timelineRect: timeline ? timeline.getBoundingClientRect().toJSON() : null,
          timelineVisible: timeline ? window.getComputedStyle(timeline).display !== 'none' : false
        };
      })()`,
      returnByValue: true
    });

    const dRes = desktopEval.result.value;
    console.log('  Desktop Evaluation Result:', JSON.stringify(dRes, null, 2));

    const dPass = dRes.hasCanvas &&
                  !dRes.webglContextLost &&
                  dRes.noOverflow &&
                  dRes.hudVisible &&
                  dRes.camVisible &&
                  dRes.timelineVisible;

    testReport.tests.push({
      name: 'Desktop Viewport (1920x1080) Structure & Layout',
      passed: dPass,
      details: dRes
    });
    console.log(`  [${dPass ? 'PASS' : 'FAIL'}] Desktop Viewport (1920x1080)`);

    // -------------------------------------------------------------------------
    // TEST 2: Mobile Viewport (<480px, e.g. 390x844 iPhone 14/15 profile)
    // -------------------------------------------------------------------------
    console.log('\n  --- Test 2: Mobile Viewport (390x844, scale 3.0, <480px) ---');
    await send('Emulation.setDeviceMetricsOverride', {
      width: 390,
      height: 844,
      deviceScaleFactor: 3,
      mobile: true
    });
    await send('Runtime.evaluate', { expression: 'window.dispatchEvent(new Event("resize"))' });
    await new Promise(r => setTimeout(r, 800));

    const mobileEval = await send('Runtime.evaluate', {
      expression: `(() => {
        const canvas = document.querySelector('#canvas-container canvas') || document.querySelector('canvas');
        const hud = document.querySelector('.hud-panel');
        const cam = document.querySelector('.camera-widget');
        const timeline = document.querySelector('.timeline-bar');
        const hudRect = hud ? hud.getBoundingClientRect().toJSON() : null;
        const camRect = cam ? cam.getBoundingClientRect().toJSON() : null;
        const timelineRect = timeline ? timeline.getBoundingClientRect().toJSON() : null;

        const maxAllowedHudHeight = window.innerHeight * 0.40 + 1.0; // 40vh with sub-pixel tolerance
        const hudHeightValid = hudRect ? (hudRect.height <= maxAllowedHudHeight) : false;

        return {
          hasCanvas: !!canvas,
          canvasClientWidth: canvas?.clientWidth,
          canvasClientHeight: canvas?.clientHeight,
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          noOverflow: document.documentElement.scrollWidth <= window.innerWidth,
          innerHeight: window.innerHeight,
          hudHeight: hudRect?.height,
          maxAllowedHudHeight,
          hudHeightValid,
          hudRect,
          camRect,
          timelineRect
        };
      })()`,
      returnByValue: true
    });

    const mRes = mobileEval.result.value;
    console.log('  Mobile Evaluation Result:', JSON.stringify(mRes, null, 2));

    const mPass = mRes.hasCanvas &&
                  mRes.noOverflow &&
                  mRes.hudHeightValid;

    testReport.tests.push({
      name: 'Mobile Viewport (390x844) Structure, Layout & HUD <= 40vh',
      passed: mPass,
      details: mRes
    });
    console.log(`  [${mPass ? 'PASS' : 'FAIL'}] Mobile Viewport (390x844) - HUD Height: ${mRes.hudHeight}px <= ${mRes.maxAllowedHudHeight}px`);

    // -------------------------------------------------------------------------
    // TEST 3: Ultra-Narrow Stress Viewport (320x568, iPhone SE profile)
    // -------------------------------------------------------------------------
    console.log('\n  --- Test 3: Ultra-Narrow Stress Viewport (320x568, iPhone SE) ---');
    await send('Emulation.setDeviceMetricsOverride', {
      width: 320,
      height: 568,
      deviceScaleFactor: 2,
      mobile: true
    });
    await send('Runtime.evaluate', { expression: 'window.dispatchEvent(new Event("resize"))' });
    await new Promise(r => setTimeout(r, 600));

    const narrowEval = await send('Runtime.evaluate', {
      expression: `(() => {
        const hud = document.querySelector('.hud-panel');
        const hudRect = hud ? hud.getBoundingClientRect().toJSON() : null;
        const maxAllowed = window.innerHeight * 0.40 + 1.0;
        return {
          scrollWidth: document.documentElement.scrollWidth,
          innerWidth: window.innerWidth,
          noOverflow: document.documentElement.scrollWidth <= window.innerWidth,
          hudHeight: hudRect?.height,
          maxAllowed,
          hudHeightValid: hudRect ? hudRect.height <= maxAllowed : false
        };
      })()`,
      returnByValue: true
    });
    const nRes = narrowEval.result.value;
    const nPass = nRes.noOverflow && nRes.hudHeightValid;
    testReport.tests.push({
      name: 'Ultra-Narrow (320x568) Stress Test',
      passed: nPass,
      details: nRes
    });
    console.log(`  [${nPass ? 'PASS' : 'FAIL'}] Ultra-Narrow 320px - Overflow: ${!nRes.noOverflow ? 'YES' : 'NONE'}, HUD Height: ${nRes.hudHeight}px`);

    // -------------------------------------------------------------------------
    // TEST 4: Rapid Viewport Transition Jitter Stress Test
    // -------------------------------------------------------------------------
    console.log('\n  --- Test 4: Rapid Viewport Jitter Stress Test ---');
    const jitterDims = [
      { w: 1920, h: 1080, m: false },
      { w: 768, h: 1024, m: true },
      { w: 390, h: 844, m: true },
      { w: 320, h: 568, m: true },
      { w: 1920, h: 1080, m: false }
    ];
    let jitterPass = true;
    for (const dim of jitterDims) {
      await send('Emulation.setDeviceMetricsOverride', {
        width: dim.w,
        height: dim.h,
        deviceScaleFactor: dim.m ? 2 : 1,
        mobile: dim.m
      });
      await send('Runtime.evaluate', { expression: 'window.dispatchEvent(new Event("resize"))' });
      await new Promise(r => setTimeout(r, 150));
    }
    await new Promise(r => setTimeout(r, 500));
    const jitterCheck = await send('Runtime.evaluate', {
      expression: `(() => {
        const canvas = document.querySelector('canvas');
        const gl = canvas ? (canvas.getContext('webgl2') || canvas.getContext('webgl')) : null;
        return {
          hasCanvas: !!canvas,
          contextLost: gl ? gl.isContextLost() : true,
          noOverflow: document.documentElement.scrollWidth <= window.innerWidth
        };
      })()`,
      returnByValue: true
    });
    jitterPass = jitterCheck.result.value.hasCanvas && !jitterCheck.result.value.contextLost;
    testReport.tests.push({
      name: 'Rapid Viewport Jitter & Resize Resilience',
      passed: jitterPass,
      details: jitterCheck.result.value
    });
    console.log(`  [${jitterPass ? 'PASS' : 'FAIL'}] Jitter Stress Test - WebGL Context Preserved`);

    // -------------------------------------------------------------------------
    // TEST 5: Interactive Elements Stress Test
    // -------------------------------------------------------------------------
    console.log('\n  --- Test 5: Interactive Elements & UI Controller Stress Test ---');
    const interactiveActions = [
      { name: 'Fly to Italy', selector: '#fly-italy' },
      { name: 'Fly to Japan', selector: '#fly-japan' },
      { name: 'Toggle Optical Clouds', selector: '#layer-clouds' },
      { name: 'Toggle 24h Tendency layer', selector: '#layer-tend' },
      { name: 'Toggle Satellite 8K PBR layer', selector: '#layer-sat' },
      { name: 'Toggle Ensemble Spread layer', selector: '#layer-spread' },
      { name: 'Toggle CATALYST APS mode', selector: '#toggle-catalyst-aps' },
      { name: 'Toggle SAR Display Mode', selector: '#toggle-sar-mode' },
      { name: 'Click Play Forecast', selector: '#btn-play-forecast' },
      { name: 'Open Comparison Modal', selector: '#open-comparison' }
    ];

    for (const action of interactiveActions) {
      const clickRes = await send('Runtime.evaluate', {
        expression: `(() => {
          const btn = document.querySelector('${action.selector}');
          if (!btn) return { error: 'Element not found: ${action.selector}' };
          btn.click();
          return { clicked: true };
        })()`,
        returnByValue: true
      });
      await new Promise(r => setTimeout(r, 350));
    }

    // Check modal open state and overflow
    const modalCheck = await send('Runtime.evaluate', {
      expression: `(() => {
        const modal = document.querySelector('#comparison-modal');
        const isHidden = modal ? modal.classList.contains('hidden') : true;
        const noOverflow = document.documentElement.scrollWidth <= window.innerWidth;
        // Close modal
        document.querySelector('#modal-close')?.click();
        return {
          modalOpened: !isHidden,
          noOverflowWithModal: noOverflow
        };
      })()`,
      returnByValue: true
    });
    await new Promise(r => setTimeout(r, 300));

    // Reset camera
    await send('Runtime.evaluate', {
      expression: 'document.querySelector("#btn-camera-reset")?.click();'
    });
    await new Promise(r => setTimeout(r, 500));

    const interactPass = modalCheck.result.value.modalOpened && modalCheck.result.value.noOverflowWithModal;
    testReport.tests.push({
      name: 'Interactive UI Buttons & Comparison Modal',
      passed: interactPass,
      details: modalCheck.result.value
    });
    console.log(`  [${interactPass ? 'PASS' : 'FAIL'}] Interactive Stress Test (Modal Opened: ${modalCheck.result.value.modalOpened})`);

    // -------------------------------------------------------------------------
    // TEST 5b: Interactive 6-Step Mission Tutorial Tour
    // -------------------------------------------------------------------------
    const tourCheck = await send('Runtime.evaluate', {
      expression: `(async () => {
        const startBtn = document.querySelector('#btn-mission-tutorial');
        const card = document.querySelector('#mission-tour-card');
        const nextBtn = document.querySelector('#tour-next-btn');
        const closeBtn = document.querySelector('#tour-close-btn');
        if (!startBtn || !card || !nextBtn || !closeBtn) return { ok: false, reason: 'missing tour elements' };
        startBtn.click();
        const open1 = !card.classList.contains('hidden');
        const badge1 = document.querySelector('#tour-step-badge')?.innerText || '';
        nextBtn.click();
        const badge2 = document.querySelector('#tour-step-badge')?.innerText || '';
        nextBtn.click();
        nextBtn.click();
        const badge4 = document.querySelector('#tour-step-badge')?.innerText || '';
        closeBtn.click();
        const closed = card.classList.contains('hidden');
        return { ok: open1 && badge1.includes('1 / 6') && badge2.includes('2 / 6') && badge4.includes('4 / 6') && closed, badge1, badge2, badge4, closed };
      })()`,
      awaitPromise: true,
      returnByValue: true
    });
    const tRes = tourCheck.result.value;
    testReport.tests.push({
      name: 'Interactive 6-Step Mission Tutorial Tour',
      passed: Boolean(tRes?.ok),
      details: tRes
    });
    console.log(`  [${tRes?.ok ? 'PASS' : 'FAIL'}] Mission Tutorial Tour (Step 1 -> 2 -> 4 -> Close: ${tRes?.ok})`);

    // -------------------------------------------------------------------------
    // TEST 6: Brand Scrub & Attribution Verification in Rendered DOM
    // -------------------------------------------------------------------------
    console.log('\n  --- Test 6: Brand Scrub & Attribution Audit in Rendered DOM ---');
    const brandAudit = await send('Runtime.evaluate', {
      expression: `(() => {
        const fullHtml = document.documentElement.innerHTML;
        const fullText = document.documentElement.innerText;
        const bannedPatterns = [
          /origin[-_ ]?datum/gi,
          /eo[-_ ]?obscura/gi
        ];
        const violations = [];
        for (const pat of bannedPatterns) {
          const mHtml = fullHtml.match(pat);
          if (mHtml) violations.push({ pattern: String(pat), countHtml: mHtml.length });
        }
        const hasZhane = /Zhane Daye/i.test(fullText);
        return {
          violations,
          clean: violations.length === 0,
          hasZhane
        };
      })()`,
      returnByValue: true
    });
    const bRes = brandAudit.result.value;
    const bPass = bRes.clean && bRes.hasZhane;
    testReport.tests.push({
      name: 'Brand Scrub & Zhane Daye Attribution Audit',
      passed: bPass,
      details: bRes
    });
    console.log(`  [${bPass ? 'PASS' : 'FAIL'}] Brand Scrub: Clean = ${bRes.clean}, Zhane Daye Present = ${bRes.hasZhane}`);

    // Summary of console and runtime errors
    const zeroConsoleErrors = testReport.consoleErrors.length === 0;
    const zeroExceptions = testReport.runtimeExceptions.length === 0;

    testReport.tests.push({
      name: 'Zero Console Errors',
      passed: zeroConsoleErrors,
      details: { errors: testReport.consoleErrors }
    });
    testReport.tests.push({
      name: 'Zero Runtime Exceptions',
      passed: zeroExceptions,
      details: { exceptions: testReport.runtimeExceptions }
    });

    console.log(`\n  Console Errors: ${testReport.consoleErrors.length}`);
    console.log(`  Runtime Exceptions: ${testReport.runtimeExceptions.length}`);
    console.log(`  Network Failures: ${testReport.networkFailures.length}`);

    testReport.passed = testReport.tests.every(t => t.passed);
    console.log(`\n  >>> SUITE VERDICT: ${testReport.passed ? 'ALL PASSED' : 'FAILURES DETECTED'} <<<`);

    ws.close();
  } finally {
    console.log('  Terminating Chrome instance...');
    chrome.kill('SIGKILL');
    await new Promise(r => setTimeout(r, 800));
    try {
      fs.rmSync(tmpUserDataDir, { recursive: true, force: true });
    } catch (e) {}
  }

  return testReport;
}

async function main() {
  console.log('================================================================');
  console.log('EARTH-2 SAR & InSAR MISSION TWIN — HEADLESS BROWSER VERIFIER');
  console.log('================================================================');

  // Step 1: Production Asset Health Check
  const prodAssets = await verifyAssets(PROD_URL, 'Production Vercel Assets');

  // Step 2: Production CDP Verification
  const prodReport = await runCdpSession(PROD_URL, 'Production Vercel (https://earth2-sar-insar.vercel.app)', 9226);

  // Step 3: Local Build Preview & Verification
  const previewProc = startVitePreview();
  let localReport = null;
  let localAssets = null;

  try {
    const ready = await waitForServer(LOCAL_PREVIEW_URL, 30, 250);
    if (!ready) {
      throw new Error(`Vite preview failed to respond on ${LOCAL_PREVIEW_URL} within 7.5s`);
    }
    console.log(`Vite preview confirmed active on ${LOCAL_PREVIEW_URL}`);

    localAssets = await verifyAssets(LOCAL_PREVIEW_URL, 'Local Vite Preview Assets');
    localReport = await runCdpSession(LOCAL_PREVIEW_URL, 'Local Build Preview (http://127.0.0.1:4173)', 9227);
  } finally {
    console.log('\n--- Shutting down Vite Preview Server ---');
    killProcessTree(previewProc);
  }

  // Summary Report
  console.log('\n================================================================');
  console.log('                    OVERALL VERIFICATION SUMMARY               ');
  console.log('================================================================');
  console.log(`Production Asset Failures: ${prodAssets.failedCount}`);
  console.log(`Production CDP Passed:     ${prodReport.passed}`);
  console.log(`Local Asset Failures:      ${localAssets ? localAssets.failedCount : 'N/A'}`);
  console.log(`Local CDP Passed:          ${localReport ? localReport.passed : false}`);

  const overallPassed = prodAssets.failedCount === 0 &&
                        prodReport.passed &&
                        (localAssets && localAssets.failedCount === 0) &&
                        (localReport && localReport.passed);

  console.log(`\nFINAL SYSTEM VERDICT: ${overallPassed ? 'APPROVE' : 'REQUEST_CHANGES'}`);

  // Return full JSON payload for programmatic consumption or logging
  const finalSummary = {
    timestamp: new Date().toISOString(),
    overallPassed,
    verdict: overallPassed ? 'APPROVE' : 'REQUEST_CHANGES',
    prodAssets,
    prodReport,
    localAssets,
    localReport
  };

  fs.writeFileSync(path.join(VIEWER_APP_DIR, 'test', 'last_cdp_verification_result.json'), JSON.stringify(finalSummary, null, 2));

  if (!overallPassed) {
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Fatal verification failure:', err);
  process.exit(1);
});
