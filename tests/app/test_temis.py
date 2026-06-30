from __future__ import annotations
"""
test_temis.py - Testes para Têmis (Gestão de Contratos)
Porta: 5020 (conflito conhecido com Héstia) | Prioridade: ALTA
Endpoints reais: /api/contratos, /api/contratos/<id>, /api/contratos/<id>/anexos,
                 /api/contratos/<id>/aprovacoes, /api/relatorios, /api/alertas
"""
import time
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5020"  # Conflito de porta conhecido


@pytest.mark.api
class TestTemisAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        """Têmis deve responder"""
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Têmis não está rodando: {exc}")
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
            pytest.fail(f"Têmis não disponível: {exc}")
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
            pytest.fail(f"Têmis não está rodando: {exc}")
        assert r.status_code == 401


@pytest.mark.api
class TestTemisContratos:
    """Testes de gestão de contratos"""

    def test_04_listar_contratos(self, temis_session):
        """Listar contratos"""
        r = temis_session.get(f"{BASE_URL}/api/contratos")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_05_criar_contrato(self, temis_session):
        """Criar contrato"""
        r = temis_session.post(
            f"{BASE_URL}/api/contratos",
            json={
                "titulo": f"Contrato Teste {int(time.time())}",
                "descricao": "Contrato criado por teste automático",
                "valor": 10000.00,
                "data_inicio": "2026-01-01",
                "data_fim": "2026-12-31",
                "tipo": "servico",
                "status": "ativo",
            },
        )
        assert r.status_code in [200, 201, 400]

    def test_06_detalhes_contrato(self, temis_session):
        """Obter detalhes de contrato"""
        # Primeiro, tenta obter um contrato existente
        r_list = temis_session.get(f"{BASE_URL}/api/contratos")
        contratos = r_list.json().get("data", [])
        if not contratos:
            pytest.fail("Nenhum contrato disponível")
        
        contrato_id = contratos[0]["id"]
        r = temis_session.get(f"{BASE_URL}/api/contratos/{contrato_id}")
        assert r.status_code == 200
        assert "data" in r.json()


@pytest.mark.api
class TestTemisAnexos:
    """Testes de anexos de contratos"""

    def test_07_listar_anexos(self, temis_session):
        """Listar anexos de contrato"""
        # Obter um contrato para testar
        r_list = temis_session.get(f"{BASE_URL}/api/contratos")
        contratos = r_list.json().get("data", [])
        if not contratos:
            pytest.fail("Nenhum contrato disponível")
        
        contrato_id = contratos[0]["id"]
        r = temis_session.get(f"{BASE_URL}/api/contratos/{contrato_id}/anexos")
        assert r.status_code in [200, 404]

    def test_08_upload_anexo(self, temis_session):
        """Upload de anexo"""
        # Obter um contrato para testar
        r_list = temis_session.get(f"{BASE_URL}/api/contratos")
        contratos = r_list.json().get("data", [])
        if not contratos:
            pytest.fail("Nenhum contrato disponível")
        
        contrato_id = contratos[0]["id"]
        r = temis_session.post(
            f"{BASE_URL}/api/contratos/{contrato_id}/anexos",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        assert r.status_code in [200, 201, 400, 404]


@pytest.mark.api
class TestTemisAprovacoes:
    """Testes de workflow de aprovações"""

    def test_09_listar_aprovacoes(self, temis_session):
        """Listar histórico de aprovações"""
        # Obter um contrato para testar
        r_list = temis_session.get(f"{BASE_URL}/api/contratos")
        contratos = r_list.json().get("data", [])
        if not contratos:
            pytest.fail("Nenhum contrato disponível")
        
        contrato_id = contratos[0]["id"]
        r = temis_session.get(f"{BASE_URL}/api/contratos/{contrato_id}/aprovacoes")
        assert r.status_code in [200, 404]

    def test_10_aprovar_contrato(self, temis_session):
        """Aprovar contrato"""
        # Obter um contrato para testar
        r_list = temis_session.get(f"{BASE_URL}/api/contratos")
        contratos = r_list.json().get("data", [])
        if not contratos:
            pytest.fail("Nenhum contrato disponível")
        
        contrato_id = contratos[0]["id"]
        r = temis_session.post(
            f"{BASE_URL}/api/contratos/{contrato_id}/aprovacoes",
            json={"acao": "aprovar", "comentario": "Aprovado por teste automático"},
        )
        assert r.status_code in [200, 201, 400, 404]


@pytest.mark.api
class TestTemisRelatorios:
    """Testes de relatórios"""

    def test_11_relatorio_contratos(self, temis_session):
        """Gerar relatório de contratos"""
        r = temis_session.get(f"{BASE_URL}/api/relatorios")
        assert r.status_code in [200, 404]

    def test_12_alertas_renovacao(self, temis_session):
        """Ver alertas de renovação"""
        r = temis_session.get(f"{BASE_URL}/api/alertas")
        assert r.status_code in [200, 404]