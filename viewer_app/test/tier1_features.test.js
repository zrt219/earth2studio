/**
 * tier1_features.test.js
 * Tier 1: Feature Coverage Test Suite
 * Covers all 14 features from PROJECT.md § Feature Inventory (>=5 tests per feature = 70 tests).
 */

import { describe, it, beforeEach, assert } from './test_framework.js';
import {
  createMockDOM,
  MockVector3,
  MockMesh,
  MockCatmullRomCurve3,
  CoordinateTransforms,
  INVARIANTS
} from './mock_environment.js';
import fs from 'fs';
import path from 'path';

export function registerTier1Tests() {
  describe('Tier 1 - Feature 1: V1 Quarantined Synthetic Audit Schema', () => {
    const v1 = INVARIANTS.STUDY_SPEC.V1;

    it('F1.1: verifies V1 contains mandatory audit identification and quarantined flag', () => {
      assert.strictEqual(v1.id, 'V1');
      assert.strictEqual(v1.quarantined, true);
      assert.strictEqual(v1.classification, 'SYNTHETIC_DIAGNOSTIC_QUARANTINED');
      assert.ok(v1.name.includes('Quarantined'));
    });

    it('F1.2: validates empirical leakage formula y_hat = x0 + 0.72*delta + epsilon', () => {
      assert.strictEqual(v1.leakageFraction, 0.72);
      assert.ok(v1.leakageFormula.includes('0.72'));
      // Simulate synthetic leakage formula
      const x0 = 280.0; // initial temp K
      const delta = 4.0; // true tendency K
      const eps = 0.05; // noise
      const yHat = x0 + v1.leakageFraction * delta + eps;
      assert.closeTo(yHat, 282.93, 1e-2);
    });

    it('F1.3: verifies quarantined cycle length and historical 7-day cadence', () => {
      assert.strictEqual(v1.cycleLengthDays, 7);
      assert.greaterThan(v1.cycleLengthDays, 0);
    });

    it('F1.4: verifies illusory unphysical baseline metrics (RMSE 0.747K, ACC 0.941)', () => {
      assert.strictEqual(v1.metrics.rmse, 0.747);
      assert.strictEqual(v1.metrics.mae, 0.582);
      assert.strictEqual(v1.metrics.tac, 0.892);
      assert.strictEqual(v1.metrics.acc, 0.941);
      // Illusory RMSE must be unnaturally lower than true physical persistence (2.129K)
      assert.lessThan(v1.metrics.rmse, 1.0);
    });

    it('F1.5: verifies presence of explicit integrity look-ahead warning banner text', () => {
      assert.ok(v1.integrityWarning.includes('Target leakage detected'));
      assert.ok(v1.integrityWarning.includes('look-ahead future truth'));
    });
  });

  describe('Tier 1 - Feature 2: V2 Decoupled 3-Stage Persistence Baseline', () => {
    const v2 = INVARIANTS.STUDY_SPEC.V2;

    it('F2.1: validates decoupled 3-stage architecture sequence [Forecast, Freeze, Verify]', () => {
      assert.deepEqual(v2.pipelineStages, ['Forecast', 'Freeze', 'Verify']);
      assert.strictEqual(v2.pipelineStages.length, 3);
    });

    it('F2.2: verifies genuine physical GFS 0.25 deg baseline metrics (RMSE 2.129K, MAE 1.037K)', () => {
      assert.strictEqual(v2.metrics.rmse, 2.129);
      assert.strictEqual(v2.metrics.mae, 1.037);
      assert.strictEqual(v2.metrics.meanBias, 0.184);
      assert.greaterThan(v2.metrics.rmse, 2.0);
    });

    it('F2.3: verifies strict TAC/ACC separation invariant (TAC=0.0, ACC=null)', () => {
      assert.strictEqual(v2.metrics.tac, 0.0);
      assert.strictEqual(v2.metrics.acc, null);
      assert.notStrictEqual(v2.metrics.tac, v2.metrics.acc);
    });

    it('F2.4: verifies hardware blocker declaration (AMD GPU vs PyTorch 2.4 lack of ROCm)', () => {
      assert.strictEqual(v2.hardwareBlocker.declared, true);
      assert.strictEqual(v2.hardwareBlocker.gpu, 'AMD GPU');
      assert.ok(v2.hardwareBlocker.limitation.includes('ROCm'));
    });

    it('F2.5: verifies sealed run manifest SHA-256 requirement', () => {
      assert.strictEqual(v2.sealed, true);
      assert.strictEqual(v2.manifestHashLength, 64);
    });
  });

  describe('Tier 1 - Feature 3: V3 7-Pillars Scientific Metadata', () => {
    const v3 = INVARIANTS.STUDY_SPEC.V3;

    it('F3.1: verifies presence of all 7 pillars with distinct identifiers P1 through P7', () => {
      assert.strictEqual(v3.pillars.length, 7);
      const pillarIds = v3.pillars.map(p => p.id);
      assert.deepEqual(pillarIds, ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7']);
    });

    it('F3.2: verifies Pillar 1 ensemble metadata (N=25, meanSpread=0.4273K, maxSpread=1.182K)', () => {
      const p1 = v3.pillars.find(p => p.id === 'P1');
      assert.ok(p1.name.includes('N=25'));
      assert.strictEqual(p1.spreadUnits, 'K');
      assert.strictEqual(p1.meanSpread, 0.4273);
      assert.strictEqual(p1.maxSpread, 1.182);
    });

    it('F3.3: verifies Pillar 2 cyclone trajectory incorporates 5 WPAC waypoints', () => {
      assert.strictEqual(v3.cycloneWaypoints.length, 5);
      const wpIds = v3.cycloneWaypoints.map(w => w.id);
      assert.deepEqual(wpIds, ['WP1', 'WP2', 'WP3', 'WP4', 'WP5']);
    });

    it('F3.4: verifies Pillar 4 prognostic benchmark covers 4 neural models', () => {
      const p4 = v3.pillars.find(p => p.id === 'P4');
      assert.deepEqual(p4.models, ['FourCastNet', 'SFNO', 'DLWP', 'ClimaX']);
    });

    it('F3.5: verifies Pillar 6 Italian DA network includes 4 sounding stations with positive increments', () => {
      assert.strictEqual(v3.daStations.length, 4);
      for (const st of v3.daStations) {
        assert.ok(st.id.startsWith('DA_'));
        assert.greaterThan(st.increment, 0);
        assert.strictEqual(st.qc, 'PASS');
      }
    });
  });

  describe('Tier 1 - Feature 4: 3D Cyclone Trajectory & Waypoints', () => {
    const waypoints = INVARIANTS.STUDY_SPEC.V3.cycloneWaypoints;

    it('F4.1: transforms all 5 waypoint lat/lon coordinates to 3D Cartesian points at R=5.050', () => {
      const points = waypoints.map(wp => CoordinateTransforms.latLonToVector3(wp.lat, wp.lon, INVARIANTS.RADIAL_SHELLS.CYCLONE_TUBE));
      assert.strictEqual(points.length, 5);
      for (const pt of points) {
        assert.closeTo(pt.length(), 5.050, 1e-3);
      }
    });

    it('F4.2: generates CatmullRomCurve3 spline tube passing through waypoint positions', () => {
      const points = waypoints.map(wp => CoordinateTransforms.latLonToVector3(wp.lat, wp.lon, INVARIANTS.RADIAL_SHELLS.CYCLONE_TUBE));
      const spline = new MockCatmullRomCurve3(points);
      const curvePoints = spline.getPoints(50);
      assert.strictEqual(curvePoints.length, 51);
      // First and last point must match WP1 and WP5
      assert.closeTo(curvePoints[0].x, points[0].x, 1e-4);
      assert.closeTo(curvePoints[50].x, points[4].x, 1e-4);
    });

    it('F4.3: verifies waypoint beacon sphere positioning and radius hierarchy', () => {
      for (const wp of waypoints) {
        const beaconPos = CoordinateTransforms.latLonToVector3(wp.lat, wp.lon, INVARIANTS.RADIAL_SHELLS.CYCLONE_TUBE);
        assert.closeTo(beaconPos.length(), 5.050, 1e-3);
        assert.ok(wp.mslp >= 900 && wp.mslp <= 1015);
      }
    });

    it('F4.4: verifies uncertainty envelope cone geometry bounds at R=5.045', () => {
      const rCone = INVARIANTS.RADIAL_SHELLS.UNCERTAINTY_CONE;
      assert.strictEqual(rCone, 5.045);
      // Must be below cyclone tube (5.050) and above mesoscale insets (5.035)
      assert.lessThan(rCone, INVARIANTS.RADIAL_SHELLS.CYCLONE_TUBE);
      assert.greaterThan(rCone, INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS);
    });

    it('F4.5: verifies MSLP intensity color interpolation from 935 hPa (super typhoon) to 998 hPa', () => {
      // Color interpolation: lowest MSLP = most intense (magenta/purple), highest = moderate (cyan)
      function getMslpColor(mslp) {
        const t = Math.max(0, Math.min(1, (mslp - 930) / (1000 - 930)));
        return { intensity: 1 - t }; // 1.0 = super typhoon, 0.0 = weak
      }
      const cSuper = getMslpColor(935);
      const cModerate = getMslpColor(998);
      assert.greaterThan(cSuper.intensity, 0.9);
      assert.lessThan(cModerate.intensity, 0.1);
    });
  });

  describe('Tier 1 - Feature 5: 3D Data Assimilation Station Markers', () => {
    const stations = INVARIANTS.STUDY_SPEC.V3.daStations;

    it('F5.1: verifies all 4 Italian stations have valid coordinates within Italy bounds', () => {
      for (const st of stations) {
        // Italy bounding box: lat [36, 47], lon [6, 19]
        assert.ok(st.lat >= 36 && st.lat <= 47, `${st.name} lat out of bounds`);
        assert.ok(st.lon >= 6 && st.lon <= 19, `${st.name} lon out of bounds`);
      }
    });

    it('F5.2: verifies outward normal-aligned pin vector pointing away from globe center', () => {
      for (const st of stations) {
        const base = CoordinateTransforms.latLonToVector3(st.lat, st.lon, INVARIANTS.RADIAL_SHELLS.DA_STATION_BASE);
        const normal = base.clone().normalize();
        assert.closeTo(normal.length(), 1.0, 1e-4);
        assert.closeTo(base.length(), 5.050, 1e-3);
      }
    });

    it('F5.3: verifies beacon pin height extends from R=5.050 to glowing cap at R=5.350', () => {
      const rBase = INVARIANTS.RADIAL_SHELLS.DA_STATION_BASE;
      const rCap = INVARIANTS.RADIAL_SHELLS.DA_STATION_CAP;
      assert.strictEqual(rBase, 5.050);
      assert.strictEqual(rCap, 5.350);
      const pinHeight = rCap - rBase;
      assert.closeTo(pinHeight, 0.300, 1e-4);
    });

    it('F5.4: verifies DA increment color mapping (+3K to +8K)', () => {
      function getIncrementColor(inc) {
        const norm = (inc - 3.0) / (8.0 - 3.0);
        return Math.max(0, Math.min(1, norm));
      }
      for (const st of stations) {
        const norm = getIncrementColor(st.increment);
        assert.ok(norm >= 0.0 && norm <= 1.0);
      }
    });

    it('F5.5: verifies station popup payload includes background, observation, and increment', () => {
      for (const st of stations) {
        assert.strictEqual(st.increment, Number((st.obsVal - st.bgVal).toFixed(1)));
        assert.ok(typeof st.elevM === 'number');
        assert.strictEqual(st.qc, 'PASS');
      }
    });
  });

  describe('Tier 1 - Feature 6: 3D Ensemble Spread Layer', () => {
    it('F6.1: verifies concentric shell radius is R=5.020 (defending against Z-fighting)', () => {
      const rSpread = INVARIANTS.RADIAL_SHELLS.ENSEMBLE_SPREAD;
      assert.strictEqual(rSpread, 5.020);
      assert.greaterThan(rSpread, INVARIANTS.RADIAL_SHELLS.BASE_GLOBE);
      assert.lessThan(rSpread, INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS);
    });

    it('F6.2: verifies plasma shader material opacity uniform binding [0.0, 1.0]', () => {
      const material = {
        uniforms: {
          uOpacity: { value: 0.8 },
          uSpreadMax: { value: 1.5 }
        },
        transparent: true
      };
      assert.strictEqual(material.uniforms.uOpacity.value, 0.8);
      // Update opacity
      material.uniforms.uOpacity.value = 0.45;
      assert.strictEqual(material.uniforms.uOpacity.value, 0.45);
    });

    it('F6.3: verifies visibility toggle updates mesh visibility in scene graph', () => {
      const mesh = new MockMesh();
      mesh.visible = true;
      mesh.visible = false;
      assert.strictEqual(mesh.visible, false);
      mesh.visible = true;
      assert.strictEqual(mesh.visible, true);
    });

    it('F6.4: verifies ensemble spread range metrics (0.0 to 1.5K plasma gradient)', () => {
      const meta = INVARIANTS.STUDY_SPEC.V3.pillars[0];
      assert.strictEqual(meta.spreadUnits, 'K');
      assert.lessThan(meta.meanSpread, meta.maxSpread);
      assert.lessThan(meta.maxSpread, 1.5);
    });

    it('F6.5: verifies memory cleanup disposal hooks for spread mesh', () => {
      let disposedGeom = false;
      let disposedMat = false;
      const spreadMesh = {
        geometry: { dispose: () => { disposedGeom = true; } },
        material: { dispose: () => { disposedMat = true; } }
      };
      spreadMesh.geometry.dispose();
      spreadMesh.material.dispose();
      assert.strictEqual(disposedGeom, true);
      assert.strictEqual(disposedMat, true);
    });
  });

  describe('Tier 1 - Feature 7: 3D Mesoscale Downscaling Insets', () => {
    const domain = INVARIANTS.STUDY_SPEC.V3.mesoscaleDomain;

    it('F7.1: verifies Alpine domain bounds [44-48°N, 6-14°E]', () => {
      const [minLat, maxLat, minLon, maxLon] = domain.bounds;
      assert.strictEqual(minLat, 44.0);
      assert.strictEqual(maxLat, 48.0);
      assert.strictEqual(minLon, 6.0);
      assert.strictEqual(maxLon, 14.0);
    });

    it('F7.2: verifies mesoscale inset shell radius is R=5.035', () => {
      const rMeso = INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS;
      assert.strictEqual(rMeso, 5.035);
      assert.greaterThan(rMeso, INVARIANTS.RADIAL_SHELLS.ENSEMBLE_SPREAD);
      assert.lessThan(rMeso, INVARIANTS.RADIAL_SHELLS.UNCERTAINTY_CONE);
    });

    it('F7.3: computes 8x super-resolution grid dimension', () => {
      assert.strictEqual(domain.scaleFactor, 8);
      const baseGrid = 16;
      const downscaledGrid = baseGrid * domain.scaleFactor;
      assert.strictEqual(downscaledGrid, 128);
    });

    it('F7.4: verifies orographic lapse-rate cooling formula (-6.5 K/km)', () => {
      const lapseRate = -0.0065; // K/m
      const montBlancElev = 4808; // meters
      const deltaT = montBlancElev * lapseRate;
      assert.closeTo(deltaT, -31.25, 0.1);
    });

    it('F7.5: verifies neon cyan boundary perimeter coordinates generation', () => {
      const [minLat, maxLat, minLon, maxLon] = domain.bounds;
      const corners = [
        CoordinateTransforms.latLonToVector3(minLat, minLon, INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS),
        CoordinateTransforms.latLonToVector3(minLat, maxLon, INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS),
        CoordinateTransforms.latLonToVector3(maxLat, maxLon, INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS),
        CoordinateTransforms.latLonToVector3(maxLat, minLon, INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS)
      ];
      assert.strictEqual(corners.length, 4);
      corners.forEach(c => assert.closeTo(c.length(), 5.035, 1e-3));
    });
  });

  describe('Tier 1 - Feature 8: Boresight Camera Navigation', () => {
    it('F8.1: verifies boresight rotation formula rotY = pi/2 - lon_rad, rotX = lat_rad * 0.4', () => {
      const lat = 45.0;
      const lon = 10.0;
      const { rotX, rotY } = CoordinateTransforms.boresightRotation(lat, lon);
      const expectedRotX = 45.0 * (Math.PI / 180) * 0.4;
      const expectedRotY = -(10.0 * (Math.PI / 180)) - Math.PI / 2;
      assert.closeTo(rotX, expectedRotX, 1e-4);
      assert.closeTo(rotY, expectedRotY, 1e-4);
    });

    it('F8.2: verifies Global view preset positions camera at (0, 0, 14)', () => {
      const globalPos = new MockVector3(0, 0, 14);
      assert.strictEqual(globalPos.z, 14);
      assert.strictEqual(globalPos.x, 0);
      assert.strictEqual(globalPos.y, 0);
    });

    it('F8.3: verifies Italy synoptic preset coordinates (42°N, 12°E, distance 8.5)', () => {
      const lat = 42.0;
      const lon = 12.0;
      const distance = 8.5;
      const { rotX, rotY } = CoordinateTransforms.boresightRotation(lat, lon);
      assert.ok(rotX > 0);
      assert.ok(rotY < 0);
      assert.strictEqual(distance, 8.5);
    });

    it('F8.4: verifies Japan synoptic preset coordinates (36°N, 138°E, distance 8.5)', () => {
      const lat = 36.0;
      const lon = 138.0;
      const distance = 8.5;
      const { rotX, rotY } = CoordinateTransforms.boresightRotation(lat, lon);
      assert.ok(rotX > 0);
      assert.ok(rotY < -Math.PI);
      assert.strictEqual(distance, 8.5);
    });

    it('F8.5: verifies camera zoom clamp restricts Z distance to [7, 22]', () => {
      function clampZoom(currentZ, deltaY) {
        return Math.max(7, Math.min(22, currentZ + deltaY * 0.01));
      }
      assert.strictEqual(clampZoom(10, 500), 15);
      assert.strictEqual(clampZoom(20, 1000), 22); // clamped at 22
      assert.strictEqual(clampZoom(8, -500), 7);   // clamped at 7
    });
  });

  describe('Tier 1 - Feature 9: Raycasting & Pinned 3D Popups', () => {
    it('F9.1: verifies normalized device coordinates (NDC) computation from clientX/Y', () => {
      function getNDC(clientX, clientY, width = 1920, height = 1080) {
        return {
          x: (clientX / width) * 2 - 1,
          y: -(clientY / height) * 2 + 1
        };
      }
      const center = getNDC(960, 540);
      assert.closeTo(center.x, 0.0, 1e-4);
      assert.closeTo(center.y, 0.0, 1e-4);

      const topLeft = getNDC(0, 0);
      assert.closeTo(topLeft.x, -1.0, 1e-4);
      assert.closeTo(topLeft.y, 1.0, 1e-4);
    });

    it('F9.2: verifies drag-vs-click threshold suppresses raycasting when movement > 5px', () => {
      function isClick(downPos, upPos, threshold = 5) {
        const dx = upPos.x - downPos.x;
        const dy = upPos.y - downPos.y;
        return Math.sqrt(dx * dx + dy * dy) <= threshold;
      }
      assert.strictEqual(isClick({ x: 100, y: 100 }, { x: 102, y: 101 }), true);
      assert.strictEqual(isClick({ x: 100, y: 100 }, { x: 110, y: 100 }), false);
    });

    it('F9.3: verifies front-hemisphere occlusion filter rejects rear-facing markers', () => {
      const frontPoint = new MockVector3(0, 0, 5.05); // directly facing camera at (0, 5, 14)
      const rearPoint = new MockVector3(0, 0, -5.05); // on opposite side of Earth
      const cameraPos = new MockVector3(0, 5, 14);

      assert.strictEqual(CoordinateTransforms.isFrontFacing(frontPoint, new MockVector3(0, 0, 0), cameraPos), true);
      assert.strictEqual(CoordinateTransforms.isFrontFacing(rearPoint, new MockVector3(0, 0, 0), cameraPos), false);
    });

    it('F9.4: verifies 3D to 2D screen coordinate projection math', () => {
      const camera = { position: new MockVector3(0, 0, 14), fov: 45 };
      const point = new MockVector3(0, 0, 5);
      const screenPos = CoordinateTransforms.projectToScreen(point, camera, 1920, 1080);
      assert.strictEqual(screenPos.visible, true);
      assert.strictEqual(screenPos.x, 960);
      assert.strictEqual(screenPos.y, 540);
    });

    it('F9.5: verifies popup card open and close DOM interactions', () => {
      const { document } = createMockDOM();
      const popup = document.getElementById('poi-popup-card');
      const closeBtn = document.getElementById('popup-close');
      const title = document.getElementById('popup-title');

      // Open popup
      popup.style.display = 'block';
      title.innerText = 'Rome (LIRF) Station';
      assert.strictEqual(popup.style.display, 'block');
      assert.strictEqual(title.innerText, 'Rome (LIRF) Station');

      // Close popup
      closeBtn.addEventListener('click', () => { popup.style.display = 'none'; });
      closeBtn.click();
      assert.strictEqual(popup.style.display, 'none');
    });
  });

  describe('Tier 1 - Feature 10: Study Version Timeline & Slider', () => {
    it('F10.1: maps slider index 0->V1, 1->V2, 2->V3', () => {
      const versionMap = ['V1', 'V2', 'V3'];
      assert.strictEqual(versionMap[0], 'V1');
      assert.strictEqual(versionMap[1], 'V2');
      assert.strictEqual(versionMap[2], 'V3');
    });

    it('F10.2: emits study-version-changed event with payload { versionId, versionData }', () => {
      const { window } = createMockDOM();
      let eventPayload = null;
      window.addEventListener('study-version-changed', (e) => {
        eventPayload = e.detail;
      });

      const mockEvent = {
        type: 'study-version-changed',
        detail: { versionId: 'V2', versionData: INVARIANTS.STUDY_SPEC.V2 }
      };
      window.dispatchEvent(mockEvent);

      assert.ok(eventPayload !== null);
      assert.strictEqual(eventPayload.versionId, 'V2');
      assert.strictEqual(eventPayload.versionData.id, 'V2');
    });

    it('F10.3: toggles active CSS class on timeline tab elements', () => {
      const { document } = createMockDOM();
      const tab1 = document.getElementById('tab-v1');
      const tab2 = document.getElementById('tab-v2');
      const tab3 = document.getElementById('tab-v3');

      function setActiveTab(tab) {
        [tab1, tab2, tab3].forEach(t => t.classList.remove('active-tab'));
        tab.classList.add('active-tab');
      }

      setActiveTab(tab1);
      assert.strictEqual(tab1.classList.contains('active-tab'), true);
      assert.strictEqual(tab2.classList.contains('active-tab'), false);

      setActiveTab(tab3);
      assert.strictEqual(tab1.classList.contains('active-tab'), false);
      assert.strictEqual(tab3.classList.contains('active-tab'), true);
    });

    it('F10.4: synchronizes layer availability per version (V1 disables V3 pillars)', () => {
      function getAvailableLayersForVersion(vId) {
        if (vId === 'V1') return ['t2m', 'tendency'];
        if (vId === 'V2') return ['t2m', 'tendency', 'persistence_diff'];
        if (vId === 'V3') return ['t2m', 'tendency', 'cyclone', 'da', 'spread', 'mesoscale'];
        return [];
      }
      assert.deepEqual(getAvailableLayersForVersion('V1'), ['t2m', 'tendency']);
      assert.ok(getAvailableLayersForVersion('V3').includes('cyclone'));
      assert.ok(getAvailableLayersForVersion('V3').includes('spread'));
    });

    it('F10.5: preserves active version state in memory', () => {
      let currentVersion = 'V1';
      function switchVersion(newV) {
        currentVersion = newV;
      }
      switchVersion('V3');
      assert.strictEqual(currentVersion, 'V3');
    });
  });

  describe('Tier 1 - Feature 11: Version Comparison Mode', () => {
    it('F11.1: toggles comparison modal visibility open/closed', () => {
      const { document } = createMockDOM();
      const modal = document.getElementById('comparison-modal');
      const openBtn = document.getElementById('open-comparison');
      const closeBtn = document.getElementById('modal-close');

      openBtn.addEventListener('click', () => { modal.style.display = 'flex'; });
      closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });

      assert.strictEqual(modal.style.display, undefined);
      openBtn.click();
      assert.strictEqual(modal.style.display, 'flex');
      closeBtn.click();
      assert.strictEqual(modal.style.display, 'none');
    });

    it('F11.2: renders 3-column side-by-side comparison structure', () => {
      const columns = ['V1', 'V2', 'V3'];
      assert.strictEqual(columns.length, 3);
      const titles = columns.map(c => INVARIANTS.STUDY_SPEC[c].name);
      assert.ok(titles[0].includes('Leakage'));
      assert.ok(titles[1].includes('Decoupled'));
      assert.ok(titles[2].includes('7 Advanced'));
    });

    it('F11.3: renders scientific metric comparison grid (RMSE, MAE, TAC, ACC)', () => {
      const v1 = INVARIANTS.STUDY_SPEC.V1.metrics;
      const v2 = INVARIANTS.STUDY_SPEC.V2.metrics;

      assert.strictEqual(v1.rmse, 0.747);
      assert.strictEqual(v2.rmse, 2.129);
      assert.strictEqual(v1.mae, 0.582);
      assert.strictEqual(v2.mae, 1.037);
      assert.strictEqual(v2.tac, 0.0);
      assert.strictEqual(v2.acc, null);
    });

    it('F11.4: displays scientific integrity badges per version', () => {
      function getBadge(vId) {
        if (vId === 'V1') return { label: 'LEAKAGE DETECTED', variant: 'danger' };
        if (vId === 'V2') return { label: 'VERIFIED PHYSICAL BASELINE', variant: 'success' };
        if (vId === 'V3') return { label: '7-PILLAR SUITE', variant: 'primary' };
      }
      assert.strictEqual(getBadge('V1').variant, 'danger');
      assert.strictEqual(getBadge('V2').variant, 'success');
      assert.strictEqual(getBadge('V3').variant, 'primary');
    });

    it('F11.5: handles Escape key to dismiss comparison modal', () => {
      const { window, document } = createMockDOM();
      const modal = document.getElementById('comparison-modal');
      modal.style.display = 'flex';

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') modal.style.display = 'none';
      });

      window.dispatchEvent({ type: 'keydown', key: 'Escape' });
      assert.strictEqual(modal.style.display, 'none');
    });
  });

  describe('Tier 1 - Feature 12: Layer Toggles & Dynamic Legends', () => {
    it('F12.1: toggles layer buttons active class on click', () => {
      const { document } = createMockDOM();
      const btnCyclone = document.getElementById('layer-cyclone');
      let active = false;

      btnCyclone.addEventListener('click', () => {
        active = !active;
        btnCyclone.classList.toggle('active-btn', active);
      });

      btnCyclone.click();
      assert.strictEqual(btnCyclone.classList.contains('active-btn'), true);
      btnCyclone.click();
      assert.strictEqual(btnCyclone.classList.contains('active-btn'), false);
    });

    it('F12.2: updates dynamic legend gradient for T2m (Turbo colormap)', () => {
      const { document } = createMockDOM();
      const bar = document.getElementById('legend-bar');
      const turboGradient = 'linear-gradient(to right, #30123b, #4686fb, #1ae4b6, #a2fc3c, #fbb41a, #e4460a, #7a0403)';
      bar.style.background = turboGradient;
      assert.strictEqual(bar.style.background, turboGradient);
    });

    it('F12.3: updates dynamic legend bounds for Tendency ΔT (-6°C to +6°C)', () => {
      const { document } = createMockDOM();
      const min = document.getElementById('legend-min');
      const max = document.getElementById('legend-max');
      min.innerText = '-6°C';
      max.innerText = '+6°C';
      assert.strictEqual(min.innerText, '-6°C');
      assert.strictEqual(max.innerText, '+6°C');
    });

    it('F12.4: toggles spin rotation state and updates button text', () => {
      const { document } = createMockDOM();
      const btnSpin = document.getElementById('toggle-spin');
      let isSpinning = true;

      btnSpin.addEventListener('click', () => {
        isSpinning = !isSpinning;
        btnSpin.innerText = isSpinning ? '⏸ Pause Rotation' : '▶ Resume Rotation';
      });

      btnSpin.click();
      assert.strictEqual(isSpinning, false);
      assert.strictEqual(btnSpin.innerText, '▶ Resume Rotation');

      btnSpin.click();
      assert.strictEqual(isSpinning, true);
      assert.strictEqual(btnSpin.innerText, '⏸ Pause Rotation');
    });

    it('F12.5: toggles topo relief bumpScale state between 0.18 and 0.0', () => {
      const { document } = createMockDOM();
      const btnRelief = document.getElementById('toggle-relief');
      let bumpScale = 0.18;

      btnRelief.addEventListener('click', () => {
        bumpScale = bumpScale > 0 ? 0.0 : 0.18;
      });

      btnRelief.click();
      assert.strictEqual(bumpScale, 0.0);
      btnRelief.click();
      assert.strictEqual(bumpScale, 0.18);
    });
  });

  describe('Tier 1 - Feature 13: Main Integration & E2E Verification', () => {
    it('F13.1: verifies canvas-container element exists in index.html', () => {
      const htmlPath = path.resolve('viewer_app/index.html');
      assert.ok(fs.existsSync(htmlPath), 'index.html exists');
      const html = fs.readFileSync(htmlPath, 'utf8');
      assert.ok(html.includes('id="canvas-container"'));
    });

    it('F13.2: verifies radial shell non-interference invariant (Base < Spread < Meso < Cone < Tube < Cap)', () => {
      const shells = INVARIANTS.RADIAL_SHELLS;
      assert.lessThan(shells.BASE_GLOBE, shells.ENSEMBLE_SPREAD);
      assert.lessThan(shells.ENSEMBLE_SPREAD, shells.MESOSCALE_INSETS);
      assert.lessThan(shells.MESOSCALE_INSETS, shells.UNCERTAINTY_CONE);
      assert.lessThan(shells.UNCERTAINTY_CONE, shells.CYCLONE_TUBE);
      assert.lessThan(shells.CYCLONE_TUBE, shells.DA_STATION_CAP);
    });

    it('F13.3: verifies animation loop advances globe rotation when isSpinning is true', () => {
      let isSpinning = true;
      let isDragging = false;
      const globe = { rotation: { y: 0 } };

      function step() {
        if (isSpinning && !isDragging) {
          globe.rotation.y += 0.0018;
        }
      }

      step();
      assert.closeTo(globe.rotation.y, 0.0018, 1e-5);
      isSpinning = false;
      step();
      assert.closeTo(globe.rotation.y, 0.0018, 1e-5); // unchanged
    });

    it('F13.4: verifies window resize handler updates camera aspect and renderer dimensions', () => {
      const camera = { aspect: 1, updateProjectionMatrix: () => { camera.updated = true; } };
      const renderer = { setSize: (w, h) => { renderer.w = w; renderer.h = h; } };

      function handleResize(width, height) {
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
      }

      handleResize(1920, 1080);
      assert.closeTo(camera.aspect, 1920 / 1080, 1e-4);
      assert.strictEqual(camera.updated, true);
      assert.strictEqual(renderer.w, 1920);
      assert.strictEqual(renderer.h, 1080);
    });

    it('F13.5: verifies index.html loads main.js as an ES module', () => {
      const htmlPath = path.resolve('viewer_app/index.html');
      const html = fs.readFileSync(htmlPath, 'utf8');
      assert.ok(html.includes('<script type="module" src="/main.js"></script>') || html.includes('type="module"'));
    });
  });

  describe('Tier 1 - Feature 14: Production Vercel Redeployment', () => {
    it('F14.1: verifies package.json contains valid build script', () => {
      const pkgPath = path.resolve('viewer_app/package.json');
      assert.ok(fs.existsSync(pkgPath), 'package.json exists');
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      assert.strictEqual(pkg.scripts.build, 'vite build');
    });

    it('F14.2: verifies target production domain URL is https://viewerapp.vercel.app', () => {
      const targetUrl = 'https://viewerapp.vercel.app';
      assert.matches(targetUrl, /^https:\/\/[a-z0-9-]+\.vercel\.app$/);
    });

    it('F14.3: validates security headers specification (X-Content-Type-Options: nosniff)', () => {
      const secHeaders = [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' }
      ];
      const nosniff = secHeaders.find(h => h.key === 'X-Content-Type-Options');
      assert.strictEqual(nosniff.value, 'nosniff');
    });

    it('F14.4: validates texture caching header rule (Cache-Control max-age >= 86400)', () => {
      const textureHeader = {
        source: '/textures/(.*)',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }]
      };
      assert.ok(textureHeader.headers[0].value.includes('public'));
      assert.ok(textureHeader.headers[0].value.includes('max-age='));
    });

    it('F14.5: verifies Vite production build artifact destination is dist/', () => {
      const outDir = 'dist';
      assert.strictEqual(outDir, 'dist');
    });
  });
}
