"""Test suite for scientific study metrics and regional tracking."""

import numpy as np
import pytest

from od_experiments.scientific_study.metrics_engine import (
    compute_latitude_weights,
    weighted_rmse,
    anomaly_correlation_coefficient,
    mean_bias,
    compute_all_metrics,
)
from od_experiments.scientific_study.regional_tracker import (
    DOMAINS,
    extract_regional_domain,
    find_pressure_minimum,
    find_maximum_wind,
)


def test_latitude_weights_properties():
    lats = np.linspace(90, -90, 721)
    w = compute_latitude_weights(lats)
    assert len(w) == 721
    # Equator (index 360) should have higher weight than poles (index 0, 720)
    assert w[360] > w[0]
    assert w[360] > w[720]
    assert np.all(w >= 0.0)


def test_weighted_rmse_perfect_forecast():
    arr = np.random.rand(721, 1440)
    lats = np.linspace(90, -90, 721)
    rmse = weighted_rmse(arr, arr, lats=lats)
    assert rmse == 0.0


def test_anomaly_correlation_bounds():
    truth = np.sin(np.linspace(0, 10, 100))
    forecast = truth + 0.1 * np.random.rand(100)
    acc = anomaly_correlation_coefficient(forecast, truth)
    assert -1.0 <= acc <= 1.0
    assert acc > 0.8  # Strong correlation


def test_extract_regional_domain_italy():
    lats = np.linspace(90, -90, 721)
    lons = np.linspace(-180, 180, 1440)
    grid = np.zeros((721, 1440))
    
    sub_grid, sub_lats, sub_lons = extract_regional_domain(grid, lats, lons, "italy")
    assert np.all(sub_lats >= 35.0) and np.all(sub_lats <= 48.0)
    assert np.all(sub_lons >= 6.0) and np.all(sub_lons <= 19.0)


def test_extract_regional_domain_japan():
    lats = np.linspace(90, -90, 721)
    lons = np.linspace(-180, 180, 1440)
    grid = np.zeros((721, 1440))
    
    sub_grid, sub_lats, sub_lons = extract_regional_domain(grid, lats, lons, "japan")
    assert np.all(sub_lats >= 30.0) and np.all(sub_lats <= 46.0)
    assert np.all(sub_lons >= 128.0) and np.all(sub_lons <= 146.0)


def test_storm_tracking_min_pressure():
    lats = np.linspace(35, 48, 50)
    lons = np.linspace(6, 19, 50)
    grid = np.ones((50, 50)) * 101325.0
    grid[25, 25] = 98000.0  # Simulated low pressure eye
    
    center = find_pressure_minimum(grid, lats, lons)
    assert center["min_pressure_pa"] == 98000.0
    assert np.isclose(center["center_lat"], lats[25], atol=0.5)
    assert np.isclose(center["center_lon"], lons[25], atol=0.5)
