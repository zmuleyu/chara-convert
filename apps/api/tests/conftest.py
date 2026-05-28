import sys
import site
from pathlib import Path

# Add site-packages from hermes venv where fastapi is installed
site.addsitedir("C:\\Users\\Admin\\AppData\\Local\\hermes\\hermes-agent\\venv\\Lib\\site-packages")

# Add chara-convert and apps/api to path BEFORE importing anything
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "chara-convert"))
sys.path.insert(0, str(repo_root / "apps" / "api"))

import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
