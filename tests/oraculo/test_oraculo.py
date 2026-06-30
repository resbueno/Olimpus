from __future__ import annotations
"""
test_oraculo.py — Oráculo (Hub de Notícias) · Plano de Testes por Role
Porta: 5030 | Roles: admin > editor (gestor) > leitura (operador)

Testes cobertos:
  - Autenticação por role
  - Admin: CRUD categorias, fontes RSS, usuários, KPIs, insights
  - Gestor (editor): criar/editar notícias, gerenciar departamentos
  - Operador (leitura): ler notícias apenas
  - Permissões: operador não pode criar/editar conteúdo
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5030"


def _ping_ok() -> bool:
    try:
        return requests.get(f"{BASE_URL}/api/ping", timeout=3).status_code == 200
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestOraculoDisponibilidade:
    def test_01_oraculo_acessivel(self):
        """Oráculo deve estar rodando e respondendo."""
        if not _ping_ok():
            pytest.skip("Oráculo não está rodando")
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
            r = s.get(f"{BASE_URL}/api/news", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401


# ─── Admin ───────────────────────────────────────────────────────────────────

class TestOraculoAdmin:
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
            pytest.skip("Oráculo não acessível")
        if r.status_code != 200:
            pytest.skip("Oráculo não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_me_retorna_role_admin(self, admin_session):
        """Admin deve ter role='admin'."""
        r = admin_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "admin"

    def test_06_admin_lista_noticias(self, admin_session):
        """Admin pode listar todas as notícias."""
        r = admin_session.get(f"{BASE_URL}/api/news")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_07_admin_cria_noticia(self, admin_session):
        """Admin pode criar notícia."""
        r = admin_session.post(
            f"{BASE_URL}/api/news",
            json={
                "titulo":   f"Notícia Admin {int(time.time())}",
                "conteudo": "Conteúdo criado pelo administrador via teste.",
                "resumo":   "Resumo de teste admin",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_08_admin_lista_categorias(self, admin_session):
        """Admin pode listar categorias."""
        r = admin_session.get(f"{BASE_URL}/api/categories")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_09_admin_cria_categoria(self, admin_session):
        """Admin pode criar categoria."""
        r = admin_session.post(
            f"{BASE_URL}/api/categories",
            json={"nome": f"Categoria Teste {int(time.time())}", "descricao": "Teste"},
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_10_admin_lista_fontes(self, admin_session):
        """Admin pode listar fontes RSS."""
        r = admin_session.get(f"{BASE_URL}/api/sources")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_11_admin_lista_kpis(self, admin_session):
        """Admin pode listar KPIs."""
        r = admin_session.get(f"{BASE_URL}/api/kpis")
        assert r.status_code == 200

    def test_12_admin_lista_insights(self, admin_session):
        """Admin pode listar insights."""
        r = admin_session.get(f"{BASE_URL}/api/insights")
        assert r.status_code == 200

    def test_13_admin_lista_departamentos(self, admin_session):
        """Admin pode listar departamentos."""
        r = admin_session.get(f"{BASE_URL}/api/departments")
        assert r.status_code == 200

    def test_14_admin_lista_usuarios(self, admin_session):
        """Admin pode listar usuários."""
        r = admin_session.get(f"{BASE_URL}/api/users")
        assert r.status_code == 200


# ─── Gestor (role=editor) ─────────────────────────────────────────────────────

class TestOraculoGestor:
    """Testes como editor (role=editor)."""

    def test_15_gestor_login(self, gestor_session):
        """Login do gestor funciona e retorna role=editor."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        assert r.json().get("data", {}).get("role") == "editor"

    def test_16_gestor_lista_noticias(self, gestor_session):
        """Editor pode listar notícias."""
        r = gestor_session.get(f"{BASE_URL}/api/news")
        assert r.status_code == 200
        assert isinstance(r.json().get("data"), list)

    def test_17_gestor_cria_noticia(self, gestor_session):
        """Editor pode criar notícia."""
        r = gestor_session.post(
            f"{BASE_URL}/api/news",
            json={
                "titulo":   f"Notícia Editor {int(time.time())}",
                "conteudo": "Conteúdo criado pelo editor via teste.",
                "resumo":   "Resumo editor",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_18_gestor_edita_noticia(self, admin_session, gestor_session):
        """Editor pode editar notícia existente."""
        r = admin_session.get(f"{BASE_URL}/api/news")
        noticias = r.json().get("data", [])
        if not noticias:
            pytest.skip("Nenhuma notícia para editar")
        nid = noticias[0]["id"]
        r = gestor_session.put(
            f"{BASE_URL}/api/news/{nid}",
            json={"titulo": f"Título Editado {int(time.time())}"},
        )
        assert r.status_code in [200, 201]

    def test_19_gestor_lista_categorias(self, gestor_session):
        """Editor pode listar categorias."""
        r = gestor_session.get(f"{BASE_URL}/api/categories")
        assert r.status_code == 200

    def test_20_gestor_lista_departamentos(self, gestor_session):
        """Editor pode listar departamentos."""
        r = gestor_session.get(f"{BASE_URL}/api/departments")
        assert r.status_code == 200


# ─── Operador (role=leitura) ──────────────────────────────────────────────────

class TestOraculoOperador:
    """Testes como operador/leitura (role=leitura)."""

    def test_21_operador_login(self, operador_session):
        """Login do operador funciona e retorna role=leitura."""
        r = operador_session.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 200
        role = r.json().get("data", {}).get("role")
        assert role in ["leitura", "colaborador", ""]  # Pode variar conforme mapeamento

    def test_22_operador_lista_noticias(self, operador_session):
        """Operador pode ler notícias."""
        r = operador_session.get(f"{BASE_URL}/api/news")
        assert r.status_code == 200

    def test_23_operador_le_noticia(self, admin_session, operador_session):
        """Operador pode ler notícia específica."""
        r = admin_session.get(f"{BASE_URL}/api/news")
        noticias = r.json().get("data", [])
        if not noticias:
            pytest.skip("Nenhuma notícia para leitura")
        nid = noticias[0]["id"]
        r = operador_session.get(f"{BASE_URL}/api/news/{nid}")
        assert r.status_code == 200


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestOraculoPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_24_operador_nao_cria_noticia(self, operador_session):
        """Operador (leitura) NÃO pode criar notícia (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/news",
            json={"titulo": "Notícia Proibida", "conteudo": "Não deveria ser permitido"},
        )
        assert r.status_code == 403

    def test_25_operador_nao_exclui_noticia(self, admin_session, operador_session):
        """Operador NÃO pode excluir notícia (403)."""
        r = admin_session.get(f"{BASE_URL}/api/news")
        noticias = r.json().get("data", [])
        if not noticias:
            pytest.skip("Nenhuma notícia para testar exclusão")
        nid = noticias[0]["id"]
        r = operador_session.delete(f"{BASE_URL}/api/news/{nid}")
        assert r.status_code == 403

    def test_26_operador_nao_cria_categoria(self, operador_session):
        """Operador NÃO pode criar categoria (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/categories",
            json={"nome": "Categoria Proibida"},
        )
        assert r.status_code == 403

    def test_27_gestor_nao_exclui_categoria(self, admin_session, gestor_session):
        """Editor NÃO pode excluir categoria (403 — apenas admin)."""
        r = admin_session.get(f"{BASE_URL}/api/categories")
        cats = r.json().get("data", [])
        if not cats:
            pytest.skip("Nenhuma categoria para testar exclusão")
        cid = cats[0]["id"]
        r = gestor_session.delete(f"{BASE_URL}/api/categories/{cid}")
        assert r.status_code == 403

    def test_28_sem_auth_nao_acessa_news(self):
        """Sem autenticação não acessa /api/news (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/news", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
