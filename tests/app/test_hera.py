from __future__ import annotations
"""
test_hera.py - Testes para Hera (Gestão de Pessoas/RH)
Porta: 5041 | Prioridade: ALTA
Endpoints reais: /api/users, /api/departments, /api/ferias, /api/ciclos, /api/onboarding
"""
import time
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5041"


@pytest.mark.api
class TestHeraAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Hera não está rodando: {exc}")
        assert r.status_code == 200

    def test_02_login(self):
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
                timeout=10,
            )
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Hera não disponível: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True


@pytest.mark.api
class TestHeraColaboradores:
    """Testes de colaboradores"""

    def test_03_listar_users(self, hera_session):
        """Listar colaboradores"""
        r = hera_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_04_listar_departamentos(self, hera_session):
        """Listar departamentos"""
        r = hera_session.get(f"{BASE_URL}/api/departments")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_05_onboarding_etapas(self, hera_session):
        """Listar etapas de onboarding"""
        r = hera_session.get(f"{BASE_URL}/api/onboarding/etapas")
        assert r.status_code == 200
        assert "data" in r.json()


@pytest.mark.api
class TestHeraFerias:
    """Testes de férias"""

    def test_06_listar_ferias(self, hera_session):
        """Listar solicitações de férias"""
        r = hera_session.get(f"{BASE_URL}/api/ferias")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_07_solicitar_ferias(self, hera_session):
        """Solicitar férias"""
        r = hera_session.post(
            f"{BASE_URL}/api/ferias",
            json={"data_inicio": "2026-07-01", "data_fim": "2026-07-15"},
        )
        assert r.status_code in [200, 201, 400]


@pytest.mark.api
class TestHeraCiclosAvaliacao:
    """Testes de avaliações 360°"""

    def test_08_listar_ciclos(self, hera_session):
        """Listar ciclos de avaliação"""
        r = hera_session.get(f"{BASE_URL}/api/ciclos")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_09_criar_ciclo(self, hera_session):
        """Criar ciclo de avaliação"""
        r = hera_session.post(
            f"{BASE_URL}/api/ciclos",
            json={
                "titulo":      f"Ciclo Teste {int(time.time())}",
                "tipo":        "360",
                "data_inicio": "2026-05-01",
                "data_fim":    "2026-05-31",
            },
        )
        assert r.status_code in [200, 201, 400]


@pytest.mark.api
class TestHeraEngajamento:
    """Testes de feedbacks, kudos e PDI"""

    def test_10_listar_feedbacks(self, hera_session):
        """Listar feedbacks"""
        r = hera_session.get(f"{BASE_URL}/api/feedbacks")
        assert r.status_code == 200

    def test_11_kudos_feed(self, hera_session):
        """Ver feed de kudos"""
        r = hera_session.get(f"{BASE_URL}/api/kudos/feed")
        assert r.status_code == 200

    def test_12_listar_treinamentos(self, hera_session):
        """Listar treinamentos"""
        r = hera_session.get(f"{BASE_URL}/api/treinamentos")
        assert r.status_code == 200
        assert "data" in r.json()
