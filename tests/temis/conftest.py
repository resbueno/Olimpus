from __future__ import annotations
"""conftest.py — Têmis (Gestão de Contratos) · Fixtures de teste por role"""
import sys
import pytest
import requests
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from _log_plugin import gerar_relatorio_final

APP_NOME = "Têmis – Gestão de Contratos"
BASE_URL = "http://localhost:5020"   # ATENÇÃO: Têmis usa 5020 — conflito com Héstia. Rode separadamente!
LOG_PATH = str(Path(__file__).parent / f"test_temis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Padrão B: usa funcoes do Atlas. Gestor tem funcao 'admin'.
ADMIN_EMAIL    = "admin@olimpus.local"
ADMIN_SENHA    = "Atlas@2024"
GESTOR_EMAIL   = "gestor.temis@olimpus.local"
GESTOR_SENHA   = "Teste@2024"
OPERADOR_EMAIL = "operador.temis@olimpus.local"
OPERADOR_SENHA = "Teste@2024"

_PASSWORD_FIELD = "password"


def _make_session(email: str, senha: str) -> requests.Session | None:
    s = requests.Session()
    try:
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": email, _PASSWORD_FIELD: senha}, timeout=10)
        if r.status_code == 200 and r.json().get("ok"):
            return s
    except Exception:
        pass
    return None


@pytest.fixture(scope="session")
def admin_session():
    s = _make_session(ADMIN_EMAIL, ADMIN_SENHA)
    if not s:
        pytest.skip("Têmis não acessível ou credenciais admin inválidas")
    return s


@pytest.fixture(scope="session")
def gestor_session():
    s = _make_session(GESTOR_EMAIL, GESTOR_SENHA)
    if not s:
        pytest.skip("Login como gestor.temis falhou — rode setup_usuarios.bat primeiro")
    return s


@pytest.fixture(scope="session")
def operador_session():
    s = _make_session(OPERADOR_EMAIL, OPERADOR_SENHA)
    if not s:
        pytest.skip("Login como operador.temis falhou — rode setup_usuarios.bat primeiro")
    return s


@pytest.fixture
def base_url():
    return BASE_URL


def pytest_terminal_summary(terminalreporter, exitstatus):
    gerar_relatorio_final(terminalreporter, exitstatus, APP_NOME, LOG_PATH)
