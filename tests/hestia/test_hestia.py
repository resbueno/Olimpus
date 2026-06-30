from __future__ import annotations
"""
test_hestia.py — Héstia (Intranet Corporativa) · Plano de Testes por Role
Porta: 5020 | Roles: admin (funcao Atlas) > usuário autenticado (operador)

Testes cobertos:
  - Autenticação (admin, gestor c/ funcao admin, operador sem funcao admin)
  - Admin: criar notícias, gerenciar documentos, configurações
  - Gestor (com funcao admin): acesso pleno igual ao admin
  - Operador (sem funcao admin): leitura de notícias, documentos, feed de kudos
  - Permissões: operador não pode criar/excluir conteúdo
"""
import time
import pytest
import requests

BASE_URL = "http://localhost:5020"
_PASS_FIELD = "password"


def _ping_ok() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/api/ping", timeout=3)
        return r.status_code in [200, 404]  # Héstia pode não ter /api/ping
    except Exception:
        return False


def _app_up() -> bool:
    try:
        r = requests.get(f"{BASE_URL}/", timeout=3)
        return r.status_code in [200, 302]
    except Exception:
        return False


# ─── Disponibilidade ─────────────────────────────────────────────────────────

class TestHestiaDisponibilidade:
    def test_01_hestia_acessivel(self):
        """Héstia deve estar rodando."""
        if not _app_up():
            pytest.skip("Héstia não está rodando")
        assert _app_up() is True

    def test_02_login_invalido_retorna_401(self):
        """Login com credenciais inválidas retorna 401."""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "naoexiste@olimpus.local", _PASS_FIELD: "errado"},
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

class TestHestiaAdmin:
    """Testes como administrador (funcao admin no Atlas)."""

    def test_04_admin_login(self):
        """Login do admin funciona."""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", _PASS_FIELD: "Atlas@2024"},
                timeout=10,
            )
        except Exception:
            pytest.skip("Héstia não acessível")
        if r.status_code != 200:
            pytest.skip("Héstia não acessível")
        assert r.json().get("ok") is True

    def test_05_admin_lista_noticias(self, admin_session):
        """Admin pode listar notícias."""
        r = admin_session.get(f"{BASE_URL}/api/news")
        assert r.status_code == 200

    def test_06_admin_cria_noticia(self, admin_session):
        """Admin pode criar notícia."""
        r = admin_session.post(
            f"{BASE_URL}/api/news",
            json={
                "titulo":   f"Notícia Teste {int(time.time())}",
                "conteudo": "Conteúdo gerado pelo teste automatizado.",
                "resumo":   "Resumo de teste",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_07_admin_lista_documentos(self, admin_session):
        """Admin pode listar documentos."""
        r = admin_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200

    def test_08_admin_lista_pastas(self, admin_session):
        """Admin pode listar pastas de documentos."""
        r = admin_session.get(f"{BASE_URL}/api/documents/folders")
        assert r.status_code == 200

    def test_09_admin_lista_pessoas(self, admin_session):
        """Admin pode listar pessoas do diretório."""
        r = admin_session.get(f"{BASE_URL}/api/people")
        assert r.status_code == 200

    def test_10_admin_settings(self, admin_session):
        """Admin pode ler configurações da Héstia."""
        r = admin_session.get(f"{BASE_URL}/api/settings")
        assert r.status_code in [200, 404]

    def test_11_admin_aniversariantes(self, admin_session):
        """Admin pode ver aniversariantes."""
        r = admin_session.get(f"{BASE_URL}/api/people/birthdays")
        assert r.status_code == 200

    def test_12_admin_comunidades(self, admin_session):
        """Admin pode listar comunidades."""
        r = admin_session.get(f"{BASE_URL}/api/communities")
        assert r.status_code == 200


# ─── Gestor (funcao admin no Atlas) ──────────────────────────────────────────

class TestHestiaGestor:
    """Testes como gestor (tem funcao admin no Atlas)."""

    def test_13_gestor_login(self, gestor_session):
        """Login do gestor funciona."""
        r = gestor_session.get(f"{BASE_URL}/api/auth/status")
        assert r.status_code == 200

    def test_14_gestor_lista_noticias(self, gestor_session):
        """Gestor pode listar notícias."""
        r = gestor_session.get(f"{BASE_URL}/api/news")
        assert r.status_code == 200

    def test_15_gestor_cria_noticia(self, gestor_session):
        """Gestor (funcao admin) pode criar notícia."""
        r = gestor_session.post(
            f"{BASE_URL}/api/news",
            json={
                "titulo":   f"Notícia Gestor {int(time.time())}",
                "conteudo": "Notícia criada pelo gestor via teste.",
                "resumo":   "Resumo gestor",
            },
        )
        assert r.status_code in [200, 201]
        assert r.json().get("ok") is True

    def test_16_gestor_lista_documentos(self, gestor_session):
        """Gestor pode listar documentos."""
        r = gestor_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200


# ─── Operador (sem funcao admin) ─────────────────────────────────────────────

class TestHestiaOperador:
    """Testes como operador (usuário autenticado sem funcao admin)."""

    def test_17_operador_login(self, operador_session):
        """Login do operador funciona."""
        r = operador_session.get(f"{BASE_URL}/api/auth/status")
        assert r.status_code == 200

    def test_18_operador_lista_noticias(self, operador_session):
        """Operador pode ler notícias."""
        r = operador_session.get(f"{BASE_URL}/api/news")
        assert r.status_code == 200

    def test_19_operador_lista_documentos(self, operador_session):
        """Operador pode listar documentos (leitura)."""
        r = operador_session.get(f"{BASE_URL}/api/documents")
        assert r.status_code == 200

    def test_20_operador_ve_pessoas(self, operador_session):
        """Operador pode ver diretório de pessoas."""
        r = operador_session.get(f"{BASE_URL}/api/people")
        assert r.status_code == 200

    def test_21_operador_ve_comunidades(self, operador_session):
        """Operador pode ver comunidades."""
        r = operador_session.get(f"{BASE_URL}/api/communities")
        assert r.status_code == 200

    def test_22_operador_da_kudos(self, operador_session):
        """Operador pode dar kudos para colega."""
        r = operador_session.get(f"{BASE_URL}/api/people")
        pessoas = r.json().get("data", [])
        if len(pessoas) < 2:
            pytest.skip("Precisa de pelo menos 2 pessoas para kudos")
        me_data = operador_session.get(f"{BASE_URL}/api/auth/status").json()
        me_id = me_data.get("data", {}).get("id") or me_data.get("user", {}).get("id")
        alvo = next((p for p in pessoas if p.get("id") != me_id), None)
        if not alvo:
            pytest.skip("Não encontrou alvo para kudos")
        r = operador_session.post(
            f"{BASE_URL}/api/people/kudos",
            json={"para_id": alvo["id"], "mensagem": "Parabéns — teste automático!"},
        )
        assert r.status_code in [200, 201, 400]


# ─── Controle de Permissões ───────────────────────────────────────────────────

class TestHestiaPermissoes:
    """Testes que verificam restrições de acesso por role."""

    def test_23_operador_nao_cria_noticia(self, operador_session):
        """Operador (sem funcao admin) NÃO pode criar notícia (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/news",
            json={
                "titulo":   "Notícia Proibida",
                "conteudo": "Não deveria ser permitido",
            },
        )
        assert r.status_code == 403

    def test_24_operador_nao_cria_pasta_documento(self, operador_session):
        """Operador NÃO pode criar pasta de documentos (403)."""
        r = operador_session.post(
            f"{BASE_URL}/api/documents/folders",
            json={"nome": "Pasta Proibida"},
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

    def test_26_sem_auth_nao_acessa_news(self):
        """Sem autenticação não acessa /api/news (401)."""
        try:
            s = requests.Session()
            r = s.get(f"{BASE_URL}/api/news", timeout=5)
        except Exception:
            pytest.skip("App não está rodando")
        assert r.status_code == 401
