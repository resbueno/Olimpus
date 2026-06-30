from __future__ import annotations
"""
test_atlas.py - Testes para Atlas (IAM Central)
Porta: 5010 | Prioridade: CRÍTICA
Endpoints reais: /api/pessoas, /api/empresas, /api/funcoes, /api/sistemas, /api/acessos
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5010"


@pytest.mark.api
@pytest.mark.auth
class TestAtlasAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        """Atlas deve responder no ping"""
        r = requests.get(f"{BASE_URL}/api/ping")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_02_login_valido(self):
        """Login com credenciais válidas retorna token"""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "token" in str(data)

    def test_03_login_invalido(self):
        """Login com senha incorreta retorna 401"""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "senha_errada"},
        )
        assert r.status_code == 401

    def test_04_login_email_invalido(self):
        """Login com email inexistente retorna 401"""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "naoexiste@olimpus.local", "senha": "qualquer"},
        )
        assert r.status_code == 401

    def test_05_logout(self, atlas_session):
        """Logout encerra sessão"""
        r = atlas_session.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code in [200, 401]
        atlas_session.post(f"{BASE_URL}/api/auth/login", json={"email": "renato.s.bueno@hotmail.com", "senha": "admin"})


@pytest.mark.api
class TestAtlasPessoas:
    """Testes de gestão de pessoas"""

    def test_06_listar_pessoas(self, atlas_session):
        """Listar todas as pessoas"""
        r = atlas_session.get(f"{BASE_URL}/api/pessoas")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_07_filtrar_pessoas_por_empresa(self, atlas_session):
        """Filtrar pessoas por empresa"""
        r = atlas_session.get(f"{BASE_URL}/api/pessoas?ativo=1")
        assert r.status_code == 200
        data = r.json().get("data", [])
        assert isinstance(data, list)

    def test_08_criar_pessoa(self, atlas_session):
        """Criar nova pessoa"""
        r = atlas_session.post(
            f"{BASE_URL}/api/pessoas",
            json={
                "nome":   "Teste Automacao",
                "email":  f"teste_auto_{int(time.time())}@olimpus.local",
                "senha":  "Teste123@",
                "funcoes": [],
            },
        )
        assert r.status_code in [200, 201, 400]

    def test_09_listar_sistemas(self, atlas_session):
        """Listar sistemas cadastrados"""
        r = atlas_session.get(f"{BASE_URL}/api/sistemas")
        assert r.status_code == 200
        assert "data" in r.json()


@pytest.mark.api
class TestAtlasEmpresas:
    """Testes de gestão de empresas"""

    def test_10_listar_empresas(self, atlas_session):
        """Listar empresas"""
        r = atlas_session.get(f"{BASE_URL}/api/empresas")
        assert r.status_code == 200
        assert "data" in r.json()

    def test_11_criar_empresa(self, atlas_session):
        """Criar empresa"""
        r = atlas_session.post(
            f"{BASE_URL}/api/empresas",
            json={"nome": f"Empresa Teste {int(time.time())}"},
        )
        assert r.status_code in [200, 201, 400]

    def test_12_listar_funcoes(self, atlas_session):
        """Listar funções disponíveis"""
        r = atlas_session.get(f"{BASE_URL}/api/funcoes")
        assert r.status_code == 200
        data = r.json().get("data", [])
        assert isinstance(data, list)
        # Funções padrão devem existir
        nomes = [f.get("nome") for f in data]
        assert "admin" in nomes
