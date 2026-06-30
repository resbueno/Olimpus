from __future__ import annotations
"""
test_hestia.py - Testes para Héstia (Intranet Corporativa)
Porta: 5020 | Prioridade: ALTA
Endpoints reais: /api/news, /api/documents, /api/people, /api/communities, /api/events
"""
import time
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5020"


@pytest.mark.api
class TestHestiaAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        """Héstia deve responder"""
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Héstia não está rodando: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_02_login_valido(self):
        """Login via Atlas deve funcionar"""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", "password": "Atlas@2024"},
                timeout=10,
            )
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Héstia não está rodando: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_03_login_invalido(self):
        """Login com credenciais inválidas retorna 401"""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "teste@olimpus.local", "password": "errado"},
                timeout=5,
            )
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Héstia não está rodando: {exc}")
        assert r.status_code == 401

    def test_04_auth_status(self, hestia_session):
        """Sessão autenticada deve indicar autenticado"""
        r = hestia_session.get(f"{BASE_URL}/api/auth/status")
        assert r.status_code == 200
        data = r.json()
        assert data.get("authenticated") is True


@pytest.mark.api
class TestHestiaNews:
    """Testes de notícias"""

    def test_05_listar_news(self, hestia_session):
        """Listar notícias"""
        r = hestia_session.get(f"{BASE_URL}/api/news?limit=10")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_06_listar_news_com_limite(self, hestia_session):
        """Limite de resultados deve ser respeitado"""
        r = hestia_session.get(f"{BASE_URL}/api/news?limit=3")
        assert r.status_code == 200
        news = r.json().get("data", [])
        assert len(news) <= 3

    def test_07_criar_news(self, hestia_session):
        """Criar notícia (admin)"""
        r = hestia_session.post(
            f"{BASE_URL}/api/news",
            json={
                "title":   f"Notícia Teste {int(time.time())}",
                "content": "Conteúdo de teste automatizado",
            },
        )
        assert r.status_code in [200, 201, 400]


@pytest.mark.api
class TestHestiaDocuments:
    """Testes de documentos"""

    def test_08_listar_documentos(self, hestia_session):
        """Listar documentos"""
        r = hestia_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_09_listar_pastas(self, hestia_session):
        """Listar pastas de documentos"""
        r = hestia_session.get(f"{BASE_URL}/api/documents/folders")
        assert r.status_code == 200
        assert "data" in r.json()


@pytest.mark.api
class TestHestiaPeople:
    """Testes de diretório de pessoas"""

    def test_10_listar_pessoas(self, hestia_session):
        """Listar pessoas"""
        r = hestia_session.get(f"{BASE_URL}/api/people")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_11_buscar_pessoa(self, hestia_session):
        """Buscar pessoa por nome"""
        r = hestia_session.get(f"{BASE_URL}/api/people?search=admin")
        assert r.status_code == 200

    def test_12_aniversariantes(self, hestia_session):
        """Listar aniversariantes"""
        r = hestia_session.get(f"{BASE_URL}/api/people/birthdays")
        assert r.status_code == 200

    def test_13_kudos_feed(self, hestia_session):
        """Listar kudos"""
        r = hestia_session.get(f"{BASE_URL}/api/people/kudos?limit=10")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_14_enviar_kudos(self, hestia_session):
        """Enviar kudos para outra pessoa"""
        # Busca uma pessoa para enviar
        people = hestia_session.get(f"{BASE_URL}/api/people").json().get("data", [])
        if not people:
            pytest.fail("Sem pessoas cadastradas para enviar kudos")
        r = hestia_session.post(
            f"{BASE_URL}/api/people/kudos",
            json={"to_person_id": people[0]["id"], "message": "Ótimo trabalho! Teste automático."},
        )
        assert r.status_code in [200, 201, 400]


@pytest.mark.api
class TestHestiaCommunities:
    """Testes de comunidades"""

    def test_15_listar_comunidades(self, hestia_session):
        """Listar comunidades"""
        r = hestia_session.get(f"{BASE_URL}/api/communities")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_16_criar_comunidade(self, hestia_session):
        """Criar comunidade (admin)"""
        r = hestia_session.post(
            f"{BASE_URL}/api/communities",
            json={
                "name":        f"Comunidade Teste {int(time.time())}",
                "description": "Criada por teste automático",
            },
        )
        assert r.status_code in [200, 201, 400]


@pytest.mark.api
class TestHestiaEvents:
    """Testes de eventos"""

    def test_17_listar_eventos(self, hestia_session):
        """Listar eventos"""
        r = hestia_session.get(f"{BASE_URL}/api/events")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_18_stats(self, hestia_session):
        """Estatísticas gerais"""
        r = hestia_session.get(f"{BASE_URL}/api/stats")
        assert r.status_code == 200
