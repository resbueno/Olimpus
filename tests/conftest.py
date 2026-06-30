from __future__ import annotations
"""
conftest.py — Fixtures globais para Olimpus Test Suite v2.0

Todos os apps Olimpus usam sessões Flask com cookies — NÃO Bearer tokens.
Cada fixture de sessão faz login direto no app e mantém o cookie.
"""
import os
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

# conftest.py está em tests/ — .env está na mesma pasta
load_dotenv(Path(__file__).parent / ".env")

TEST_EMAIL    = os.getenv("TEST_EMAIL",    "admin@olimpus.local")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "Atlas@2024")

# URLs dos apps (porta conforme olimpus.json)
APPS = {
    "atlas":    "http://localhost:5010",
    "hub":      "http://localhost:5100",
    "argos":    "http://localhost:5000",
    "hestia":   "http://localhost:5020",
    "cronos":   "http://localhost:5025",
    "oraculo":  "http://localhost:5030",
    "hera":     "http://localhost:5041",
    "hercules": "http://localhost:5001",
    "hermes":   "http://localhost:5050",
    "iris":     "http://localhost:5070",
    "ploutos":  "http://localhost:5080",
    "tiresias": "http://localhost:5090",
    # Têmis configurado para 5020 (mesmo que Héstia — conflito de porta conhecido)
    "temis":    "http://localhost:5020",
}

# Apps que usam campo "password" no login (auth.py compartilhado)
# Demais apps usam "senha"
_PASSWORD_FIELD = {
    "argos":    "password",
    "hestia":   "password",
    "iris":     "password",
    "temis":    "password",
    "tiresias": "password",
}


def _make_session(app_name: str) -> requests.Session:
    """Cria sessão autenticada (cookie-based) para qualquer app Olimpus.
    Falha o teste imediatamente se o app não estiver acessível.
    """
    base = APPS[app_name]
    field = _PASSWORD_FIELD.get(app_name, "senha")
    s = requests.Session()
    try:
        r = s.post(
            f"{base}/api/auth/login",
            json={"email": TEST_EMAIL, field: TEST_PASSWORD},
            timeout=10,
        )
        if r.status_code == 200 and r.json().get("ok"):
            return s
        pytest.fail(f"{app_name} login falhou — status {r.status_code}")
    except Exception as exc:
        pytest.fail(f"{app_name} não acessível em {base}: {exc}")


# ── Fixtures de sessão por app ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def atlas_session():
    return _make_session("atlas")


@pytest.fixture(scope="session")
def hub_session():
    return _make_session("hub")


@pytest.fixture(scope="session")
def hestia_session():
    return _make_session("hestia")


@pytest.fixture(scope="session")
def iris_session():
    return _make_session("iris")


@pytest.fixture(scope="session")
def hera_session():
    return _make_session("hera")


@pytest.fixture(scope="session")
def cronos_session():
    return _make_session("cronos")


@pytest.fixture(scope="session")
def hercules_session():
    return _make_session("hercules")


@pytest.fixture(scope="session")
def hermes_session():
    return _make_session("hermes")


@pytest.fixture(scope="session")
def oraculo_session():
    return _make_session("oraculo")


@pytest.fixture(scope="session")
def ploutos_session():
    return _make_session("ploutos")


@pytest.fixture(scope="session")
def argos_session():
    return _make_session("argos")


@pytest.fixture(scope="session")
def temis_session():
    return _make_session("temis")


@pytest.fixture(scope="session")
def tiresias_session():
    return _make_session("tiresias")


# ── Token Atlas JWT (apenas para testes de SSO) ───────────────────────────────

@pytest.fixture(scope="session")
def atlas_token():
    """Token JWT do Atlas — usado em testes de SSO e apps que aceitam Bearer token."""
    try:
        r = requests.post(
            f"{APPS['atlas']}/api/auth/login",
            json={"email": TEST_EMAIL, "senha": TEST_PASSWORD},
            timeout=10,
        )
        if r.status_code == 200:
            token = r.json().get("data", {}).get("token")
            if token:
                return token
        pytest.fail(f"Atlas login falhou ao obter token — status {r.status_code}")
    except Exception as exc:
        pytest.fail(f"Atlas não acessível para obter token: {exc}")


# ── Utilitários ───────────────────────────────────────────────────────────────

@pytest.fixture
def app_url():
    """Retorna URL do app pelo nome."""
    return lambda name: APPS.get(name.lower(), "")


def pytest_configure(config):
    config.addinivalue_line("markers", "api: testes de API")
    config.addinivalue_line("markers", "integration: testes de integração")


def pytest_report_header(config):
    return [
        "Olimpus Test Suite v2.0",
        f"Atlas: {APPS['atlas']}  |  Usuário: {TEST_EMAIL}",
        "Auth: sessão cookie por app (não Bearer token)",
    ]
