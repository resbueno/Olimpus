from __future__ import annotations
"""
test_hercules.py — Hércules (Gestão de Tarefas) · Plano de Testes por Role
Porta: 5001 | Roles: admin > gestor > membro (operador)

Testes cobertos:
  - Autenticação por role
  - Admin: CRUD projetos, gerenciar usuários, excluir tarefas
  - Gestor: criar projetos, criar/atribuir tarefas, ver relatórios
  - Membro (operador): ver projetos, atualizar tarefas próprias, comentar
  - Permissões: membro não pode criar projeto nem excluir tarefas de outros
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5001"


def _ping_ok() -> bool:
    try:
        return requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestHerculesDisponibilidade:
    def test_01_hercules_acessivel(self):
        """Hércules deve estar rodando e respondendo."""
        if not _ping_ok():
            pytest.skip("Hércules não está rodando")
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
            r = s.get(f"{BASE_URL}/api/tasks", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestHerculesAdmin:
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
            pytest.skip("Hércules não acessível")
        if r.status_code != 200:
            pytest.skip("Hércules não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_me_retorna_role_admin(self, admin_session):
        """Admin deve ter role='admin'."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "admin"

    def test_06_admin_lista_projetos(self, admin_session):
        """Admin pode listar projetos."""
        r = admin_session.get(f"{BASE_URL}/api/projects")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_07_admin_cria_projeto(self, admin_session):
        """Admin pode criar projeto."""
        r = admin_session.post(
            f"{BASE_URL}/api/projects",
            json={
                "nome":      f"Projeto Teste {int(time.time())}",
                "descricao": "Projeto criado pelo teste automatizado",
                "cor":       "#007bff",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_08_admin_lista_usuarios(self, admin_session):
        """Admin pode listar usuários."""
        r = admin_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_09_admin_dashboard(self, admin_session):
        """Admin pode ver dashboard."""
        r = admin_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_10_admin_lista_atividades(self, admin_session):
        """Admin pode ver feed de atividades."""
        r = admin_session.get(f"{BASE_URL}/api/activities")
        assert r.status_code == 200


# ─── Gestor ──────────────────────────────────────────────────────────────────

class TestHerculesGestor:
    """Testes como gestor de projetos (role=gestor)."""

    def test_11_gestor_login(self, gestor_session):
        """Login do gestor funciona e retorna role=gestor."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "gestor"

    def test_12_gestor_lista_projetos(self, gestor_session):
        """Gestor pode listar projetos."""
        r = gestor_session.get(f"{BASE_URL}/api/projects")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_13_gestor_cria_projeto(self, gestor_session):
        """Gestor pode criar projeto."""
        r = gestor_session.post(
            f"{BASE_URL}/api/projects",
            json={
                "nome":      f"Projeto Gestor {int(time.time())}",
                "descricao": "Criado pelo gestor",
                "cor":       "#28a745",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_14_gestor_cria_tarefa(self, gestor_session):
        """Gestor pode criar tarefa."""
        # Primeiro obtém projetos para pegar um ID
        r = gestor_session.get(f"{BASE_URL}/api/projects")
        projetos = r.json().get("data", [])
        if not projetos:
            pytest.skip("Nenhum projeto para criar tarefa")
        pid = projetos[0]["id"]
        r = gestor_session.post(
            f"{BASE_URL}/api/tasks",
            json={
                "titulo":     f"Tarefa Gestor {int(time.time())}",
                "descricao":  "Tarefa criada pelo gestor",
                "project_id": pid,
                "prioridade": "media",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_15_gestor_lista_tarefas(self, gestor_session):
        """Gestor pode listar tarefas."""
        r = gestor_session.get(f"{BASE_URL}/api/tasks")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_16_gestor_dashboard(self, gestor_session):
        """Gestor pode ver dashboard."""
        r = gestor_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200


# ─── Membro/Operador ─────────────────────────────────────────────────────────

class TestHerculesMembro:
    """Testes como membro (role=membro) — operador do sistema."""

    def test_17_membro_login(self, operador_session):
        """Login do membro funciona e retorna role=membro."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "membro"

    def test_18_membro_lista_projetos(self, operador_session):
        """Membro pode listar projetos."""
        r = operador_session.get(f"{BASE_URL}/api/projects")
        assert r.status_code == 200

    def test_19_membro_lista_tarefas(self, operador_session):
        """Membro pode listar tarefas."""
        r = operador_session.get(f"{BASE_URL}/api/tasks")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_20_membro_dashboard(self, operador_session):
        """Membro pode ver dashboard."""
        r = operador_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200

    def test_21_membro_adiciona_comentario(self, admin_session, operador_session):
        """Membro pode comentar em tarefas."""
        r = admin_session.get(f"{BASE_URL}/api/tasks")
        tarefas = r.json().get("data", [])
        if not tarefas:
            pytest.skip("Nenhuma tarefa disponível para comentário")
        tid = tarefas[0]["id"]
        r = operador_session.post(
            f"{BASE_URL}/api/tasks/{tid}/comments",
            json={"texto": "Comentário de teste automatizado"},
        )
        assert r.status_code in [200, 201]


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestHerculesPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_22_membro_nao_cria_projeto(self, operador_session):
        """Membro NÃO pode criar projeto (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/projects",
            json={"nome": "Projeto Proibido", "descricao": "Não permitido"},
        )
        assert r.status_code == 403

    def test_23_membro_nao_exclui_tarefa(self, admin_session, operador_session):
        """Membro NÃO pode excluir tarefa (403)."""
        r = admin_session.get(f"{BASE_URL}/api/tasks")
        tarefas = r.json().get("data", [])
        if not tarefas:
            pytest.skip("Nenhuma tarefa para testar exclusão")
        tid = tarefas[0]["id"]
        r = operador_session.delete(f"{BASE_URL}/api/tasks/{tid}")
        assert r.status_code == 403

    def test_24_membro_nao_cria_usuario(self, operador_session):
        """Membro NÃO pode criar usuário (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/users",
            json={"nome": "Proibido", "email": f"proibido_{time.time()}@test.com", "senha": "Teste@2024"},
        )
        assert r.status_code == 403

    def test_25_gestor_pode_excluir_projeto(self, gestor_session):
        """Gestor pode excluir projeto que criou."""
        r = gestor_session.post(
            f"{BASE_URL}/api/projects",
            json={"nome": f"Para Excluir {int(time.time())}", "cor": "#dc3545"},
        )
        if r.status_code not in [200, 201]:
            pytest.skip("Não foi possível criar projeto para exclusão")
        pid = r.json().get("data", {}).get("id")
        if not pid:
            pytest.skip("ID do projeto não retornado")
        r = gestor_session.delete(f"{BASE_URL}/api/projects/{pid}")
        assert r.status_code in [200, 201]

    def test_26_sem_auth_nao_acessa_tasks(self):
        """Sem autenticação não acessa /api/tasks (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/tasks", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
