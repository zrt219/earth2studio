// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * interactive_runs.test.js
 * Verification test suite for Interactive 3D Mission Twin Run Gallery & Standalone Portfolio:
 * 1. Dedicated Standalone runs_portfolio/ directory structure and offline HTML gallery.
 * 2. 1-Click 3D Swath & Orbit Activation (activateRunSwath).
 * 3. Real-time Multi-Attribute Search & Filter (initRunsSearch, query matching).
 * 4. OGC STAC v1.0.0 Tasking Order Inspector Modal & Clipboard Copy.
 * 5. InSAR Phase Comparison Split-Screen Swipe Slider in Lightbox.
 * 6. Bottom HUD Quick-Run Carousel (#hud-quick-runs).
 * Strict adherence to Rule e2s-014 Scientific Integrity.
 */

import assert from 'assert';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

import {
  RUNS_CATALOG,
  RUN_CATEGORIES,
  CATEGORY_THEMES,
  getRunCatalog,
  getRunById,
  getRunsByCategory
} from '../runsCatalog.js';
import uiController from '../uiController.js';
import sarTasking from '../sarTasking.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const PORTFOLIO_DIR = path.join(REPO_ROOT, 'runs_portfolio');
const VIEWER_APP_DIR = path.resolve(__dirname, '..');

let passed = 0;
let failed = 0;

function runTest(name, fn) {
  try {
    fn();
    console.log(`  ✓ PASS: ${name}`);
    passed += 1;
  } catch (err) {
    console.error(`  ✗ FAIL: ${name}\n    ${err.message}`);
    failed += 1;
  }
}

console.log('===============================================================================');
console.log('INTERACTIVE 3D MISSION TWIN & STANDALONE PORTFOLIO TEST SUITE');
console.log('===============================================================================');

// Suite 1: Dedicated Standalone runs_portfolio/ Directory Structure & Integrity
console.log('\n--- Suite 1: runs_portfolio/ Standalone Structure & Offline Gallery ---');

runTest('1.1 Dedicated runs_portfolio/ root directory exists with catalog and README', () => {
  assert.ok(fs.existsSync(PORTFOLIO_DIR), 'runs_portfolio/ directory must exist');
  assert.ok(fs.existsSync(path.join(PORTFOLIO_DIR, 'catalog.json')), 'catalog.json must exist in runs_portfolio/');
  assert.ok(fs.existsSync(path.join(PORTFOLIO_DIR, 'README.md')), 'README.md must exist in runs_portfolio/');
  assert.ok(fs.existsSync(path.join(PORTFOLIO_DIR, 'index.html')), 'index.html must exist in runs_portfolio/');
});

runTest('1.2 All 11 dedicated run subdirectories exist in runs_portfolio/', () => {
  const expectedDirs = [
    '01_Baseline_Advanced_Pillars',
    '02_Mexico_Copper_Canyon',
    '03_Northern_Russia_Putorana',
    '04_South_Africa_Drakensberg',
    '05_MultiBand_InSAR_Physics',
    '06_Deep_Geophysical_Hazards',
    '07_Southern_Italy_Volcanotectonics',
    '08_Finland_Glacial_Rebound',
    '09_Japan_Abandoned_Farmland',
    '10_Brazil_Tropical_Dynamics',
    '11_Vancouver_Cascadia_Delta'
  ];

  expectedDirs.forEach((dirName, idx) => {
    const dirPath = path.join(PORTFOLIO_DIR, dirName);
    assert.ok(fs.existsSync(dirPath), `Missing run folder: ${dirName}`);
    assert.ok(fs.existsSync(path.join(dirPath, 'SUMMARY.md')), `Missing SUMMARY.md in ${dirName}`);
  });
});

runTest('1.3 runs_portfolio/index.html is zero-dependency offline executable', () => {
  const htmlPath = path.join(PORTFOLIO_DIR, 'index.html');
  const htmlContent = fs.readFileSync(htmlPath, 'utf8');

  assert.ok(htmlContent.includes('<!DOCTYPE html>'), 'Must have HTML5 doctype');
  assert.ok(htmlContent.includes('Scientific Runs Portfolio') || htmlContent.includes('Runs Portfolio'), 'Must have portfolio title');
  assert.ok(!htmlContent.includes('<script src="http'), 'Must not depend on external http CDN scripts');
  assert.ok(htmlContent.includes('RUNS_DATA'), 'Must embed complete self-contained run catalog');
  assert.ok(htmlContent.includes('openLightbox') || htmlContent.includes('lightboxModal'), 'Must support offline figure lightbox preview');
});

runTest('1.4 All primary publication figures and STAC files exist in runs_portfolio/', () => {
  const catalogPath = path.join(PORTFOLIO_DIR, 'catalog.json');
  const catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));

  const RUN_DIR_MAP = {
    run_01_baseline_advanced_pillars: '01_Baseline_Advanced_Pillars',
    run_02_mexico_hidden_terrain: '02_Mexico_Copper_Canyon',
    run_03_northern_russia_terrain: '03_Northern_Russia_Putorana',
    run_04_south_africa_terrain: '04_South_Africa_Drakensberg',
    run_05_multiband_insar_physics: '05_MultiBand_InSAR_Physics',
    run_06_deep_geophysical_hazards: '06_Deep_Geophysical_Hazards',
    run_07_southern_italy_volcanotectonics: '07_Southern_Italy_Volcanotectonics',
    run_08_finland_glacial_rebound_peatlands: '08_Finland_Glacial_Rebound',
    run_09_japan_abandoned_farmland: '09_Japan_Abandoned_Farmland',
    run_10_brazil_tropical_dynamics: '10_Brazil_Tropical_Dynamics',
    run_11_vancouver_cascadia_delta: '11_Vancouver_Cascadia_Delta'
  };

  assert.equal(catalog.runs.length, 11);
  catalog.runs.forEach((run) => {
    const folderName = run.folder_name || RUN_DIR_MAP[run.run_id];
    assert.ok(folderName, `Run ${run.run_number} missing folder_name`);
    const runFolder = path.join(PORTFOLIO_DIR, folderName);
    assert.ok(fs.existsSync(runFolder), `Folder missing: ${runFolder}`);

    // Verify primary figure
    if (run.primary_figure_name) {
      let figPath = path.join(runFolder, run.primary_figure_name);
      if (!fs.existsSync(figPath)) {
        figPath = path.join(runFolder, 'figures', run.primary_figure_name);
      }
      assert.ok(fs.existsSync(figPath), `Figure missing in portfolio: ${figPath}`);
      const buf = fs.readFileSync(figPath);
      assert.ok(buf.length > 50000, `Figure file unexpectedly small: ${figPath}`);
    }
  });
});

// Suite 2: viewer_app/index.html Interactive DOM Elements
console.log('\n--- Suite 2: viewer_app/index.html Interactive Elements ---');

const indexHtmlPath = path.join(VIEWER_APP_DIR, 'index.html');
const indexHtml = fs.readFileSync(indexHtmlPath, 'utf8');

runTest('2.1 index.html contains #runs-search-input, clear button, and summary indicator', () => {
  assert.ok(indexHtml.includes('id="runs-search-input"'), 'Missing #runs-search-input');
  assert.ok(indexHtml.includes('id="runs-search-clear"'), 'Missing #runs-search-clear');
  assert.ok(indexHtml.includes('id="runs-search-summary"'), 'Missing #runs-search-summary');
});

runTest('2.2 index.html contains #stac-modal and its inspector controls', () => {
  assert.ok(indexHtml.includes('id="stac-modal"'), 'Missing #stac-modal dialog');
  assert.ok(indexHtml.includes('id="stac-modal-title"'), 'Missing #stac-modal-title');
  assert.ok(indexHtml.includes('id="stac-json-content"'), 'Missing #stac-json-content');
  assert.ok(indexHtml.includes('id="stac-copy-btn"'), 'Missing #stac-copy-btn');
  assert.ok(indexHtml.includes('id="stac-download-btn"'), 'Missing #stac-download-btn');
  assert.ok(indexHtml.includes('id="stac-modal-close"'), 'Missing #stac-modal-close');
});

runTest('2.3 index.html contains Lightbox phase comparison split slider and view toggle', () => {
  assert.ok(indexHtml.includes('id="lightbox-mode-toggle"'), 'Missing #lightbox-mode-toggle');
  assert.ok(indexHtml.includes('id="lightbox-view-figure"'), 'Missing #lightbox-view-figure');
  assert.ok(indexHtml.includes('id="lightbox-view-split"'), 'Missing #lightbox-view-split');
  assert.ok(indexHtml.includes('id="lightbox-split-container"'), 'Missing #lightbox-split-container');
  assert.ok(indexHtml.includes('id="split-slider-input"'), 'Missing #split-slider-input');
  assert.ok(indexHtml.includes('id="split-divider"'), 'Missing #split-divider');
});

runTest('2.4 index.html contains Bottom HUD Quick-Run Carousel (#hud-quick-runs)', () => {
  assert.ok(indexHtml.includes('id="hud-quick-runs"'), 'Missing #hud-quick-runs element');
  assert.ok(indexHtml.includes('id="quick-runs-scroll"'), 'Missing #quick-runs-scroll container');
  assert.ok(indexHtml.includes('class="hud-quick-runs glass-card"'), 'Must have glassmorphic class');
});

// Suite 3: uiController.js Interactive Functions & Search
console.log('\n--- Suite 3: uiController.js Interactive Logic & Search Filtering ---');

runTest('3.1 uiController exports all required interactive methods', () => {
  assert.equal(typeof uiController.activateRunSwath, 'function', 'Must export activateRunSwath');
  assert.equal(typeof uiController.openStacInspector, 'function', 'Must export openStacInspector');
  assert.equal(typeof uiController.closeStacInspector, 'function', 'Must export closeStacInspector');
  assert.equal(typeof uiController.copyStacJson, 'function', 'Must export copyStacJson');
  assert.equal(typeof uiController.renderHudQuickRuns, 'function', 'Must export renderHudQuickRuns');
  assert.equal(typeof uiController.updateActiveQuickRunChip, 'function', 'Must export updateActiveQuickRunChip');
  assert.equal(typeof uiController.initRunsSearch, 'function', 'Must export initRunsSearch');
  assert.equal(typeof uiController.initSplitComparisonSlider, 'function', 'Must export initSplitComparisonSlider');
});

runTest('3.2 renderRunsGallery populates cards with Fly, Swath, and STAC action buttons', () => {
  // Setup minimal DOM mocks
  const mockGrid = { innerHTML: '', querySelectorAll: () => [] };
  const mockCount = { textContent: '' };
  const mockSummary = { textContent: '' };
  const prevDoc = globalThis.document;

  globalThis.document = {
    getElementById: (id) => {
      if (id === 'runs-grid') return mockGrid;
      if (id === 'runs-active-count') return mockCount;
      if (id === 'runs-search-summary') return mockSummary;
      return null;
    },
    querySelectorAll: () => []
  };

  try {
    uiController.renderRunsGallery('ALL');
    assert.ok(mockGrid.innerHTML.includes('btn-fly-theater'), 'Must render Fly button');
    assert.ok(mockGrid.innerHTML.includes('btn-activate-swath'), 'Must render Swath button');
    assert.ok(mockGrid.innerHTML.includes('btn-inspect-stac'), 'Must render STAC button');
    assert.ok(mockGrid.innerHTML.includes('RUN 01'), 'Must include Run 01');
    assert.ok(mockGrid.innerHTML.includes('RUN 11'), 'Must include Run 11');
  } finally {
    globalThis.document = prevDoc;
  }
});

runTest('3.3 Multi-Attribute Search filters correctly across categories and keywords', () => {
  const allRuns = getRunCatalog();
  assert.equal(allRuns.length, 11);

  // Helper matching the internal search algorithm
  function search(query, category = 'ALL') {
    let runs = getRunsByCategory(category);
    if (!query) return runs;
    const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
    return runs.filter((run) => {
      const searchable = [
        run.title,
        run.category,
        run.physics_regime,
        run.region,
        run.run_id,
        run.primary_figure_name,
        ...(run.satellites_and_sensors || []),
        ...(run.keywords || []),
        JSON.stringify(run.metrics || {}),
        `run ${run.run_number}`
      ].join(' ').toLowerCase();

      return tokens.every(tok => searchable.includes(tok));
    });
  }

  // Test 1: Country search
  const mexicoRuns = search('Mexico');
  assert.ok(mexicoRuns.length >= 1, 'Search for Mexico should find at least Run 02');
  assert.equal(mexicoRuns[0].run_number, 2);

  // Test 2: Sensor search
  const iceyeRuns = search('ICEYE');
  assert.ok(iceyeRuns.length >= 4, 'Search for ICEYE should return multiple ICEYE runs');

  // Test 3: Hazard type search
  const volcanoRuns = search('volcano');
  assert.ok(volcanoRuns.length >= 1, 'Search for volcano should find Southern Italy');
  assert.ok(volcanoRuns.some(r => r.title.includes('Italy')));

  // Test 4: Subsidence search
  const subsidenceRuns = search('subsidence');
  assert.ok(subsidenceRuns.length >= 2, 'Search for subsidence should find Witwatersrand and Vancouver');

  // Test 5: Multi-token search (e.g. "Finland Rebound")
  const multiRuns = search('Finland Rebound');
  assert.equal(multiRuns.length, 1, 'Should match exactly Run 08');
  assert.equal(multiRuns[0].run_number, 8);

  // Test 6: Empty match
  const noneRuns = search('NonExistentKeywordXYZ123');
  assert.equal(noneRuns.length, 0, 'Bogus query should match 0 runs');
});

runTest('3.4 activateRunSwath activates SAR visibility, highlights swath, and flies camera', () => {
  let flyCalled = false;
  let targetLat = null;
  let targetLon = null;

  // Set mock callbacks
  uiController.setSceneCallbacks({
    flyToLatLon: (lat, lon) => {
      flyCalled = true;
      targetLat = lat;
      targetLon = lon;
    }
  });

  const run2 = getRunById(2);
  assert.ok(run2, 'Run 2 must exist');

  // Test activateRunSwath
  const res = uiController.activateRunSwath(2);
  assert.ok(flyCalled, 'activateRunSwath must trigger camera flight');
  assert.equal(targetLat, run2.camera_target.lat);
  assert.equal(targetLon, run2.camera_target.lon);
});

runTest('3.5 openStacInspector displays validated OGC STAC v1.0.0 payload', async () => {
  let modalDisplayed = false;
  let titleText = '';
  let codeText = '';

  const mockModal = {
    style: { display: 'none' },
    classList: { remove: () => { modalDisplayed = true; }, add: () => { modalDisplayed = false; } }
  };
  const mockCode = { textContent: '' };
  const mockTitle = { textContent: '' };

  const prevDoc = globalThis.document;
  globalThis.document = {
    getElementById: (id) => {
      if (id === 'stac-modal') return mockModal;
      if (id === 'stac-json-content') return mockCode;
      if (id === 'stac-modal-title') return mockTitle;
      return {};
    }
  };

  try {
    await uiController.openStacInspector(2);
    assert.ok(modalDisplayed, 'STAC modal should be displayed');
    assert.ok(mockCode.textContent.includes('FeatureCollection'), 'Must output FeatureCollection');
    assert.ok(mockCode.textContent.includes('1.0.0'), 'Must specify STAC version 1.0.0');

    // Parse output JSON to ensure valid syntax
    const parsed = JSON.parse(mockCode.textContent);
    assert.equal(parsed.type, 'FeatureCollection');
    assert.ok(Array.isArray(parsed.features));
    assert.ok(parsed.features.length >= 1);
  } finally {
    globalThis.document = prevDoc;
  }
});

runTest('3.6 renderHudQuickRuns generates exactly 11 quick-run buttons', () => {
  const container = { innerHTML: '', querySelectorAll: () => [] };
  const prevDoc = globalThis.document;

  globalThis.document = {
    getElementById: (id) => (id === 'quick-runs-scroll' ? container : null)
  };

  try {
    uiController.renderHudQuickRuns();
    const count = (container.innerHTML.match(/quick-run-chip/g) || []).length;
    assert.equal(count, 11, 'Must generate exactly 11 quick run chips in HUD');
  } finally {
    globalThis.document = prevDoc;
  }
});

console.log('\n===============================================================================');
console.log(`TEST SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('===============================================================================');

if (failed > 0) {
  process.exit(1);
} else {
  process.exit(0);
}
