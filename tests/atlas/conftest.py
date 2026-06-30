from __future__ import annotations
"""conftest.py — Atlas (IAM Central) · Fixtures de teste"""
import os
import sys
import pytest
import requests
from datetime import datetime
from pathlib import Path

# Permite importar _log_plugin da pasta tests/
sys.path.insert(0, str(Path(__file__).parent.parent))
from _log_plugin import gerar_relatorio_final

APP_NOME = "Atlas - Gestão de Acessos"
BASE_URL = "http://localhost:5010"
LOG_PATH = str(Path(__file__).parent / f"test_atlas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Credenciais
ADMIN_EMAIL  = "admin@olimpus.local"
ADMIN_SENHA  = "Atlas@2024"


def _make_session(email: str, senha: str, label: str) -> requests.Session:
    s = requests.Session()
    try:
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": email, "senha": senha}, timeout=10)
        if r.status_code == 200 and r.json().get("ok"):
            return s
    except Exception as e:
        pass
    return None


@pytest.fixture(scope="session")
def admin_session():
    s = _make_session(ADMIN_EMAIL, ADMIN_SENHA, "admin")
    if not s:
        pytest.skip("Atlas não acessível ou credenciais admin inválidas")
    return s


@pytest.fixture
def base_url():
    return BASE_URL


def pytest_terminal_summary(terminalreporter, exitstatus):
    gerar_relatorio_final(terminalreporter, exitstatus, APP_NOME, LOG_PATH)
