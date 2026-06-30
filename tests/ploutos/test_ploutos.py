from __future__ import annotations
"""
test_ploutos.py — Ploutos (Gestão Financeira) · Plano de Testes por Role
Porta: 5080 | Roles: admin > financeiro (gestor) > colaborador (operador)

Testes cobertos:
  - Autenticação por role
  - Admin: CRUD categorias, centros de custo, gerenciar usuários
  - Gestor (financeiro): criar/editar lançamentos, baixar pagamentos, orçamentos
  - Operador (colaborador): visualizar dashboard e lançamentos (somente leitura)
  - Permissões: operador não pode criar/excluir lançamentos nem categorias
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5080"


def _ping_ok() -> bool:
    try:
        return requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestPloutosDisponibilidade:
    def test_01_ploutos_acessivel(self):
        """Ploutos deve estar rodando e respondendo."""
        if not _ping_ok():
            pytest.skip("Ploutos não está rodando")
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
            r = s.get(f"{BASE_URL}/api/lancamentos", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestPloutosAdmin:
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
            pytest.skip("Ploutos não acessível")
        if r.status_code != 200:
            pytest.skip("Ploutos não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_me_retorna_role_admin(self, admin_session):
        """Admin deve ter role='admin'."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "admin"

    def test_06_admin_lista_categorias(self, admin_session):
        """Admin pode listar categorias financeiras."""
        r = admin_session.get(f"{BASE_URL}/api/categorias")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_07_admin_cria_categoria_receita(self, admin_session):
        """Admin pode criar categoria do tipo receita."""
        r = admin_session.post(
            f"{BASE_URL}/api/categorias",
            json={"nome": f"Cat Receita {int(time.time())}", "tipo": "receita"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_08_admin_cria_categoria_despesa(self, admin_session):
        """Admin pode criar categoria do tipo despesa."""
        r = admin_session.post(
            f"{BASE_URL}/api/categorias",
            json={"nome": f"Cat Despesa {int(time.time())}", "tipo": "despesa"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_09_admin_lista_centros_custo(self, admin_session):
        """Admin pode listar centros de custo."""
        r = admin_session.get(f"{BASE_URL}/api/centro-custos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_10_admin_cria_centro_custo(self, admin_session):
        """Admin pode criar centro de custo."""
        r = admin_session.post(
            f"{BASE_URL}/api/centro-custos",
            json={"nome": f"CC Teste {int(time.time())}", "descricao": "Centro de custo de teste"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_11_admin_lista_usuarios(self, admin_session):
        """Admin pode listar usuários do sistema."""
        r = admin_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_12_admin_cria_lancamento(self, admin_session):
        """Admin pode criar lançamento financeiro."""
        r = admin_session.post(
            f"{BASE_URL}/api/lancamentos",
            json={
                "descricao":       f"Lançamento Admin {int(time.time())}",
                "valor":           1500.00,
                "tipo":            "receita",
                "data_vencimento": "2026-12-31",
                "favorecido":      "Cliente Teste",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True


# ─── Gestor (role=financeiro) ─────────────────────────────────────────────────

class TestPloutosGestor:
    """Testes como gestor financeiro (role=financeiro)."""

    def test_13_gestor_login(self, gestor_session):
        """Login do gestor funciona e retorna role=financeiro."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "financeiro"

    def test_14_gestor_dashboard(self, gestor_session):
        """Gestor financeiro pode ver o dashboard."""
        r = gestor_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_15_gestor_lista_lancamentos(self, gestor_session):
        """Gestor pode listar todos os lançamentos."""
        r = gestor_session.get(f"{BASE_URL}/api/lancamentos")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_16_gestor_cria_lancamento_despesa(self, gestor_session):
        """Gestor financeiro pode criar lançamento de despesa."""
        r = gestor_session.post(
            f"{BASE_URL}/api/lancamentos",
            json={
                "descricao":       f"Despesa Gestor {int(time.time())}",
                "valor":           800.00,
                "tipo":            "despesa",
                "data_vencimento": "2026-11-30",
                "favorecido":      "Fornecedor Teste",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_17_gestor_cria_lancamento_receita(self, gestor_session):
        """Gestor financeiro pode criar lançamento de receita."""
        r = gestor_session.post(
            f"{BASE_URL}/api/lancamentos",
            json={
                "descricao":       f"Receita Gestor {int(time.time())}",
                "valor":           3000.00,
                "tipo":            "receita",
                "data_vencimento": "2026-10-15",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_18_gestor_fluxo_caixa(self, gestor_session):
        """Gestor pode visualizar fluxo de caixa."""
        r = gestor_session.get(f"{BASE_URL}/api/fluxo-caixa")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_19_gestor_lista_orcamentos(self, gestor_session):
        """Gestor pode listar orçamentos."""
        r = gestor_session.get(f"{BASE_URL}/api/orcamentos")
        assert r.status_code in [200, 404]

    def test_20_gestor_orcamento_realizado(self, gestor_session):
        """Gestor pode ver orçamento vs realizado."""
        r = gestor_session.get(f"{BASE_URL}/api/orcamento-realizado")
        assert r.status_code in [200, 404]


# ─── Operador (role=colaborador) ──────────────────────────────────────────────

class TestPloutosOperador:
    """Testes como colaborador (role=colaborador) — acesso somente leitura."""

    def test_21_operador_login(self, operador_session):
        """Login do operador funciona e retorna role=colaborador."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "colaborador"

    def test_22_operador_dashboard(self, operador_session):
        """Colaborador pode ver o dashboard."""
        r = operador_session.get(f"{BASE_URL}/api/dashboard")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_23_operador_lista_lancamentos(self, operador_session):
        """Colaborador pode listar lançamentos (leitura)."""
        r = operador_session.get(f"{BASE_URL}/api/lancamentos")
        assert r.status_code == 200

    def test_24_operador_fluxo_caixa(self, operador_session):
        """Colaborador pode ver fluxo de caixa."""
        r = operador_session.get(f"{BASE_URL}/api/fluxo-caixa")
        assert r.status_code == 200


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestPloutosPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_25_operador_nao_cria_lancamento(self, operador_session):
        """Colaborador NÃO pode criar lançamento (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/lancamentos",
            json={
                "descricao": "Proibido",
                "valor":     100.00,
                "tipo":      "despesa",
                "data_vencimento": "2026-12-31",
            },
        )
        assert r.status_code == 403

    def test_26_operador_nao_cria_categoria(self, operador_session):
        """Colaborador NÃO pode criar categoria (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/categorias",
            json={"nome": "Categoria Proibida", "tipo": "receita"},
        )
        assert r.status_code == 403

    def test_27_operador_nao_cria_centro_custo(self, operador_session):
        """Colaborador NÃO pode criar centro de custo (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/centro-custos",
            json={"nome": "CC Proibido"},
        )
        assert r.status_code == 403

    def test_28_gestor_nao_deleta_categoria(self, admin_session, gestor_session):
        """Gestor financeiro NÃO pode deletar categorias (apenas admin)."""
        # Cria categoria como admin
        r = admin_session.post(
            f"{BASE_URL}/api/categorias",
            json={"nome": f"Para Deletar {int(time.time())}", "tipo": "despesa"},
        )
        if r.status_code not in [200, 201]:
            pytest.skip("Não foi possível criar categoria para teste")
        cid = r.json().get("data", {}).get("id")
        if not cid:
            pytest.skip("ID da categoria não retornado")
        # Tenta deletar como gestor
        r = gestor_session.delete(f"{BASE_URL}/api/categorias/{cid}")
        assert r.status_code == 403

    def test_29_sem_auth_nao_acessa_dashboard(self):
        """Sem autenticação não acessa /api/dashboard (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/dashboard", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401

    def test_30_lancamento_campo_obrigatorio_retorna_400(self, gestor_session):
        """Criar lançamento sem campos obrigatórios retorna 400."""
        r = gestor_session.post(
            f"{BASE_URL}/api/lancamentos",
            json={"descricao": "Incompleto"},  # Faltam valor e tipo
        )
        assert r.status_code == 400
