/**
 * @fileoverview E2E & Adversarial Verification Suite for GEOINT SAR & CATALYST APS Trifecta
 * Study ID: OD-EARTH2-001 (Milestone 5)
 *
 * Tests:
 *  - studyData.js SAR_TASKING_METADATA schema, deep immutability, and exact physical numbers
 *  - generateStacTaskingOrderGeoJSON() OGC STAC v1.0.0 FeatureCollection contract
 *  - sarTasking.js 3D SSO orbital tracks, satellite buses, slant-range frustums, and GLSL shaders
 *  - CATALYST APS fringe toggle (uApsCorrected = 0.0 -> 1.0) and Display Mode toggle (uDisplayMode = 0.0 -> 1.0)
 *  - Clean disposal and re-initialization without memory leaks
 */

import assert from 'node:assert/strict';
import * as THREE from 'three';
import studyData from '../studyData.js';
import sarTasking from '../sarTasking.js';
import tutorialTour from '../tutorialTour.js';
import tiledEarth from '../tiledEarth.js';
import citySelector from '../citySelector.js';
import explainerToolbar from '../explainerToolbar.js';
import hazardAlerts from '../hazardAlerts.js';
import windParticles from '../windParticles.js';

let passed = 0;
let failed = 0;

function runTest(name, fn) {
  try {
    fn();
    console.log(`  ✓ PASS: ${name}`);
    passed++;
  } catch (err) {
    console.error(`  ✗ FAIL: ${name}`);
    console.error(`    ${err.message}`);
    failed++;
  }
}

console.log('===============================================================================');
console.log('OD-EARTH2-001 MILESTONE 5: GEOINT SAR & CATALYST APS TRIFECTA E2E TEST SUITE');
console.log('===============================================================================\n');

// -----------------------------------------------------------------------------
// Suite 1: studyData.js SAR Metadata & Deep Immutability
// -----------------------------------------------------------------------------
console.log('--- Suite 1: studyData.js SAR_TASKING_METADATA & STAC Generator ---');

runTest('1.1 getSarTaskingMetadata() returns deeply frozen metadata with ICEYE and Synspective StriX satellites', () => {
  const meta = studyData.getSarTaskingMetadata();
  assert.ok(meta, 'SAR metadata must exist');
  assert.equal(meta.carrierFrequencyGhz, 9.65);
  assert.equal(meta.wavelengthCm, 3.1067);
  assert.equal(meta.constellations.length, 2);

  const iceye = meta.constellations.find(s => s.id === 'ICEYE-X38');
  const strix = meta.constellations.find(s => s.id === 'STRIX-3');
  assert.ok(iceye, 'ICEYE-X38 satellite must exist');
  assert.ok(strix, 'STRIX-3 satellite must exist');

  // Verify exact physical metrics synchronized with Python manifest
  assert.equal(iceye.apsMetrics.fringesRemoved, 12.20);
  assert.equal(iceye.apsMetrics.uncorrectedRmseRad, 14.7763);
  assert.equal(iceye.apsMetrics.correctedRmseRad, 0.1874);
  assert.equal(iceye.apsMetrics.rmseReductionPct, 98.73);
  assert.equal(iceye.attributionMetrics.inundatedAreaKm2, 735.27);

  assert.equal(strix.apsMetrics.fringesRemoved, 9.24);
  assert.equal(strix.apsMetrics.uncorrectedRmseRad, 13.8243);
  assert.equal(strix.apsMetrics.correctedRmseRad, 0.1641);
  assert.equal(strix.apsMetrics.rmseReductionPct, 98.81);
  assert.equal(strix.attributionMetrics.highRiskSlopeAreaKm2, 550.73);

  // Verify deep freeze
  assert.throws(() => {
    meta.constellations[0].apsMetrics.rmseReductionPct = 50.0;
  }, TypeError);
});

runTest('1.2 generateStacTaskingOrderGeoJSON() returns valid STAC v1.0.0 FeatureCollection', () => {
  const stac = studyData.generateStacTaskingOrderGeoJSON();
  assert.equal(stac.type, 'FeatureCollection');
  assert.equal(stac.stac_version, '1.0.0');
  assert.equal(stac.features.length, 2);

  for (const feat of stac.features) {
    assert.equal(feat.type, 'Feature');
    assert.ok(Array.isArray(feat.stac_extensions));
    assert.ok(feat.stac_extensions.some(ext => ext.includes('sar')));
    assert.equal(feat.geometry.type, 'Polygon');
    assert.equal(feat.geometry.coordinates[0].length, 5, 'Closed polygon ring must have 5 vertices');
    assert.equal(feat.properties['sar:frequency_band'], 'X');
    assert.equal(feat.properties['sar:center_frequency'], 9.65);
    assert.equal(feat.properties['tasking:status'], 'LOCKED_SLANT_SWATH');
  }
});

// -----------------------------------------------------------------------------
// Suite 2: sarTasking.js 3D Scene Graph, Shaders, and Uniform Toggles
// -----------------------------------------------------------------------------
console.log('\n--- Suite 2: sarTasking.js 3D Orbits, Look-Cones & GLSL Shaders ---');

const globe = new THREE.Group();

runTest('2.1 initSarTasking(globe) constructs SSO orbit rings, satellite buses, look-cones, and ground swaths', () => {
  const group = sarTasking.initSarTasking(globe);
  assert.ok(group, 'sarGroup must be returned');
  assert.equal(group.name, 'geoint_sar_tasking_group');
  assert.equal(sarTasking.getSarTaskingVisibility(), true);

  const pickables = sarTasking.getSarPickableObjects();
  assert.equal(pickables.length, 4, 'Must have 4 pickable objects (2 satellites + 2 ground swaths)');

  const satPickables = pickables.filter(p => p.userData.type === 'sar_satellite');
  const swathPickables = pickables.filter(p => p.userData.type === 'sar_swath');
  assert.equal(satPickables.length, 2);
  assert.equal(swathPickables.length, 2);
});

runTest('2.2 Orbit radius is R = 5.420 and ground swath radius is R = 5.040 (collision-free shell hierarchy)', () => {
  assert.equal(sarTasking.SAR_SHELLS.SAR_FOOTPRINT, 5.040);
  assert.equal(sarTasking.SAR_SHELLS.SSO_ORBIT, 5.420);

  const pickables = sarTasking.getSarPickableObjects();
  const satBus = pickables.find(p => p.userData.type === 'sar_satellite');
  const dist = satBus.parent.position.length();
  assert.ok(Math.abs(dist - 5.420) < 1e-2, `Satellite rig radial distance ${dist} should be ~5.420`);
});

runTest('2.3 setCatalystApsCorrection() updates GLSL shader uniform uApsCorrected across all swaths', () => {
  const pickables = sarTasking.getSarPickableObjects();
  const swaths = pickables.filter(p => p.userData.type === 'sar_swath');

  // Default is false (0.0 - Raw Uncorrected Phase Fringes)
  assert.equal(sarTasking.getCatalystApsCorrection(), false);
  for (const s of swaths) {
    assert.equal(s.material.uniforms.uApsCorrected.value, 0.0);
  }

  // Toggle to true (1.0 - CATALYST APS Corrected)
  sarTasking.setCatalystApsCorrection(true);
  assert.equal(sarTasking.getCatalystApsCorrection(), true);
  for (const s of swaths) {
    assert.equal(s.material.uniforms.uApsCorrected.value, 1.0);
  }

  // Toggle back to false (0.0 - Raw Uncorrected)
  sarTasking.setCatalystApsCorrection(false);
  assert.equal(sarTasking.getCatalystApsCorrection(), false);
  for (const s of swaths) {
    assert.equal(s.material.uniforms.uApsCorrected.value, 0.0);
  }
});

runTest('2.4 setSarDisplayMode() toggles GLSL shader uniform uDisplayMode between InSAR Fringes (0.0) and Flood/Coherence (1.0)', () => {
  const pickables = sarTasking.getSarPickableObjects();
  const swaths = pickables.filter(p => p.userData.type === 'sar_swath');

  assert.equal(sarTasking.getSarDisplayMode(), 'insar_fringes');
  for (const s of swaths) {
    assert.equal(s.material.uniforms.uDisplayMode.value, 0.0);
  }

  sarTasking.setSarDisplayMode('flood_coherence');
  assert.equal(sarTasking.getSarDisplayMode(), 'flood_coherence');
  for (const s of swaths) {
    assert.equal(s.material.uniforms.uDisplayMode.value, 1.0);
  }

  // Invalid mode falls back to 'insar_fringes'
  sarTasking.setSarDisplayMode('invalid_mode');
  assert.equal(sarTasking.getSarDisplayMode(), 'insar_fringes');
  for (const s of swaths) {
    assert.equal(s.material.uniforms.uDisplayMode.value, 0.0);
  }
});

runTest('2.5 updateSarTasking(elapsedTime) animates satellite positions and updates look-cone frustum vertices', () => {
  const pickables = sarTasking.getSarPickableObjects();
  const satBus = pickables.find(p => p.userData.type === 'sar_satellite');
  const pos0 = satBus.parent.position.clone();

  sarTasking.updateSarTasking(1.8);
  const pos1 = satBus.parent.position.clone();

  assert.ok(pos0.distanceTo(pos1) > 0.01, 'Satellite must move along SSO orbit track over elapsed time');
  assert.ok(Math.abs(pos1.length() - 5.420) < 1e-2, 'Satellite must remain on R=5.420 orbital shell');
});

runTest('2.6 exportStacTaskingOrder(false) returns valid STAC FeatureCollection in headless environment', () => {
  const stac = sarTasking.exportStacTaskingOrder(false);
  assert.equal(stac.type, 'FeatureCollection');
  assert.equal(stac.features.length, 2);
  assert.equal(stac.features[0].properties['catalyst:rmse_reduction_pct'], 98.73);
  assert.equal(stac.features[1].properties['catalyst:rmse_reduction_pct'], 98.81);
});

runTest('2.7 disposeSarTasking() cleanly removes scene objects and resets pickables without memory leaks', () => {
  sarTasking.disposeSarTasking();
  assert.equal(sarTasking.getSarPickableObjects().length, 0);
  // Re-init works idempotently
  sarTasking.initSarTasking(globe);
  assert.equal(sarTasking.getSarPickableObjects().length, 4);
  sarTasking.disposeSarTasking();
});

// -----------------------------------------------------------------------------
// Suite 3: uiController.js SAR Popup Unwrapping, Legend & Version Synchronization
// -----------------------------------------------------------------------------
import uiController from '../uiController.js';
import layers3D from '../layers3D.js';

console.log('\n--- Suite 3: uiController.js SAR Popup Unwrapping, Legend & Version Sync ---');

function createMockDOM() {
  const elements = new Map();
  const makeEl = (id) => {
    const classes = new Set(['active-btn']);
    const listeners = {};
    const attrs = {};
    const children = [];
    return {
      id,
      innerText: '',
      innerHTML: '',
      textContent: '',
      value: '2',
      disabled: false,
      children,
      style: { display: 'none', opacity: '1.0', background: '', left: '0px', top: '0px', color: '' },
      setAttribute: (k, v) => { attrs[k] = String(v); },
      getAttribute: (k) => attrs[k] ?? null,
      appendChild: (c) => {
        if (c && c.id && c.id !== 'dynamic') elements.set(c.id, c);
        children.push(c);
        return c;
      },
      getBoundingClientRect: () => ({ left: 100, top: 100, right: 200, bottom: 130, width: 100, height: 30 }),
      closest: () => null,
      focus: () => {},
      scrollIntoView: () => {},
      classList: {
        add: (c) => classes.add(c),
        remove: (c) => classes.delete(c),
        contains: (c) => classes.has(c),
        toggle: (c, force) => {
          const next = force !== undefined ? Boolean(force) : !classes.has(c);
          if (next) classes.add(c);
          else classes.delete(c);
          return next;
        }
      },
      addEventListener: (evt, fn) => {
        listeners[evt] = listeners[evt] || [];
        listeners[evt].push(fn);
      },
      click: () => {
        (listeners.click || []).forEach(fn => fn({ target: elements.get(id), stopPropagation: () => {} }));
      }
    };
  };

  [
    'poi-popup-card', 'popup-title', 'popup-body', 'popup-close',
    'legend-title', 'legend-bar', 'legend-min', 'legend-max',
    'tab-v1', 'tab-v2', 'tab-v3', 'timeline-slider',
    'layer-cyclone', 'layer-da', 'layer-spread', 'layer-mesoscale',
    'layer-sat', 'layer-t2m', 'layer-tend',
    'layer-sar-tasking', 'toggle-catalyst-aps', 'toggle-sar-mode', 'btn-export-stac',
    'sar-aps-status-line', 'sar-telemetry-drawer', 'btn-play-forecast', 'toggle-spin', 'toggle-relief',
    'btn-mission-tutorial', 'mission-tour-card', 'tour-step-badge', 'tour-step-title',
    'tour-step-target', 'tour-step-body', 'tour-step-eq', 'tour-progress-fill',
    'tour-prev-btn', 'tour-next-btn', 'tour-close-btn',
    'city-select-italy', 'city-select-japan',
    'city-select-south-africa', 'city-select-mexico', 'city-select-russia',
    'fly-south-africa', 'fly-mexico', 'fly-russia',
    'layer-cities',
    'btn-toolbar-cities', 'btn-toolbar-tour', 'btn-toolbar-sar', 'btn-toolbar-aps',
    'btn-toolbar-clouds', 'btn-toolbar-help',
    'explainer-drawer', 'explainer-close-btn', 'explainer-topic-tabs',
    'explainer-topic-badge', 'explainer-topic-title', 'explainer-topic-summary',
    'explainer-topic-howto', 'explainer-topic-metrics', 'explainer-try-btn',
    'preset-clean', 'preset-sar', 'preset-weather', 'preset-all', 'btn-clear-layers',
    'active-layers-badge', 'layer-clouds', 'layer-wind', 'layer-hazards', 'layer-sentinel-lod',
    'comparison-modal', 'comparison-grid', 'modal-close', 'open-comparison',
    'trajectory-callout', 'forecast-time-label', 'lod-res-badge',
    'btn-hud-collapse', 'btn-mobile-cam-toggle', 'camera-controls-widget',
    'globe-hover-pill'
  ].forEach(id => elements.set(id, makeEl(id)));

  const bodyEl = makeEl('body');
  const hudPanelEl = makeEl('hud-panel');
  elements.set('hud-panel', hudPanelEl);

  globalThis.document = {
    body: bodyEl,
    getElementById: (id) => elements.get(id) || null,
    querySelector: (sel) => (sel === '.hud-panel' ? hudPanelEl : null),
    querySelectorAll: () => [],
    addEventListener: () => {},
    createElement: () => makeEl('dynamic')
  };
  globalThis.window = {
    innerWidth: 1920,
    innerHeight: 1080,
    matchMedia: () => ({ matches: true }),
    addEventListener: () => {},
    dispatchEvent: () => {}
  };
  return elements;
}

runTest('3.1 showPopup() unwraps nested obj.userData ({ type, data }) from SAR raycast and renders rich telemetry', () => {
  const els = createMockDOM();
  sarTasking.initSarTasking(globe);
  const pickables = sarTasking.getSarPickableObjects();
  const satMesh = pickables.find(p => p.userData.type === 'sar_satellite');

  // Pass raw obj.userData wrapper directly (regression test for Issue 1)
  uiController.showPopup(satMesh.userData, { x: 640, y: 400, visible: true });
  const titleText = els.get('popup-title').innerText;
  const bodyHtml = els.get('popup-body').innerHTML;

  assert.ok(titleText.includes('ICEYE-X38') || titleText.includes('StriX-3'), `Expected SAR title, got: ${titleText}`);
  assert.ok(bodyHtml.includes('CATALYST APS ZTD'), 'Popup body must render CATALYST APS ZTD telemetry');
  assert.ok(bodyHtml.includes('9.65 GHz'), 'Popup body must render 9.65 GHz X-band telemetry');
});

runTest('3.2 updatePopupPosition() projects both SAR satellites (R=5.420) and SAR swaths (R=5.040) on viewport resize', () => {
  const els = createMockDOM();
  const cam = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 1000);
  cam.position.set(0, 0, 14);
  cam.lookAt(0, 0, 0);
  cam.updateMatrixWorld();

  uiController.initUI(globe, cam, null, layers3D);
  const pickables = sarTasking.getSarPickableObjects();
  const swathMesh = pickables.find(p => p.userData.type === 'sar_swath' && p.userData.data.id === 'ICEYE-X38');

  // Rotate globe so Italy faces camera (0, 0, 14)
  const { rotX, rotY } = layers3D.boresightRotation(swathMesh.userData.data.lat, swathMesh.userData.data.lon);
  globe.rotation.set(rotX, rotY, 0);

  uiController.showPopup(swathMesh.userData, { x: 500, y: 500, visible: true });
  uiController.updatePopupPosition(cam, 1440, 900);

  const popupEl = els.get('poi-popup-card');
  assert.equal(popupEl.style.display, 'block', 'Front-facing SAR swath popup must remain visible on resize');
});

runTest('3.3 Rapid concurrent toggling of V3 <-> V1, #layer-sar-tasking, #toggle-catalyst-aps, and #toggle-sar-mode stays synchronized', () => {
  const els = createMockDOM();
  const cam = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 1000);
  sarTasking.initSarTasking(globe);
  uiController.initUI(globe, cam, null, layers3D);

  // Switch to V1 -> SAR layer and buttons must disable and hide
  uiController.setStudyVersion('V1');
  assert.equal(sarTasking.getSarTaskingVisibility(), false);
  assert.equal(els.get('layer-sar-tasking').disabled, true);
  assert.equal(els.get('toggle-catalyst-aps').disabled, true);
  assert.equal(els.get('toggle-sar-mode').disabled, true);

  // Switch back to V3 -> SAR layer and buttons re-enable and show
  uiController.setStudyVersion('V3');
  assert.equal(sarTasking.getSarTaskingVisibility(), true);
  assert.equal(els.get('layer-sar-tasking').disabled, false);
  assert.equal(els.get('layer-sar-tasking').classList.contains('active-btn'), true);

  // Click #toggle-sar-mode -> switches to flood_coherence and updates legend
  els.get('toggle-sar-mode').click();
  assert.equal(sarTasking.getSarDisplayMode(), 'flood_coherence');
  assert.ok(els.get('legend-title').innerText.includes('Flood Backscatter'), 'Legend must update to SAR Flood/Coherence');

  // Click #toggle-catalyst-aps -> switches APS correction ON and updates status line
  els.get('toggle-catalyst-aps').click();
  assert.equal(sarTasking.getCatalystApsCorrection(), true);
  assert.ok(els.get('sar-aps-status-line').innerText.includes('CATALYST GFS-Corrected'));

  sarTasking.disposeSarTasking();
  delete globalThis.document;
  delete globalThis.window;
});

console.log('\n--- Suite 4: tutorialTour.js Interactive 6-Step Mission Briefing Tour ---');

runTest('4.1 initMissionTutorial() binds tour controls and walks all 6 steps updating camera, SAR modes & APS state', () => {
  const els = createMockDOM();
  sarTasking.initSarTasking(globe);
  let lastTex = null;
  let lastFly = null;
  tutorialTour.initMissionTutorial({
    setBaseTexture: (m) => { lastTex = m; },
    flyToLatLon: (lat, lon, dist) => { lastFly = { lat, lon, dist }; },
    flyTo: (x, y, z) => { lastFly = { x, y, z }; },
    setSpinState: () => {}
  });

  assert.equal(tutorialTour.TOUR_STEPS.length, 6, 'Mission briefing must have 6 curated steps');
  els.get('btn-mission-tutorial').click();
  assert.equal(tutorialTour.isMissionTourActive(), true);
  assert.equal(tutorialTour.getCurrentTourStep(), 0);
  assert.equal(lastTex, 'sat');

  // Step 2: ICEYE flood mode over Po Valley
  els.get('tour-next-btn').click();
  assert.equal(tutorialTour.getCurrentTourStep(), 1);
  assert.equal(sarTasking.getSarDisplayMode(), 'flood_coherence');
  assert.ok(lastFly && Math.abs(lastFly.lat - 45.1) < 0.1, 'Step 2 must fly to Po Valley');

  // Step 3: CATALYST raw uncorrected fringes
  els.get('tour-next-btn').click();
  assert.equal(tutorialTour.getCurrentTourStep(), 2);
  assert.equal(sarTasking.getSarDisplayMode(), 'insar_fringes');
  assert.equal(sarTasking.getCatalystApsCorrection(), false);

  // Step 4: CATALYST APS corrected ON
  els.get('tour-next-btn').click();
  assert.equal(tutorialTour.getCurrentTourStep(), 3);
  assert.equal(sarTasking.getCatalystApsCorrection(), true);

  // Step 5: Synspective StriX-3 Honshu
  els.get('tour-next-btn').click();
  assert.equal(tutorialTour.getCurrentTourStep(), 4);
  assert.ok(lastFly && Math.abs(lastFly.lat - 35.5) < 0.1, 'Step 5 must fly to Honshu');

  // Step 6 & Finish closes tour cleanly
  els.get('tour-next-btn').click();
  assert.equal(tutorialTour.getCurrentTourStep(), 5);
  assert.equal(els.get('tour-next-btn').innerText, 'Finish ✓');
  els.get('tour-next-btn').click();
  assert.equal(tutorialTour.isMissionTourActive(), false);
  assert.equal(els.get('mission-tour-card').classList.contains('hidden'), true);

  sarTasking.disposeSarTasking();
  delete globalThis.document;
  delete globalThis.window;
});

console.log('\n--- Suite 5: tiledEarth.js 16K Global Octants & 131K Sentinel-2 LOD Engine ---');

runTest('5.1 TILED_SHELLS strictly preserve monotonic non-intersecting radial hierarchy (5.002 < 5.003 < 5.005 < 5.012 < 5.040)', () => {
  const { TILED_16K_OCTANTS, SENTINEL2_LIVE_TILES, SENTINEL2_REGION_INSETS } = tiledEarth.TILED_SHELLS;
  assert.ok(TILED_16K_OCTANTS > 5.000 && TILED_16K_OCTANTS < SENTINEL2_LIVE_TILES);
  assert.ok(SENTINEL2_LIVE_TILES < SENTINEL2_REGION_INSETS);
  assert.ok(SENTINEL2_REGION_INSETS < 5.012);
  assert.ok(5.012 < sarTasking.SAR_SHELLS.SAR_FOOTPRINT);
});

runTest('5.2 getCameraBoresightLatLon() recovers accurate geographic coordinates from boresightRotation', () => {
  const testGlobe = new THREE.Mesh(new THREE.SphereGeometry(5, 16, 16), new THREE.MeshBasicMaterial());
  const cam = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
  cam.position.set(0, 0, 8.2);

  // Rotate globe so Greenwich Equator (0, 0) faces +Z camera
  const rotEq = layers3D.boresightRotation(0, 0);
  testGlobe.rotation.set(rotEq.rotX, rotEq.rotY, 0);
  testGlobe.updateMatrixWorld();
  const resEq = tiledEarth.getCameraBoresightLatLon(cam, testGlobe);
  assert.ok(Math.abs(resEq.lat) < 0.5 && Math.abs(resEq.lon) < 0.5, `Expected ~(0,0), got (${resEq.lat},${resEq.lon})`);
  assert.ok(Math.abs(resEq.dist - 8.2) < 0.01);
});

runTest('5.3 initTiledEarth() and LOD/thermal toggles manage visibility and resolution badge cleanly', () => {
  const els = createMockDOM();
  const root = tiledEarth.initTiledEarth(globe);
  assert.equal(root.visible, true);
  assert.equal(tiledEarth.getActiveResolutionLabel(), '16K Global Octants');

  tiledEarth.setSatelliteModeActive(false);
  assert.equal(root.visible, false);
  assert.equal(tiledEarth.getActiveResolutionLabel(), '4K GFS Thermal');

  tiledEarth.setSatelliteModeActive(true);
  assert.equal(root.visible, true);

  tiledEarth.setTiledEarthEnabled(false);
  assert.equal(root.visible, false);
  assert.equal(tiledEarth.getActiveResolutionLabel(), '8K NASA PBR');

  tiledEarth.setTiledEarthEnabled(true);
  tiledEarth.disposeTiledEarth();
  delete globalThis.document;
  delete globalThis.window;
});

// -----------------------------------------------------------------------------
// Suite 6: Interactive Italy & Japan City Selector + '?' Explainer Toolbar
// -----------------------------------------------------------------------------
console.log('\n--- Suite 6: Italy & Japan City Selector + Explainer Toolbar ---');

runTest('6.1 TARGET_CITIES exposes 13 frozen cities strictly inside 131K Sentinel-2 bounds', () => {
  const all = studyData.getTargetCities();
  const it = studyData.getTargetCities('Italy');
  const jp = studyData.getTargetCities('Japan');
  assert.equal(all.length, 13);
  assert.equal(it.length, 7);
  assert.equal(jp.length, 6);
  assert.ok(Object.isFrozen(all));
  it.forEach((c) => {
    assert.ok(c.lat >= 38 && c.lat <= 48 && c.lon >= 6 && c.lon <= 18, `Italy bounds check failed for ${c.id}`);
  });
  jp.forEach((c) => {
    assert.ok(c.lat >= 30 && c.lat <= 42 && c.lon >= 128 && c.lon <= 145, `Japan bounds check failed for ${c.id}`);
  });
});

runTest('6.2 citySelector creates 3D beacons at R=5.056 and focusCity centers exact boresight + telemetry popup', () => {
  createMockDOM();
  const group = citySelector.initCitySelector(globe, {
    flyToLatLon: (lat, lon, dist) => {
      const rot = layers3D.boresightRotation(lat, lon);
      globe.rotation.set(rot.rotX, rot.rotY, 0);
      globe.updateMatrixWorld();
      const cam = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
      cam.position.set(0, 0, dist);
      const recovered = tiledEarth.getCameraBoresightLatLon(cam, globe);
      assert.ok(Math.abs(recovered.lat - lat) < 0.5 && Math.abs(recovered.lon - lon) < 0.5,
        `Boresight mismatch for (${lat},${lon}): got (${recovered.lat},${recovered.lon})`);
    },
    setSpinState: () => {},
    showPopup: (poi, pos) => uiController.showPopup(poi, pos)
  });
  assert.ok(group && citySelector.getInteractiveCityObjects().length === 39);
  assert.equal(citySelector.CITY_SHELL_RADIUS, 5.056);

  const milan = citySelector.focusCity('it_milan', {
    flyToLatLon: (lat, lon, dist) => {
      const rot = layers3D.boresightRotation(lat, lon);
      globe.rotation.set(rot.rotX, rot.rotY, 0);
      globe.updateMatrixWorld();
      const cam = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
      cam.position.set(0, 0, dist);
      const recovered = tiledEarth.getCameraBoresightLatLon(cam, globe);
      assert.ok(Math.abs(recovered.lat - lat) < 0.5 && Math.abs(recovered.lon - lon) < 0.5);
    },
    setSpinState: () => {},
    showPopup: (poi, pos) => uiController.showPopup(poi, pos)
  });
  assert.equal(milan.id, 'it_milan');
  assert.ok(globalThis.document.getElementById('popup-title').innerText.includes('Milan'));

  const tokyo = citySelector.focusCity('jp_tokyo', {
    flyToLatLon: (lat, lon, dist) => {
      const rot = layers3D.boresightRotation(lat, lon);
      globe.rotation.set(rot.rotX, rot.rotY, 0);
      globe.updateMatrixWorld();
      const cam = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
      cam.position.set(0, 0, dist);
      const recovered = tiledEarth.getCameraBoresightLatLon(cam, globe);
      assert.ok(Math.abs(recovered.lat - lat) < 0.5 && Math.abs(recovered.lon - lon) < 0.5);
    },
    setSpinState: () => {},
    showPopup: (poi, pos) => uiController.showPopup(poi, pos)
  });
  assert.equal(tokyo.id, 'jp_tokyo');
  assert.ok(globalThis.document.getElementById('popup-title').innerText.includes('Tokyo'));

  citySelector.disposeCitySelector();
  delete globalThis.document;
  delete globalThis.window;
});

runTest('6.3 explainerToolbar exposes all 7 topics and opens/closes contextual explainer cleanly', () => {
  createMockDOM();
  explainerToolbar.initExplainerToolbar({});
  assert.equal(explainerToolbar.getExplainerTopics().length, 7);
  const topic = explainerToolbar.openExplainer('sar_tasking');
  assert.equal(topic.id, 'sar_tasking');
  assert.equal(explainerToolbar.isExplainerOpen(), true);
  assert.equal(globalThis.document.getElementById('explainer-drawer').style.display, 'flex');
  explainerToolbar.closeExplainer();
  assert.equal(explainerToolbar.isExplainerOpen(), false);
  delete globalThis.document;
  delete globalThis.window;
});

// -----------------------------------------------------------------------------
// Suite 7: Clean-Boot Presets, Executive Clarity, e2s-014 Parity, Raycast & Lazy LOD
// -----------------------------------------------------------------------------
console.log('\n--- Suite 7: Clean-Boot Presets, Clarity Parity, Raycast Filtering & Lazy LOD ---');

runTest('7.1 Clean-boot defaults start with 0/8 overlays and Quick View Presets switch cleanly', () => {
  const els = createMockDOM();
  const cam = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 1000);
  cam.position.set(0, 0, 14);
  layers3D.initLayers(globe, cam, null);
  sarTasking.initSarTasking(globe);
  citySelector.initCitySelector(globe, {});
  hazardAlerts.initHazardAlerts(globe);
  windParticles.initWindParticles(globe, 64);

  uiController.initUI(globe, cam, null, layers3D);
  uiController.applyCleanBootDefaults();

  assert.equal(uiController.updateActiveOverlayBadge(), 0, 'Clean boot must start with 0 active overlays');
  assert.equal(els.get('active-layers-badge').innerText, 'Active: 0/8 overlays');
  assert.equal(els.get('preset-clean').classList.contains('active-btn'), true);
  assert.equal(studyData.getState().activeVersionId, 'V3');
  assert.equal(citySelector.getCityMarkersVisibility(), false);
  assert.equal(hazardAlerts.getHazardAlertsVisibility(), false);
  assert.equal(sarTasking.getSarTaskingVisibility(), false);
  assert.equal(studyData.getState().activeLayers.cyclone, false);
  assert.equal(studyData.getState().activeLayers.da_stations, false);
  assert.equal(studyData.getState().activeLayers.mesoscale_insets, false);
  assert.equal(studyData.getState().activeLayers.ensemble_spread, false);
  assert.equal(els.get('layer-clouds').classList.contains('active-btn'), true, 'Optical clouds stay ON in clean_globe preset');

  // Switch to sar_focus (2/8: city_markers + sar_tasking)
  assert.equal(uiController.applyLayerPreset('sar_focus'), true);
  assert.equal(uiController.updateActiveOverlayBadge(), 2);
  assert.equal(els.get('active-layers-badge').innerText, 'Active: 2/8 overlays');
  assert.equal(sarTasking.getSarTaskingVisibility(), true);
  assert.equal(citySelector.getCityMarkersVisibility(), true);
  assert.equal(els.get('preset-sar').classList.contains('active-btn'), true);

  // Switch to extreme_weather (3/8: hazards + cyclone + wind)
  assert.equal(uiController.applyLayerPreset('extreme_weather'), true);
  assert.equal(uiController.updateActiveOverlayBadge(), 3);
  assert.equal(hazardAlerts.getHazardAlertsVisibility(), true);
  assert.equal(studyData.getState().activeLayers.cyclone, true);
  assert.equal(els.get('layer-wind').classList.contains('active-btn'), true);

  // Switch to all_telemetry (8/8)
  assert.equal(uiController.applyLayerPreset('all_telemetry'), true);
  assert.equal(uiController.updateActiveOverlayBadge(), 8);
  assert.equal(els.get('active-layers-badge').innerText, 'Active: 8/8 overlays');

  // Switch to clear_all (0/8 + clouds OFF)
  assert.equal(uiController.applyLayerPreset('clear_all'), true);
  assert.equal(uiController.updateActiveOverlayBadge(), 0);
  assert.equal(els.get('layer-clouds').classList.contains('active-btn'), false);
  assert.equal(uiController.applyLayerPreset('unknown_preset'), false);

  layers3D.disposeLayers();
  sarTasking.disposeSarTasking();
  citySelector.disposeCitySelector();
  hazardAlerts.disposeHazardAlerts();
  windParticles.disposeWindParticles();
  delete globalThis.document;
  delete globalThis.window;
});

runTest('7.2 showPopup() converts DA station Kelvin temperatures to Celsius alongside Kelvin', () => {
  const els = createMockDOM();
  const milanStation = studyData.getDAStationById('LIMC');
  assert.ok(milanStation, 'LIMC station must exist in studyData');

  uiController.showPopup(milanStation, { x: 520, y: 380, visible: true });
  const bodyHtml = els.get('popup-body').innerHTML;

  const expectedBgC = (milanStation.bgVal - 273.15).toFixed(1);
  const expectedObsC = (milanStation.obsVal - 273.15).toFixed(1);
  assert.ok(bodyHtml.includes(`${expectedBgC} °C (${milanStation.bgVal} K)`), `Expected bgVal in C/K, got: ${bodyHtml}`);
  assert.ok(bodyHtml.includes(`${expectedObsC} °C (${milanStation.obsVal} K)`), `Expected obsVal in C/K, got: ${bodyHtml}`);
  assert.ok(bodyHtml.includes(`+${milanStation.increment} K`), 'Expected DA increment in popup');

  delete globalThis.document;
  delete globalThis.window;
});

runTest('7.3 renderComparisonGrid(), trajectory callout & explainerToolbar maintain exact Rule e2s-014 parity with studyData.js', () => {
  const els = createMockDOM();
  const versions = studyData.getStudyVersions();
  const matrix = studyData.getComparisonMatrix();
  const ensemble = studyData.getEnsembleMetadata();

  assert.equal(versions.V1.auditStatus, 'STATUS: QUARANTINED_DEFECTIVE_SYNTHETIC');
  assert.equal(versions.V2.auditStatus, 'STATUS: VERIFIED_GENUINE_BASELINE');

  uiController.openComparisonModal();
  const gridHtml = els.get('comparison-grid').innerHTML;
  assert.ok(gridHtml.includes('1. Caught Fake Skill'), 'Governance summary strip must be rendered');
  assert.ok(gridHtml.includes('2. Proved Air-Gap Integrity'), 'Stage 2 governance strip must be rendered');
  assert.ok(gridHtml.includes('3. Live SAR'), 'Stage 3 governance strip must be rendered');
  assert.ok(gridHtml.includes('STATUS: VERIFIED_GENUINE_BASELINE'), 'V2 auditStatus must be VERIFIED_GENUINE_BASELINE');
  assert.ok(gridHtml.includes(`CRPS ${ensemble.crps}`), 'Ensemble CRPS must match studyData.js');
  assert.ok(gridHtml.includes(`SSR ${ensemble.ssr}`), 'Ensemble SSR must match studyData.js');
  assert.ok(gridHtml.includes('735.27'), 'ICEYE flood km2 must appear in comparison grid');
  assert.ok(gridHtml.includes('550.73'), 'StriX slope risk km2 must appear in comparison grid');
  for (const row of matrix) {
    assert.ok(gridHtml.includes(uiController.sanitizeHTML(row.dimension)), `Matrix dimension "${row.dimension}" must render from studyData.js`);
  }

  // Verify trajectory callout transitions across V1 -> V2 -> V3
  uiController.updateTrajectoryCallout('V1');
  assert.ok(els.get('trajectory-callout').innerHTML.includes('Stage 1 Quarantined'));
  uiController.updateTrajectoryCallout('V2');
  assert.ok(els.get('trajectory-callout').innerHTML.includes('Stage 2 Air-Gapped Baseline'));
  uiController.updateTrajectoryCallout('V3');
  assert.ok(els.get('trajectory-callout').innerHTML.includes('Stage 3 Live Ops'));

  // Verify explainerToolbar metric and station parity with studyData.js
  const topics = explainerToolbar.getExplainerTopics();
  const pillarsTopic = topics.find(t => t.id === 'pillars');
  const timelineTopic = topics.find(t => t.id === 'timeline');
  const sarTopic = topics.find(t => t.id === 'sar_tasking');
  assert.ok(pillarsTopic.keyMetrics.some(m => m.includes(`CRPS = ${ensemble.crps}`) && m.includes(`SSR = ${ensemble.ssr}`)));
  assert.ok(pillarsTopic.keyMetrics.some(m => m.includes('LIMC (16066)') && m.includes('LIRQ (16170)') && m.includes('LIRF (16242)') && m.includes('LIRN (16289)')));
  assert.ok(timelineTopic.keyMetrics.some(m => m.includes('2.1290 K') && m.includes('TAC 0.0000')));
  assert.ok(sarTopic.keyMetrics.some(m => m.includes('12.20 fringes') && m.includes('-98.73%')));

  delete globalThis.document;
  delete globalThis.window;
});

runTest('7.4 timestep-changed event highlights active cyclone waypoint and resets on clear', () => {
  const els = createMockDOM();
  const cam = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 1000);
  cam.position.set(0, 0, 14);
  layers3D.initLayers(globe, cam, null);
  uiController.initUI(globe, cam, null, layers3D);
  layers3D.setLayerVisibility('cyclone', true);

  studyData.setActiveTimeStep(2);
  const cycloneGroup = layers3D.getLayers().cyclone;
  const wp2 = cycloneGroup.getObjectByName('waypoint_WP-2');
  const wp0 = cycloneGroup.getObjectByName('waypoint_WP-0');
  assert.ok(wp2 && wp0, 'Cyclone waypoint meshes must exist');
  assert.ok(Math.abs(wp2.scale.x - 1.65) < 1e-4, `Active WP-2 scale expected 1.65, got ${wp2.scale.x}`);
  assert.ok(Math.abs(wp2.material.emissiveIntensity - 1.6) < 1e-4);
  assert.ok(Math.abs(wp0.scale.x - 0.9) < 1e-4, `Inactive WP-0 scale expected 0.9, got ${wp0.scale.x}`);

  layers3D.highlightCycloneWaypoint(-1);
  assert.ok(Math.abs(wp2.scale.x - 1.0) < 1e-4, 'Cleared highlight must restore scale 1.0');
  assert.ok(Math.abs(wp2.material.emissiveIntensity - 0.85) < 1e-4);

  layers3D.disposeLayers();
  delete globalThis.document;
  delete globalThis.window;
});

runTest('7.5 { visibleOnly: true } filters pickables and handleRaycast ignores hidden layers', () => {
  createMockDOM();
  const cam = new THREE.PerspectiveCamera(45, 1920 / 1080, 0.1, 1000);
  cam.position.set(0, 0, 14);
  cam.lookAt(0, 0, 0);
  cam.updateMatrixWorld();

  layers3D.initLayers(globe, cam, null);
  sarTasking.initSarTasking(globe);
  citySelector.initCitySelector(globe, {});
  hazardAlerts.initHazardAlerts(globe);

  // Orient globe so LIMC station (45.63, 8.73) faces dead-center camera
  const limc = studyData.getDAStationById('LIMC');
  const rot = layers3D.boresightRotation(limc.lat, limc.lon);
  globe.rotation.set(rot.rotX, rot.rotY, 0);
  globe.updateMatrixWorld(true);

  // Hide all layers
  layers3D.setLayerVisibility('cyclone', false);
  layers3D.setLayerVisibility('da_stations', false);
  sarTasking.setSarTaskingVisibility(false);
  citySelector.setCityMarkersVisibility(false);
  hazardAlerts.setHazardAlertsVisibility(false);

  assert.equal(layers3D.getInteractiveObjects({ visibleOnly: true }).length, 0);
  assert.ok(layers3D.getInteractiveObjects().length > 0);
  assert.equal(sarTasking.getSarPickableObjects({ visibleOnly: true }).length, 0);
  assert.equal(sarTasking.getSarPickableObjects().length, 4);
  assert.equal(citySelector.getInteractiveCityObjects({ visibleOnly: true }).length, 0);
  assert.equal(citySelector.getInteractiveCityObjects().length, 39);
  assert.equal(hazardAlerts.getHazardPickableObjects({ visibleOnly: true }).length, 0);
  assert.ok(hazardAlerts.getHazardPickableObjects().length > 0);

  const hiddenHit = layers3D.handleRaycast(
    { clientX: 960, clientY: 540 },
    cam,
    1920,
    1080,
    { visibleOnly: true, skipDragCheck: true }
  );
  assert.equal(hiddenHit, null, 'Raycast with visibleOnly:true must not hit hidden DA station');

  // Enable DA stations and verify pickable + raycast hit
  layers3D.setLayerVisibility('da_stations', true);
  assert.equal(layers3D.getInteractiveObjects({ visibleOnly: true }).length, 4);
  const visibleHit = layers3D.handleRaycast(
    { clientX: 960, clientY: 540 },
    cam,
    1920,
    1080,
    { visibleOnly: true, skipDragCheck: true }
  );
  assert.ok(visibleHit && visibleHit.type === 'da_station', 'Visible DA station must be hit at screen center');

  layers3D.disposeLayers();
  sarTasking.disposeSarTasking();
  citySelector.disposeCitySelector();
  hazardAlerts.disposeHazardAlerts();
  delete globalThis.document;
  delete globalThis.window;
});

runTest('7.6 tiledEarth lazy loading defers octants/regions at boot until camera zooms inside dist < 12.2', () => {
  createMockDOM();
  const root = tiledEarth.initTiledEarth(globe);
  const octantGroup = root.getObjectByName('tiled_16k_octants');
  const regionGroup = root.getObjectByName('sentinel2_regional_131k');
  const liveGroup = root.getObjectByName('sentinel2_live_stream');

  assert.equal(root.visible, true);
  assert.equal(octantGroup.visible, false);
  assert.equal(octantGroup.children.length, 0, 'Boot must not eagerly load 16K octants');
  assert.equal(regionGroup.visible, false);
  assert.equal(regionGroup.children.length, 0, 'Boot must not eagerly load 4K regional insets');
  assert.equal(liveGroup.visible, false);
  assert.equal(tiledEarth.hasActiveOctantCoverage(), false);

  // Far global orbit (dist = 14 >= 12.2): groups remain hidden
  const camFar = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
  camFar.position.set(0, 0, 14);
  tiledEarth.updateTiledEarth(camFar, globe);
  assert.equal(octantGroup.visible, false);
  assert.equal(regionGroup.visible, false);
  assert.equal(tiledEarth.hasActiveOctantCoverage(), false);

  // Re-init to reset 180ms throttle and zoom into Italy (dist = 8.2 < 12.2)
  const root2 = tiledEarth.initTiledEarth(globe);
  const rotItaly = layers3D.boresightRotation(42.0, 12.0);
  globe.rotation.set(rotItaly.rotX, rotItaly.rotY, 0);
  globe.updateMatrixWorld(true);
  const camNear = new THREE.PerspectiveCamera(45, 1.77, 0.1, 1000);
  camNear.position.set(0, 0, 8.2);
  camNear.lookAt(0, 0, 0);
  tiledEarth.updateTiledEarth(camNear, globe);

  assert.equal(root2.getObjectByName('tiled_16k_octants').visible, true);
  assert.equal(root2.getObjectByName('sentinel2_regional_131k').visible, true);
  assert.equal(tiledEarth.getActiveResolutionLabel(), '131K Sentinel-2 Regional');

  tiledEarth.disposeTiledEarth();
  delete globalThis.document;
  delete globalThis.window;
});

console.log('\n===============================================================================');
console.log(`TEST SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('===============================================================================');

if (failed > 0) {
  process.exit(1);
}

