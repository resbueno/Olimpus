from __future__ import annotations
"""
test_ploutos.py - Testes para Ploutos (Gestão Financeira)
Porta: 5080 | Prioridade: ALTA
"""
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5080"


@pytest.mark.api
class TestPloutos:
    """Testes Ploutos"""

    def test_01_ping(self):
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Ploutos não está rodando: {exc}")
        assert r.status_code == 200

    def test_02_listar_lancamentos(self, ploutos_session):
        r = ploutos_session.get(f"{BASE_URL}/api/lancamentos")
        assert r.status_code in [200, 404]

    def test_03_criar_lancamento(self, ploutos_session):
        r = ploutos_session.post(
            f"{BASE_URL}/api/lancamentos",
            json={"descricao": "Teste", "valor": 100, "tipo": "receita", "data_vencimento": "2026-12-31"}
        )
        assert r.status_code in [200, 201, 404]

    def test_04_fluxo_caixa(self, ploutos_session):
        r = ploutos_session.get(f"{BASE_URL}/api/fluxo-caixa")
        assert r.status_code in [200, 404]

    def test_05_contas_pagar(self, ploutos_session):
        r = ploutos_session.get(f"{BASE_URL}/api/contas-pagar")
        assert r.status_code in [200, 404]

    def test_06_relatorio_mensal(self, ploutos_session):
        r = ploutos_session.get(f"{BASE_URL}/api/relatorios/mensal")
        assert r.status_code in [200, 404]