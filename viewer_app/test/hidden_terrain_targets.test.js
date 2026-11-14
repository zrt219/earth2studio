// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

/**
 * hidden_terrain_targets.test.js
 * Verification test suite for 10 Synoptic Theaters target coordinates integration:
 * Baseline Italy & Japan (13), Mexico (5), Northern Russia (6), South Africa (6),
 * Southern Italy (6), Finland (6), Japan Abandoned Farmland (6), Brazil (6), and Vancouver (6).
 */

import assert from 'assert';
import * as THREE from 'three';
import fs from 'fs';
import path from 'path';
import studyData, {
  TARGET_CITIES,
  MEXICO_TARGET_CITIES,
  RUSSIA_TARGET_CITIES,
  SOUTH_AFRICA_TARGET_CITIES,
  SOUTHERN_ITALY_TARGET_CITIES,
  FINLAND_TARGET_CITIES,
  JAPAN_FARMLAND_TARGET_CITIES,
  BRAZIL_TARGET_CITIES,
  VANCOUVER_TARGET_CITIES,
  PHASE3_TARGET_CITIES,
  HIDDEN_TERRAIN_TARGET_CITIES,
  ALL_TARGET_CITIES,
  HIDDEN_TERRAIN_SAR_CONSTELLATIONS,
  PHASE3_SAR_CONSTELLATIONS,
  ALL_SAR_CONSTELLATIONS,
  getTargetCities,
  getAllTargetCities,
  getHiddenTerrainTargetCities,
  getTargetCityById,
  getSarTaskingMetadata,
  generateStacTaskingOrderGeoJSON,
  validateStudyData
} from '../studyData.js';
import citySelector, { CITY_SHELL_RADIUS } from '../citySelector.js';
import sarTasking from '../sarTasking.js';
import layers3D from '../layers3D.js';

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
console.log('10 THEATERS TARGET COORDINATES INTEGRATION & 3D TWIN TEST SUITE');
console.log('===============================================================================');

// Suite 1: StudyData Schema & Invariants
console.log('\n--- Suite 1: studyData.js 10 Theaters Catalog Invariants ---');

runTest('1.1 Baseline TARGET_CITIES strictly preserved with 13 Italy & Japan cities', () => {
  assert.equal(TARGET_CITIES.length, 13);
  assert.ok(Object.isFrozen(TARGET_CITIES));
  const it = getTargetCities('Italy');
  const jp = getTargetCities('Japan');
  assert.equal(it.length, 7);
  assert.equal(jp.length, 6);
  assert.equal(getTargetCities('Italy', { includeHiddenTerrain: true }).length, 13);
  assert.equal(getTargetCities('Japan', { includeHiddenTerrain: true }).length, 12);
  assert.equal(getTargetCities().length, 13);
});

runTest('1.2 MEXICO_TARGET_CITIES contains 5 frozen high-relief volcanic & canyon targets', () => {
  assert.equal(MEXICO_TARGET_CITIES.length, 5);
  assert.ok(Object.isFrozen(MEXICO_TARGET_CITIES));
  const expectedIds = ['mx_copper_canyon', 'mx_orizaba', 'mx_popocatepetl', 'mx_culiacan_valley', 'mx_colima_volcano'];
  expectedIds.forEach((id) => {
    const city = MEXICO_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Mexico target ${id}`);
    assert.equal(city.country, 'Mexico');
    assert.equal(city.countryCode, 'MX');
    assert.ok(city.lat >= 14 && city.lat <= 33, `Mexico lat out of range for ${id}`);
    assert.ok(city.lon >= -118 && city.lon <= -86, `Mexico lon out of range for ${id}`);
    assert.ok(city.elevM > 0, `Missing elevation for ${id}`);
  });
});

runTest('1.3 RUSSIA_TARGET_CITIES contains 6 frozen sub-zero basalt & permafrost targets', () => {
  assert.equal(RUSSIA_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(RUSSIA_TARGET_CITIES));
  const expectedIds = [
    'ru_putorana_kamen',
    'ru_norilsk_traps',
    'ru_verkhoyansk_pole',
    'ru_batagay_megaslump',
    'ru_yakutsk_lena_jam',
    'ru_pokrovsk_choke'
  ];
  expectedIds.forEach((id) => {
    const city = RUSSIA_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Russia target ${id}`);
    assert.equal(city.country, 'Russia');
    assert.equal(city.countryCode, 'RU');
    assert.ok(city.lat >= 60 && city.lat <= 75, `Russia lat out of range for ${id}`);
    assert.ok(city.lon >= 80 && city.lon <= 150, `Russia lon out of range for ${id}`);
    assert.ok(city.elevM > 0, `Missing elevation for ${id}`);
  });
});

runTest('1.4 SOUTH_AFRICA_TARGET_CITIES contains 6 frozen Drakensberg & Cape Fold targets', () => {
  assert.equal(SOUTH_AFRICA_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(SOUTH_AFRICA_TARGET_CITIES));
  const expectedIds = [
    'za_thabana_ntlenyana',
    'za_mont_aux_sources',
    'za_durban',
    'za_tugela_mouth',
    'za_swartberg_pass',
    'za_cape_town'
  ];
  expectedIds.forEach((id) => {
    const city = SOUTH_AFRICA_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Southern Africa target ${id}`);
    assert.ok(city.country === 'South Africa' || city.country === 'Lesotho');
    assert.ok(city.countryCode === 'ZA' || city.countryCode === 'LS');
    assert.ok(city.lat >= -35.5 && city.lat <= -26.0, `Southern Africa lat out of range for ${id}`);
    assert.ok(city.lon >= 18.0 && city.lon <= 33.0, `Southern Africa lon out of range for ${id}`);
    assert.ok(city.elevM > 0, `Missing elevation for ${id}`);
  });
});

runTest('1.5a SOUTHERN_ITALY_TARGET_CITIES contains 6 frozen volcanotectonic targets', () => {
  assert.equal(SOUTHERN_ITALY_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(SOUTHERN_ITALY_TARGET_CITIES));
  const expectedIds = ['it_mount_etna', 'it_campi_flegrei', 'it_aspromonte_sila', 'it_apulia_karst', 'it_catania_simeto', 'it_vesuvius'];
  expectedIds.forEach((id) => {
    const city = SOUTHERN_ITALY_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Southern Italy target ${id}`);
    assert.equal(city.country, 'Italy');
    assert.ok(city.lat >= 36.5 && city.lat <= 42.0);
    assert.ok(city.lon >= 13.5 && city.lon <= 19.0);
  });
});

runTest('1.5b FINLAND_TARGET_CITIES contains 6 frozen post-glacial rebound & lake ice targets', () => {
  assert.equal(FINLAND_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(FINLAND_TARGET_CITIES));
  const expectedIds = ['fi_kvarken_vaasa', 'fi_saimaa_lake', 'fi_paijanne_lake', 'fi_siikaneva_peatland', 'fi_martimoaapa_mire', 'fi_halti_lapland'];
  expectedIds.forEach((id) => {
    const city = FINLAND_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Finland target ${id}`);
    assert.equal(city.country, 'Finland');
    assert.ok(city.lat >= 60.0 && city.lat <= 70.5);
    assert.ok(city.lon >= 20.0 && city.lon <= 32.0);
  });
});

runTest('1.5c JAPAN_FARMLAND_TARGET_CITIES contains 6 frozen terraced paddy satoyama targets', () => {
  assert.equal(JAPAN_FARMLAND_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(JAPAN_FARMLAND_TARGET_CITIES));
  const expectedIds = ['jp_yamakoshi_tanada', 'jp_hoshitoge_tanada', 'jp_obasute_tanada', 'jp_iya_valley_terrace', 'jp_kamikatsu_terrace', 'jp_shiroyone_senmaida'];
  expectedIds.forEach((id) => {
    const city = JAPAN_FARMLAND_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Japan Farmland target ${id}`);
    assert.equal(city.country, 'Japan');
    assert.ok(city.lat >= 33.0 && city.lat <= 38.5);
    assert.ok(city.lon >= 133.0 && city.lon <= 140.0);
  });
});

runTest('1.5d BRAZIL_TARGET_CITIES contains 6 frozen Serra do Mar & Pantanal targets', () => {
  assert.equal(BRAZIL_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(BRAZIL_TARGET_CITIES));
  const expectedIds = ['br_sao_sebastiao', 'br_petropolis', 'br_corumba_pantanal', 'br_cuiaba_pantanal', 'br_sinop_arc', 'br_alta_floresta_frontier'];
  expectedIds.forEach((id) => {
    const city = BRAZIL_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Brazil target ${id}`);
    assert.equal(city.country, 'Brazil');
    assert.ok(city.lat >= -26.0 && city.lat <= -8.0);
    assert.ok(city.lon >= -60.0 && city.lon <= -41.0);
  });
});

runTest('1.5e VANCOUVER_TARGET_CITIES contains 6 frozen Fraser delta & Coast Mountain targets', () => {
  assert.equal(VANCOUVER_TARGET_CITIES.length, 6);
  assert.ok(Object.isFrozen(VANCOUVER_TARGET_CITIES));
  const expectedIds = ['van_roberts_bank', 'van_richmond_lulu', 'van_garibaldi_summit', 'van_howe_sound', 'van_yvr_airport', 'van_sumas_prairie'];
  expectedIds.forEach((id) => {
    const city = VANCOUVER_TARGET_CITIES.find((c) => c.id === id);
    assert.ok(city, `Missing Vancouver target ${id}`);
    assert.equal(city.country, 'Canada');
    assert.ok(city.lat >= 48.5 && city.lat <= 50.5);
    assert.ok(city.lon >= -124.0 && city.lon <= -121.5);
  });
});

runTest('1.6 ALL_TARGET_CITIES aggregates 60 globally unique target coordinates across 10 theaters', () => {
  assert.equal(ALL_TARGET_CITIES.length, 60);
  assert.ok(Object.isFrozen(ALL_TARGET_CITIES));
  assert.equal(HIDDEN_TERRAIN_TARGET_CITIES.length, 17);
  assert.equal(PHASE3_TARGET_CITIES.length, 30);
  const ids = new Set(ALL_TARGET_CITIES.map((c) => c.id));
  assert.equal(ids.size, 60, 'All 60 target IDs must be strictly unique');
});

runTest('1.7 getTargetCities filtering and getTargetCityById lookup across all 60 targets', () => {
  assert.equal(getTargetCities('Mexico').length, 5);
  assert.equal(getTargetCities('MX').length, 5);
  assert.equal(getTargetCities('Russia').length, 6);
  assert.equal(getTargetCities('RU').length, 6);
  assert.equal(getTargetCities('South Africa').length, 5);
  assert.equal(getTargetCities('Lesotho').length, 1);
  assert.equal(getTargetCities('Finland').length, 6);
  assert.equal(getTargetCities('Brazil').length, 6);
  assert.equal(getTargetCities('Canada').length, 6);
  assert.equal(getTargetCities('all').length, 60);
  assert.equal(getTargetCities('hidden_terrain').length, 17);
  assert.equal(getTargetCities('phase3').length, 30);
  assert.equal(getAllTargetCities().length, 60);

  // Every city resolves by ID
  ALL_TARGET_CITIES.forEach((c) => {
    const found = getTargetCityById(c.id);
    assert.ok(found, `Failed to resolve ${c.id} by getTargetCityById`);
    assert.equal(found.id, c.id);
  });
});

runTest('1.8 validateStudyData runtime schema passes cleanly with zero errors', () => {
  const res = validateStudyData();
  assert.ok(res.valid, `validateStudyData failed with errors: ${res.errors.join('; ')}`);
  assert.equal(res.errors.length, 0);
  assert.ok(res.total >= 40);
});

// Suite 2: 3D Twin City Selector Integration
console.log('\n--- Suite 2: citySelector.js 3D Twin Rendering & Interaction ---');

const globe = new THREE.Group();

runTest('2.1 citySelector.initCitySelector creates 60 beacons when includeHiddenTerrain: true', () => {
  const group = citySelector.initCitySelector(globe, {
    includeHiddenTerrain: true
  });
  assert.ok(group, 'cityGroup must be instantiated');
  assert.equal(citySelector.CITY_SHELL_RADIUS, 5.056);
  // 60 cities * 3 pickable meshes (hitMesh, coreMesh, ringMesh) = 180 pickables
  assert.equal(citySelector.getInteractiveCityObjects().length, 180);
  citySelector.disposeCitySelector();
});

runTest('2.2 citySelector.initCitySelector preserves default 13 baseline beacons (39 pickables)', () => {
  const group = citySelector.initCitySelector(globe, {});
  assert.ok(group);
  assert.equal(citySelector.getInteractiveCityObjects().length, 39);
});

runTest('2.3 loadHiddenTerrainBeacons dynamically expands beacon network from 13 to 60', () => {
  const added = citySelector.loadHiddenTerrainBeacons();
  assert.equal(added.length, 47);
  assert.equal(citySelector.getInteractiveCityObjects().length, 180);
});

runTest('2.4 focusCity navigates and triggers telemetry popup for Copper Canyon (Mexico)', () => {
  let focusedLat = null;
  let focusedLon = null;
  let popupPayload = null;

  const target = citySelector.focusCity('mx_copper_canyon', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
      focusedLon = lon;
    },
    showPopup: (data) => {
      popupPayload = data;
    },
    setSpinState: () => {}
  });

  assert.ok(target);
  assert.equal(target.id, 'mx_copper_canyon');
  assert.equal(focusedLat, 27.5322);
  assert.equal(focusedLon, -107.8214);
  assert.ok(popupPayload);
  assert.equal(popupPayload.name, 'Copper Canyon (Divisadero)');
  assert.equal(popupPayload.sarSatelliteId, 'ICEYE-X38');
});

runTest('2.5 focusCity navigates and triggers telemetry popup for Putorana (Russia)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('ru_putorana_kamen', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, 69.1500);
  assert.equal(popupPayload.sarSatelliteId, 'ICEYE-X41');
});

runTest('2.6 focusCity navigates and triggers telemetry popup for Durban (South Africa)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('za_durban', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, -29.8587);
  assert.equal(popupPayload.sarSatelliteId, 'ICEYE-X42');
});

runTest('2.7 focusCity navigates and triggers telemetry popup for São Sebastião (Brazil)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('br_sao_sebastiao', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, -23.76);
  assert.equal(popupPayload.sarSatelliteId, 'STRIX-4');
});

runTest('2.8 focusCity navigates and triggers telemetry popup for Kvarken (Finland)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('fi_kvarken_vaasa', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, 63.095);
  assert.equal(popupPayload.sarSatelliteId, 'ICEYE-X41');
});

runTest('2.9 focusCity navigates and triggers telemetry popup for Mount Etna (Southern Italy)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('it_mount_etna', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, 37.751);
  assert.equal(popupPayload.sarSatelliteId, 'STRIX-4');
});

runTest('2.10 focusCity navigates and triggers telemetry popup for Yamakoshi (Japan Farmland)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('jp_yamakoshi_tanada', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, 37.33);
  assert.equal(popupPayload.sarSatelliteId, 'STRIX-3');
});

runTest('2.11 focusCity navigates and triggers telemetry popup for Roberts Bank (Vancouver)', () => {
  let focusedLat = null;
  let popupPayload = null;

  const target = citySelector.focusCity('van_roberts_bank', {
    flyToLatLon: (lat, lon) => {
      focusedLat = lat;
    },
    showPopup: (data) => {
      popupPayload = data;
    }
  });

  assert.ok(target);
  assert.equal(focusedLat, 49.0194);
  assert.equal(popupPayload.sarSatelliteId, 'ICEYE-X45');
});

runTest('2.12 updateCityMarkers animates beacon pulse and disposeCitySelector cleans up', () => {
  citySelector.updateCityMarkers(1.5);
  citySelector.disposeCitySelector();
  assert.equal(citySelector.getInteractiveCityObjects().length, 0);
  assert.equal(globe.children.length, 0);
});

// Suite 3: 3D Twin UI Fly-To Navigation & Dropdown Selector Controls
console.log('\n--- Suite 3: 3D Twin UI Fly-To Navigation & Dropdown Selectors ---');

runTest('3.1 index.html contains camera fly-to buttons for all 10 synoptic theaters', () => {
  const htmlPath = fs.existsSync('index.html') ? path.resolve('index.html') : path.resolve('viewer_app/index.html');
  const html = fs.readFileSync(htmlPath, 'utf8');
  assert.ok(html.includes('id="fly-south-africa"'), 'Must define #fly-south-africa button in index.html');
  assert.ok(html.includes('id="fly-mexico"'), 'Must define #fly-mexico button in index.html');
  assert.ok(html.includes('id="fly-russia"'), 'Must define #fly-russia button in index.html');
  assert.ok(html.includes('id="fly-southern-italy"'), 'Must define #fly-southern-italy button in index.html');
  assert.ok(html.includes('id="fly-finland"'), 'Must define #fly-finland button in index.html');
  assert.ok(html.includes('id="fly-japan-farmland"'), 'Must define #fly-japan-farmland button in index.html');
  assert.ok(html.includes('id="fly-brazil"'), 'Must define #fly-brazil button in index.html');
  assert.ok(html.includes('id="fly-vancouver"'), 'Must define #fly-vancouver button in index.html');
});

runTest('3.2 index.html contains dropdown selectors for all 10 theaters', () => {
  const htmlPath = fs.existsSync('index.html') ? path.resolve('index.html') : path.resolve('viewer_app/index.html');
  const html = fs.readFileSync(htmlPath, 'utf8');
  assert.ok(html.includes('id="city-select-south-africa"'), 'Must define #city-select-south-africa dropdown in index.html');
  assert.ok(html.includes('id="city-select-mexico"'), 'Must define #city-select-mexico dropdown in index.html');
  assert.ok(html.includes('id="city-select-russia"'), 'Must define #city-select-russia dropdown in index.html');
  assert.ok(html.includes('id="city-select-southern-italy"'), 'Must define #city-select-southern-italy dropdown in index.html');
  assert.ok(html.includes('id="city-select-finland"'), 'Must define #city-select-finland dropdown in index.html');
  assert.ok(html.includes('id="city-select-japan-farmland"'), 'Must define #city-select-japan-farmland dropdown in index.html');
  assert.ok(html.includes('id="city-select-brazil"'), 'Must define #city-select-brazil dropdown in index.html');
  assert.ok(html.includes('id="city-select-vancouver"'), 'Must define #city-select-vancouver dropdown in index.html');

  // Verify all 60 target options exist in HTML
  ALL_TARGET_CITIES.forEach((city) => {
    assert.ok(html.includes(`value="${city.id}"`), `HTML must contain option for target ${city.id}`);
  });
});

runTest('3.3 focusCity updates matching dropdown selector and resets other dropdowns', () => {
  const mockSelects = {
    'city-select-italy': { value: '' },
    'city-select-japan': { value: '' },
    'city-select-south-africa': { value: '' },
    'city-select-mexico': { value: '' },
    'city-select-russia': { value: '' },
    'city-select-southern-italy': { value: '' },
    'city-select-finland': { value: '' },
    'city-select-japan-farmland': { value: '' },
    'city-select-brazil': { value: '' },
    'city-select-vancouver': { value: '' }
  };

  const oldDoc = globalThis.document;
  globalThis.document = {
    getElementById: (id) => mockSelects[id] || null,
    querySelectorAll: () => []
  };

  try {
    // Focus Mexico target
    citySelector.focusCity('mx_popocatepetl', {});
    assert.equal(mockSelects['city-select-mexico'].value, 'mx_popocatepetl');
    assert.equal(mockSelects['city-select-italy'].value, '');
    assert.equal(mockSelects['city-select-japan'].value, '');
    assert.equal(mockSelects['city-select-south-africa'].value, '');
    assert.equal(mockSelects['city-select-russia'].value, '');

    // Focus Brazil target
    citySelector.focusCity('br_sao_sebastiao', {});
    assert.equal(mockSelects['city-select-brazil'].value, 'br_sao_sebastiao');
    assert.equal(mockSelects['city-select-mexico'].value, '');

    // Focus Vancouver target
    citySelector.focusCity('van_roberts_bank', {});
    assert.equal(mockSelects['city-select-vancouver'].value, 'van_roberts_bank');
    assert.equal(mockSelects['city-select-brazil'].value, '');

    // Focus Finland target
    citySelector.focusCity('fi_kvarken_vaasa', {});
    assert.equal(mockSelects['city-select-finland'].value, 'fi_kvarken_vaasa');
    assert.equal(mockSelects['city-select-vancouver'].value, '');

    // Focus Southern Italy target
    citySelector.focusCity('it_mount_etna', {});
    assert.equal(mockSelects['city-select-southern-italy'].value, 'it_mount_etna');
    assert.equal(mockSelects['city-select-finland'].value, '');
  } finally {
    globalThis.document = oldDoc;
  }
});

// Suite 4: 3D SAR Swath Footprints for 10 Theaters STAC Orders
console.log('\n--- Suite 4: 3D SAR Swath Footprints for 10 Theaters STAC Orders ---');

runTest('4.1 HIDDEN_TERRAIN_SAR_CONSTELLATIONS and PHASE3_SAR_CONSTELLATIONS define 27 STAC tasking orders', () => {
  assert.equal(HIDDEN_TERRAIN_SAR_CONSTELLATIONS.length, 9);
  assert.equal(PHASE3_SAR_CONSTELLATIONS.length, 18);
  assert.ok(Object.isFrozen(HIDDEN_TERRAIN_SAR_CONSTELLATIONS));
  assert.ok(Object.isFrozen(PHASE3_SAR_CONSTELLATIONS));
  assert.equal(ALL_SAR_CONSTELLATIONS.length, 29);

  const mexOrders = HIDDEN_TERRAIN_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'MEXICO');
  const ruOrders = HIDDEN_TERRAIN_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'RUSSIA');
  const zaOrders = HIDDEN_TERRAIN_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'SOUTH_AFRICA');

  assert.equal(mexOrders.length, 3, 'Must have 3 Mexico SAR orders');
  assert.equal(ruOrders.length, 3, 'Must have 3 Russia SAR orders');
  assert.equal(zaOrders.length, 3, 'Must have 3 South Africa SAR orders');

  const sItOrders = PHASE3_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'SOUTHERN_ITALY');
  const fiOrders = PHASE3_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'FINLAND');
  const jpFarmOrders = PHASE3_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'JAPAN_FARMLAND');
  const brOrders = PHASE3_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'BRAZIL');
  const vanOrders = PHASE3_SAR_CONSTELLATIONS.filter(s => s.targetRegion === 'VANCOUVER');

  assert.equal(sItOrders.length, 4, 'Must have 4 Southern Italy SAR orders');
  assert.equal(fiOrders.length, 3, 'Must have 3 Finland SAR orders');
  assert.equal(jpFarmOrders.length, 4, 'Must have 4 Japan Farmland SAR orders');
  assert.equal(brOrders.length, 4, 'Must have 4 Brazil SAR orders');
  assert.equal(vanOrders.length, 3, 'Must have 3 Vancouver SAR orders');
});

runTest('4.2 sarTasking.initSarTasking({ includeHiddenTerrain: true }) creates 29 constellations (58 pickable meshes)', () => {
  const sarGlobe = new THREE.Group();
  const group = sarTasking.initSarTasking(sarGlobe, { includeHiddenTerrain: true });
  assert.ok(group);

  const pickables = sarTasking.getSarPickableObjects();
  // 29 constellations * 2 pickables each (satellite bus + ground swath mesh) = 58
  assert.equal(pickables.length, 58, `Expected 58 SAR pickable objects, got ${pickables.length}`);

  const sats = pickables.filter(p => p.userData.type === 'sar_satellite');
  const swaths = pickables.filter(p => p.userData.type === 'sar_swath');
  assert.equal(sats.length, 29);
  assert.equal(swaths.length, 29);

  sarTasking.disposeSarTasking();
  assert.equal(sarTasking.getSarPickableObjects().length, 0);
});

runTest('4.3 exportStacTaskingOrder({ includeHiddenTerrain: true }) exports full 29 STAC v1.0.0 tasking orders', () => {
  const stac = sarTasking.exportStacTaskingOrder(false, { includeHiddenTerrain: true });
  assert.equal(stac.type, 'FeatureCollection');
  assert.equal(stac.stac_version, '1.0.0');
  assert.equal(stac.features.length, 29);

  stac.features.forEach((feat) => {
    assert.equal(feat.type, 'Feature');
    assert.equal(feat.geometry.type, 'Polygon');
    assert.equal(feat.geometry.coordinates[0].length, 5, 'Polygon ring must have 5 coordinates');
    assert.equal(feat.properties['sar:frequency_band'], 'X');
    assert.equal(feat.properties['sar:center_frequency'], 9.65);
  });
});

runTest('4.4 sarTasking preserves baseline defaults with 4 pickables when includeHiddenTerrain is omitted', () => {
  const sarGlobe = new THREE.Group();
  sarTasking.initSarTasking(sarGlobe);
  assert.equal(sarTasking.getSarPickableObjects().length, 4);
  const stac = sarTasking.exportStacTaskingOrder(false);
  assert.equal(stac.features.length, 2);
  sarTasking.disposeSarTasking();
});

console.log('===============================================================================');
console.log(`TEST SUMMARY: Total: ${passed + failed} | Passed: ${passed} | Failed: ${failed}`);
console.log('===============================================================================');

if (failed > 0) {
  process.exit(1);
}
