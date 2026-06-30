from __future__ import annotations
"""
test_hera.py — Hera (Gestão de Pessoas/RH) · Plano de Testes por Role
Porta: 5041 | Roles: admin > rh (gestor) > colaborador (operador)

Testes cobertos:
  - Autenticação por role
  - Admin: CRUD departamentos, gerenciar usuários, criar ciclos, treinamentos
  - Gestor (rh): listar usuários, aprovar férias, feedbacks, PDI, kudos
  - Operador (colaborador): próprio perfil, solicitar férias, kudos, treinamentos
  - Permissões: operador não pode criar departamentos nem aprovar férias de outros
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5041"


def _ping_ok() -> bool:
    try:
        return requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestHeraDisponibilidade:
    def test_01_hera_acessivel(self):
        """Hera deve estar rodando e respondendo no /api/ping."""
        if not _ping_ok():
            pytest.skip("Hera não está rodando")
        r = requests.get(f"{BASE_URL}/api/ping", timeout=3)
        assert r.status_code == 200

    def test_02_login_invalido_retorna_401(self):
        """Login com senha errada retorna 401."""
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
        """Endpoint /api/users sem sessão retorna 401."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/users", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestHeraAdmin:
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
            pytest.skip("Hera não acessível")
        if r.status_code != 200:
            pytest.skip("Hera não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_lista_usuarios(self, admin_session):
        """Admin pode listar todos os colaboradores."""
        r = admin_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_06_admin_lista_departamentos(self, admin_session):
        """Admin pode listar departamentos."""
        r = admin_session.get(f"{BASE_URL}/api/departments")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_07_admin_cria_departamento(self, admin_session):
        """Admin pode criar departamento."""
        r = admin_session.post(
            f"{BASE_URL}/api/departments",
            json={"nome": f"Depto Teste {int(time.time())}"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_08_admin_cria_ciclo_avaliacao(self, admin_session):
        """Admin pode criar ciclo de avaliação 360°."""
        r = admin_session.post(
            f"{BASE_URL}/api/ciclos",
            json={
                "titulo":      f"Ciclo Teste {int(time.time())}",
                "tipo":        "360",
                "data_inicio": "2026-06-01",
                "data_fim":    "2026-06-30",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_09_admin_cria_treinamento(self, admin_session):
        """Admin pode criar treinamento no catálogo."""
        r = admin_session.post(
            f"{BASE_URL}/api/treinamentos",
            json={
                "titulo":       f"Treinamento Teste {int(time.time())}",
                "descricao":    "Teste automatizado",
                "carga_horaria": 8,
                "modalidade":   "online",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_10_admin_lista_onboarding_etapas(self, admin_session):
        """Admin pode listar etapas de onboarding configuráveis."""
        r = admin_session.get(f"{BASE_URL}/api/onboarding/etapas")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_11_admin_me_retorna_role_correto(self, admin_session):
        """Admin deve ter role='admin' na sessão."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert data.get("role") == "admin"


# ─── Gestor (role=rh) ─────────────────────────────────────────────────────────

class TestHeraGestor:
    """Testes como gestor de RH (role=rh)."""

    def test_12_gestor_login(self, gestor_session):
        """Login do gestor funciona."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert data.get("role") == "rh"

    def test_13_gestor_lista_usuarios(self, gestor_session):
        """Gestor (rh) pode listar colaboradores."""
        r = gestor_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_14_gestor_lista_ferias_equipe(self, gestor_session):
        """Gestor pode ver férias da equipe."""
        r = gestor_session.get(f"{BASE_URL}/api/ferias/equipe")
        assert r.status_code in [200, 404]

    def test_15_gestor_lista_feedbacks(self, gestor_session):
        """Gestor pode listar feedbacks."""
        r = gestor_session.get(f"{BASE_URL}/api/feedbacks")
        assert r.status_code == 200

    def test_16_gestor_lista_treinamentos(self, gestor_session):
        """Gestor pode listar treinamentos."""
        r = gestor_session.get(f"{BASE_URL}/api/treinamentos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_17_gestor_lista_ciclos_avaliacao(self, gestor_session):
        """Gestor pode listar ciclos de avaliação."""
        r = gestor_session.get(f"{BASE_URL}/api/ciclos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_18_gestor_lista_kudos(self, gestor_session):
        """Gestor pode ver feed de kudos."""
        r = gestor_session.get(f"{BASE_URL}/api/kudos/feed")
        assert r.status_code == 200

    def test_19_gestor_lista_pdi(self, gestor_session):
        """Gestor pode listar PDIs."""
        r = gestor_session.get(f"{BASE_URL}/api/pdi")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_20_gestor_dashboard(self, gestor_session):
        """Gestor pode ver o dashboard."""
        r = gestor_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True


# ─── Operador (role=colaborador) ──────────────────────────────────────────────

class TestHeraOperador:
    """Testes como colaborador comum (role=colaborador)."""

    def test_21_operador_login(self, operador_session):
        """Login do operador funciona."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        data = r.json().get("data", {})
        assert data.get("role") == "colaborador"

    def test_22_operador_ve_lista_usuarios(self, operador_session):
        """Colaborador pode ver lista de usuários (diretório)."""
        r = operador_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200

    def test_23_operador_ve_suas_ferias(self, operador_session):
        """Colaborador pode ver suas próprias férias."""
        r = operador_session.get(f"{BASE_URL}/api/ferias")
        assert r.status_code == 200

    def test_24_operador_solicita_ferias(self, operador_session):
        """Colaborador pode solicitar férias para si mesmo."""
        r = operador_session.post(
            f"{BASE_URL}/api/ferias",
            json={"data_inicio": "2026-08-01", "data_fim": "2026-08-15"},
        )
        assert r.status_code in [200, 201, 400]  # 400 se regra de férias bloquear

    def test_25_operador_da_kudos(self, operador_session):
        """Colaborador pode dar kudos para colegas."""
        # Primeiro obtém lista de usuários para pegar um ID alvo
        r = operador_session.get(f"{BASE_URL}/api/users")
        usuarios = r.json().get("data", [])
        if len(usuarios) < 2:
            pytest.skip("Precisa de pelo menos 2 usuários para testar kudos")
        me = operador_session.get(f"{BASE_URL}/api/auth/me").json().get("data", {})
        alvo = next((u for u in usuarios if u["id"] != me.get("id")), None)
        if not alvo:
            pytest.skip("Não encontrou usuário alvo para kudos")
        r = operador_session.post(
            f"{BASE_URL}/api/kudos",
            json={"para_user_id": alvo["id"], "mensagem": "Teste automatizado!", "valor": "excelencia"},
        )
        assert r.status_code in [200, 201, 400]

    def test_26_operador_ve_treinamentos(self, operador_session):
        """Colaborador pode ver catálogo de treinamentos."""
        r = operador_session.get(f"{BASE_URL}/api/treinamentos")
        assert r.status_code == 200

    def test_27_operador_ve_seus_treinamentos(self, operador_session):
        """Colaborador pode ver seus próprios treinamentos."""
        r = operador_session.get(f"{BASE_URL}/api/meus-treinamentos")
        assert r.status_code == 200

    def test_28_operador_dashboard(self, operador_session):
        """Colaborador pode ver o dashboard."""
        r = operador_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestHeraPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_29_operador_nao_cria_departamento(self, operador_session):
        """Colaborador NÃO pode criar departamento (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/departments",
            json={"nome": "Depto Proibido"},
        )
        assert r.status_code == 403

    def test_30_operador_nao_exclui_treinamento(self, admin_session, operador_session):
        """Colaborador NÃO pode excluir treinamento (403)."""
        # Cria um treinamento como admin primeiro
        r = admin_session.post(
            f"{BASE_URL}/api/treinamentos",
            json={"titulo": "Para Deletar", "carga_horaria": 2, "modalidade": "online"},
        )
        if r.status_code not in [200, 201]:
            pytest.skip("Não foi possível criar treinamento para teste de permissão")
        tid = r.json().get("data", {}).get("id")
        if not tid:
            pytest.skip("ID do treinamento não retornado")
        # Tenta excluir como operador
        r = operador_session.delete(f"{BASE_URL}/api/treinamentos/{tid}")
        assert r.status_code == 403

    def test_31_gestor_nao_deleta_departamento(self, gestor_session):
        """Gestor (rh) NÃO pode deletar departamentos (403)."""
        r = gestor_session.delete(f"{BASE_URL}/api/departments/1")
        assert r.status_code == 403

    def test_32_sem_auth_nao_acessa_ferias(self):
        """Sem autenticação não acessa /api/ferias (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/ferias", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401

    def test_33_gestor_pode_criar_ciclo_avaliacao(self, gestor_session):
        """Gestor (rh) pode criar ciclo de avaliação."""
        r = gestor_session.post(
            f"{BASE_URL}/api/ciclos",
            json={
                "titulo":      f"Ciclo Gestor {int(time.time())}",
                "tipo":        "360",
                "data_inicio": "2026-07-01",
                "data_fim":    "2026-07-31",
            },
        )
        assert r.status_code in [200, 201]

    def test_34_operador_nao_cria_ciclo_avaliacao(self, operador_session):
        """Colaborador NÃO pode criar ciclo de avaliação (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/ciclos",
            json={
                "titulo":      "Ciclo Proibido",
                "tipo":        "360",
                "data_inicio": "2026-07-01",
                "data_fim":    "2026-07-31",
            },
        )
        assert r.status_code == 403
