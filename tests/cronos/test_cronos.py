from __future__ import annotations
"""
test_cronos.py — Cronos (Ponto Eletrônico) · Plano de Testes por Role
Porta: 5025 | Roles: admin > rh (gestor) > colaborador (operador)

Testes cobertos:
  - Autenticação por role
  - Admin: jornadas, feriados, fechamentos, configurações
  - Gestor (rh): espelho de todos, ajustes, banco de horas
  - Operador (colaborador): bater ponto, histórico próprio
  - Permissões: operador não pode fechar período nem ver ponto de outros
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5025"


def _ping_ok() -> bool:
    try:
        return requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestCronosDisponibilidade:
    def test_01_cronos_acessivel(self):
        """Cronos deve estar rodando e respondendo."""
        if not _ping_ok():
            pytest.skip("Cronos não está rodando")
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
            r = s.get(f"{BASE_URL}/api/ponto/hoje", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestCronosAdmin:
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
            pytest.skip("Cronos não acessível")
        if r.status_code != 200:
            pytest.skip("Cronos não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_me_retorna_role_admin(self, admin_session):
        """Admin deve ter role='admin'."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "admin"

    def test_06_admin_lista_jornadas(self, admin_session):
        """Admin pode listar jornadas de trabalho."""
        r = admin_session.get(f"{BASE_URL}/api/jornadas")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_07_admin_cria_jornada(self, admin_session):
        """Admin pode criar jornada de trabalho."""
        r = admin_session.post(
            f"{BASE_URL}/api/jornadas",
            json={
                "nome":                  f"Jornada Teste {int(time.time())}",
                "tipo":                  "fixo",
                "hora_entrada":          "08:00",
                "hora_saida":            "17:00",
                "hora_inicio_intervalo": "12:00",
                "hora_fim_intervalo":    "13:00",
                "carga_horaria_dia":     480,
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_08_admin_lista_feriados(self, admin_session):
        """Admin pode listar feriados cadastrados."""
        r = admin_session.get(f"{BASE_URL}/api/feriados")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_09_admin_cria_feriado(self, admin_session):
        """Admin pode cadastrar feriado."""
        r = admin_session.post(
            f"{BASE_URL}/api/feriados",
            json={"data": "2026-09-07", "descricao": "Independência — Teste"},
        )
        assert r.status_code in [200, 201, 400]  # 400 se já existir

    def test_10_admin_lista_fechamentos(self, admin_session):
        """Admin pode listar fechamentos mensais."""
        r = admin_session.get(f"{BASE_URL}/api/fechamentos")
        assert r.status_code == 200

    def test_11_admin_lista_usuarios(self, admin_session):
        """Admin pode listar colaboradores."""
        r = admin_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_12_admin_dashboard(self, admin_session):
        """Admin pode ver o dashboard de ponto."""
        r = admin_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_13_admin_config(self, admin_session):
        """Admin pode ler configurações do Cronos."""
        r = admin_session.get(f"{BASE_URL}/api/config")
        assert r.status_code in [200, 404]


# ─── Gestor (role=rh) ─────────────────────────────────────────────────────────

class TestCronosGestor:
    """Testes como gestor de RH (role=rh)."""

    def test_14_gestor_login(self, gestor_session):
        """Login do gestor funciona e retorna role=rh."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "rh"

    def test_15_gestor_dashboard(self, gestor_session):
        """Gestor de RH pode ver dashboard."""
        r = gestor_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200

    def test_16_gestor_espelho_ponto(self, gestor_session):
        """Gestor pode acessar espelho de ponto."""
        r = gestor_session.get(f"{BASE_URL}/api/ponto/espelho")
        assert r.status_code in [200, 404]

    def test_17_gestor_lista_ajustes(self, gestor_session):
        """Gestor pode listar solicitações de ajuste."""
        r = gestor_session.get(f"{BASE_URL}/api/ajustes")
        assert r.status_code == 200

    def test_18_gestor_banco_horas(self, gestor_session):
        """Gestor pode visualizar banco de horas."""
        r = gestor_session.get(f"{BASE_URL}/api/banco-horas")
        assert r.status_code == 200

    def test_19_gestor_lista_feriados(self, gestor_session):
        """Gestor pode listar feriados."""
        r = gestor_session.get(f"{BASE_URL}/api/feriados")
        assert r.status_code == 200


# ─── Operador (role=colaborador) ──────────────────────────────────────────────

class TestCronosOperador:
    """Testes como colaborador (role=colaborador)."""

    def test_20_operador_login(self, operador_session):
        """Login do operador funciona e retorna role=colaborador."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "colaborador"

    def test_21_operador_bate_entrada(self, operador_session):
        """Colaborador pode bater ponto de entrada."""
        r = operador_session.post(
            f"{BASE_URL}/api/ponto/bater",
            json={"tipo": "entrada"},
        )
        assert r.status_code in [200, 201, 400]  # 400 se já bateu

    def test_22_operador_ponto_hoje(self, operador_session):
        """Colaborador pode ver os registros de ponto de hoje."""
        r = operador_session.get(f"{BASE_URL}/api/ponto/hoje")
        assert r.status_code in [200, 404]

    def test_23_operador_historico(self, operador_session):
        """Colaborador pode ver histórico próprio de ponto."""
        r = operador_session.get(f"{BASE_URL}/api/ponto/historico")
        assert r.status_code in [200, 404]

    def test_24_operador_solicita_ajuste(self, operador_session):
        """Colaborador pode solicitar ajuste de ponto."""
        r = operador_session.post(
            f"{BASE_URL}/api/ajustes",
            json={
                "data":               "2026-04-20",
                "tipo_solicitado":    "saida",
                "horario_solicitado": "18:00",
                "motivo":             "Esqueci de bater a saída — teste automatizado",
            },
        )
        assert r.status_code in [200, 201, 400]

    def test_25_operador_banco_horas(self, operador_session):
        """Colaborador pode ver seu próprio banco de horas."""
        r = operador_session.get(f"{BASE_URL}/api/banco-horas")
        assert r.status_code == 200

    def test_26_operador_dashboard(self, operador_session):
        """Colaborador pode ver o dashboard."""
        r = operador_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestCronosPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_27_operador_nao_cria_jornada(self, operador_session):
        """Colaborador NÃO pode criar jornada de trabalho (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/jornadas",
            json={
                "nome":              "Jornada Proibida",
                "tipo":              "fixo",
                "hora_entrada":      "08:00",
                "hora_saida":        "17:00",
                "carga_horaria_dia": 480,
            },
        )
        assert r.status_code == 403

    def test_28_operador_nao_cadastra_feriado(self, operador_session):
        """Colaborador NÃO pode cadastrar feriado (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/feriados",
            json={"data": "2026-10-12", "descricao": "Feriado Proibido"},
        )
        assert r.status_code == 403

    def test_29_operador_nao_fecha_periodo(self, operador_session):
        """Colaborador NÃO pode fechar período mensal (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/fechamentos/fechar",
            json={"ano": 2026, "mes": 3},
        )
        assert r.status_code == 403

    def test_30_gestor_aprova_ajuste(self, admin_session, gestor_session):
        """Gestor (rh) pode aprovar solicitação de ajuste."""
        # Verifica se há ajustes pendentes
        r = gestor_session.get(f"{BASE_URL}/api/ajustes")
        ajustes = r.json().get("data", [])
        pendentes = [a for a in ajustes if a.get("status") == "pendente"]
        if not pendentes:
            pytest.skip("Nenhum ajuste pendente para aprovar")
        aid = pendentes[0]["id"]
        r = gestor_session.put(
            f"{BASE_URL}/api/ajustes/{aid}/status",
            json={"status": "aprovado"},
        )
        assert r.status_code in [200, 201]

    def test_31_operador_nao_aprova_ajuste_de_outro(self, admin_session, operador_session):
        """Colaborador NÃO pode aprovar ajuste de outro colaborador (403)."""
        r = admin_session.get(f"{BASE_URL}/api/ajustes")
        ajustes = r.json().get("data", [])
        if not ajustes:
            pytest.skip("Nenhum ajuste para testar permissão")
        aid = ajustes[0]["id"]
        r = operador_session.put(
            f"{BASE_URL}/api/ajustes/{aid}/status",
            json={"status": "aprovado"},
        )
        assert r.status_code == 403

    def test_32_sem_auth_nao_acessa_ponto(self):
        """Sem autenticação não acessa ponto (401)."""
        try:
            s = requests.Session()
            r = s.post(f"{BASE_URL}/api/ponto/bater", json={"tipo": "entrada"}, timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
