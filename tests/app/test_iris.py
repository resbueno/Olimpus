from __future__ import annotations
"""
test_iris.py - Testes para Iris (Formulários e Workflow)
Porta: 5070 | Prioridade: ALTA
Endpoints reais: /api/formularios, /api/ordens, /api/ordens/<id>/avancar
"""
import time
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5070"


@pytest.mark.api
class TestIrisAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        """Iris deve responder"""
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Iris não está rodando: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_02_login_valido(self):
        """Login com credenciais válidas"""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", "password": "Atlas@2024"},
                timeout=10,
            )
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Iris não disponível: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_03_auth_status(self, iris_session):
        """Sessão autenticada deve indicar autenticado"""
        r = iris_session.get(f"{BASE_URL}/api/auth/status")
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert data.get("data", {}).get("authenticated") is True


@pytest.mark.api
class TestIrisFormularios:
    """Testes de templates de formulários"""

    def test_04_listar_formularios(self, iris_session):
        """Listar templates de formulários"""
        r = iris_session.get(f"{BASE_URL}/api/formularios")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_05_criar_formulario(self, iris_session):
        """Criar template de formulário com campos e etapas"""
        r = iris_session.post(
            f"{BASE_URL}/api/formularios",
            json={
                "nome":     f"Form Teste {int(time.time())}",
                "descricao": "Formulário criado por teste automático",
                "categoria": "generico",
                "campos":   [{"nome": "descricao", "tipo": "text", "obrigatorio": True}],
                "etapas":   [{"nome": "Solicitação"}, {"nome": "Aprovação"}, {"nome": "Conclusão"}],
                "grupos_acesso": [],
            },
        )
        assert r.status_code in [200, 201]
        data = r.json()
        assert data.get("ok") is True
        return data.get("data", {}).get("id")

    def test_06_formulario_sem_nome_falha(self, iris_session):
        """Criar formulário sem nome deve retornar erro"""
        r = iris_session.post(
            f"{BASE_URL}/api/formularios",
            json={"descricao": "sem nome"},
        )
        assert r.status_code == 400


@pytest.mark.api
class TestIrisOrdens:
    """Testes de ordens de serviço"""

    def _get_formulario_id(self, iris_session):
        """Obtém ou cria um formulário para usar nos testes."""
        r = iris_session.get(f"{BASE_URL}/api/formularios?ativo=1")
        forms = r.json().get("data", [])
        if forms:
            return forms[0]["id"]
        r2 = iris_session.post(
            f"{BASE_URL}/api/formularios",
            json={
                "nome":   "Form Teste OS",
                "campos": [],
                "etapas": [{"nome": "Entrada"}, {"nome": "Revisão"}, {"nome": "Fechamento"}],
            },
        )
        return r2.json().get("data", {}).get("id")

    def test_07_listar_ordens(self, iris_session):
        """Listar ordens de serviço"""
        r = iris_session.get(f"{BASE_URL}/api/ordens")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_08_criar_ordem(self, iris_session):
        """Criar ordem de serviço"""
        fid = self._get_formulario_id(iris_session)
        if not fid:
            pytest.fail("Nenhum formulário disponível para criar ordem")
        r = iris_session.post(
            f"{BASE_URL}/api/ordens",
            json={
                "formulario_id": fid,
                "titulo":       f"OS Teste {int(time.time())}",
                "dados":        {"descricao": "teste automático"},
                "prioridade":   "normal",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_09_filtrar_ordens_por_status(self, iris_session):
        """Filtrar ordens por status"""
        r = iris_session.get(f"{BASE_URL}/api/ordens?status=aberta")
        assert r.status_code == 200

    def test_10_avancar_ordem_inexistente(self, iris_session):
        """Avançar OS inexistente deve retornar 404"""
        r = iris_session.post(
            f"{BASE_URL}/api/ordens/999999/avancar",
            json={"acao": "avancar"},
        )
        assert r.status_code == 404

    def test_11_stats(self, iris_session):
        """Estatísticas devem ser retornadas"""
        r = iris_session.get(f"{BASE_URL}/api/stats")
        assert r.status_code == 200
        assert r.json().get("ok") is True
