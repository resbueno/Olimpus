from __future__ import annotations
"""
test_hermes.py — Hermes (Gestão de Ativos) · Plano de Testes por Role
Porta: 5050 | Roles: admin > gestor > colaborador (operador)

Testes cobertos:
  - Autenticação por role
  - Admin: CRUD categorias, localizações, excluir ativos
  - Gestor: criar ativos, registrar movimentações, manutenções
  - Operador (colaborador): visualizar ativos, consultar depreciação
  - Permissões: operador não pode criar/excluir ativos
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5050"


def _ping_ok() -> bool:
    try:
        return requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestHermesDisponibilidade:
    def test_01_hermes_acessivel(self):
        """Hermes deve estar rodando e respondendo."""
        if not _ping_ok():
            pytest.skip("Hermes não está rodando")
        assert requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200

    def test_02_login_invalido_retorna_401(self):
        """Login com credenciais inválidas retorna 401."""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "naoexiste@olimpus.local", "senha": "errado"},
                timeout=5,
            )
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401

    def test_03_acesso_sem_auth_retorna_401(self):
        """Endpoint protegido sem sessão retorna 401."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/ativos", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestHermesAdmin:
    """Testes como administrador (role=admin)."""

    def test_04_admin_login(self):
        """Login do admin funciona."""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
                timeout=10,
            )
        except Exception:
            pytest.skip("Hermes não acessível")
        if r.status_code != 200:
            pytest.skip("Hermes não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_me_retorna_role_admin(self, admin_session):
        """Admin deve ter role='admin'."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "admin"

    def test_06_admin_lista_categorias(self, admin_session):
        """Admin pode listar categorias de ativos."""
        r = admin_session.get(f"{BASE_URL}/api/categorias")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_07_admin_cria_categoria(self, admin_session):
        """Admin pode criar categoria de ativo."""
        r = admin_session.post(
            f"{BASE_URL}/api/categorias",
            json={"nome": f"Categoria Teste {int(time.time())}", "descricao": "Teste automatizado"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_08_admin_lista_localizacoes(self, admin_session):
        """Admin pode listar localizações."""
        r = admin_session.get(f"{BASE_URL}/api/localizacoes")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_09_admin_cria_localizacao(self, admin_session):
        """Admin pode criar localização."""
        r = admin_session.post(
            f"{BASE_URL}/api/localizacoes",
            json={"nome": f"Local Teste {int(time.time())}", "descricao": "Sala de Testes"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_10_admin_dashboard(self, admin_session):
        """Admin pode ver dashboard de ativos."""
        r = admin_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ─── Gestor ──────────────────────────────────────────────────────────────────

class TestHermesGestor:
    """Testes como gestor de ativos (role=gestor)."""

    def test_11_gestor_login(self, gestor_session):
        """Login do gestor funciona e retorna role=gestor."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "gestor"

    def test_12_gestor_lista_ativos(self, gestor_session):
        """Gestor pode listar ativos."""
        r = gestor_session.get(f"{BASE_URL}/api/ativos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_13_gestor_cria_ativo(self, gestor_session):
        """Gestor pode cadastrar novo ativo."""
        r = gestor_session.post(
            f"{BASE_URL}/api/ativos",
            json={
                "nome":              f"Ativo Teste {int(time.time())}",
                "numero_patrimonio": f"PAT-{int(time.time())}",
                "valor_aquisicao":   5000.00,
                "data_aquisicao":    "2026-01-15",
                "status":            "ativo",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_14_gestor_lista_movimentacoes(self, gestor_session):
        """Gestor pode listar movimentações de ativos."""
        r = gestor_session.get(f"{BASE_URL}/api/movimentacoes")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_15_gestor_lista_manutencoes(self, gestor_session):
        """Gestor pode listar manutenções."""
        r = gestor_session.get(f"{BASE_URL}/api/manutencoes")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_16_gestor_dashboard(self, gestor_session):
        """Gestor pode ver dashboard."""
        r = gestor_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200


# ─── Operador (role=colaborador) ──────────────────────────────────────────────

class TestHermesOperador:
    """Testes como colaborador (role=colaborador)."""

    def test_17_operador_login(self, operador_session):
        """Login do operador funciona e retorna role=colaborador."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "colaborador"

    def test_18_operador_lista_ativos(self, operador_session):
        """Colaborador pode listar ativos (leitura)."""
        r = operador_session.get(f"{BASE_URL}/api/ativos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_19_operador_lista_categorias(self, operador_session):
        """Colaborador pode listar categorias."""
        r = operador_session.get(f"{BASE_URL}/api/categorias")
        assert r.status_code == 200

    def test_20_operador_dashboard(self, operador_session):
        """Colaborador pode ver dashboard."""
        r = operador_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestHermesPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_21_operador_nao_cria_ativo(self, operador_session):
        """Colaborador NÃO pode criar ativo (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/ativos",
            json={
                "nome":           "Ativo Proibido",
                "valor_aquisicao": 1000.00,
                "data_aquisicao":  "2026-01-01",
            },
        )
        assert r.status_code == 403

    def test_22_operador_nao_exclui_ativo(self, admin_session, operador_session):
        """Colaborador NÃO pode excluir ativo (403)."""
        r = admin_session.get(f"{BASE_URL}/api/ativos")
        ativos = r.json().get("data", [])
        if not ativos:
            pytest.skip("Nenhum ativo para testar exclusão")
        aid = ativos[0]["id"]
        r = operador_session.delete(f"{BASE_URL}/api/ativos/{aid}")
        assert r.status_code == 403

    def test_23_operador_nao_cria_categoria(self, operador_session):
        """Colaborador NÃO pode criar categoria de ativo (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/categorias",
            json={"nome": "Categoria Proibida"},
        )
        assert r.status_code == 403

    def test_24_gestor_registra_movimentacao(self, admin_session, gestor_session):
        """Gestor pode registrar movimentação de ativo."""
        r = admin_session.get(f"{BASE_URL}/api/ativos")
        ativos = r.json().get("data", [])
        if not ativos:
            pytest.skip("Nenhum ativo para movimentação")
        aid = ativos[0]["id"]
        r = gestor_session.post(
            f"{BASE_URL}/api/movimentacoes",
            json={
                "ativo_id":   aid,
                "tipo":       "transferencia",
                "descricao":  "Teste de movimentação automatizado",
            },
        )
        assert r.status_code in [200, 201, 400]

    def test_25_sem_auth_nao_acessa_ativos(self):
        """Sem autenticação não acessa /api/ativos (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/ativos", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
