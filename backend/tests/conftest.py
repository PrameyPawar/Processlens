"""
Pytest fixtures for ProcessLens backend testing.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import require_analysis_user
from app.schemas.auth import UserResponse, UserRole

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLES_DIR = BASE_DIR / "data" / "ProcessLens_Development_Data" / "samples"
_TEST_ANALYSIS_USER = UserResponse(
    id="test-analysis-user",
    email="test-customer@example.test",
    name="Test Customer",
    role=UserRole.CUSTOMER,
    created_at="2026-01-01T00:00:00Z",
)
app.dependency_overrides[require_analysis_user] = lambda: _TEST_ANALYSIS_USER

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
