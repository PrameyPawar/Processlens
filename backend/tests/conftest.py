"""
Pytest fixtures for ProcessLens backend testing.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = BASE_DIR / "data" / "ProcessLens_Development_Data" / "samples"

@pytest.fixture
def client():
    """FastAPI TestClient instance."""
    return TestClient(app)

@pytest.fixture
def sample_quickstart_path():
    return SAMPLES_DIR / "manufacturing_orders_quickstart.csv"

@pytest.fixture
def sample_clean_path():
    return SAMPLES_DIR / "manufacturing_orders_clean.csv"

@pytest.fixture
def sample_rework_path():
    return SAMPLES_DIR / "manufacturing_orders_rework.csv"

@pytest.fixture
def sample_messy_path():
    return SAMPLES_DIR / "manufacturing_orders_messy.csv"
