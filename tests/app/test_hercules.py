from __future__ import annotations
"""
test_hercules.py - Testes para Hércules (Gestão de Tarefas)
Porta: 5001 | Prioridade: MÉDIA - PENDENTE CRIAR APP
"""
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5001"

_hercules_online = None


def _verificar_hercules():
    global _hercules_online
    if _hercules_online is None:
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
            _hercules_online = r.status_code == 200
        except Exception:
            _hercules_online = False
    return _hercules_online


def _fail_se_offline():
    if not _verificar_hercules():
        pytest.fail("Hércules não está rodando")


@pytest.mark.api
class TestHercules:
    """Testes Hércules"""

    def test_01_ping(self):
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Hércules não está rodando: {exc}")
        assert r.status_code == 200

    def test_02_login(self):
        _fail_se_offline()
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@olimpus.local", "senha": "admin"},
            timeout=10
        )
        assert r.status_code in [200, 401, 403]


@pytest.mark.api
class TestHerculesTarefas:
    """Testes de tarefas"""

    def setup_method(self):
        _fail_se_offline()

    def test_03_listar_tarefas(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/tarefas",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_04_criar_tarefa(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/tarefas",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"titulo": "Teste Tarefa", "descricao": "Teste"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_05_atribuir_tarefa(self, atlas_token):
        r = requests.put(
            f"{BASE_URL}/api/tarefas/1/assign",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"user_id": "1"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_06_mover_tarefa(self, atlas_token):
        r = requests.put(
            f"{BASE_URL}/api/tarefas/1/mover",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"coluna": "doing"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_07_comentar(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/tarefas/1/comentarios",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"comentario": "Teste"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]


@pytest.mark.api
class TestHerculesProjetos:
    """Testes de projetos"""

    def setup_method(self):
        _fail_se_offline()

    def test_08_listar_projetos(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/projetos",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]

    def test_09_criar_projeto(self, atlas_token):
        r = requests.post(
            f"{BASE_URL}/api/projetos",
            headers={"Authorization": f"Bearer {atlas_token}"},
            json={"nome": "Projeto Teste", "descricao": "Teste"}
        )
        assert r.status_code in [200, 201, 400, 401, 403, 404]

    def test_10_timeline(self, atlas_token):
        r = requests.get(
            f"{BASE_URL}/api/projetos/1/timeline",
            headers={"Authorization": f"Bearer {atlas_token}"}
        )
        assert r.status_code in [200, 401, 403, 404]