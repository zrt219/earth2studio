import * as THREE from 'three';

let scene, camera, renderer, globe, clouds;
let isSpinning = true;
let isReliefActive = true;
let targetPosition = null;

const container = document.getElementById('canvas-container');

// Texture Loader
const textureLoader = new THREE.TextureLoader();
const t2mTex = textureLoader.load('/textures/earth_t2m.jpg');
const tendTex = textureLoader.load('/textures/earth_tendency.jpg');
const bumpTex = textureLoader.load('/textures/earth_elevation.jpg');

function init() {
  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set(0, 5, 14);

  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  container.appendChild(renderer.domElement);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
  dirLight.position.set(12, 10, 15);
  scene.add(dirLight);

  // Starfield background
  createStarfield();

  // Create 3D Earth Mesh
  const geometry = new THREE.SphereGeometry(5, 128, 128);
  const material = new THREE.MeshStandardMaterial({
    map: t2mTex,
    bumpMap: bumpTex,
    bumpScale: 0.18,
    roughness: 0.55,
    metalness: 0.1
  });

  globe = new THREE.Mesh(geometry, material);
  scene.add(globe);

  // Atmosphere Glow Shell
  const atmosGeom = new THREE.SphereGeometry(5.08, 64, 64);
  const atmosMat = new THREE.MeshBasicMaterial({
    color: 0x38bdf8,
    transparent: true,
    opacity: 0.12,
    side: THREE.BackSide
  });
  const atmos = new THREE.Mesh(atmosGeom, atmosMat);
  scene.add(atmos);

  // Event Listeners
  window.addEventListener('resize', onWindowResize);
  setupControls();
  setupPointerDrag();

  animate();
}

function createStarfield() {
  const starGeom = new THREE.BufferGeometry();
  const starCount = 1200;
  const starPositions = new Float32Array(starCount * 3);

  for (let i = 0; i < starCount * 3; i += 3) {
    starPositions[i] = (Math.random() - 0.5) * 350;
    starPositions[i + 1] = (Math.random() - 0.5) * 350;
    starPositions[i + 2] = (Math.random() - 0.5) * 350;
  }

  starGeom.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
  const starMat = new THREE.PointsMaterial({ color: 0x94a3b8, size: 0.8, transparent: true, opacity: 0.7 });
  const starField = new THREE.Points(starGeom, starMat);
  scene.add(starField);
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}

// Mouse drag rotation
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };

function setupPointerDrag() {
  window.addEventListener('mousedown', (e) => {
    if (e.target.tagName === 'BUTTON') return;
    isDragging = true;
    previousMousePosition = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging || !globe) return;
    const deltaX = e.clientX - previousMousePosition.x;
    const deltaY = e.clientY - previousMousePosition.y;

    globe.rotation.y += deltaX * 0.005;
    globe.rotation.x += deltaY * 0.005;

    previousMousePosition = { x: e.clientX, y: e.clientY };
  });

  window.addEventListener('mouseup', () => isDragging = false);

  window.addEventListener('wheel', (e) => {
    camera.position.z = Math.max(7, Math.min(22, camera.position.z + e.deltaY * 0.01));
  });
}

function setupControls() {
  const btnT2m = document.getElementById('layer-t2m');
  const btnTend = document.getElementById('layer-tend');
  const btnSpin = document.getElementById('toggle-spin');
  const btnRelief = document.getElementById('toggle-relief');
  const btnGlobal = document.getElementById('fly-global');
  const btnItaly = document.getElementById('fly-italy');
  const btnJapan = document.getElementById('fly-japan');

  const legendTitle = document.getElementById('legend-title');
  const legendBar = document.getElementById('legend-bar');
  const legendMin = document.getElementById('legend-min');
  const legendMax = document.getElementById('legend-max');

  btnT2m.addEventListener('click', () => {
    btnT2m.classList.add('active-btn');
    btnTend.classList.remove('active-btn');
    globe.material.map = t2mTex;
    globe.material.needsUpdate = true;
    legendTitle.innerText = "Surface Temperature (°C)";
    legendBar.style.background = "linear-gradient(to right, #30123b, #4686fb, #1ae4b6, #a2fc3c, #fbb41a, #e4460a, #7a0403)";
    legendMin.innerText = "-45°C";
    legendMax.innerText = "+38°C";
  });

  btnTend.addEventListener('click', () => {
    btnTend.classList.add('active-btn');
    btnT2m.classList.remove('active-btn');
    globe.material.map = tendTex;
    globe.material.needsUpdate = true;
    legendTitle.innerText = "24h Tendency ΔT (°C)";
    legendBar.style.background = "linear-gradient(to right, #3b4cc0, #8cb2f9, #f7f7f7, #f49a7b, #b40426)";
    legendMin.innerText = "-6°C";
    legendMax.innerText = "+6°C";
  });

  btnSpin.addEventListener('click', () => {
    isSpinning = !isSpinning;
    btnSpin.innerText = isSpinning ? "⏸ Pause Rotation" : "▶ Resume Rotation";
  });

  btnRelief.addEventListener('click', () => {
    isReliefActive = !isReliefActive;
    globe.material.bumpScale = isReliefActive ? 0.18 : 0.0;
    globe.material.needsUpdate = true;
    btnRelief.classList.toggle('active-btn', isReliefActive);
  });

  btnGlobal.addEventListener('click', () => flyTo(0, 0, 14));
  btnItaly.addEventListener('click', () => {
    isSpinning = false;
    btnSpin.innerText = "▶ Resume Rotation";
    // Latitude 42N, Longitude 12E
    flyToLatLon(42, 12, 8.5);
  });
  btnJapan.addEventListener('click', () => {
    isSpinning = false;
    btnSpin.innerText = "▶ Resume Rotation";
    // Latitude 36N, Longitude 138E
    flyToLatLon(36, 138, 8.5);
  });
}

function flyToLatLon(lat, lon, distance) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  // Rotate globe so region faces camera
  globe.rotation.x = lat * (Math.PI / 180) * 0.4;
  globe.rotation.y = - (lon) * (Math.PI / 180) - Math.PI / 2;
  camera.position.set(0, 1.5, distance);
}

function flyTo(x, y, z) {
  camera.position.set(x, y, z);
}

function animate() {
  requestAnimationFrame(animate);

  if (isSpinning && globe && !isDragging) {
    globe.rotation.y += 0.0018;
  }

  renderer.render(scene, camera);
}

init();
