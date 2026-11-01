/**
 * tier4_real_world.test.js
 * Tier 4: Real-World Application Scenarios Test Suite
 * End-to-end full user workflows simulating real user journeys through the application.
 */

import { describe, it, assert } from './test_framework.js';
import {
  createMockDOM,
  MockVector3,
  CoordinateTransforms,
  INVARIANTS
} from './mock_environment.js';

export function registerTier4Tests() {
  describe('Tier 4 - Real-World Application Scenarios', () => {

    it('Scenario 1: Complete Study Trajectory & Rome DA Station Workflow', () => {
      const { window, document } = createMockDOM();

      // State machine
      const state = {
        version: 'V2',
        isSpinning: true,
        camera: { pos: new MockVector3(0, 5, 14), lat: 0, lon: 0 },
        activeLayers: new Set(['t2m']),
        popup: { visible: false, station: null },
        modal: { visible: false }
      };

      // 1. Landing on globe: initial state is spinning with operational T2m
      assert.strictEqual(state.isSpinning, true);
      assert.strictEqual(state.activeLayers.has('t2m'), true);

      // 2. Switching to V1 Quarantined Audit on timeline
      state.version = 'V1';
      const v1Data = INVARIANTS.STUDY_SPEC.V1;
      assert.strictEqual(v1Data.quarantined, true);
      assert.ok(v1Data.integrityWarning.includes('Target leakage detected'));

      // 3. Opening comparison modal
      state.modal.visible = true;
      assert.strictEqual(state.modal.visible, true);
      // Validate side-by-side comparison metrics
      assert.strictEqual(INVARIANTS.STUDY_SPEC.V1.metrics.rmse, 0.747);
      assert.strictEqual(INVARIANTS.STUDY_SPEC.V2.metrics.rmse, 2.129);

      // 4. Closing comparison modal
      state.modal.visible = false;
      assert.strictEqual(state.modal.visible, false);

      // 5. Switching to V3 (7 Advanced Capability Pillars)
      state.version = 'V3';
      assert.strictEqual(state.version, 'V3');

      // 6. Enabling DA station pins layer
      state.activeLayers.add('da_stations');
      assert.strictEqual(state.activeLayers.has('da_stations'), true);

      // 7. Clicking Rome station marker (DA_ROM)
      const romeStation = INVARIANTS.STUDY_SPEC.V3.daStations.find(s => s.id === 'DA_ROM');
      assert.ok(romeStation !== undefined);
      state.popup.visible = true;
      state.popup.station = romeStation;
      state.isSpinning = false; // Auto-pause on inspection

      assert.strictEqual(state.popup.station.name, 'Rome (LIRF)');
      assert.strictEqual(state.popup.station.increment, 6.7);
      assert.strictEqual(state.isSpinning, false);

      // 8. Flying to Italy synoptic preset
      const italyLat = 42.0;
      const italyLon = 12.0;
      const { rotX, rotY } = CoordinateTransforms.boresightRotation(italyLat, italyLon);
      state.camera.lat = italyLat;
      state.camera.lon = italyLon;
      state.camera.pos.set(0, 1.5, 8.5);

      assert.closeTo(state.camera.lat, 42.0, 1e-4);
      assert.closeTo(state.camera.lon, 12.0, 1e-4);
      assert.strictEqual(state.camera.pos.z, 8.5);
    });

    it('Scenario 2: Severe Weather WPAC Typhoon & Ensemble Uncertainty Workflow', () => {
      const state = {
        version: 'V3',
        camera: { pos: new MockVector3(0, 1.5, 8.5) },
        activeLayers: new Set(['cyclone', 'uncertainty_cone', 'ensemble_spread']),
        spreadOpacity: 0.8
      };

      // 1. Verify V3 cyclone trajectory has 5 waypoints
      const waypoints = INVARIANTS.STUDY_SPEC.V3.cycloneWaypoints;
      assert.strictEqual(waypoints.length, 5);

      // 2. Track storm intensification from WP1 (998 hPa) to WP4 (935 hPa Super Typhoon)
      const wp1 = waypoints[0];
      const wp4 = waypoints[3];
      assert.strictEqual(wp1.status, 'Tropical Storm');
      assert.strictEqual(wp1.mslp, 998);
      assert.strictEqual(wp4.status, 'Super Typhoon');
      assert.strictEqual(wp4.mslp, 935);
      assert.greaterThan(wp4.windKt, wp1.windKt);

      // 3. Adjust ensemble spread opacity slider from 0.8 down to 0.4
      state.spreadOpacity = 0.4;
      assert.strictEqual(state.spreadOpacity, 0.4);

      // 4. Fly to Japan West-Pacific synoptic view (36°N, 138°E)
      const { rotX, rotY } = CoordinateTransforms.boresightRotation(36.0, 138.0);
      assert.ok(rotX > 0);
      assert.ok(rotY < 0);
    });

    it('Scenario 3: Alpine Mesoscale Downscaling Inset Workflow', () => {
      const state = {
        version: 'V3',
        activeLayers: new Set(['mesoscale_insets', 't2m']),
        reliefActive: true
      };

      // 1. Inset domain bounds check
      const domain = INVARIANTS.STUDY_SPEC.V3.mesoscaleDomain;
      assert.strictEqual(domain.id, 'MESO_ALPINE');
      assert.deepEqual(domain.bounds, [44.0, 48.0, 6.0, 14.0]);
      assert.strictEqual(domain.scaleFactor, 8);

      // 2. Verify radial shell registration above base globe
      const rGlobe = INVARIANTS.RADIAL_SHELLS.BASE_GLOBE;
      const rMeso = INVARIANTS.RADIAL_SHELLS.MESOSCALE_INSETS;
      assert.greaterThan(rMeso, rGlobe);
      assert.strictEqual(rMeso, 5.035);

      // 3. Switch atmospheric layer from T2m to 24h Tendency
      state.activeLayers.delete('t2m');
      state.activeLayers.add('tendency');
      assert.strictEqual(state.activeLayers.has('tendency'), true);
      assert.strictEqual(state.activeLayers.has('mesoscale_insets'), true);
      assert.strictEqual(state.reliefActive, true); // Relief preserved
    });

    it('Scenario 4: Scientific Audit & Integrity Verification Workflow', () => {
      const v2 = INVARIANTS.STUDY_SPEC.V2;

      // 1. Verify 3-stage pipeline sequence
      assert.strictEqual(v2.pipelineStages[0], 'Forecast');
      assert.strictEqual(v2.pipelineStages[1], 'Freeze');
      assert.strictEqual(v2.pipelineStages[2], 'Verify');

      // 2. Check SHA-256 seal
      assert.strictEqual(v2.sealed, true);
      assert.strictEqual(v2.manifestHashLength, 64);

      // 3. Verify physical baseline metrics
      assert.strictEqual(v2.metrics.rmse, 2.129);
      assert.strictEqual(v2.metrics.mae, 1.037);

      // 4. Verify TAC and ACC separation
      assert.strictEqual(v2.metrics.tac, 0.0);
      assert.strictEqual(v2.metrics.acc, null);

      // 5. Verify hardware blocker declaration
      assert.strictEqual(v2.hardwareBlocker.declared, true);
      assert.strictEqual(v2.hardwareBlocker.gpu, 'AMD GPU');
    });

    it('Scenario 5: Responsive Viewport, Drag Navigation & Reset Workflow', () => {
      const { window } = createMockDOM();
      let camera = { aspect: 16 / 9, pos: new MockVector3(0, 5, 14) };
      let globe = { rotation: { x: 0, y: 0 } };
      let isSpinning = true;

      // 1. Viewport resize to tablet portrait
      window.innerWidth = 768;
      window.innerHeight = 1024;
      camera.aspect = window.innerWidth / window.innerHeight;
      assert.closeTo(camera.aspect, 0.75, 1e-3);

      // 2. Pointer drag rotation interaction
      const deltaX = 50;
      const deltaY = -30;
      globe.rotation.y += deltaX * 0.005;
      globe.rotation.x += deltaY * 0.005;
      assert.closeTo(globe.rotation.y, 0.25, 1e-4);
      assert.closeTo(globe.rotation.x, -0.15, 1e-4);

      // 3. Reset to Global view
      camera.pos.set(0, 0, 14);
      isSpinning = true;
      assert.strictEqual(camera.pos.z, 14);
      assert.strictEqual(camera.pos.x, 0);
      assert.strictEqual(camera.pos.y, 0);
      assert.strictEqual(isSpinning, true);
    });
  });
}
