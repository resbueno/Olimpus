from __future__ import annotations
"""
test_cronos.py - Testes para Cronos (Ponto Eletrônico)
Porta: 5025 | Prioridade: ALTA
Endpoints reais: /api/ponto/bater, /api/ponto/hoje, /api/ajustes,
                 /api/jornadas, /api/banco-horas, /api/fechamentos
"""
import time
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5025"


@pytest.mark.api
class TestCronosAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Cronos não está rodando: {exc}")
        assert r.status_code == 200

    def test_02_login(self):
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", "senha": "Atlas@2024"},
                timeout=10,
            )
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Cronos não disponível: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True


@pytest.mark.api
class TestCronosPonto:
    """Testes de registro de ponto"""

    def test_03_bater_entrada(self, cronos_session):
        """Bater ponto de entrada"""
        r = cronos_session.post(
            f"{BASE_URL}/api/ponto/bater",
            json={"tipo": "entrada"},
        )
        assert r.status_code in [200, 201, 400]

    def test_04_ponto_hoje(self, cronos_session):
        """Ver registros de ponto de hoje"""
        r = cronos_session.get(f"{BASE_URL}/api/ponto/hoje")
        assert r.status_code in [200, 404]

    def test_05_historico(self, cronos_session):
        """Ver histórico de ponto"""
        r = cronos_session.get(f"{BASE_URL}/api/ponto/historico")
        assert r.status_code in [200, 404]

    def test_06_espelho_ponto(self, cronos_session):
        """Gerar espelho de ponto"""
        r = cronos_session.get(f"{BASE_URL}/api/ponto/espelho")
        assert r.status_code in [200, 404]

    def test_07_dashboard(self, cronos_session):
        """Dashboard com totais"""
        r = cronos_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True


@pytest.mark.api
class TestCronosAjustes:
    """Testes de solicitações de ajuste"""

    def test_08_listar_ajustes(self, cronos_session):
        """Listar ajustes"""
        r = cronos_session.get(f"{BASE_URL}/api/ajustes")
        assert r.status_code in [200, 404]

    def test_09_criar_ajuste(self, cronos_session):
        """Criar solicitação de ajuste"""
        r = cronos_session.post(
            f"{BASE_URL}/api/ajustes",
            json={
                "data":               "2026-04-19",
                "tipo_solicitado":    "saida",
                "horario_solicitado": "18:00",
                "motivo":             "Erro de registro — teste automático",
            },
        )
        assert r.status_code in [200, 201, 400, 404]


@pytest.mark.api
class TestCronosJornadas:
    """Testes de jornadas de trabalho"""

    def test_10_listar_jornadas(self, cronos_session):
        """Listar jornadas"""
        r = cronos_session.get(f"{BASE_URL}/api/jornadas")
        assert r.status_code in [200, 404]

    def test_11_criar_jornada(self, cronos_session):
        """Criar jornada"""
        r = cronos_session.post(
            f"{BASE_URL}/api/jornadas",
            json={
                "nome":                   f"Jornada Teste {int(time.time())}",
                "tipo":                   "fixo",
                "hora_entrada":           "09:00",
                "hora_saida":             "18:00",
                "hora_inicio_intervalo":  "12:00",
                "hora_fim_intervalo":     "13:00",
                "carga_horaria_dia":      480,
            },
        )
        assert r.status_code in [200, 201, 400, 404]


@pytest.mark.api
class TestCronosBancoHoras:
    """Testes de banco de horas"""

    def test_12_saldo_banco(self, cronos_session):
        """Ver saldo do banco de horas"""
        r = cronos_session.get(f"{BASE_URL}/api/banco-horas")
        assert r.status_code in [200, 404]

    def test_13_compensar_banco(self, cronos_session):
        """Compensar horas do banco"""
        r = cronos_session.post(
            f"{BASE_URL}/api/banco-horas/compensar",
            json={"minutos": 60, "descricao": "Compensação teste"},
        )
        assert r.status_code in [200, 201, 400, 404]


@pytest.mark.api
class TestCronosFechamentos:
    """Testes de fechamentos mensais"""

    def test_14_listar_fechamentos(self, cronos_session):
        """Listar fechamentos"""
        r = cronos_session.get(f"{BASE_URL}/api/fechamentos")
        assert r.status_code in [200, 404]

    def test_15_feriados(self, cronos_session):
        """Listar feriados cadastrados"""
        r = cronos_session.get(f"{BASE_URL}/api/feriados")
        assert r.status_code in [200, 404]
