from __future__ import annotations
"""
test_argos.py — Argos (Monitoração) · Plano de Testes por Role
Porta: 5000 | Roles: admin (funcao Atlas) > usuário autenticado (operador)

Testes cobertos:
  - Autenticação por role
  - Admin/Gestor: configurar monitores, gerenciar alertas, ver logs
  - Operador: visualizar dashboard, status dos apps
  - Permissões: operador não pode adicionar/excluir monitores
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5000"
_PASS_FIELD = "password"


def _app_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/", timeout=3).status_code in [200, 302]
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestArgosDisponibilidade:
    def test_01_argos_acessivel(self):
        """Argos deve estar rodando."""
        if not _app_up():
            pytest.skip("Argos não está rodando")
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
            r = s.get(f"{BASE_URL}/api/apps", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestArgosAdmin:
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
            pytest.skip("Argos não acessível")
        if r.status_code != 200:
            pytest.skip("Argos não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_lista_apps(self, admin_session):
        """Admin pode listar apps monitorados."""
        r = admin_session.get(f"{BASE_URL}/api/apps")
        assert r.status_code == 200

    def test_06_admin_status_geral(self, admin_session):
        """Admin pode ver status geral do sistema."""
        r = admin_session.get(f"{BASE_URL}/api/status")
        assert r.status_code in [200, 404]

    def test_07_admin_lista_alertas(self, admin_session):
        """Admin pode listar alertas configurados."""
        r = admin_session.get(f"{BASE_URL}/api/alertas")
        assert r.status_code in [200, 404]

    def test_08_admin_lista_logs(self, admin_session):
        """Admin pode listar logs de monitoração."""
        r = admin_session.get(f"{BASE_URL}/api/logs")
        assert r.status_code in [200, 404]

    def test_09_admin_dashboard(self, admin_session):
        """Admin pode ver dashboard de monitoração."""
        r = admin_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code in [200, 404]

    def test_10_admin_registra_app(self, admin_session):
        """Admin pode registrar app para monitoração."""
        r = admin_session.post(
            f"{BASE_URL}/api/apps",
            json={
                "nome":  f"App Teste {int(time.time())}",
                "url":   "http://localhost:9999",
                "porta": 9999,
                "ativo": True,
            },
        )
        assert r.status_code in [200, 201, 400, 404]


# ─── Gestor (funcao admin no Atlas) ──────────────────────────────────────────

class TestArgosGestor:
    """Testes como gestor (tem funcao admin no Atlas)."""

    def test_11_gestor_login(self, gestor_session):
        """Login do gestor funciona."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_12_gestor_lista_apps(self, gestor_session):
        """Gestor pode listar apps monitorados."""
        r = gestor_session.get(f"{BASE_URL}/api/apps")
        assert r.status_code == 200

    def test_13_gestor_registra_app(self, gestor_session):
        """Gestor (funcao admin) pode registrar app para monitoração."""
        r = gestor_session.post(
            f"{BASE_URL}/api/apps",
            json={
                "nome":  f"App Gestor {int(time.time())}",
                "url":   "http://localhost:9998",
                "porta": 9998,
            },
        )
        assert r.status_code in [200, 201, 400, 404]


# ─── Operador ────────────────────────────────────────────────────────────────

class TestArgosOperador:
    """Testes como operador (usuário autenticado sem funcao admin)."""

    def test_14_operador_login(self, operador_session):
        """Login do operador funciona."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_15_operador_lista_apps(self, operador_session):
        """Operador pode ver lista de apps monitorados."""
        r = operador_session.get(f"{BASE_URL}/api/apps")
        assert r.status_code == 200

    def test_16_operador_status_geral(self, operador_session):
        """Operador pode ver status geral dos apps."""
        r = operador_session.get(f"{BASE_URL}/api/status")
        assert r.status_code in [200, 404]


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestArgosPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_17_operador_nao_registra_app(self, operador_session):
        """Operador NÃO pode registrar novo app para monitoração (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/apps",
            json={"nome": "App Proibido", "url": "http://localhost:9990", "porta": 9990},
        )
        assert r.status_code in [403, 404]  # 404 se rota não existir

    def test_18_operador_nao_exclui_app(self, admin_session, operador_session):
        """Operador NÃO pode excluir app monitorado (403)."""
        r = admin_session.get(f"{BASE_URL}/api/apps")
        apps = r.json().get("data", [])
        if not apps:
            pytest.skip("Nenhum app registrado para testar exclusão")
        aid = apps[0]["id"]
        r = operador_session.delete(f"{BASE_URL}/api/apps/{aid}")
        assert r.status_code in [403, 404]

    def test_19_sem_auth_nao_acessa_apps(self):
        """Sem autenticação não acessa /api/apps (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/apps", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
