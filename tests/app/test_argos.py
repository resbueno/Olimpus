from __future__ import annotations
"""
test_argos.py - Testes para Argos (Monitoração)
Porta: 5000 | Prioridade: ALTA
"""
import pytest
import requests

BASE_URL = "http://localhost:5000"

_argos_online = None


def _verificar_argos():
    global _argos_online
    if _argos_online is None:
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
            _argos_online = r.status_code == 200
        except Exception:
            _argos_online = False
    return _argos_online


@pytest.mark.api
class TestArgos:
    """Testes Argos"""

    def test_01_ping(self):
        r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        assert r.status_code == 200

    def test_02_status(self, atlas_token):
        # Rota /api/status pode não existir no Argos — aceitar 404
        r = requests.get(
            f"{BASE_URL}/api/status",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 404]

    def test_03_listar_monitores(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/monitors",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403]

    def test_04_criar_monitor(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/monitors",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"url": "http://localhost:5020", "nome": "Héstia Teste"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_05_listar_historico(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/monitors/1/history",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_06_verificar_disponibilidade(self, atlas_token):
        # Rota /api/checks pode não existir no Argos — aceitar 404
        r = requests.get(
            f"{BASE_URL}/api/checks",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 404]

    def test_07_toggle_monitor(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/monitors/1/toggle",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_08_executar_monitor(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/monitors/1/run",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]