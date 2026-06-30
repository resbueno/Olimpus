from __future__ import annotations
"""
test_hub.py - Testes para Hub Olimpus
Porta: 5100 | Prioridade: CRÍTICA
Endpoints reais: /api/apps, /api/launch/<folder>, /api/ready/<port>
"""
import pytest
import requests

BASE_URL = "http://localhost:5100"


@pytest.mark.api
class TestHubAuth:
    """Testes de autenticação do Hub"""

    def test_01_ping(self):
        """Hub deve responder"""
        r = requests.get(f"{BASE_URL}/api/ping")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_02_login_valido(self):
        """Login com credenciais Atlas válidas"""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
            timeout=10,
        )
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_03_login_invalido(self):
        """Login com credenciais inválidas retorna 401 ou erro Atlas"""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "errado"},
        )
        assert r.status_code in [401, 502, 503]

    def test_04_me_sem_sessao(self):
        """Endpoint /api/auth/me sem sessão retorna 401"""
        r = requests.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401


@pytest.mark.api
class TestHubApps:
    """Testes de listagem e lançamento de apps"""

    def test_05_listar_apps(self, hub_session):
        """Listar apps disponíveis para o usuário"""
        r = hub_session.get(f"{BASE_URL}/api/apps")
        assert r.status_code == 200
        apps = r.json()
        assert isinstance(apps, list)
        # Hub retorna lista direta (não wrapped em {ok, data})
        if apps:
            assert "folder" in apps[0]
            assert "port" in apps[0]

    def test_06_me_autenticado(self, hub_session):
        """Usuário autenticado deve aparecer em /api/auth/me"""
        r = hub_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert data.get("data", {}).get("email") == "renato.s.bueno@hotmail.com"

    def test_07_ready_porta_invalida(self, hub_session):
        """Verificar porta fora do range retorna 400"""
        r = hub_session.get(f"{BASE_URL}/api/ready/80")
        assert r.status_code == 400

    def test_08_ready_porta_valida(self, hub_session):
        """Verificar porta válida retorna status ready"""
        r = hub_session.get(f"{BASE_URL}/api/ready/5010")
        assert r.status_code == 200
        data = r.json()
        assert "ready" in data
