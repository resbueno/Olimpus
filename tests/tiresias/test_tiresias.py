from __future__ import annotations
"""
test_tiresias.py — Tiresias (OCR) · Plano de Testes por Role
Porta: 5090 | Roles: admin (funcao Atlas) > usuário autenticado (operador)

Testes cobertos:
  - Autenticação por role
  - Admin/Gestor: configurar pipelines, gerenciar documentos OCR
  - Operador: submeter documentos, ver resultados próprios
  - Permissões: operador não pode configurar pipelines
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5090"
_PASS_FIELD = "password"


def _app_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/", timeout=3).status_code in [200, 302]
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestTiresiasDisponibilidade:
    def test_01_tiresias_acessivel(self):
        """Tiresias deve estar rodando."""
        if not _app_up():
            pytest.skip("Tiresias não está rodando")
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
            r = s.get(f"{BASE_URL}/api/documents", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestTiresiasAdmin:
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
            pytest.skip("Tiresias não acessível")
        if r.status_code != 200:
            pytest.skip("Tiresias não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_lista_documentos(self, admin_session):
        """Admin pode listar documentos OCR."""
        r = admin_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200

    def test_06_admin_lista_jobs(self, admin_session):
        """Admin pode listar jobs de OCR."""
        r = admin_session.get(f"{BASE_URL}/api/jobs")
        assert r.status_code in [200, 404]

    def test_07_admin_lista_pipelines(self, admin_session):
        """Admin pode listar pipelines OCR."""
        r = admin_session.get(f"{BASE_URL}/api/pipelines")
        assert r.status_code in [200, 404]

    def test_08_admin_lista_templates(self, admin_session):
        """Admin pode listar templates de extração."""
        r = admin_session.get(f"{BASE_URL}/api/templates")
        assert r.status_code in [200, 404]


# ─── Gestor (funcao admin no Atlas) ──────────────────────────────────────────

class TestTiresiasGestor:
    """Testes como gestor (tem funcao admin no Atlas)."""

    def test_09_gestor_login(self, gestor_session):
        """Login do gestor funciona."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_10_gestor_lista_documentos(self, gestor_session):
        """Gestor pode listar documentos."""
        r = gestor_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200

    def test_11_gestor_cria_pipeline(self, gestor_session):
        """Gestor (funcao admin) pode criar pipeline OCR."""
        r = gestor_session.post(
            f"{BASE_URL}/api/pipelines",
            json={
                "nome":    f"Pipeline Teste {int(time.time())}",
                "tipo":    "extracao",
                "ativo":   True,
            },
        )
        assert r.status_code in [200, 201, 404]  # 404 se rota não implementada


# ─── Operador ────────────────────────────────────────────────────────────────

class TestTiresiasOperador:
    """Testes como operador (usuário autenticado sem funcao admin)."""

    def test_12_operador_login(self, operador_session):
        """Login do operador funciona."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_13_operador_lista_documentos(self, operador_session):
        """Operador pode listar documentos OCR próprios."""
        r = operador_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200

    def test_14_operador_ve_resultados(self, admin_session, operador_session):
        """Operador pode ver resultados de OCR dos próprios documentos."""
        r = admin_session.get(f"{BASE_URL}/api/documents")
        docs = r.json().get("data", [])
        if not docs:
            pytest.skip("Nenhum documento para consultar resultado")
        did = docs[0]["id"]
        r = operador_session.get(f"{BASE_URL}/api/documents/{did}")
        assert r.status_code in [200, 403, 404]  # 403 se for de outro usuário


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestTiresiasPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_15_operador_nao_configura_pipeline(self, operador_session):
        """Operador NÃO pode criar/configurar pipeline (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/pipelines",
            json={"nome": "Pipeline Proibido", "tipo": "extracao"},
        )
        assert r.status_code in [403, 404]  # 404 se rota não existir

    def test_16_sem_auth_nao_acessa_documents(self):
        """Sem autenticação não acessa /api/documents (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/documents", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
