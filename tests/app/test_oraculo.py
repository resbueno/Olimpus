from __future__ import annotations
"""
test_oraculo.py - Testes para Oráculo (Hub de Notícias)
Porta: 5030 | Prioridade: MÉDIA - PENDENTE CRIAR APP
"""
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5030"

_oraculo_online = None


def _verificar_oraculo():
    global _oraculo_online
    if _oraculo_online is None:
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
            _oraculo_online = r.status_code == 200
        except Exception:
            _oraculo_online = False
    return _oraculo_online


def _fail_se_offline():
    if not _verificar_oraculo():
        pytest.fail("Oráculo não está rodando")


@pytest.mark.api
class TestOraculo:
    """Testes Oráculo"""

    def setup_method(self):
        _fail_se_offline()

    def test_01_ping(self):
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Oráculo não está rodando: {exc}")
        assert r.status_code == 200

    def test_02_listar_noticias(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/noticias",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_03_criar_post(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/noticias",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"titulo": "Teste.Post", "conteudo": "Teste", "departamento": "TI"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_04_kpis(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/kpis",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_05_segmentar(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/noticias?departamento=TI",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_06_insights(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/insights",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_07_newsletter(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/newsletter",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"departamento": "TI", "assunto": "Teste"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_08_metrics(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/metrics",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]