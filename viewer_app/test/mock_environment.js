/**
 * mock_environment.js
 * Virtual DOM, Three.js headless math, and specification reference oracles
 * for OD-EARTH2-001 / EO-OBSCURA 3D WebGL Digital Twin E2E Testing.
 */

// 1. DOM Virtualization
class MockClassList {
  constructor(element) {
    this.classes = new Set();
    this.element = element;
  }
  add(...names) {
    names.forEach(n => this.classes.add(n));
  }
  remove(...names) {
    names.forEach(n => this.classes.delete(n));
  }
  toggle(name, force) {
    if (force !== undefined) {
      if (force) this.classes.add(name);
      else this.classes.delete(name);
      return force;
    }
    if (this.classes.has(name)) {
      this.classes.delete(name);
      return false;
    }
    this.classes.add(name);
    return true;
  }
  contains(name) {
    return this.classes.has(name);
  }
  toString() {
    return Array.from(this.classes).join(' ');
  }
}

class MockElement {
  constructor(tagName, id = '') {
    this.tagName = tagName.toUpperCase();
    this.id = id;
    this.classList = new MockClassList(this);
    this.style = {};
    this.children = [];
    this.parentNode = null;
    this._innerText = '';
    this._innerHTML = '';
    this.listeners = new Map();
    this.value = '';
    this.disabled = false;
    this.attributes = new Map();
  }

  get innerText() {
    return this._innerText;
  }
  set innerText(val) {
    this._innerText = String(val);
  }

  get innerHTML() {
    return this._innerHTML;
  }
  set innerHTML(val) {
    this._innerHTML = String(val);
  }

  setAttribute(k, v) {
    this.attributes.set(k, String(v));
  }
  getAttribute(k) {
    return this.attributes.get(k) || null;
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    const idx = this.children.indexOf(child);
    if (idx !== -1) {
      this.children.splice(idx, 1);
      child.parentNode = null;
    }
    return child;
  }

  addEventListener(type, cb) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type).push(cb);
  }

  removeEventListener(type, cb) {
    if (this.listeners.has(type)) {
      const list = this.listeners.get(type).filter(fn => fn !== cb);
      this.listeners.set(type, list);
    }
  }

  dispatchEvent(event) {
    if (!event.target) event.target = this;
    if (this.listeners.has(event.type)) {
      this.listeners.get(event.type).forEach(cb => cb(event));
    }
    return true;
  }

  click() {
    this.dispatchEvent({ type: 'click', target: this, clientX: 100, clientY: 100 });
  }

  querySelector(selector) {
    if (selector.startsWith('#')) {
      const targetId = selector.slice(1);
      if (this.id === targetId) return this;
      for (const child of this.children) {
        const found = child.querySelector(selector);
        if (found) return found;
      }
    }
    return null;
  }

  querySelectorAll(selector) {
    const results = [];
    if (selector.startsWith('.')) {
      const className = selector.slice(1);
      if (this.classList.contains(className)) results.push(this);
      for (const child of this.children) {
        results.push(...child.querySelectorAll(selector));
      }
    }
    return results;
  }
}

export function createMockDOM() {
  const elements = new Map();

  function register(id, tag = 'div') {
    const el = new MockElement(tag, id);
    elements.set(id, el);
    return el;
  }

  // Base canvas container
  register('canvas-container');

  // Baseline HUD controls
  register('layer-t2m', 'button');
  register('layer-tend', 'button');
  register('fly-global', 'button');
  register('fly-italy', 'button');
  register('fly-japan', 'button');
  register('toggle-spin', 'button');
  register('toggle-relief', 'button');
  register('legend-title');
  register('legend-bar');
  register('legend-min');
  register('legend-max');

  // M1-M3 Upgrades
  register('timeline-slider', 'input');
  register('tab-v1', 'button');
  register('tab-v2', 'button');
  register('tab-v3', 'button');

  register('layer-cyclone', 'button');
  register('layer-da', 'button');
  register('layer-spread', 'button');
  register('layer-mesoscale', 'button');
  register('spread-opacity-slider', 'input');

  register('comparison-modal');
  register('modal-close', 'button');
  register('comparison-grid');
  register('open-comparison', 'button');

  register('poi-popup-card');
  register('popup-title');
  register('popup-body');
  register('popup-close', 'button');

  const doc = {
    getElementById(id) {
      if (!elements.has(id)) {
        return register(id);
      }
      return elements.get(id);
    },
    createElement(tag) {
      return new MockElement(tag);
    },
    querySelector(sel) {
      if (sel.startsWith('#')) return this.getElementById(sel.slice(1));
      return null;
    },
    elements
  };

  const win = {
    innerWidth: 1920,
    innerHeight: 1080,
    devicePixelRatio: 2,
    listeners: new Map(),
    addEventListener(type, cb) {
      if (!this.listeners.has(type)) this.listeners.set(type, []);
      this.listeners.get(type).push(cb);
    },
    removeEventListener(type, cb) {
      if (this.listeners.has(type)) {
        this.listeners.set(type, this.listeners.get(type).filter(f => f !== cb));
      }
    },
    dispatchEvent(event) {
      if (this.listeners.has(event.type)) {
        this.listeners.get(event.type).forEach(cb => cb(event));
      }
    }
  };

  return { document: doc, window: win };
}

// 2. Three.js Virtual Math & Coordinate Transform Simulation
export class MockVector3 {
  constructor(x = 0, y = 0, z = 0) {
    this.x = x;
    this.y = y;
    this.z = z;
  }
  set(x, y, z) {
    this.x = x;
    this.y = y;
    this.z = z;
    return this;
  }
  clone() {
    return new MockVector3(this.x, this.y, this.z);
  }
  copy(v) {
    this.x = v.x;
    this.y = v.y;
    this.z = v.z;
    return this;
  }
  add(v) {
    this.x += v.x;
    this.y += v.y;
    this.z += v.z;
    return this;
  }
  sub(v) {
    this.x -= v.x;
    this.y -= v.y;
    this.z -= v.z;
    return this;
  }
  multiplyScalar(s) {
    this.x *= s;
    this.y *= s;
    this.z *= s;
    return this;
  }
  dot(v) {
    return this.x * v.x + this.y * v.y + this.z * v.z;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
  }
  normalize() {
    const l = this.length();
    if (l > 1e-6) this.multiplyScalar(1 / l);
    return this;
  }
  distanceTo(v) {
    const dx = this.x - v.x;
    const dy = this.y - v.y;
    const dz = this.z - v.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
}

export class MockCatmullRomCurve3 {
  constructor(points = []) {
    this.points = points;
  }
  getPoints(divisions = 50) {
    const result = [];
    if (this.points.length === 0) return result;
    if (this.points.length === 1) return [this.points[0].clone()];

    for (let i = 0; i <= divisions; i++) {
      const t = i / divisions;
      result.push(this.getPointAt(t));
    }
    return result;
  }
  getPointAt(t) {
    if (this.points.length === 0) return new MockVector3();
    const p = Math.max(0, Math.min(1, t)) * (this.points.length - 1);
    const idx = Math.floor(p);
    const frac = p - idx;
    const p0 = this.points[idx];
    const p1 = this.points[Math.min(idx + 1, this.points.length - 1)];

    return new MockVector3(
      p0.x + (p1.x - p0.x) * frac,
      p0.y + (p1.y - p0.y) * frac,
      p0.z + (p1.z - p0.z) * frac
    );
  }
}

export class MockObject3D {
  constructor() {
    this.position = new MockVector3();
    this.rotation = { x: 0, y: 0, z: 0 };
    this.scale = new MockVector3(1, 1, 1);
    this.visible = true;
    this.children = [];
    this.parent = null;
    this.userData = {};
  }
  add(child) {
    child.parent = this;
    this.children.push(child);
    return this;
  }
  remove(child) {
    const idx = this.children.indexOf(child);
    if (idx !== -1) {
      this.children.splice(idx, 1);
      child.parent = null;
    }
    return this;
  }
  traverse(cb) {
    cb(this);
    this.children.forEach(c => c.traverse(cb));
  }
}

export class MockMesh extends MockObject3D {
  constructor(geometry = {}, material = {}) {
    super();
    this.geometry = geometry;
    this.material = material;
  }
}

// 3. Mathematical Transforms (Conforming strictly to PROJECT.md)
export const CoordinateTransforms = {
  /**
   * Convert latitude and longitude to 3D Cartesian coordinates on sphere of given radius.
   * Conforming to PROJECT.md and main.js:
   * phi = (90 - lat) * (PI / 180)
   * theta = (lon + 180) * (PI / 180)
   * x = -(radius * sin(phi) * cos(theta))
   * z = radius * sin(phi) * sin(theta)
   * y = radius * cos(phi)
   */
  latLonToVector3(lat, lon, radius = 5.0) {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);
    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const z = radius * Math.sin(phi) * Math.sin(theta);
    const y = radius * Math.cos(phi);
    return new MockVector3(x, y, z);
  },

  /**
   * Compute boresight rotation angles to orient target (lat, lon) directly facing camera.
   * From PROJECT.md § Feature 8:
   * rotY = PI/2 - lon_rad
   * rotX = lat_rad * 0.4
   */
  boresightRotation(lat, lon) {
    const latRad = lat * (Math.PI / 180);
    const lonRad = lon * (Math.PI / 180);
    return {
      rotX: latRad * 0.4,
      rotY: -(lonRad) - Math.PI / 2
    };
  },

  /**
   * Screen-space 2D projection simulation from 3D world coordinate
   */
  projectToScreen(vector3, camera, screenWidth = 1920, screenHeight = 1080) {
    // Basic pinhole projection approximation
    const depth = Math.max(0.1, camera.position.z - vector3.z);
    const fovFactor = (screenHeight / 2) / Math.tan((camera.fov || 45) * Math.PI / 360);
    const x = (vector3.x / depth) * fovFactor + screenWidth / 2;
    const y = -(vector3.y / depth) * fovFactor + screenHeight / 2;
    return { x: Math.round(x), y: Math.round(y), visible: vector3.z <= camera.position.z };
  },

  /**
   * Front-hemisphere occlusion test (dot product with camera ray)
   */
  isFrontFacing(pointOnSphere, globeCenter = new MockVector3(0, 0, 0), cameraPos = new MockVector3(0, 5, 14)) {
    const normal = pointOnSphere.clone().sub(globeCenter).normalize();
    const toCamera = cameraPos.clone().sub(pointOnSphere).normalize();
    return normal.dot(toCamera) > 0;
  }
};

// 4. Invariant Constants & Schemas (Defending against Z-Fighting & Leakage)
export const INVARIANTS = {
  // Radial hierarchy: Base < Spread < Mesoscale < Uncertainty < Cyclone < DA Beacon Caps
  RADIAL_SHELLS: {
    BASE_GLOBE: 5.000,
    ENSEMBLE_SPREAD: 5.020,
    MESOSCALE_INSETS: 5.035,
    UNCERTAINTY_CONE: 5.045,
    CYCLONE_TUBE: 5.050,
    DA_STATION_BASE: 5.050,
    DA_STATION_CAP: 5.350,
    ATMOSPHERE_GLOW: 5.150
  },

  // Authoritative Study Data Specification
  STUDY_SPEC: {
    V1: {
      id: 'V1',
      name: 'Quarantined Synthetic Leakage Audit',
      classification: 'SYNTHETIC_DIAGNOSTIC_QUARANTINED',
      leakageFormula: 'y_hat = x0 + 0.72*delta + epsilon',
      leakageFraction: 0.72,
      cycleLengthDays: 7,
      metrics: {
        rmse: 0.747,
        mae: 0.582,
        tac: 0.892,
        acc: 0.941
      },
      quarantined: true,
      integrityWarning: 'Target leakage detected: look-ahead future truth contaminates prediction'
    },
    V2: {
      id: 'V2',
      name: 'Decoupled 3-Stage Persistence Baseline',
      classification: 'REAL_MODEL_FORECAST_BASELINE',
      pipelineStages: ['Forecast', 'Freeze', 'Verify'],
      dataSource: 'NOAA GFS 0.25 deg Analysis',
      metrics: {
        rmse: 2.129,
        mae: 1.037,
        meanBias: 0.184,
        tac: 0.0,
        acc: null
      },
      hardwareBlocker: {
        declared: true,
        gpu: 'AMD GPU',
        limitation: 'PyTorch 2.4 lack of upstream ROCm support for Earth2Studio neural models'
      },
      manifestHashLength: 64,
      sealed: true
    },
    V3: {
      id: 'V3',
      name: 'The 7 Advanced Capability Pillars',
      classification: 'ADVANCED_MULTICAPABILITY_SUITE',
      pillars: [
        { id: 'P1', name: 'Massive Ensembles N=25', spreadUnits: 'K', meanSpread: 0.4273, maxSpread: 1.182 },
        { id: 'P2', name: 'Cyclone Trajectory Tracking', basin: 'WPAC', typhoonWaypoints: 5 },
        { id: 'P3', name: 'Multi-Source Data Ingestion', sources: ['NOAA GFS', 'ECMWF ERA5', 'JMA MSM', 'Himawari-9'] },
        { id: 'P4', name: 'Prognostic Benchmark', models: ['FourCastNet', 'SFNO', 'DLWP', 'ClimaX'] },
        { id: 'P5', name: 'Mesoscale Super-Resolution', domain: 'European Alps', scaleFactor: 8 },
        { id: 'P6', name: 'Data Assimilation Increments', domain: 'Italy', soundingStations: 4 },
        { id: 'P7', name: '3D Spherical Digital Twin', engine: 'Three.js WebGL', url: 'https://viewerapp.vercel.app' }
      ],
      cycloneWaypoints: [
        { id: 'WP1', time: '2024-09-01T00:00Z', lat: 14.5, lon: 132.0, mslp: 998, windKt: 45, status: 'Tropical Storm' },
        { id: 'WP2', time: '2024-09-02T00:00Z', lat: 17.2, lon: 129.4, mslp: 980, windKt: 65, status: 'Typhoon Cat 1' },
        { id: 'WP3', time: '2024-09-03T00:00Z', lat: 20.8, lon: 126.8, mslp: 955, windKt: 95, status: 'Typhoon Cat 3' },
        { id: 'WP4', time: '2024-09-04T00:00Z', lat: 24.5, lon: 124.5, mslp: 935, windKt: 115, status: 'Super Typhoon' },
        { id: 'WP5', time: '2024-09-05T00:00Z', lat: 28.0, lon: 123.0, mslp: 960, windKt: 85, status: 'Weakening Typhoon' }
      ],
      daStations: [
        { id: 'DA_MIL', name: 'Milan (LIML)', lat: 45.45, lon: 9.28, elevM: 107, bgVal: 288.4, obsVal: 293.6, increment: 5.2, qc: 'PASS' },
        { id: 'DA_ROM', name: 'Rome (LIRF)', lat: 41.80, lon: 12.24, elevM: 4, bgVal: 291.1, obsVal: 297.8, increment: 6.7, qc: 'PASS' },
        { id: 'DA_FLO', name: 'Florence (LIRQ)', lat: 43.81, lon: 11.20, elevM: 44, bgVal: 289.7, obsVal: 293.9, increment: 4.2, qc: 'PASS' },
        { id: 'DA_NAP', name: 'Naples (LIRN)', lat: 40.88, lon: 14.29, elevM: 90, bgVal: 292.0, obsVal: 299.5, increment: 7.5, qc: 'PASS' }
      ],
      mesoscaleDomain: {
        id: 'MESO_ALPINE',
        name: 'Alpine High-Resolution Domain',
        bounds: [44.0, 48.0, 6.0, 14.0], // minLat, maxLat, minLon, maxLon
        resolutionKm: 3.125,
        scaleFactor: 8
      }
    }
  }
};
