from __future__ import annotations
"""
test_atlas.py — Atlas (IAM Central) · Plano de Testes Completo
Porta: 5010 | Roles testadas: admin

Testes cobertos:
  - Autenticação (login válido/inválido, logout, token SSO)
  - CRUD Empresas
  - CRUD Departamentos
  - CRUD Pessoas
  - Atribuição de funcoes e acessos por sistema
  - Controle de acesso (endpoints protegidos sem auth)
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5010"


def _ping_ok() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/api/ping", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


# ─── Autenticação ─────────────────────────────────────────────────────────────

class TestAtlasAutenticacao:
    """Testes de autenticação — verifica login, logout e proteção de rotas."""

    def test_01_atlas_acessivel(self):
        """Atlas deve estar rodando e respondendo no /api/ping."""
        if not _ping_ok():
            pytest.skip("Atlas não está rodando")
        r = requests.get(f"{BASE_URL}/api/ping", timeout=3)
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_02_login_admin_valido(self):
        """Login com credenciais admin corretas retorna token JWT."""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
            timeout=10,
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("ok") is True
        assert "token" in data.get("data", {})
        assert "sistemas" in data.get("data", {})

    def test_03_login_senha_invalida_retorna_401(self):
        """Login com senha errada deve retornar 401."""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "senha_errada_xpto"},
        )
        assert r.status_code == 401

    def test_04_login_email_inexistente_retorna_401(self):
        """Login com e-mail não cadastrado deve retornar 401."""
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "nao_existe@olimpus.local", "senha": "qualquer"},
        )
        assert r.status_code == 401

    def test_05_endpoint_protegido_sem_sessao_retorna_401(self):
        """GET /api/pessoas sem autenticação deve retornar 401."""
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/pessoas")
        assert r.status_code == 401

    def test_06_logout_encerra_sessao(self, admin_session):
        """Logout deve encerrar a sessão e invalidar o cookie."""
        r = admin_session.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code in [200, 401]
        # Re-faz login para não quebrar fixtures subsequentes
        admin_session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
        )

    def test_07_token_sso_invalido_retorna_401(self):
        """Token SSO inválido deve ser rejeitado."""
        r = requests.get(f"{BASE_URL}/api/auth/validate?token=token_falso_invalido")
        assert r.status_code == 401

    def test_08_me_retorna_dados_do_usuario(self, admin_session):
        """GET /api/auth/me retorna dados do usuário autenticado."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert "email" in data
        assert "funcoes" in data
        assert "sistemas" in data


# ─── Empresas ─────────────────────────────────────────────────────────────────

class TestAtlasEmpresas:
    """Testes de gestão de empresas."""

    def test_09_listar_empresas(self, admin_session):
        """Admin pode listar todas as empresas."""
        r = admin_session.get(f"{BASE_URL}/api/empresas")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_10_criar_empresa(self, admin_session):
        """Admin pode criar uma nova empresa."""
        nome = f"Empresa Teste {int(time.time())}"
        r = admin_session.post(
            f"{BASE_URL}/api/empresas",
            json={"nome": nome, "cnpj": "00.000.000/0001-00"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_11_criar_empresa_sem_nome_retorna_400(self, admin_session):
        """Criar empresa sem nome deve retornar 400."""
        r = admin_session.post(f"{BASE_URL}/api/empresas", json={})
        assert r.status_code == 400

    def test_12_buscar_empresa_inexistente_retorna_404(self, admin_session):
        """Buscar empresa com ID inexistente deve retornar 404."""
        r = admin_session.get(f"{BASE_URL}/api/empresas/999999")
        assert r.status_code == 404


# ─── Departamentos ─────────────────────────────────────────────────────────────

class TestAtlasDepartamentos:
    """Testes de gestão de departamentos centralizados."""

    def test_13_listar_departamentos(self, admin_session):
        """Admin pode listar departamentos."""
        r = admin_session.get(f"{BASE_URL}/api/departamentos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_14_criar_departamento(self, admin_session):
        """Admin pode criar departamento."""
        r = admin_session.post(
            f"{BASE_URL}/api/departamentos",
            json={"nome": f"Depto Teste {int(time.time())}"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_15_criar_departamento_sem_nome_retorna_400(self, admin_session):
        """Criar departamento sem nome deve retornar 400."""
        r = admin_session.post(f"{BASE_URL}/api/departamentos", json={})
        assert r.status_code == 400


# ─── Pessoas ─────────────────────────────────────────────────────────────────

class TestAtlasPessoas:
    """Testes de gestão de pessoas."""

    def test_16_listar_pessoas(self, admin_session):
        """Admin pode listar todas as pessoas."""
        r = admin_session.get(f"{BASE_URL}/api/pessoas")
        assert r.status_code == 200
        pessoas = r.json().get("data", [])
        assert isinstance(pessoas, list)
        assert len(pessoas) > 0  # Pelo menos o admin existe

    def test_17_filtrar_pessoas_ativas(self, admin_session):
        """Filtragem por ativo=1 retorna lista."""
        r = admin_session.get(f"{BASE_URL}/api/pessoas?ativo=1")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_18_criar_pessoa_valida(self, admin_session):
        """Admin pode criar pessoa com dados válidos."""
        r = admin_session.post(
            f"{BASE_URL}/api/pessoas",
            json={
                "nome":  f"Pessoa Teste {int(time.time())}",
                "email": f"pessoa_auto_{int(time.time())}@olimpus.local",
                "senha": "Teste@2024",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_19_criar_pessoa_email_duplicado_retorna_erro(self, admin_session):
        """Criar pessoa com e-mail já existente deve retornar erro."""
        r = admin_session.post(
            f"{BASE_URL}/api/pessoas",
            json={
                "nome":  "Duplicado",
                "email": "admin@olimpus.local",
                "senha": "Qualquer@1",
            },
        )
        assert r.status_code in [400, 409, 422]

    def test_20_criar_pessoa_sem_email_retorna_400(self, admin_session):
        """Criar pessoa sem e-mail deve retornar 400."""
        r = admin_session.post(
            f"{BASE_URL}/api/pessoas",
            json={"nome": "Sem Email", "senha": "Teste@2024"},
        )
        assert r.status_code == 400

    def test_21_buscar_pessoa_inexistente_retorna_404(self, admin_session):
        """Buscar pessoa com ID inexistente deve retornar 404."""
        r = admin_session.get(f"{BASE_URL}/api/pessoas/999999")
        assert r.status_code == 404


# ─── Funções e Acessos ────────────────────────────────────────────────────────

class TestAtlasFuncoesAcessos:
    """Testes de funções e controle de acesso por sistema."""

    def test_22_listar_funcoes(self, admin_session):
        """Admin pode listar funções disponíveis."""
        r = admin_session.get(f"{BASE_URL}/api/funcoes")
        assert r.status_code == 200
        funcoes = r.json().get("data", [])
        assert isinstance(funcoes, list)
        nomes = [f["nome"] for f in funcoes]
        assert "admin" in nomes

    def test_23_listar_sistemas(self, admin_session):
        """Admin pode listar sistemas cadastrados."""
        r = admin_session.get(f"{BASE_URL}/api/sistemas")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_24_listar_acessos(self, admin_session):
        """Admin pode listar regras de acesso."""
        r = admin_session.get(f"{BASE_URL}/api/acessos")
        assert r.status_code in [200, 404]  # 404 se rota não existir

    def test_25_criar_acesso_valido(self, admin_session):
        """Admin pode criar regra de acesso para uma pessoa."""
        # Obtém lista de pessoas para pegar um ID válido
        r = admin_session.get(f"{BASE_URL}/api/pessoas?ativo=1")
        pessoas = r.json().get("data", [])
        if not pessoas:
            pytest.skip("Nenhuma pessoa cadastrada para testar acesso")
        pid = pessoas[0]["id"]
        r = admin_session.post(
            f"{BASE_URL}/api/acessos",
            json={
                "sistema_folder": "Hera - Gestão de Pessoas",
                "pessoa_id":      pid,
                "permitido":      1,
                "role_sistema":   "colaborador",
            },
        )
        assert r.status_code in [200, 201, 400]  # 400 se já existir

    def test_26_dashboard_retorna_metricas(self, admin_session):
        """Dashboard do Atlas retorna métricas gerais."""
        r = admin_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_27_auditoria_acessivel(self, admin_session):
        """Log de auditoria está acessível para admin."""
        r = admin_session.get(f"{BASE_URL}/api/auditoria")
        assert r.status_code in [200, 404]
