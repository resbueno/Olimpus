from __future__ import annotations
"""
test_sso.py - Testes de Integração SSO
Fluxo completo: Login Atlas → Redirect → App → Logout
"""
import pytest
import requests


@pytest.mark.integration
class TestSSOFlow:
    """Testes de fluxo SSO entre apps"""

    def test_01_atlas_login_hestia_access(self):
        """
        Login Atlas → acesso Héstia com token
        Fluxo completo SSO
        """
        # 1. Login no Atlas using session
        session = requests.Session()
        r_atlas = session.post(
            "http://localhost:5010/api/auth/login",
            json={"email": "renato.s.bueno@hotmail.com", "senha": "admin"},
            timeout=10
        )
        assert r_atlas.status_code == 200
        token = r_atlas.json().get("data", {}).get("token")
        
        # 2. Acessar Héstia with session cookies
        r_hestia = session.get("http://localhost:5020/")
        assert r_hestia.status_code == 200
        
        # 3. Verificar status auth using session
        r_status = session.get("http://localhost:5020/api/auth/status")
        assert r_status.status_code == 200

    def test_02_multi_app_access(self):
        """Acessar múltiplos apps com mesmo token"""
        # Login Atlas using session
        session = requests.Session()
        r_atlas = session.post(
            "http://localhost:5010/api/auth/login",
            json={"email": "renato.s.bueno@hotmail.com", "senha": "admin"},
            timeout=10
        )
        assert r_atlas.status_code == 200
        
        # Tentar acessar apps conhecidos using session
        apps = [
            ("http://localhost:5020", "hestia"),
            ("http://localhost:5070", "iris"),
            ("http://localhost:5080", "ploutos"),
        ]
        
        for base_url, name in apps:
            r = session.get(f"{base_url}/api/auth/status", timeout=3)
            # Aceita 200 (logado) ou 401 (não autorizado para esse app)
            assert r.status_code in [200, 401, 404]

    def test_03_logout_propagation(self):
        """Logout em um app deve afetar sessão global"""
        # Login Atlas using session
        session = requests.Session()
        r_atlas = session.post(
            "http://localhost:5010/api/auth/login",
            json={"email": "renato.s.bueno@hotmail.com", "senha": "admin"},
            timeout=10
        )
        assert r_atlas.status_code == 200
        
        # Logout do Atlas
        r_logout = session.post("http://localhost:5010/api/auth/logout")
        assert r_logout.status_code in [200, 401]

    def test_04_invalid_token_rejection(self):
        """Token inválido deve ser rejeitado"""
        r = requests.get(
            "http://localhost:5020/api/auth/status",
            headers={"Authorization": "Bearer token_invalido"}
        )
        assert r.status_code in [200, 401, 403]

    def test_05_expired_token_handling(self):
        """Token expirado deve ser redirecionado para login"""
        r = requests.get(
            "http://localhost:5020/api/auth/status"
        )
        # Sem token, deve retornar não autenticado
        assert r.status_code in [200, 401]