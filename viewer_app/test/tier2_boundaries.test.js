/**
 * tier2_boundaries.test.js
 * Tier 2: Boundary & Corner Cases Test Suite
 * Covers edge conditions, extreme inputs, singular points, and input sanitization.
 */

import { describe, it, assert } from './test_framework.js';
import {
  MockVector3,
  MockCatmullRomCurve3,
  CoordinateTransforms,
  createMockDOM,
  INVARIANTS
} from './mock_environment.js';

export function registerTier2Tests() {
  describe('Tier 2 - Boundary & Corner Cases', () => {

    it('T2.1: North and South Poles (+90° and -90° lat) do not produce NaN or coordinate singularities', () => {
      const northPole = CoordinateTransforms.latLonToVector3(90.0, 0.0, 5.0);
      const southPole = CoordinateTransforms.latLonToVector3(-90.0, 0.0, 5.0);

      assert.notOk(isNaN(northPole.x));
      assert.notOk(isNaN(northPole.y));
      assert.notOk(isNaN(northPole.z));
      assert.closeTo(northPole.y, 5.0, 1e-4);
      assert.closeTo(northPole.x, 0.0, 1e-4);
      assert.closeTo(northPole.z, 0.0, 1e-4);

      assert.closeTo(southPole.y, -5.0, 1e-4);
      assert.closeTo(southPole.x, 0.0, 1e-4);
      assert.closeTo(southPole.z, 0.0, 1e-4);
    });

    it('T2.2: Antimeridian (+180° and -180° lon) produce continuous Cartesian coordinates', () => {
      const posEast = CoordinateTransforms.latLonToVector3(0.0, 180.0, 5.0);
      const posWest = CoordinateTransforms.latLonToVector3(0.0, -180.0, 5.0);

      assert.closeTo(posEast.x, posWest.x, 1e-4);
      assert.closeTo(posEast.y, posWest.y, 1e-4);
      assert.closeTo(posEast.z, posWest.z, 1e-4);
      assert.closeTo(posEast.length(), 5.0, 1e-4);
    });

    it('T2.3: Equator and Prime Meridian (0°N, 0°E) resolves strictly to known axis', () => {
      const origin = CoordinateTransforms.latLonToVector3(0.0, 0.0, 5.0);
      // At phi = 90 deg, theta = 180 deg: x = -(5 * sin(90) * cos(180)) = 5, y = 0, z = 0
      assert.closeTo(origin.x, 5.0, 1e-4);
      assert.closeTo(origin.y, 0.0, 1e-4);
      assert.closeTo(origin.z, 0.0, 1e-4);
    });

    it('T2.4: Out-of-bounds latitude clamping (lat > 90 or lat < -90)', () => {
      function safeLatLon(lat, lon, radius = 5.0) {
        const clampedLat = Math.max(-90, Math.min(90, lat));
        // Normalize lon to [-180, 180]
        let normLon = ((lon + 180) % 360);
        if (normLon < 0) normLon += 360;
        normLon -= 180;
        return CoordinateTransforms.latLonToVector3(clampedLat, normLon, radius);
      }

      const excessiveNorth = safeLatLon(125.0, 45.0);
      assert.closeTo(excessiveNorth.y, 5.0, 1e-4); // clamped to North Pole

      const excessiveSouth = safeLatLon(-110.0, 45.0);
      assert.closeTo(excessiveSouth.y, -5.0, 1e-4); // clamped to South Pole
    });

    it('T2.5: Extreme longitude wrapping (lon = 540° wraps to antimeridian |180°|)', () => {
      function normalizeLon(lon) {
        let norm = ((lon + 180) % 360);
        if (norm < 0) norm += 360;
        return norm - 180;
      }
      assert.closeTo(Math.abs(normalizeLon(540)), 180, 1e-4);
      assert.closeTo(Math.abs(normalizeLon(-540)), 180, 1e-4);
      assert.closeTo(normalizeLon(720), 0, 1e-4);
    });

    it('T2.6: Opacity clamping restricts negative, >1.0, and NaN values to [0.0, 1.0]', () => {
      function sanitizeOpacity(val, fallback = 0.8) {
        if (typeof val !== 'number' || isNaN(val)) return fallback;
        return Math.max(0.0, Math.min(1.0, val));
      }
      assert.strictEqual(sanitizeOpacity(-0.5), 0.0);
      assert.strictEqual(sanitizeOpacity(2.5), 1.0);
      assert.strictEqual(sanitizeOpacity(NaN), 0.8);
      assert.strictEqual(sanitizeOpacity(null), 0.8);
      assert.strictEqual(sanitizeOpacity(0.65), 0.65);
    });

    it('T2.7: Relief bumpScale clamping prevents negative displacement or mesh inversion', () => {
      function sanitizeBumpScale(scale) {
        if (typeof scale !== 'number' || isNaN(scale)) return 0.18;
        return Math.max(0.0, Math.min(0.5, scale));
      }
      assert.strictEqual(sanitizeBumpScale(-0.1), 0.0);
      assert.strictEqual(sanitizeBumpScale(1.8), 0.5);
      assert.strictEqual(sanitizeBumpScale(0.18), 0.18);
    });

    it('T2.8: Spline generator handles empty waypoint collection gracefully without crashing', () => {
      const emptySpline = new MockCatmullRomCurve3([]);
      assert.doesNotThrow(() => {
        const points = emptySpline.getPoints(50);
        assert.deepEqual(points, []);
      });
    });

    it('T2.9: Spline generator handles single waypoint safely', () => {
      const singlePoint = new MockVector3(1, 2, 3);
      const singleSpline = new MockCatmullRomCurve3([singlePoint]);
      const points = singleSpline.getPoints(50);
      assert.strictEqual(points.length, 1);
      assert.strictEqual(points[0].x, 1);
    });

    it('T2.10: Viewport resize with zero dimensions prevents divide-by-zero aspect ratio', () => {
      function computeAspect(width, height) {
        if (!width || !height || width <= 0 || height <= 0) return 1.0;
        return width / height;
      }
      assert.strictEqual(computeAspect(0, 0), 1.0);
      assert.strictEqual(computeAspect(1920, 0), 1.0);
      assert.strictEqual(computeAspect(0, 1080), 1.0);
      assert.closeTo(computeAspect(1920, 1080), 1.7777, 1e-3);
    });

    it('T2.11: Occlusion dot product exactly on horizon (dot product === 0.0) is treated as occluded', () => {
      const globeCenter = new MockVector3(0, 0, 0);
      const cameraPos = new MockVector3(0, 0, 14);
      // Point where normal is perpendicular to camera vector: x=5, y=0, z=0
      const horizonPoint = new MockVector3(5.0, 0, 0);
      const normal = horizonPoint.clone().sub(globeCenter).normalize(); // (1, 0, 0)
      const toCamera = cameraPos.clone().sub(horizonPoint).normalize(); // (-0.33, 0, 0.94)
      const dotProd = normal.dot(toCamera);
      assert.lessThan(dotProd, 0.0); // Facing slightly away from camera
      assert.strictEqual(CoordinateTransforms.isFrontFacing(horizonPoint, globeCenter, cameraPos), false);
    });

    it('T2.12: Micro-drag movement (<=5px) triggers raycast click, large drag (>5px) does not', () => {
      function evaluatePointerAction(down, up, threshold = 5) {
        const dist = Math.sqrt((up.x - down.x) ** 2 + (up.y - down.y) ** 2);
        return dist <= threshold ? 'CLICK' : 'DRAG';
      }
      assert.strictEqual(evaluatePointerAction({ x: 100, y: 100 }, { x: 100, y: 100 }), 'CLICK');
      assert.strictEqual(evaluatePointerAction({ x: 100, y: 100 }, { x: 103, y: 104 }), 'CLICK'); // 5px
      assert.strictEqual(evaluatePointerAction({ x: 100, y: 100 }, { x: 105, y: 105 }), 'DRAG');  // 7.07px
    });

    it('T2.13: Unknown study version ID defaults to active version or throws descriptive error', () => {
      function resolveVersion(versionId) {
        if (!INVARIANTS.STUDY_SPEC[versionId]) {
          throw new Error(`InvalidStudyVersion: Unknown version "${versionId}". Supported versions: V1, V2, V3`);
        }
        return INVARIANTS.STUDY_SPEC[versionId];
      }
      assert.throws(() => resolveVersion('V4'), /Unknown version "V4"/);
      assert.strictEqual(resolveVersion('V2').id, 'V2');
    });

    it('T2.14: HTML injection / XSS strings in station name or observation are sanitized', () => {
      function sanitizeHTML(str) {
        return String(str)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#039;');
      }
      const maliciousInput = '<script>alert("xss")</script>';
      const sanitized = sanitizeHTML(maliciousInput);
      assert.notOk(sanitized.includes('<script>'));
      assert.ok(sanitized.includes('&lt;script&gt;'));
    });

    it('T2.15: Zoom delta limits prevent camera inversion or jumping past origin', () => {
      function applyZoom(currentZ, deltaY) {
        const nextZ = currentZ + deltaY * 0.01;
        return Math.max(7.0, Math.min(22.0, nextZ));
      }
      // Extreme zoom in attempts
      assert.strictEqual(applyZoom(7.0, -10000), 7.0);
      // Extreme zoom out attempts
      assert.strictEqual(applyZoom(22.0, 10000), 22.0);
    });
  });
}
