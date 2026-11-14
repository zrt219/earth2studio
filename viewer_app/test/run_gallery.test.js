// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * run_gallery.test.js
 * Verification test suite for 3D Twin Run Gallery & High-Resolution Figure Registry:
 * Browsing all 11 research runs across 4 categories, high-res figure previews from /runs/,
 * and 3D globe camera theater fly-to navigation.
 * Strict compliance with Rule e2s-014 Scientific Integrity.
 */

import assert from 'assert';
import fs from 'fs';
import path from 'path';
import {
  RUNS_CATALOG,
  RUN_CATEGORIES,
  CATEGORY_THEMES,
  getRunCatalog,
  getRunById,
  getRunsByCategory
} from '../runsCatalog.js';
import studyData, { validateStudyData } from '../studyData.js';
import uiController from '../uiController.js';

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
console.log('3D TWIN RUN GALLERY & HIGH-RESOLUTION FIGURE REGISTRY TEST SUITE');
console.log('===============================================================================');

// Suite 1: Catalog Invariants & Schema Verification
console.log('\n--- Suite 1: runsCatalog.js Schema & Invariants ---');

runTest('1.1 RUNS_CATALOG contains exactly 11 verified research runs (deeply frozen)', () => {
  assert.equal(RUNS_CATALOG.length, 11);
  assert.ok(Object.isFrozen(RUNS_CATALOG));
  RUNS_CATALOG.forEach((run) => {
    assert.ok(Object.isFrozen(run));
    assert.ok(Object.isFrozen(run.camera_target));
    assert.ok(Object.isFrozen(run.primary_figure));
  });
});

runTest('1.2 RUN_CATEGORIES covers all 4 required scientific categories', () => {
  assert.equal(RUN_CATEGORIES.length, 4);
  const expected = [
    'Baseline Pillars',
    'Hidden Terrains',
    'Multi-Band & Deep Hazards',
    'Global Synoptic Theaters'
  ];
  expected.forEach((cat) => {
    assert.ok(RUN_CATEGORIES.includes(cat), `Missing required category: ${cat}`);
    const theme = CATEGORY_THEMES[cat];
    assert.ok(theme, `Missing theme for ${cat}`);
    assert.ok(theme.color && theme.icon && theme.bg);
  });
});

runTest('1.3 Category run distribution matches experimental design (1 + 3 + 2 + 5 = 11)', () => {
  const c1 = getRunsByCategory('Baseline Pillars');
  const c2 = getRunsByCategory('Hidden Terrains');
  const c3 = getRunsByCategory('Multi-Band & Deep Hazards');
  const c4 = getRunsByCategory('Global Synoptic Theaters');

  assert.equal(c1.length, 1, 'Baseline Pillars must have exactly 1 run');
  assert.equal(c2.length, 3, 'Hidden Terrains must have exactly 3 runs');
  assert.equal(c3.length, 2, 'Multi-Band & Deep Hazards must have exactly 2 runs');
  assert.equal(c4.length, 5, 'Global Synoptic Theaters must have exactly 5 runs');
  assert.equal(c1.length + c2.length + c3.length + c4.length, 11);
});

runTest('1.4 Every run has valid numbers (1..11), titles, and camera_target coordinates', () => {
  RUNS_CATALOG.forEach((run, idx) => {
    assert.equal(run.run_number, idx + 1);
    assert.ok(run.run_id && run.run_id.startsWith(`run_${String(idx + 1).padStart(2, '0')}`));
    assert.ok(run.title && run.title.length > 5);
    assert.ok(run.camera_target, `Missing camera_target on ${run.run_id}`);
    assert.equal(typeof run.camera_target.lat, 'number');
    assert.equal(typeof run.camera_target.lon, 'number');
    assert.ok(run.camera_target.lat >= -90 && run.camera_target.lat <= 90);
    assert.ok(run.camera_target.lon >= -180 && run.camera_target.lon <= 180);
    assert.ok(run.camera_distance >= 7.0 && run.camera_distance <= 12.0);
  });
});

runTest('1.5 Primary figures specify valid viewer_paths in /runs/ with valid SHA-256 digests', () => {
  RUNS_CATALOG.forEach((run) => {
    const fig = run.primary_figure;
    assert.ok(fig, `Missing primary_figure on ${run.run_id}`);
    assert.ok(fig.viewer_path.startsWith('/runs/'), `viewer_path must start with /runs/: ${fig.viewer_path}`);
    assert.ok(fig.viewer_path.endsWith('.png'));
    assert.ok(/^[0-9a-f]{64}$/.test(fig.sha256), `Invalid SHA-256 for ${run.run_id}: ${fig.sha256}`);
    assert.ok(fig.size_bytes > 50000, `Suspicious file size for ${run.run_id}: ${fig.size_bytes}`);
  });
});

runTest('1.6 Primary figures physically exist on disk in viewer_app/public/runs/', () => {
  RUNS_CATALOG.forEach((run) => {
    const rel = run.primary_figure.relative_path;
    const diskPath = path.resolve('public', rel);
    const altDiskPath = path.resolve('viewer_app/public', rel);
    const exists = fs.existsSync(diskPath) || fs.existsSync(altDiskPath);
    assert.ok(exists, `Publication figure does not exist on disk: ${diskPath}`);
  });
});

runTest('1.7 getRunById works for both numeric and string identifiers', () => {
  const r1 = getRunById(1);
  const r1Str = getRunById('1');
  const r1Id = getRunById('run_01_baseline_advanced_pillars');
  assert.ok(r1 && r1Str && r1Id);
  assert.equal(r1.run_number, 1);
  assert.equal(r1Str.run_number, 1);
  assert.equal(r1Id.run_number, 1);

  const r11 = getRunById(11);
  assert.ok(r11);
  assert.equal(r11.run_number, 11);
  assert.equal(r11.title, 'Vancouver Cascadia Delta Subsidence & Coast Mountain Atmospheric Rivers');

  assert.equal(getRunById(999), null);
  assert.equal(getRunById('non_existent'), null);
});

runTest('1.8 validateStudyData includes Run Gallery assertions and passes with zero errors', () => {
  const res = validateStudyData();
  assert.ok(res.valid, `validateStudyData failed with errors: ${res.errors.join('; ')}`);
  assert.equal(res.errors.length, 0);
});

// Suite 2: HTML UI & Accessibility Elements
console.log('\n--- Suite 2: index.html Run Gallery UI Elements ---');

const htmlPath = fs.existsSync('index.html') ? path.resolve('index.html') : path.resolve('viewer_app/index.html');
const htmlContent = fs.readFileSync(htmlPath, 'utf8');

runTest('2.1 index.html contains #btn-toolbar-runs in #quick-toolbar', () => {
  assert.ok(htmlContent.includes('id="btn-toolbar-runs"'), 'Must define #btn-toolbar-runs button');
  assert.ok(htmlContent.includes('🖼️ Runs'), 'Button must feature Runs label and icon');
  assert.ok(htmlContent.includes('aria-label="Browse 11 Scientific Runs"'));
});

runTest('2.2 index.html contains modern glassmorphic #runs-modal and #run-lightbox-modal', () => {
  assert.ok(htmlContent.includes('id="runs-modal"'), 'Must define #runs-modal container');
  assert.ok(htmlContent.includes('id="runs-modal-close"'), 'Must define #runs-modal-close button');
  assert.ok(htmlContent.includes('id="runs-grid"'), 'Must define #runs-grid container');
  assert.ok(htmlContent.includes('id="run-lightbox-modal"'), 'Must define #run-lightbox-modal');
  assert.ok(htmlContent.includes('id="lightbox-close-btn"'), 'Must define #lightbox-close-btn');
  assert.ok(htmlContent.includes('id="lightbox-fly-btn"'), 'Must define #lightbox-fly-btn');
});

runTest('2.3 index.html defines filter buttons for All and all 4 categories', () => {
  assert.ok(htmlContent.includes('data-category="ALL"'));
  assert.ok(htmlContent.includes('data-category="Baseline Pillars"'));
  assert.ok(htmlContent.includes('data-category="Hidden Terrains"'));
  assert.ok(htmlContent.includes('data-category="Multi-Band & Deep Hazards"'));
  assert.ok(htmlContent.includes('data-category="Global Synoptic Theaters"'));
});

runTest('2.4 shortcuts modal documents G hotkey for Run Gallery', () => {
  assert.ok(htmlContent.includes('<span class="shortcuts-key">G</span>'));
  assert.ok(htmlContent.includes('Open 3D Twin Run Gallery (11 Runs)'));
});

// Suite 3: UI Controller Run Gallery & Navigation Logic
console.log('\n--- Suite 3: uiController.js Run Gallery & Fly-To Logic ---');

runTest('3.1 uiController exports all required modal and gallery functions', () => {
  assert.equal(typeof uiController.openRunsModal, 'function');
  assert.equal(typeof uiController.closeRunsModal, 'function');
  assert.equal(typeof uiController.openRunLightbox, 'function');
  assert.equal(typeof uiController.closeRunLightbox, 'function');
  assert.equal(typeof uiController.flyToRun, 'function');
  assert.equal(typeof uiController.renderRunsGallery, 'function');
});

runTest('3.2 renderRunsGallery populates #runs-grid with 11 cards and handles filtering', () => {
  const mockGrid = { innerHTML: '', querySelectorAll: () => [] };
  const mockCount = { textContent: '' };
  const mockFilterBtns = [
    { getAttribute: () => 'ALL', classList: { toggle: () => {} }, setAttribute: () => {} },
    { getAttribute: () => 'Hidden Terrains', classList: { toggle: () => {} }, setAttribute: () => {} }
  ];

  const oldDoc = globalThis.document;
  globalThis.document = {
    getElementById: (id) => {
      if (id === 'runs-grid') return mockGrid;
      if (id === 'runs-active-count') return mockCount;
      return null;
    },
    querySelectorAll: (sel) => {
      if (sel === '.runs-filter-btn') return mockFilterBtns;
      return [];
    }
  };

  try {
    // Render all runs
    uiController.renderRunsGallery('ALL');
    assert.equal(mockCount.textContent, '11 Runs');
    assert.ok(mockGrid.innerHTML.includes('RUN 01'));
    assert.ok(mockGrid.innerHTML.includes('RUN 11'));
    assert.ok(mockGrid.innerHTML.includes('Vancouver Cascadia Delta'));

    // Render filtered runs
    uiController.renderRunsGallery('Hidden Terrains');
    assert.equal(mockCount.textContent, '3 Runs');
    assert.ok(mockGrid.innerHTML.includes('RUN 02'));
    assert.ok(mockGrid.innerHTML.includes('RUN 03'));
    assert.ok(mockGrid.innerHTML.includes('RUN 04'));
    assert.ok(!mockGrid.innerHTML.includes('RUN 01'));
  } finally {
    globalThis.document = oldDoc;
  }
});

runTest('3.3 flyToRun triggers camera navigation with exact coordinates and optimal zoom', () => {
  let flownLat = null;
  let flownLon = null;
  let flownDist = null;
  let spinState = null;

  uiController.setSceneCallbacks({
    flyToLatLon: (lat, lon, dist) => {
      flownLat = lat;
      flownLon = lon;
      flownDist = dist;
    }
  });

  const oldDoc = globalThis.document;
  globalThis.document = {
    getElementById: () => ({ style: {}, classList: { add: () => {}, remove: () => {} } }),
    querySelectorAll: () => []
  };

  try {
    // Fly to Run 11 (Vancouver Cascadia Delta)
    uiController.flyToRun(11);
    assert.equal(flownLat, 49.3);
    assert.equal(flownLon, -123.1);
    assert.equal(flownDist, 7.5);

    // Fly to Run 7 (Southern Italy Volcano-Tectonics)
    uiController.flyToRun(7);
    assert.equal(flownLat, 37.751);
    assert.equal(flownLon, 14.9934);
    assert.equal(flownDist, 8.5);

    // Fly to Run 10 (Brazil Tropical Dynamics)
    uiController.flyToRun('run_10_brazil_tropical_dynamics');
    assert.equal(flownLat, -23.76);
    assert.equal(flownLon, -45.41);
    assert.equal(flownDist, 10.0);
  } finally {
    globalThis.document = oldDoc;
  }
});

runTest('3.4 openRunLightbox and closeRunLightbox correctly update DOM state', () => {
  const mockModal = { style: { display: 'none' }, classList: { add: () => {}, remove: () => {} } };
  const mockTitle = { textContent: '' };
  const mockBadge = { textContent: '', style: {} };
  const mockMeta = { textContent: '' };
  const mockImg = { src: '', alt: '' };
  const mockHash = { textContent: '' };
  const mockLink = { href: '' };
  const mockFly = { onclick: null };

  const oldDoc = globalThis.document;
  globalThis.document = {
    getElementById: (id) => {
      if (id === 'run-lightbox-modal') return mockModal;
      if (id === 'lightbox-title') return mockTitle;
      if (id === 'lightbox-badge') return mockBadge;
      if (id === 'lightbox-meta') return mockMeta;
      if (id === 'lightbox-img') return mockImg;
      if (id === 'lightbox-hash') return mockHash;
      if (id === 'lightbox-download-link') return mockLink;
      if (id === 'lightbox-fly-btn') return mockFly;
      return null;
    }
  };

  try {
    uiController.openRunLightbox(9);
    assert.equal(mockModal.style.display, 'flex');
    assert.equal(mockTitle.textContent, 'Japan Abandoned Farmland & Mountain Hazard Dynamics');
    assert.ok(mockBadge.textContent.includes('RUN 09'));
    assert.ok(mockImg.src.includes('12_japan_abandoned_farmland.png'));
    assert.ok(mockHash.textContent.includes('SHA-256:'));
    assert.equal(typeof mockFly.onclick, 'function');

    uiController.closeRunLightbox();
    assert.equal(mockModal.style.display, 'none');
  } finally {
    globalThis.document = oldDoc;
  }
});

console.log('===============================================================================');
console.log(`TEST SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('===============================================================================');

if (failed > 0) {
  process.exit(1);
}
