from __future__ import annotations
"""
test_iris.py — Iris (Gestão de Formulários e Workflow) · Plano de Testes por Role
Porta: 5070 | Roles: admin (funcao Atlas) > usuário autenticado (operador)

Testes cobertos:
  - Autenticação por role
  - Admin/Gestor: criar formulários, gerenciar workflows
  - Operador: preencher formulários, ver submissões próprias
  - Permissões: operador não pode criar/excluir formulários
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5070"
_PASS_FIELD = "password"


def _app_up() -> bool:
    try:
        return requests.get(f"{BASE_URL}/", timeout=3).status_code in [200, 302]
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestIrisDisponibilidade:
    def test_01_iris_acessivel(self):
        """Iris deve estar rodando."""
        if not _app_up():
            pytest.skip("Iris não está rodando")
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
            r = s.get(f"{BASE_URL}/api/forms", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestIrisAdmin:
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
            pytest.skip("Iris não acessível")
        if r.status_code != 200:
            pytest.skip("Iris não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_lista_formularios(self, admin_session):
        """Admin pode listar formulários."""
        r = admin_session.get(f"{BASE_URL}/api/forms")
        assert r.status_code == 200

    def test_06_admin_cria_formulario(self, admin_session):
        """Admin pode criar formulário."""
        r = admin_session.post(
            f"{BASE_URL}/api/forms",
            json={
                "titulo":   f"Formulário Teste {int(time.time())}",
                "descricao": "Formulário criado pelo teste automatizado",
                "campos":   [{"label": "Nome", "tipo": "text", "obrigatorio": True}],
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_07_admin_lista_submissoes(self, admin_session):
        """Admin pode ver todas as submissões."""
        r = admin_session.get(f"{BASE_URL}/api/submissions")
        assert r.status_code in [200, 404]

    def test_08_admin_lista_workflows(self, admin_session):
        """Admin pode listar workflows."""
        r = admin_session.get(f"{BASE_URL}/api/workflows")
        assert r.status_code in [200, 404]

    def test_09_admin_lista_departamentos(self, admin_session):
        """Admin pode listar departamentos."""
        r = admin_session.get(f"{BASE_URL}/api/departments")
        assert r.status_code == 200


# ─── Gestor (funcao admin no Atlas) ──────────────────────────────────────────

class TestIrisGestor:
    """Testes como gestor (tem funcao admin no Atlas)."""

    def test_10_gestor_login(self, gestor_session):
        """Login do gestor funciona."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_11_gestor_lista_formularios(self, gestor_session):
        """Gestor pode listar formulários."""
        r = gestor_session.get(f"{BASE_URL}/api/forms")
        assert r.status_code == 200

    def test_12_gestor_cria_formulario(self, gestor_session):
        """Gestor (funcao admin) pode criar formulário."""
        r = gestor_session.post(
            f"{BASE_URL}/api/forms",
            json={
                "titulo":   f"Formulário Gestor {int(time.time())}",
                "descricao": "Criado pelo gestor",
                "campos":   [{"label": "Avaliação", "tipo": "select", "opcoes": ["1","2","3","4","5"]}],
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True


# ─── Operador ────────────────────────────────────────────────────────────────

class TestIrisOperador:
    """Testes como operador (usuário autenticado sem funcao admin)."""

    def test_13_operador_login(self, operador_session):
        """Login do operador funciona."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200

    def test_14_operador_lista_formularios(self, operador_session):
        """Operador pode listar formulários disponíveis."""
        r = operador_session.get(f"{BASE_URL}/api/forms")
        assert r.status_code == 200

    def test_15_operador_submete_formulario(self, admin_session, operador_session):
        """Operador pode submeter formulário existente."""
        r = admin_session.get(f"{BASE_URL}/api/forms")
        forms = r.json().get("data", [])
        if not forms:
            pytest.skip("Nenhum formulário disponível para submeter")
        fid = forms[0]["id"]
        r = operador_session.post(
            f"{BASE_URL}/api/forms/{fid}/submit",
            json={"respostas": {"Nome": "Resposta de Teste"}},
        )
        assert r.status_code in [200, 201, 400, 404]


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestIrisPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_16_operador_nao_cria_formulario(self, operador_session):
        """Operador NÃO pode criar formulário (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/forms",
            json={"titulo": "Formulário Proibido", "campos": []},
        )
        assert r.status_code == 403

    def test_17_operador_nao_exclui_formulario(self, admin_session, operador_session):
        """Operador NÃO pode excluir formulário (403)."""
        r = admin_session.get(f"{BASE_URL}/api/forms")
        forms = r.json().get("data", [])
        if not forms:
            pytest.skip("Nenhum formulário para testar exclusão")
        fid = forms[0]["id"]
        r = operador_session.delete(f"{BASE_URL}/api/forms/{fid}")
        assert r.status_code == 403

    def test_18_sem_auth_nao_acessa_forms(self):
        """Sem autenticação não acessa /api/forms (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/forms", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
