// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
// http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * Earth-2 X-Band SAR & InSAR Mission Twin
 * 3D Scientific Layers Engine (Three.js r170)
 *
 * Module: viewer_app/layers3D.js
 * Author: Zhane Daye (SAR & Earth System Engineering | zhanedaye@umattr.ca)
 * Compliance: .agents/rules/e2s-014-scientific-integrity.mdc
 *
 * Implements:
 *   - Radial Shell Hierarchy defending against WebGL Z-fighting
 *   - Pillar 1: 3D Concentric Ensemble Spread Layer (Plasma Shader)
 *   - Pillar 2: 3D Cyclone Trajectory Spline Tube & Expanding Uncertainty Cone
 *   - Pillar 5: 3D Mesoscale Super-Resolution Insets (Alpine & Japan) with Lapse-Rate Cooling
 *   - Pillar 6: 3D Data Assimilation Station Markers (Normal-Aligned Pins & Pulsing Caps)
 *   - Interactive Raycasting, Drag-vs-Click Disambiguation & Screen-Space Projection
 */

import * as THREE from 'three';
import studyData from './studyData.js';

// =============================================================================
// 1. RADIAL SHELL HIERARCHY (DEFENDING AGAINST Z-FIGHTING)
// =============================================================================

/**
 * Radial allocation table strictly strictly enforcing monotonic shell offsets:
 * Base Globe (5.000) < Spread (5.020) < Insets (5.035) < Cone (5.045) <
 * Cyclone Tube (5.050) == DA Base (5.050) < Atmosphere (5.150) < DA Cap (5.350)
 */
export const RADIAL_SHELLS = Object.freeze({
  BASE_GLOBE: 5.000,
  ENSEMBLE_SPREAD: 5.020,
  MESOSCALE_INSETS: 5.035,
  UNCERTAINTY_CONE: 5.045,
  CYCLONE_TUBE: 5.050,
  DA_STATION_BASE: 5.050,
  DA_STATION_CAP: 5.350,
  ATMOSPHERE_GLOW: 5.150
});

// =============================================================================
// 2. GEOSPATIAL COORDINATES & PROJECTION MATHEMATICS
// =============================================================================

/**
 * Transform geographic coordinates (lat, lon, R) to Three.js Cartesian Vector3 (x, y, z).
 * Conforms to Three.js SphereGeometry UV parameterization:
 *   u = 0.00 (180° Dateline) -> x = -R, z = 0
 *   u = 0.25 (90°W Americas) -> x = 0,  z = +R
 *   u = 0.50 (0° Greenwich)  -> x = +R, z = 0
 *   u = 0.75 (90°E Indian)   -> x = 0,  z = -R
 *
 * @param {number} lat - Latitude in degrees [-90, +90]
 * @param {number} lon - Longitude in degrees [0, 360] or [-180, +180]
 * @param {number} radius - Radial shell distance
 * @returns {THREE.Vector3}
 */
export function latLonToVector3(lat, lon, radius = RADIAL_SHELLS.BASE_GLOBE) {
  const numLat = Number.isFinite(Number(lat)) ? Number(lat) : 0.0;
  const clampedLat = Math.max(-90.0, Math.min(90.0, numLat));
  const numLon = Number.isFinite(Number(lon)) ? Number(lon) : 0.0;
  const phi = (clampedLat * Math.PI) / 180.0;
  const lambda = ((((numLon % 360) + 360) % 360) * Math.PI) / 180.0;
  const r = (Number.isFinite(Number(radius)) && Number(radius) > 0) ? Number(radius) : RADIAL_SHELLS.BASE_GLOBE;
  return new THREE.Vector3(
    r * Math.cos(phi) * Math.cos(lambda),
    r * Math.sin(phi),
    -r * Math.cos(phi) * Math.sin(lambda)
  );
}

/**
 * Compatibility alias returning plain object { x, y, z }
 */
export function latLonToCartesian(lat, lon, radius = RADIAL_SHELLS.BASE_GLOBE) {
  const v = latLonToVector3(lat, lon, radius);
  return { x: v.x, y: v.y, z: v.z };
}

/**
 * Compute exact boresight Euler angles to orient geographic target directly facing camera.
 * Conforms to Three.js SphereGeometry UV parameterization and Euler rotation order 'XYZ':
 *   rotY = -lonRad - PI/2
 *   rotX = latRad
 *
 * Rotating the globe by Euler(rotX, rotY, 0, 'XYZ') transforms the spherical surface
 * point at (lat, lon) to (0, 0, +R), orienting it dead-center along the camera boresight
 * with zero offsets and zero artificial damping.
 *
 * @param {number} lat - Latitude in degrees [-90, +90]
 * @param {number} lon - Longitude in degrees [-180, +180] or [0, 360]
 * @returns {{ rotX: number, rotY: number }}
 */
export function boresightRotation(lat, lon) {
  const numLat = Number.isFinite(Number(lat)) ? Number(lat) : 0.0;
  const clampedLat = Math.max(-90.0, Math.min(90.0, numLat));
  const numLon = Number.isFinite(Number(lon)) ? Number(lon) : 0.0;
  const latRad = clampedLat * (Math.PI / 180.0);
  const lonRad = numLon * (Math.PI / 180.0);
  return {
    rotX: latRad,
    rotY: -lonRad - Math.PI / 2.0
  };
}

/**
 * Global camera target focus point, centered at globe origin.
 */
export const cameraTarget = new THREE.Vector3(0, 0, 0);

/**
 * Smoothly pan camera along its viewing plane without geographic distortion.
 *
 * @param {number} deltaX - Horizontal screen delta
 * @param {number} deltaY - Vertical screen delta
 * @param {THREE.Camera} [camera=activeCamera] - Camera instance
 * @param {THREE.Vector3} [target=cameraTarget] - Camera target
 * @returns {THREE.Vector3} Updated target vector
 */
export function panCamera(deltaX, deltaY, camera = activeCamera, target = cameraTarget) {
  if (!camera || !target) return target;
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  if (camera.matrixWorld && typeof camera.matrixWorld.extractBasis === 'function') {
    camera.matrixWorld.extractBasis(right, up, new THREE.Vector3());
  } else {
    right.set(1, 0, 0);
    up.set(0, 1, 0);
  }

  const dist = camera.position ? camera.position.distanceTo(target) : 14.0;
  const factor = Math.max(0.002, dist * 0.0012);

  const moveX = right.multiplyScalar(-deltaX * factor);
  const moveY = up.multiplyScalar(deltaY * factor);

  if (camera.position) camera.position.add(moveX).add(moveY);
  target.add(moveX).add(moveY);
  return target;
}

/**
 * Configure globe rotation and camera focus to center precisely on (lat, lon) at camera boresight.
 *
 * @param {number} lat - Latitude in degrees
 * @param {number} lon - Longitude in degrees
 * @param {number} [distance=8.5] - Radial distance from origin
 * @param {THREE.Object3D} [globe=activeGlobe] - Globe mesh or group
 * @param {THREE.Camera} [camera=activeCamera] - Camera instance
 * @param {THREE.Vector3} [target=cameraTarget] - Camera focus target
 * @returns {{ rotX: number, rotY: number, cameraPos: {x: number, y: number, z: number}, cameraTarget: THREE.Vector3 }}
 */
export function flyToLatLon(lat, lon, distance = 8.5, globe = activeGlobe, camera = activeCamera, target = cameraTarget) {
  const { rotX, rotY } = boresightRotation(lat, lon);
  if (globe && globe.rotation) {
    globe.rotation.set(rotX, rotY, 0);
    if (typeof globe.updateMatrixWorld === 'function') {
      globe.updateMatrixWorld(true);
    }
  }
  if (target) {
    target.set(0, 0, 0);
  }
  if (camera && camera.position) {
    camera.position.set(0, 0, distance);
    if (typeof camera.lookAt === 'function' && target) {
      camera.lookAt(target.x, target.y, target.z);
    }
    if (typeof camera.updateMatrixWorld === 'function') {
      camera.updateMatrixWorld(true);
    }
  }
  return {
    rotX,
    rotY,
    cameraPos: { x: 0, y: 0, z: distance },
    cameraTarget: target
  };
}

/**
 * Front-hemisphere occlusion test rejecting rear-facing markers occluded by Earth.
 * Evaluates dot product of outward surface normal and camera vector: n_hat . (cam - pt) > 0.
 * Exactly on horizon (dot === 0.0) is treated as occluded.
 *
 * @param {THREE.Vector3} pointOnSphere - 3D marker position
 * @param {THREE.Vector3} globeCenter - Globe center position
 * @param {THREE.Vector3} cameraPos - Camera world position
 * @returns {boolean}
 */
export function isFrontFacing(pointOnSphere, globeCenter = new THREE.Vector3(0, 0, 0), cameraPos = new THREE.Vector3(0, 5, 14)) {
  if (!pointOnSphere || !cameraPos) return false;
  const normal = new THREE.Vector3().subVectors(pointOnSphere, globeCenter).normalize();
  const toCamera = new THREE.Vector3().subVectors(cameraPos, pointOnSphere).normalize();
  return normal.dot(toCamera) > 0.0;
}

/**
 * Project 3D world position to 2D screen viewport coordinates.
 *
 * @param {THREE.Vector3} vector3 - 3D world coordinate
 * @param {THREE.Camera} camera - Perspective camera
 * @param {number} screenWidth - Viewport width in pixels
 * @param {number} screenHeight - Viewport height in pixels
 * @returns {{ x: number, y: number, visible: boolean }}
 */
export function projectToScreen(vector3, camera, screenWidth = 1920, screenHeight = 1080) {
  if (!vector3 || !camera) return { x: 0, y: 0, visible: false };

  // Native Three.js vector projection if available and camera is a valid Three.js camera
  if (typeof vector3.project === 'function' && camera.isCamera && camera.projectionMatrix) {
    if (typeof camera.updateMatrixWorld === 'function') {
      camera.updateMatrixWorld();
    }
    const v = vector3.clone().project(camera);
    const visible = v.z < 1.0 && isFrontFacing(vector3, new THREE.Vector3(0, 0, 0), camera.position);
    return {
      x: Math.round((v.x * 0.5 + 0.5) * screenWidth),
      y: Math.round((-(v.y * 0.5) + 0.5) * screenHeight),
      visible
    };
  }

  // Fallback pinhole approximation (compatible with mock environments and simple camera stubs)
  const camPos = camera.position || new THREE.Vector3(0, 0, 14);
  const depth = Math.max(0.1, camPos.z - vector3.z);
  const fovFactor = (screenHeight / 2.0) / Math.tan(((camera.fov || 45) * Math.PI) / 360.0);
  const x = (vector3.x / depth) * fovFactor + screenWidth / 2.0;
  const y = -(vector3.y / depth) * fovFactor + screenHeight / 2.0;
  const visible = vector3.z <= camPos.z && isFrontFacing(vector3, new THREE.Vector3(0, 0, 0), camPos);
  return {
    x: Math.round(x),
    y: Math.round(y),
    visible
  };
}

// =============================================================================
// 3. SCIENTIFIC COLORMAPS & METRIC CONVERSIONS
// =============================================================================

/**
 * Compute MSLP intensity colormap:
 * 930 hPa = 1.0 (Super Typhoon: Magenta / Crimson #e11d48)
 * 1000 hPa = 0.0 (Tropical Storm / Weak: Cyan #06b6d4)
 *
 * @param {number} mslp - Central pressure in hPa
 * @returns {{ color: THREE.Color, intensity: number }}
 */
export function getMslpColor(mslp) {
  const norm = Math.max(0.0, Math.min(1.0, (mslp - 930.0) / (1000.0 - 930.0)));
  const intensity = 1.0 - norm;

  const color = new THREE.Color();
  if (intensity > 0.66) {
    const t = (intensity - 0.66) / 0.34;
    color.setRGB(0.85 + 0.12 * t, 0.15 - 0.05 * t, 0.25 + 0.35 * t);
  } else if (intensity > 0.33) {
    const t = (intensity - 0.33) / 0.33;
    color.setRGB(0.95 * t + 0.1 * (1.0 - t), 0.55 * t + 0.7 * (1.0 - t), 0.1 * t + 0.8 * (1.0 - t));
  } else {
    const t = intensity / 0.33;
    color.setRGB(0.04 + 0.06 * t, 0.70 + 0.10 * t, 0.85 + 0.10 * t);
  }

  return { color, intensity };
}

/**
 * Compute Data Assimilation Increment Colormap:
 * +3.0 K = 0.0 (Sky-Blue #0ea5e9)
 * +8.0 K = 1.0 (Deep Crimson / Rose #f43f5e)
 *
 * @param {number} inc - Analysis increment in K
 * @returns {{ color: THREE.Color, norm: number }}
 */
export function getIncrementColor(inc) {
  const norm = Math.max(0.0, Math.min(1.0, (inc - 3.0) / (8.0 - 3.0)));
  const color = new THREE.Color().lerpColors(
    new THREE.Color(0x0ea5e9),
    new THREE.Color(0xf43f5e),
    norm
  );
  return { color, norm };
}

/**
 * Standard orographic lapse-rate cooling formula (Gamma = 6.5 K/km = 0.0065 K/m).
 *
 * @param {number} elevationMeters - Elevation in meters
 * @param {number} lapseRateKPerKm - Lapse rate in K/km (default: 6.5)
 * @returns {number} deltaT in K
 */
export function getOrographicLapseRateDeltaT(elevationMeters, lapseRateKPerKm = 6.5) {
  const lapseRatePerM = -lapseRateKPerKm / 1000.0;
  return elevationMeters * lapseRatePerM;
}

// =============================================================================
// 4. CURVILINEAR SPHERICAL MESH GENERATORS
// =============================================================================

/**
 * Generate a true curvilinear spherical quad surface mesh conforming to globe curvature.
 * Prevents geometric clipping and polygon intersection with the globe.
 *
 * @param {number} minLat - Southern boundary in degrees
 * @param {number} maxLat - Northern boundary in degrees
 * @param {number} minLon - Western boundary in degrees
 * @param {number} maxLon - Eastern boundary in degrees
 * @param {number} radius - Spherical shell radius
 * @param {number} segments - Grid subdivisions along each axis
 * @returns {THREE.BufferGeometry}
 */
export function createSphericalPatchGeometry(minLat, maxLat, minLon, maxLon, radius = RADIAL_SHELLS.MESOSCALE_INSETS, segments = 32) {
  const geom = new THREE.BufferGeometry();
  const segs = Math.max(1, Math.floor(segments));
  const cols = segs + 1;
  const vertCount = cols * cols;
  const positions = new Float32Array(vertCount * 3);
  const normals = new Float32Array(vertCount * 3);
  const uvs = new Float32Array(vertCount * 2);
  const indexCount = segs * segs * 6;
  const indices = vertCount > 65535 ? new Uint32Array(indexCount) : new Uint16Array(indexCount);

  const r = (Number.isFinite(Number(radius)) && Number(radius) > 0) ? Number(radius) : RADIAL_SHELLS.BASE_GLOBE;
  const invR = 1.0 / r;
  const degToRad = Math.PI / 180.0;

  let vOffset = 0;
  let uvOffset = 0;
  for (let i = 0; i <= segs; i++) {
    const v = i / segs;
    const lat = Math.max(-90.0, Math.min(90.0, maxLat - v * (maxLat - minLat)));
    const phi = lat * degToRad;
    const cosPhi = Math.cos(phi);
    const sinPhi = Math.sin(phi);
    const py = r * sinPhi;

    for (let j = 0; j <= segs; j++) {
      const u = j / segs;
      const lon = minLon + u * (maxLon - minLon);
      const lambda = ((((lon % 360) + 360) % 360) * degToRad);
      const px = r * cosPhi * Math.cos(lambda);
      const pz = -r * cosPhi * Math.sin(lambda);

      positions[vOffset] = px;
      positions[vOffset + 1] = py;
      positions[vOffset + 2] = pz;

      normals[vOffset] = px * invR;
      normals[vOffset + 1] = py * invR;
      normals[vOffset + 2] = pz * invR;

      uvs[uvOffset] = u;
      uvs[uvOffset + 1] = 1.0 - v;

      vOffset += 3;
      uvOffset += 2;
    }
  }

  let idxOffset = 0;
  for (let i = 0; i < segs; i++) {
    for (let j = 0; j < segs; j++) {
      const a = i * cols + j;
      const b = (i + 1) * cols + j;
      const c = (i + 1) * cols + (j + 1);
      const d = i * cols + (j + 1);
      indices[idxOffset++] = a;
      indices[idxOffset++] = b;
      indices[idxOffset++] = d;
      indices[idxOffset++] = b;
      indices[idxOffset++] = c;
      indices[idxOffset++] = d;
    }
  }

  geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geom.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
  geom.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geom.setIndex(new THREE.BufferAttribute(indices, 1));
  return geom;
}

/**
 * Traces a glowing boundary wireframe along the spherical quad perimeter.
 */
function createPerimeterWireframe(minLat, maxLat, minLon, maxLon, radius = RADIAL_SHELLS.MESOSCALE_INSETS, color = 0x38bdf8) {
  const sub = 16;
  const pts = [];

  // North edge: (maxLat, minLon) -> (maxLat, maxLon)
  for (let i = 0; i <= sub; i++) {
    const lon = minLon + (i / sub) * (maxLon - minLon);
    pts.push(latLonToVector3(maxLat, lon, radius + 0.002));
  }
  // East edge: (maxLat, maxLon) -> (minLat, maxLon)
  for (let i = 1; i <= sub; i++) {
    const lat = maxLat - (i / sub) * (maxLat - minLat);
    pts.push(latLonToVector3(lat, maxLon, radius + 0.002));
  }
  // South edge: (minLat, maxLon) -> (minLat, minLon)
  for (let i = 1; i <= sub; i++) {
    const lon = maxLon - (i / sub) * (maxLon - minLon);
    pts.push(latLonToVector3(minLat, lon, radius + 0.002));
  }
  // West edge: (minLat, minLon) -> (maxLat, minLon)
  for (let i = 1; i <= sub; i++) {
    const lat = minLat + (i / sub) * (maxLat - minLat);
    pts.push(latLonToVector3(lat, minLon, radius + 0.002));
  }

  const lineGeom = new THREE.BufferGeometry().setFromPoints(pts);
  const lineMat = new THREE.LineBasicMaterial({
    color: color,
    linewidth: 2,
    transparent: true,
    opacity: 0.95
  });
  return new THREE.Line(lineGeom, lineMat);
}

// =============================================================================
// 5. LAYER BUILDERS: CYCLONE, DA STATIONS, ENSEMBLES & MESOSCALE
// =============================================================================

/**
 * Pillar 2: Cyclone Trajectory Spline Tube & Expanding Uncertainty Cone
 */
function createCycloneTrajectoryLayer(waypoints) {
  const group = new THREE.Group();
  group.name = 'cyclone_trajectory_layer';
  const beaconMeshes = [];

  if (!waypoints || waypoints.length === 0) {
    return { group, beaconMeshes };
  }

  // 1. Waypoint Positions
  const points = waypoints.map(wp => latLonToVector3(wp.lat, wp.lon, RADIAL_SHELLS.CYCLONE_TUBE));

  // 2. Smooth 3D Spline Curve
  let curve;
  if (points.length >= 2) {
    curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.5);
  } else {
    // Single point edge case
    curve = new THREE.CatmullRomCurve3([points[0], points[0].clone().add(new THREE.Vector3(0.001, 0, 0))]);
  }

  // 3. Spline Tube Geometry
  const tubularSegments = 64;
  const radialSegments = 8;
  const tubeGeom = new THREE.TubeGeometry(curve, tubularSegments, 0.025, radialSegments, false);

  // Intensity Colormapping along Tube Vertices
  const vertexCount = tubeGeom.attributes.position.count;
  const colors = new Float32Array(vertexCount * 3);

  for (let i = 0; i < vertexCount; i++) {
    const segIdx = Math.floor(i / (radialSegments + 1));
    const t = Math.min(1.0, segIdx / tubularSegments);
    const wpFrac = t * (waypoints.length - 1);
    const idx = Math.min(Math.floor(wpFrac), waypoints.length - 2);
    const frac = wpFrac - idx;
    const mslp0 = waypoints[idx]?.mslp ?? 964.5;
    const mslp1 = waypoints[idx + 1]?.mslp ?? 981.0;
    const currentMslp = mslp0 + frac * (mslp1 - mslp0);

    const { color } = getMslpColor(currentMslp);
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }

  tubeGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const tubeMat = new THREE.MeshStandardMaterial({
    vertexColors: true,
    roughness: 0.35,
    metalness: 0.2,
    side: THREE.DoubleSide
  });

  const tubeMesh = new THREE.Mesh(tubeGeom, tubeMat);
  tubeMesh.name = 'cyclone_tube_mesh';
  group.add(tubeMesh);

  // 4. Expanding Uncertainty Envelope Cone (R=5.045)
  if (points.length >= 2) {
    const coneGeom = new THREE.BufferGeometry();
    const conePositions = [];
    const coneUvs = [];
    const coneIndices = [];
    const divisions = 40;
    const rCone = RADIAL_SHELLS.UNCERTAINTY_CONE; // 5.045
    const earthRadiusKm = 6371.0;
    const kmToRad = 1.0 / earthRadiusKm;

    for (let i = 0; i <= divisions; i++) {
      const t = i / divisions;
      const pt = curve.getPointAt(t);
      const tangent = curve.getTangentAt(t).normalize();
      const normal = pt.clone().normalize();
      const binormal = new THREE.Vector3().crossVectors(tangent, normal).normalize();

      // Interpolate uncertainty spread: 45 km to 200 km
      const wpFrac = t * (waypoints.length - 1);
      const idx = Math.min(Math.floor(wpFrac), waypoints.length - 2);
      const frac = wpFrac - idx;
      const rKm0 = waypoints[idx]?.coneRadiusKm ?? (45 + idx * 38.75);
      const rKm1 = waypoints[idx + 1]?.coneRadiusKm ?? (45 + (idx + 1) * 38.75);
      const coneRadiusKm = rKm0 + frac * (rKm1 - rKm0);

      const halfWidth3D = rCone * Math.sin(coneRadiusKm * kmToRad);

      const left = pt.clone().add(binormal.clone().multiplyScalar(halfWidth3D)).normalize().multiplyScalar(rCone);
      const right = pt.clone().sub(binormal.clone().multiplyScalar(halfWidth3D)).normalize().multiplyScalar(rCone);

      conePositions.push(left.x, left.y, left.z);
      conePositions.push(right.x, right.y, right.z);

      coneUvs.push(0, t);
      coneUvs.push(1, t);
    }

    for (let i = 0; i < divisions; i++) {
      const a = i * 2;
      const b = i * 2 + 1;
      const c = (i + 1) * 2;
      const d = (i + 1) * 2 + 1;
      coneIndices.push(a, b, d);
      coneIndices.push(a, d, c);
    }

    coneGeom.setAttribute('position', new THREE.Float32BufferAttribute(conePositions, 3));
    coneGeom.setAttribute('uv', new THREE.Float32BufferAttribute(coneUvs, 2));
    coneGeom.setIndex(coneIndices);
    coneGeom.computeVertexNormals();

    const coneMat = new THREE.MeshBasicMaterial({
      color: 0xef4444,
      transparent: true,
      opacity: 0.22,
      side: THREE.DoubleSide,
      depthWrite: false
    });

    const coneMesh = new THREE.Mesh(coneGeom, coneMat);
    coneMesh.name = 'cyclone_uncertainty_cone';
    group.add(coneMesh);
  }

  // 5. Waypoint Beacons & Surface Rings
  waypoints.forEach((wp, index) => {
    const pos = latLonToVector3(wp.lat, wp.lon, RADIAL_SHELLS.CYCLONE_TUBE);
    const normal = pos.clone().normalize();
    const { color } = getMslpColor(wp.mslp);

    // Beacon Sphere
    const sphereGeom = new THREE.SphereGeometry(0.065, 16, 16);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0.85,
      roughness: 0.25,
      metalness: 0.1
    });
    const sphereMesh = new THREE.Mesh(sphereGeom, sphereMat);
    sphereMesh.position.copy(pos);
    sphereMesh.name = `waypoint_${wp.id || index}`;
    sphereMesh.userData = {
      type: 'cyclone_waypoint',
      data: wp,
      index,
      normal: normal.clone(),
      baseColor: color
    };
    group.add(sphereMesh);
    beaconMeshes.push(sphereMesh);

    // Surface Ring
    const ringGeom = new THREE.RingGeometry(0.04, 0.085, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.55,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    const ringMesh = new THREE.Mesh(ringGeom, ringMat);
    ringMesh.position.copy(pos);
    ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    group.add(ringMesh);
  });

  return { group, beaconMeshes, curve };
}

/**
 * Pillar 6: Data Assimilation Station Markers (Normal-Aligned Pins & Pulsing Caps)
 */
function createDAStationsLayer(stations) {
  const group = new THREE.Group();
  group.name = 'da_stations_layer';
  const capMeshes = [];

  const rBase = RADIAL_SHELLS.DA_STATION_BASE; // 5.050
  const rCap = RADIAL_SHELLS.DA_STATION_CAP;   // 5.350
  const pinHeight = rCap - rBase;             // 0.300

  if (!stations || stations.length === 0) {
    return { group, capMeshes };
  }

  stations.forEach((st, idx) => {
    const normal = latLonToVector3(st.lat, st.lon, 1.0).normalize();
    const { color } = getIncrementColor(st.increment);

    // 1. Vertical cylinder pin
    const cylGeom = new THREE.CylinderGeometry(0.015, 0.035, pinHeight, 16);
    cylGeom.translate(0, pinHeight / 2.0, 0); // Pin base at 0, top at pinHeight
    const cylMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x0284c7,
      emissiveIntensity: 0.35,
      roughness: 0.4,
      metalness: 0.3
    });
    const cylMesh = new THREE.Mesh(cylGeom, cylMat);
    cylMesh.position.copy(normal.clone().multiplyScalar(rBase));
    cylMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), normal);
    cylMesh.name = `station_pin_${st.id}`;
    group.add(cylMesh);

    // 2. Glowing pulsating cap sphere at R=5.350
    const capPos = normal.clone().multiplyScalar(rCap);
    const capGeom = new THREE.SphereGeometry(0.065, 16, 16);
    const capMat = new THREE.MeshStandardMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0.90,
      roughness: 0.2,
      metalness: 0.1
    });
    const capMesh = new THREE.Mesh(capGeom, capMat);
    capMesh.position.copy(capPos);
    capMesh.name = `station_cap_${st.id}`;
    capMesh.userData = {
      type: 'da_station',
      data: st,
      index: idx,
      normal: normal.clone(),
      worldPos: capPos.clone(),
      baseColor: color
    };
    group.add(capMesh);
    capMeshes.push(capMesh);

    // 3. Ground innovation influence ring at station base (~120 km)
    const ringGeom = new THREE.RingGeometry(0.12, 0.155, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
      depthWrite: false
    });
    const ringMesh = new THREE.Mesh(ringGeom, ringMat);
    ringMesh.position.copy(normal.clone().multiplyScalar(rBase + 0.001));
    ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), normal);
    group.add(ringMesh);
  });

  return { group, capMeshes };
}

/**
 * Pillar 1: Concentric Ensemble Spread Layer (Plasma Colormap Shader)
 */
function createEnsembleSpreadLayer() {
  const geom = new THREE.SphereGeometry(RADIAL_SHELLS.ENSEMBLE_SPREAD, 64, 64);

  const vertexShader = `
    varying vec2 vUv;
    varying vec3 vNormal;
    void main() {
      vUv = uv;
      vNormal = normalize(normalMatrix * normal);
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `;

  const fragmentShader = `
    varying vec2 vUv;
    varying vec3 vNormal;

    uniform float uOpacity;
    uniform float u_opacity;
    uniform float uSpreadMin;
    uniform float uSpreadMax;
    uniform float uTime;

    vec3 plasmaColormap(float t) {
      vec3 c0 = vec3(0.050383, 0.029803, 0.527975);
      vec3 c1 = vec3(0.493975, 0.010260, 0.657512);
      vec3 c2 = vec3(0.793740, 0.280456, 0.468752);
      vec3 c3 = vec3(0.973305, 0.584305, 0.254125);
      vec3 c4 = vec3(0.940015, 0.975155, 0.131326);
      if (t < 0.25) return mix(c0, c1, t * 4.0);
      if (t < 0.50) return mix(c1, c2, (t - 0.25) * 4.0);
      if (t < 0.75) return mix(c2, c3, (t - 0.50) * 4.0);
      return mix(c3, c4, (t - 0.75) * 4.0);
    }

    float computeSpread(vec2 uv) {
      float lat = (uv.y - 0.5) * 3.14159265;
      float lon = uv.x * 6.2831853;
      
      float latBelt = exp(-pow((abs(lat) - 0.75) / 0.35, 2.0)) * 0.45;
      float dAlps = length(vec2(lat - 0.785, lon - 0.174));
      float alpsHotspot = exp(-pow(dAlps / 0.20, 2.0)) * 0.75;
      float dWpac = length(vec2(lat - 0.436, lon - 2.356));
      float wpacHotspot = exp(-pow(dWpac / 0.35, 2.0)) * 0.65;
      float waves = 0.15 * sin(lon * 4.0 + lat * 3.0 + uTime * 0.2) +
                    0.08 * cos(lon * 7.0 - lat * 5.0 - uTime * 0.15) +
                    0.04 * sin(lon * 13.0 + lat * 9.0);
      return clamp(0.20 + latBelt + alpsHotspot + wpacHotspot + waves, 0.05, 1.45);
    }

    void main() {
      float opacity = max(uOpacity, u_opacity);
      if (opacity <= 0.001) {
        discard;
      }
      float rawSpread = computeSpread(vUv);
      float norm = clamp((rawSpread - uSpreadMin) / (uSpreadMax - uSpreadMin), 0.0, 1.0);
      vec3 color = plasmaColormap(norm);
      float alpha = smoothstep(0.08, 0.45, norm) * opacity * 0.85;
      gl_FragColor = vec4(color, alpha);
    }
  `;

  const mat = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms: {
      uOpacity: { value: 0.8 },
      u_opacity: { value: 0.8 },
      uSpreadMin: { value: 0.0 },
      uSpreadMax: { value: 1.5 },
      uTime: { value: 0.0 }
    },
    transparent: true,
    depthWrite: false,
    side: THREE.FrontSide
  });

  const mesh = new THREE.Mesh(geom, mat);
  mesh.name = 'ensemble_spread_layer';
  return mesh;
}

/**
 * Pillar 5: Mesoscale Super-Resolution Insets (Alpine 8x & Japan 4x)
 */
function createMesoscaleInsetsLayer(domains) {
  const group = new THREE.Group();
  group.name = 'mesoscale_insets_layer';

  if (!domains || domains.length === 0) {
    return group;
  }

  domains.forEach(dom => {
    const [minLat, maxLat, minLon, maxLon] = dom.bounds;

    // 1. Curvilinear surface quad mesh
    const patchGeom = createSphericalPatchGeometry(minLat, maxLat, minLon, maxLon, RADIAL_SHELLS.MESOSCALE_INSETS, 32);

    let patchMat;
    if (dom.id === 'alps_superres' || dom.id === 'MESO_ALPINE') {
      // Alpine orographic lapse-rate cooling shader
      const vertexShader = `
        varying vec2 vUv;
        varying vec3 vNormal;
        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `;
      const fragmentShader = `
        varying vec2 vUv;
        varying vec3 vNormal;

        float getElevation(vec2 uv) {
          float peak1 = exp(-pow(length(uv - vec2(0.35, 0.55)) / 0.12, 2.0)) * 4808.0;
          float peak2 = exp(-pow(length(uv - vec2(0.60, 0.65)) / 0.15, 2.0)) * 4478.0;
          float peak3 = exp(-pow(length(uv - vec2(0.75, 0.45)) / 0.18, 2.0)) * 4049.0;
          float ridges = 1200.0 * abs(sin(uv.x * 24.0 + uv.y * 18.0) * cos(uv.x * 12.0 - uv.y * 30.0));
          return clamp(600.0 + peak1 + peak2 + peak3 + ridges, 200.0, 4808.0);
        }

        void main() {
          float elev = getElevation(vUv);
          float deltaT = elev * (-0.0065); // -31.25 K at peak
          float t = clamp((elev - 400.0) / (4800.0 - 400.0), 0.0, 1.0);
          vec3 cValley = vec3(0.06, 0.35, 0.28);
          vec3 cRidge  = vec3(0.12, 0.65, 0.75);
          vec3 cPeak   = vec3(0.85, 0.95, 1.00);
          vec3 color = t < 0.5 ? mix(cValley, cRidge, t * 2.0) : mix(cRidge, cPeak, (t - 0.5) * 2.0);

          float edgeDist = min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y));
          if (edgeDist < 0.02) {
            color = mix(color, vec3(0.22, 0.74, 0.97), (0.02 - edgeDist) / 0.02);
          }
          gl_FragColor = vec4(color, 0.90);
        }
      `;
      patchMat = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide
      });
    } else {
      // General synoptic domain shader
      const vertexShader = `
        varying vec2 vUv;
        varying vec3 vNormal;
        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `;
      const fragmentShader = `
        varying vec2 vUv;
        varying vec3 vNormal;
        void main() {
          float edgeDist = min(min(vUv.x, 1.0 - vUv.x), min(vUv.y, 1.0 - vUv.y));
          vec3 base = vec3(0.15, 0.45, 0.65);
          if (edgeDist < 0.02) {
            base = mix(base, vec3(0.96, 0.62, 0.07), (0.02 - edgeDist) / 0.02);
          }
          gl_FragColor = vec4(base, 0.85);
        }
      `;
      patchMat = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide
      });
    }

    const patchMesh = new THREE.Mesh(patchGeom, patchMat);
    patchMesh.name = `mesoscale_patch_${dom.id}`;
    patchMesh.userData = { type: 'mesoscale_domain', data: dom };
    group.add(patchMesh);

    // 2. Glowing Neon Cyan Boundary Wireframe
    const wireframe = createPerimeterWireframe(
      minLat,
      maxLat,
      minLon,
      maxLon,
      RADIAL_SHELLS.MESOSCALE_INSETS,
      dom.id === 'alps_superres' ? 0x00f0ff : 0xf59e0b
    );
    group.add(wireframe);
  });

  return group;
}

// =============================================================================
// 6. ENGINE STATE, EVENT BUS & INTERACTIVE RAYCASTING
// =============================================================================

let activeGlobe = null;
let activeCamera = null;
let activeRenderer = null;
let spreadOpacity = 0.8;

const layerGroups = {
  cyclone: null,
  da: null,
  spread: null,
  mesoscale: null
};

const layerState = {
  cyclone: true,
  da_stations: true,
  ensemble_spread: true,
  mesoscale_insets: true
};

const pickableObjects = [];
const cycloneBeaconMeshes = [];
const daCapMeshes = [];
const raycaster = new THREE.Raycaster();
let pointerDownPos = null;
let pointerDownTarget = null;
let pointerDownHandler = null;
let studyDataUnsubscribers = [];
let highlightedWaypointIndex = -1;

function isObjectVisibleInHierarchy(obj) {
  let cur = obj;
  while (cur) {
    if (cur.visible === false) {
      return false;
    }
    if (cur === activeGlobe) {
      break;
    }
    cur = cur.parent;
  }
  return true;
}

/**
 * Initialize 3D Scientific Layers Engine.
 * Adds all layer groups as synchronized children of the globe mesh.
 *
 * @param {THREE.Object3D} globe - Central Earth sphere or globe group
 * @param {THREE.Camera} camera - Main perspective camera
 * @param {THREE.WebGLRenderer} renderer - WebGL renderer instance
 * @returns {object} Layer instances and collection handles
 */
export function initLayers(globe, camera, renderer) {
  // Dispose existing layers if reinitializing
  disposeLayers();

  activeGlobe = globe;
  activeCamera = camera;
  activeRenderer = renderer;

  // 1. Fetch Authoritative Datasets
  const waypoints = studyData.getCycloneWaypoints ? studyData.getCycloneWaypoints() : [];
  const stations = studyData.getDAStations ? studyData.getDAStations() : [];
  const domains = studyData.getMesoscaleDomains ? studyData.getMesoscaleDomains() : [];

  // 2. Build Layer Groups
  const cycloneResult = createCycloneTrajectoryLayer(waypoints);
  layerGroups.cyclone = cycloneResult.group;
  cycloneBeaconMeshes.push(...cycloneResult.beaconMeshes);
  pickableObjects.push(...cycloneResult.beaconMeshes);

  const daResult = createDAStationsLayer(stations);
  layerGroups.da = daResult.group;
  daCapMeshes.push(...daResult.capMeshes);
  pickableObjects.push(...daResult.capMeshes);

  layerGroups.spread = createEnsembleSpreadLayer();
  layerGroups.mesoscale = createMesoscaleInsetsLayer(domains);

  // 3. Attach all layer groups as children of the globe
  if (globe && typeof globe.add === 'function') {
    globe.add(layerGroups.cyclone);
    globe.add(layerGroups.da);
    globe.add(layerGroups.spread);
    globe.add(layerGroups.mesoscale);
  }

  // 4. Bind DOM Pointer Listeners for Drag-vs-Click Disambiguation
  if (renderer && renderer.domElement && typeof renderer.domElement.addEventListener === 'function') {
    pointerDownTarget = renderer.domElement;
    pointerDownHandler = (e) => {
      const cx = typeof e.clientX === 'number' ? e.clientX : (e.x || 0);
      const cy = typeof e.clientY === 'number' ? e.clientY : (e.y || 0);
      pointerDownPos = { x: cx, y: cy };
    };
    pointerDownTarget.addEventListener('pointerdown', pointerDownHandler);
  }

  // 5. Connect reactive listener to studyData event bus
  if (studyData && typeof studyData.on === 'function') {
    const unsubLayerToggled = studyData.on('layer-toggled', ({ layerId, visible }) => {
      setLayerVisibility(layerId, visible);
    });
    if (typeof unsubLayerToggled === 'function') studyDataUnsubscribers.push(unsubLayerToggled);

    const unsubSpreadOpacity = studyData.on('spread-opacity-changed', ({ opacity }) => {
      setEnsembleSpreadOpacity(opacity);
    });
    if (typeof unsubSpreadOpacity === 'function') studyDataUnsubscribers.push(unsubSpreadOpacity);

    const unsubVersionChanged = studyData.on('study-version-changed', ({ versionId, activeLayers }) => {
      if (activeLayers) {
        Object.entries(activeLayers).forEach(([layerId, visible]) => {
          setLayerVisibility(layerId, visible);
        });
      }
    });
    if (typeof unsubVersionChanged === 'function') studyDataUnsubscribers.push(unsubVersionChanged);

    const unsubTimestep = studyData.on('timestep-changed', (payload) => {
      const step = payload && typeof payload.step === 'number' ? payload.step : null;
      highlightCycloneWaypoint(step);
    });
    if (typeof unsubTimestep === 'function') studyDataUnsubscribers.push(unsubTimestep);
  }

  return {
    cycloneGroup: layerGroups.cyclone,
    daGroup: layerGroups.da,
    spreadMesh: layerGroups.spread,
    mesoGroup: layerGroups.mesoscale,
    pickableObjects,
    raycaster
  };
}

/**
 * Control layer visibility.
 *
 * @param {string} layerId - 'cyclone', 'da_stations', 'ensemble_spread', 'mesoscale_insets'
 * @param {boolean} visible
 */
export function setLayerVisibility(layerId, visible) {
  const normId = String(layerId).toLowerCase().trim();
  const boolVal = Boolean(visible);

  switch (normId) {
    case 'cyclone':
    case 'cyclone_trajectory':
      if (layerGroups.cyclone) layerGroups.cyclone.visible = boolVal;
      layerState.cyclone = boolVal;
      break;
    case 'da_stations':
    case 'da':
      if (layerGroups.da) layerGroups.da.visible = boolVal;
      layerState.da_stations = boolVal;
      break;
    case 'ensemble_spread':
    case 'spread':
      if (layerGroups.spread) layerGroups.spread.visible = boolVal && (spreadOpacity > 0.001);
      layerState.ensemble_spread = boolVal;
      break;
    case 'mesoscale_insets':
    case 'mesoscale':
      if (layerGroups.mesoscale) layerGroups.mesoscale.visible = boolVal;
      layerState.mesoscale_insets = boolVal;
      break;
    default:
      layerState[normId] = boolVal;
      break;
  }
}

/**
 * Control opacity of the Ensemble Spread shader layer.
 *
 * @param {number} value - Opacity scalar [0.0, 1.0]
 */
export function setEnsembleSpreadOpacity(value) {
  const num = Number(value);
  const clamped = Math.max(0.0, Math.min(1.0, isNaN(num) ? 0.0 : num));
  spreadOpacity = clamped;

  if (layerGroups.spread) {
    const mat = layerGroups.spread.material;
    if (mat && mat.uniforms) {
      if (mat.uniforms.uOpacity) mat.uniforms.uOpacity.value = clamped;
      if (mat.uniforms.u_opacity) mat.uniforms.u_opacity.value = clamped;
    }
    layerGroups.spread.visible = Boolean(layerState.ensemble_spread) && (clamped > 0.001);
  }
}

/**
 * Perform raycasting on interactive POIs (station caps, storm waypoints).
 * Enforces drag-vs-click suppression (>5px) and front-hemisphere occlusion filtering.
 *
 * @param {MouseEvent|PointerEvent|object} event
 * @param {THREE.Camera} camera
 * @param {number|object|null} width
 * @param {number|object|null} height
 * @param {object} [options={}]
 * @returns {object|null} Hit payload or null
 */
export function handleRaycast(event, camera = activeCamera, width = null, height = null, options = {}) {
  if (!event || !camera) return null;
  const targetCamera = camera;

  let resolvedWidth = width;
  let resolvedHeight = height;
  let resolvedOptions = options && typeof options === 'object' ? options : {};
  if (width !== null && typeof width === 'object') {
    resolvedOptions = width;
    resolvedWidth = null;
    resolvedHeight = null;
  } else if (height !== null && typeof height === 'object') {
    resolvedOptions = height;
    resolvedHeight = null;
  }

  const { visibleOnly = false, skipDragCheck = false } = resolvedOptions;

  if (resolvedWidth !== null && (typeof resolvedWidth !== 'number' || resolvedWidth <= 0 || !Number.isFinite(resolvedWidth))) return null;
  if (resolvedHeight !== null && (typeof resolvedHeight !== 'number' || resolvedHeight <= 0 || !Number.isFinite(resolvedHeight))) return null;

  const rawW = resolvedWidth || (activeRenderer?.domElement?.clientWidth || (typeof window !== 'undefined' ? window.innerWidth : 1920));
  const rawH = resolvedHeight || (activeRenderer?.domElement?.clientHeight || (typeof window !== 'undefined' ? window.innerHeight : 1080));
  const w = (rawW && rawW > 0) ? rawW : 1920;
  const h = (rawH && rawH > 0) ? rawH : 1080;

  const clientX = typeof event.clientX === 'number' ? event.clientX : (typeof event.x === 'number' ? event.x : NaN);
  const clientY = typeof event.clientY === 'number' ? event.clientY : (typeof event.y === 'number' ? event.y : NaN);
  if (!Number.isFinite(clientX) || !Number.isFinite(clientY)) return null;
  if (Math.abs(clientX) > 1e6 || Math.abs(clientY) > 1e6) return null;

  // Drag-vs-click suppression: reject clicks with movement > 5px
  if (pointerDownPos && !skipDragCheck) {
    const dist = Math.hypot(clientX - pointerDownPos.x, clientY - pointerDownPos.y);
    if (dist > 5) {
      return null;
    }
  }

  const targets = visibleOnly ? pickableObjects.filter(isObjectVisibleInHierarchy) : pickableObjects;
  if (targets.length === 0) return null;

  const ndc = new THREE.Vector2(
    (clientX / w) * 2 - 1,
    -(clientY / h) * 2 + 1
  );

  raycaster.setFromCamera(ndc, targetCamera);
  const intersects = raycaster.intersectObjects(targets, true);

  if (intersects.length === 0) return null;

  for (const hit of intersects) {
    const hitPoint = hit.point;
    const globeCenter = activeGlobe?.position || new THREE.Vector3(0, 0, 0);
    const camPos = targetCamera.position || new THREE.Vector3(0, 5, 14);

    // Verify visibility along parent layer hierarchy up to activeGlobe (BUG-M2-001)
    if (!isObjectVisibleInHierarchy(hit.object)) {
      continue;
    }

    // Front-hemisphere occlusion test
    if (!isFrontFacing(hitPoint, globeCenter, camPos)) {
      continue;
    }

    // Identify user data
    let obj = hit.object;
    while (obj && !obj.userData?.type && obj.parent && obj !== activeGlobe) {
      obj = obj.parent;
    }

    if (obj && obj.userData?.type) {
      const screenPos = projectToScreen(hitPoint, targetCamera, w, h);
      return {
        type: obj.userData.type,
        data: obj.userData.data,
        object: obj,
        point: hitPoint,
        screenPos
      };
    }
  }

  return null;
}

/**
 * Public click handler alias satisfying interface contract.
 */
export function onGlobeClick(mouseEvent, camera = activeCamera, width = null, height = null, options = {}) {
  return handleRaycast(mouseEvent, camera, width, height, options);
}

/**
 * Highlight an active cyclone waypoint sphere corresponding to the 24h Storm Lead-Time step.
 * Pass negative or null/undefined to clear the active highlight gracefully.
 *
 * @param {number|null|undefined} stepIndex - Waypoint index (0..4) or null/-1 to clear
 */
export function highlightCycloneWaypoint(stepIndex) {
  if (
    stepIndex === null ||
    stepIndex === undefined ||
    typeof stepIndex !== 'number' ||
    !Number.isFinite(stepIndex) ||
    stepIndex < 0
  ) {
    highlightedWaypointIndex = -1;
  } else {
    const idx = Math.floor(stepIndex);
    highlightedWaypointIndex = idx < cycloneBeaconMeshes.length ? idx : -1;
  }

  for (let idx = 0; idx < cycloneBeaconMeshes.length; idx++) {
    const mesh = cycloneBeaconMeshes[idx];
    if (!mesh) continue;
    const isActive = idx === highlightedWaypointIndex;
    const hasHighlight = highlightedWaypointIndex >= 0;
    const targetScale = isActive ? 1.65 : (hasHighlight ? 0.9 : 1.0);
    const targetEmissive = isActive ? 1.6 : (hasHighlight ? 0.55 : 0.85);
    if (mesh.scale) {
      mesh.scale.set(targetScale, targetScale, targetScale);
    }
    if (mesh.material && typeof mesh.material.emissiveIntensity === 'number') {
      mesh.material.emissiveIntensity = targetEmissive;
    }
  }
}

/**
 * Per-frame animation update driving beacon pulsing and shader time uniform.
 * Skips updates on hidden layer groups.
 *
 * @param {number} time - Elapsed time in seconds
 * @param {THREE.Camera} camera - Active camera
 */
export function updateLayers(time, camera = activeCamera) {
  const t = typeof time === 'number' ? time : (Date.now() * 0.001);

  // 1. Pulsing waypoint beacon nodes (skip if hidden)
  if (layerGroups.cyclone && layerGroups.cyclone.visible !== false && cycloneBeaconMeshes.length > 0) {
    for (let idx = 0; idx < cycloneBeaconMeshes.length; idx++) {
      const mesh = cycloneBeaconMeshes[idx];
      if (!mesh || !mesh.scale) continue;
      if (idx === highlightedWaypointIndex) {
        const s = 1.6 + 0.2 * Math.sin(t * 5.0);
        mesh.scale.set(s, s, s);
        if (mesh.material && typeof mesh.material.emissiveIntensity === 'number') {
          mesh.material.emissiveIntensity = 1.5 + 0.3 * Math.sin(t * 5.0);
        }
      } else if (highlightedWaypointIndex >= 0) {
        const s = 0.9 + 0.1 * Math.sin(t * 4.0 + idx * 0.8);
        mesh.scale.set(s, s, s);
        if (mesh.material && typeof mesh.material.emissiveIntensity === 'number') {
          mesh.material.emissiveIntensity = 0.55;
        }
      } else {
        const s = 1.0 + 0.25 * Math.sin(t * 4.0 + idx * 0.8);
        mesh.scale.set(s, s, s);
      }
    }
  }

  // 2. Pulsing DA station beacon caps (skip if hidden)
  if (layerGroups.da && layerGroups.da.visible !== false && daCapMeshes.length > 0) {
    for (let idx = 0; idx < daCapMeshes.length; idx++) {
      const mesh = daCapMeshes[idx];
      if (!mesh || !mesh.scale) continue;
      const s = 1.0 + 0.18 * Math.sin(t * 3.5 + idx * 1.2);
      mesh.scale.set(s, s, s);
      if (mesh.material && typeof mesh.material.emissiveIntensity === 'number') {
        mesh.material.emissiveIntensity = 0.75 + 0.35 * Math.sin(t * 3.5 + idx * 1.2);
      }
    }
  }

  // 3. Update ensemble spread time uniform (skip if hidden)
  if (layerGroups.spread && layerGroups.spread.visible !== false && layerGroups.spread.material?.uniforms?.uTime) {
    layerGroups.spread.material.uniforms.uTime.value = t;
  }
}

/**
 * Returns pickable 3D marker objects for raycasting.
 * @param {object} [options={}]
 * @param {boolean} [options.visibleOnly=false]
 * @returns {Array<THREE.Object3D>}
 */
export function getInteractiveObjects(options = {}) {
  if (options && options.visibleOnly) {
    return pickableObjects.filter(isObjectVisibleInHierarchy);
  }
  return pickableObjects;
}

/**
 * Returns read-only layer state snapshot.
 * @returns {object}
 */
export function getLayerState() {
  return {
    activeLayers: { ...layerState },
    spreadOpacity,
    cycloneWaypointsCount: cycloneBeaconMeshes.length,
    daStationsCount: daCapMeshes.length
  };
}

/**
 * Returns references to current Three.js layer groups.
 * @returns {object}
 */
export function getLayers() {
  return { ...layerGroups };
}

/**
 * Cleanup and dispose of geometries, materials, and listeners.
 */
export function disposeLayers() {
  Object.values(layerGroups).forEach(group => {
    if (!group) return;
    if (activeGlobe && typeof activeGlobe.remove === 'function') {
      activeGlobe.remove(group);
    }
    if (typeof group.traverse === 'function') {
      group.traverse(child => {
        if (child.geometry && typeof child.geometry.dispose === 'function') {
          child.geometry.dispose();
        }
        if (child.material) {
          if (Array.isArray(child.material)) {
            child.material.forEach(m => m && typeof m.dispose === 'function' && m.dispose());
          } else if (typeof child.material.dispose === 'function') {
            child.material.dispose();
          }
        }
      });
    }
  });

  layerGroups.cyclone = null;
  layerGroups.da = null;
  layerGroups.spread = null;
  layerGroups.mesoscale = null;

  pickableObjects.length = 0;
  cycloneBeaconMeshes.length = 0;
  daCapMeshes.length = 0;

  // Unsubscribe studyData listeners (BUG-M2-003)
  studyDataUnsubscribers.forEach(unsub => {
    try {
      if (typeof unsub === 'function') {
        unsub();
      }
    } catch {
      // Ignore errors during unsubscription
    }
  });
  studyDataUnsubscribers = [];

  // Remove DOM pointerdown listener (BUG-M2-003)
  if (pointerDownTarget && pointerDownHandler && typeof pointerDownTarget.removeEventListener === 'function') {
    try {
      pointerDownTarget.removeEventListener('pointerdown', pointerDownHandler);
    } catch {
      // Ignore errors during removal
    }
    pointerDownTarget = null;
    pointerDownHandler = null;
  }

  pointerDownPos = null;
  highlightedWaypointIndex = -1;
  activeGlobe = null;
  activeCamera = null;
  activeRenderer = null;
}

// =============================================================================
// 7. DEFAULT CONSOLIDATED EXPORT
// =============================================================================

export default {
  RADIAL_SHELLS,
  latLonToVector3,
  latLonToCartesian,
  boresightRotation,
  cameraTarget,
  panCamera,
  flyToLatLon,
  isFrontFacing,
  projectToScreen,
  getMslpColor,
  getIncrementColor,
  getOrographicLapseRateDeltaT,
  createSphericalPatchGeometry,
  initLayers,
  setLayerVisibility,
  setEnsembleSpreadOpacity,
  highlightCycloneWaypoint,
  handleRaycast,
  onGlobeClick,
  updateLayers,
  getInteractiveObjects,
  getLayerState,
  getLayers,
  disposeLayers
};
