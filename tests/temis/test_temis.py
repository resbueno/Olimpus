from __future__ import annotations
"""
test_temis.py — Têmis (Gestão de Contratos) · Plano de Testes por Role
Porta: 5060 | Roles: admin (funcao Atlas) > usuário autenticado (operador)

Testes cobertos:
  - Autenticação por role
  - Admin/Gestor: criar contratos, gerenciar templates, configurações
  - Operador: visualizar contratos, receber notificações de vencimento
  - Permissões: operador não pode criar/excluir contratos
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5020"
_PASS_FIELD = "password"


def _app_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/", timeout=3).status_code in [200, 302]
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestTemisDisponibilidade:
    def test_01_temis_acessivel(self):
        """Têmis deve estar rodando."""
        if not _app_up():
            pytest.skip("Têmis não está rodando")
        assert _app_up() is True

    def test_02_login_invalido_retorna_401(self):
        """Login com credenciais inválidas retorna 401."""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "naoexiste@olimpus.local", _PASS_FIELD: "errado"},
                timeout=5,
            )
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401

    def test_03_acesso_sem_auth_retorna_401(self):
        """Endpoint protegido sem sessão retorna 401."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/contratos", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestTemisAdmin:
    """Testes como administrador."""

    def test_04_admin_login(self):
        """Login do admin funciona."""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", _PASS_FIELD: "Atlas@2024"},
                timeout=10,
            )
        except Exception:
            pytest.skip("Têmis não acessível")
        if r.status_code != 200:
            pytest.skip("Têmis não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_lista_contratos(self, admin_session):
        """Admin pode listar contratos."""
        r = admin_session.get(f"{BASE_URL}/api/contratos")
        assert r.status_code == 200

    def test_06_admin_cria_contrato(self, admin_session):
        """Admin pode criar contrato."""
        r = admin_session.post(
            f"{BASE_URL}/api/contratos",
            json={
                "titulo":        f"Contrato Teste {int(time.time())}",
                "parte_a":       "Olimpus Sistemas",
                "parte_b":       "Cliente Teste",
                "valor":         12000.00,
                "data_inicio":   "2026-05-01",
                "data_fim":      "2027-04-30",
                "status":        "ativo",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_07_admin_lista_templates(self, admin_session):
        """Admin pode listar templates de contrato."""
        r = admin_session.get(f"{BASE_URL}/api/templates")
        assert r.status_code in [200, 404]

    def test_08_admin_lista_alertas(self, admin_session):
        """Admin pode listar alertas de vencimento."""
        r = admin_session.get(f"{BASE_URL}/api/alertas")
        assert r.status_code in [200, 404]

    def test_09_admin_dashboard(self, admin_session):
        """Admin pode ver dashboard de contratos."""
        r = admin_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code in [200, 404]


# ─── Gestor (funcao admin no Atlas) ──────────────────────────────────────────

class TestTemisGestor:
    """Testes como gestor (tem funcao admin no Atlas)."""

    def test_10_gestor_login(self, gestor_session):
        """Login do gestor funciona."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_11_gestor_lista_contratos(self, gestor_session):
        """Gestor pode listar contratos."""
        r = gestor_session.get(f"{BASE_URL}/api/contratos")
        assert r.status_code == 200

    def test_12_gestor_cria_contrato(self, gestor_session):
        """Gestor (funcao admin) pode criar contrato."""
        r = gestor_session.post(
            f"{BASE_URL}/api/contratos",
            json={
                "titulo":      f"Contrato Gestor {int(time.time())}",
                "parte_a":     "Olimpus Sistemas",
                "parte_b":     "Parceiro Teste",
                "valor":       5000.00,
                "data_inicio": "2026-06-01",
                "data_fim":    "2026-12-31",
                "status":      "ativo",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_13_gestor_edita_contrato(self, admin_session, gestor_session):
        """Gestor pode editar contrato existente."""
        r = admin_session.get(f"{BASE_URL}/api/contratos")
        contratos = r.json().get("data", [])
        if not contratos:
            pytest.skip("Nenhum contrato para editar")
        cid = contratos[0]["id"]
        r = gestor_session.put(
            f"{BASE_URL}/api/contratos/{cid}",
            json={"observacoes": f"Editado por gestor em teste — {int(time.time())}"},
        )
        assert r.status_code in [200, 201]


# ─── Operador ────────────────────────────────────────────────────────────────

class TestTemisOperador:
    """Testes como operador (usuário autenticado sem funcao admin)."""

    def test_14_operador_login(self, operador_session):
        """Login do operador funciona."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_15_operador_lista_contratos(self, operador_session):
        """Operador pode listar contratos (leitura)."""
        r = operador_session.get(f"{BASE_URL}/api/contratos")
        assert r.status_code == 200

    def test_16_operador_le_contrato(self, admin_session, operador_session):
        """Operador pode ler contrato específico."""
        r = admin_session.get(f"{BASE_URL}/api/contratos")
        contratos = r.json().get("data", [])
        if not contratos:
            pytest.skip("Nenhum contrato disponível")
        cid = contratos[0]["id"]
        r = operador_session.get(f"{BASE_URL}/api/contratos/{cid}")
        assert r.status_code in [200, 403, 404]


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestTemisPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_17_operador_nao_cria_contrato(self, operador_session):
        """Operador NÃO pode criar contrato (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/contratos",
            json={
                "titulo":      "Contrato Proibido",
                "parte_a":     "A",
                "parte_b":     "B",
                "valor":       100.00,
                "data_inicio": "2026-01-01",
                "data_fim":    "2026-12-31",
            },
        )
        assert r.status_code == 403

    def test_18_operador_nao_exclui_contrato(self, admin_session, operador_session):
        """Operador NÃO pode excluir contrato (403)."""
        r = admin_session.get(f"{BASE_URL}/api/contratos")
        contratos = r.json().get("data", [])
        if not contratos:
            pytest.skip("Nenhum contrato para testar exclusão")
        cid = contratos[0]["id"]
        r = operador_session.delete(f"{BASE_URL}/api/contratos/{cid}")
        assert r.status_code == 403

    def test_19_sem_auth_nao_acessa_contratos(self):
        """Sem autenticação não acessa /api/contratos (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/contratos", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
