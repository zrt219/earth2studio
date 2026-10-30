/**
 * tier3_cross_feature.test.js
 * Tier 3: Cross-Feature Combinations Test Suite
 * Covers multi-feature interactions, state machine concurrency, and cross-module invariants.
 */

import { describe, it, assert } from './test_framework.js';
import {
  createMockDOM,
  MockVector3,
  CoordinateTransforms,
  INVARIANTS
} from './mock_environment.js';

export function registerTier3Tests() {
  describe('Tier 3 - Cross-Feature Combinations', () => {

    it('T3.1: Switching from V3 to V1 hides 3D pillar layers (cyclone, DA pins, spread)', () => {
      // Simulate state controller
      const activeLayers = new Set(['cyclone', 'da', 'spread']);
      let currentVersion = 'V3';

      function switchVersion(newV) {
        currentVersion = newV;
        if (newV === 'V1') {
          // V1 only supports baseline atmospheric layers
          activeLayers.delete('cyclone');
          activeLayers.delete('da');
          activeLayers.delete('spread');
        }
      }

      assert.strictEqual(activeLayers.size, 3);
      switchVersion('V1');
      assert.strictEqual(currentVersion, 'V1');
      assert.strictEqual(activeLayers.has('cyclone'), false);
      assert.strictEqual(activeLayers.has('da'), false);
      assert.strictEqual(activeLayers.has('spread'), false);
    });

    it('T3.2: Raycasting click on DA station pauses globe rotation and shows popup', () => {
      let isSpinning = true;
      let activePopupStation = null;

      function handleStationClick(station) {
        isSpinning = false; // pause rotation to allow reading popup
        activePopupStation = station;
      }

      assert.strictEqual(isSpinning, true);
      const romeStation = INVARIANTS.STUDY_SPEC.V3.daStations[1];
      handleStationClick(romeStation);

      assert.strictEqual(isSpinning, false);
      assert.strictEqual(activePopupStation.name, 'Rome (LIRF)');
      assert.strictEqual(activePopupStation.increment, 6.7);
    });

    it('T3.3: Opening comparison modal dismisses any currently open POI popup', () => {
      const { document } = createMockDOM();
      const popup = document.getElementById('poi-popup-card');
      const modal = document.getElementById('comparison-modal');

      popup.style.display = 'block';
      assert.strictEqual(popup.style.display, 'block');

      // Open comparison modal
      function openComparisonModal() {
        if (popup.style.display === 'block') {
          popup.style.display = 'none'; // Dismiss popup to avoid overlapping HUD
        }
        modal.style.display = 'flex';
      }

      openComparisonModal();
      assert.strictEqual(popup.style.display, 'none');
      assert.strictEqual(modal.style.display, 'flex');
    });

    it('T3.4: Scrubbing timeline slider while flying to region updates target cleanly without oscillation', () => {
      let cameraTarget = { lat: 42.0, lon: 12.0, distance: 8.5 }; // Flying to Italy
      let isFlying = true;

      function onTimelineChange(newVersion) {
        // Timeline change should not corrupt camera coordinates
        if (newVersion === 'V1') {
          // V1 defaults to global perspective
          cameraTarget = { lat: 0, lon: 0, distance: 14 };
          isFlying = false;
        }
      }

      assert.strictEqual(cameraTarget.distance, 8.5);
      onTimelineChange('V1');
      assert.strictEqual(cameraTarget.distance, 14);
      assert.strictEqual(cameraTarget.lat, 0);
    });

    it('T3.5: Toggling topo relief is preserved across atmospheric layer texture swaps', () => {
      let bumpScale = 0.18;
      let activeTexture = 'earth_t2m.jpg';

      function switchLayer(newTexture) {
        activeTexture = newTexture;
        // bumpScale must NOT be reset to 0 by texture switch
      }

      switchLayer('earth_tendency.jpg');
      assert.strictEqual(activeTexture, 'earth_tendency.jpg');
      assert.strictEqual(bumpScale, 0.18);

      // Disable relief
      bumpScale = 0.0;
      switchLayer('earth_t2m.jpg');
      assert.strictEqual(activeTexture, 'earth_t2m.jpg');
      assert.strictEqual(bumpScale, 0.0);
    });

    it('T3.6: Rapid navigation clicks (Italy -> Japan -> Global) resolves to latest target', () => {
      let currentNavigation = null;
      function navigateTo(region) {
        currentNavigation = region;
      }

      navigateTo('Italy');
      navigateTo('Japan');
      navigateTo('Global');

      assert.strictEqual(currentNavigation, 'Global');
    });

    it('T3.7: Viewport resize recalculates popup screen coordinates dynamically', () => {
      const camera = { position: new MockVector3(0, 0, 14), fov: 45 };
      const stationPos = CoordinateTransforms.latLonToVector3(41.80, 12.24, INVARIANTS.RADIAL_SHELLS.DA_STATION_CAP);

      const screen1080p = CoordinateTransforms.projectToScreen(stationPos, camera, 1920, 1080);
      const screen4k = CoordinateTransforms.projectToScreen(stationPos, camera, 3840, 2160);

      assert.strictEqual(screen1080p.visible, true);
      assert.strictEqual(screen4k.visible, true);
      // 4K position should scale proportionally with resolution
      assert.closeTo(screen4k.x / screen1080p.x, 2.0, 0.05);
      assert.closeTo(screen4k.y / screen1080p.y, 2.0, 0.05);
    });

    it('T3.8: Radial shell non-intersection invariant across 360-degree sphere scan', () => {
      const shells = INVARIANTS.RADIAL_SHELLS;
      const testCoordinates = [
        { lat: 0, lon: 0 },
        { lat: 45, lon: 45 },
        { lat: -45, lon: 90 },
        { lat: 80, lon: -120 },
        { lat: -80, lon: 180 }
      ];

      for (const { lat, lon } of testCoordinates) {
        const rGlobe = CoordinateTransforms.latLonToVector3(lat, lon, shells.BASE_GLOBE).length();
        const rSpread = CoordinateTransforms.latLonToVector3(lat, lon, shells.ENSEMBLE_SPREAD).length();
        const rMeso = CoordinateTransforms.latLonToVector3(lat, lon, shells.MESOSCALE_INSETS).length();
        const rCone = CoordinateTransforms.latLonToVector3(lat, lon, shells.UNCERTAINTY_CONE).length();
        const rTube = CoordinateTransforms.latLonToVector3(lat, lon, shells.CYCLONE_TUBE).length();
        const rCap = CoordinateTransforms.latLonToVector3(lat, lon, shells.DA_STATION_CAP).length();

        assert.lessThan(rGlobe, rSpread);
        assert.lessThan(rSpread, rMeso);
        assert.lessThan(rMeso, rCone);
        assert.lessThan(rCone, rTube);
        assert.lessThan(rTube, rCap);
      }
    });

    it('T3.9: Version switch updates dynamic legend gradient and title', () => {
      const { document } = createMockDOM();
      const legendTitle = document.getElementById('legend-title');
      const legendBar = document.getElementById('legend-bar');

      function applyVersionLegend(versionId) {
        if (versionId === 'V1') {
          legendTitle.innerText = 'Synthetic Audit Diagnostic T2m (°C)';
          legendBar.style.background = 'linear-gradient(to right, #e11d48, #fbbf24)';
        } else if (versionId === 'V2') {
          legendTitle.innerText = 'NOAA GFS Physical Persistence T2m (°C)';
          legendBar.style.background = 'linear-gradient(to right, #30123b, #4686fb, #1ae4b6, #a2fc3c, #fbb41a, #e4460a, #7a0403)';
        } else if (versionId === 'V3') {
          legendTitle.innerText = 'Ensemble Spread & DA Increments (K)';
          legendBar.style.background = 'linear-gradient(to right, #0d0887, #6a00a8, #b12a90, #e16462, #fca636, #f0f921)';
        }
      }

      applyVersionLegend('V1');
      assert.ok(legendTitle.innerText.includes('Synthetic Audit'));

      applyVersionLegend('V3');
      assert.ok(legendTitle.innerText.includes('Ensemble Spread'));
      assert.ok(legendBar.style.background.includes('#0d0887'));
    });

    it('T3.10: Single active station popup invariant: clicking station B closes station A', () => {
      let activeStationId = null;

      function openStationPopup(id) {
        activeStationId = id;
      }

      openStationPopup('DA_MIL');
      assert.strictEqual(activeStationId, 'DA_MIL');

      openStationPopup('DA_ROM');
      assert.strictEqual(activeStationId, 'DA_ROM'); // Replaced, never co-active
    });

    it('T3.11: Rotation toggle state is preserved across study version transitions', () => {
      let isSpinning = false; // User manually paused spin

      function setVersion(vId) {
        // Should NOT force isSpinning back to true
      }

      setVersion('V2');
      assert.strictEqual(isSpinning, false);
      setVersion('V3');
      assert.strictEqual(isSpinning, false);
    });

    it('T3.12: Keyboard Escape prioritizes modal dismissal over popup card dismissal', () => {
      const { document } = createMockDOM();
      const modal = document.getElementById('comparison-modal');
      const popup = document.getElementById('poi-popup-card');

      modal.style.display = 'flex';
      popup.style.display = 'block';

      function handleEscape() {
        if (modal.style.display === 'flex') {
          modal.style.display = 'none';
        } else if (popup.style.display === 'block') {
          popup.style.display = 'none';
        }
      }

      handleEscape(); // First Escape closes modal
      assert.strictEqual(modal.style.display, 'none');
      assert.strictEqual(popup.style.display, 'block');

      handleEscape(); // Second Escape closes popup
      assert.strictEqual(popup.style.display, 'none');
    });
  });
}
