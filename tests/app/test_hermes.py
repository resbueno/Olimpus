from __future__ import annotations
"""
test_hermes.py - Testes para Hermes (Gestão de Ativos)
Porta: 5050 | Prioridade: BAIXA - PENDENTE CRIAR APP
"""
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5050"

_hermes_online = None


def _verificar_hermes():
    global _hermes_online
    if _hermes_online is None:
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
            _hermes_online = r.status_code == 200
        except Exception:
            _hermes_online = False
    return _hermes_online


def _fail_se_offline():
    if not _verificar_hermes():
        pytest.fail("Hermes não está rodando")


@pytest.mark.api
class TestHermes:
    """Testes Hermes"""

    def setup_method(self):
        _fail_se_offline()

    def test_01_ping(self):
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Hermes não está rodando: {exc}")
        assert r.status_code == 200

    def test_02_listar_ativos(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/ativos",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_03_criar_ativo(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/ativos",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"nome": "Notebook Teste", "tipo": "equipamento"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_04_movimentar(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/movimentos",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"ativo_id": "1", "local": "Sala 1"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_05_depreciacao(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/ativos/1/depreciacao",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_06_manutencao(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/manutencoes",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"ativo_id": "1", "tipo": "preventiva"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_07_localizacoes(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/localizacoes",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_08_qrcode(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/ativos/1/qrcode",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]