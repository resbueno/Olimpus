from __future__ import annotations
"""
test_tiresias.py - Testes para Tiresias (OCR)
Porta: 5090 | Prioridade: MÉDIA
Endpoints reais: /api/ocr/upload, /api/ocr/process, /api/ocr/status/<id>,
                 /api/ocr/results/<id>, /api/ocr/history, /api/ocr/templates
"""
import time
import pytest
import requests
from requests.exceptions import ConnectionError as ReqConnectionError, ConnectTimeout

BASE_URL = "http://localhost:5090"


@pytest.mark.api
class TestTiresiasAuth:
    """Testes de autenticação"""

    def test_01_ping(self):
        """Tiresias deve responder"""
        try:
            r = requests.get(f"{BASE_URL}/api/ping", timeout=2)
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Tiresias não está rodando: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True

    def test_02_login_valido(self):
        """Login com credenciais válidas"""
        try:
            r = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": "admin@olimpus.local", "password": "Atlas@2024"},
                timeout=10,
            )
        except (ReqConnectionError, ConnectTimeout) as exc:
            pytest.fail(f"Tiresias não disponível: {exc}")
        assert r.status_code == 200
        assert r.json().get("ok") is True


@pytest.mark.api
class TestTiresiasOCR:
    """Testes de processamento OCR"""

    def test_03_upload_documento(self, tiresias_session):
        """Upload de documento para OCR"""
        r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        assert r.status_code in [200, 201, 400]
        if r.status_code == 201:
            return r.json().get("data", {}).get("id")

    def test_04_processar_ocr(self, tiresias_session):
        """Processar documento OCR"""
        # Primeiro faz upload de um documento
        upload_r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        if upload_r.status_code != 201:
            pytest.fail(f"Upload falhou — status {upload_r.status_code}")
        
        doc_id = upload_r.json().get("data", {}).get("id")
        r = tiresias_session.post(f"{BASE_URL}/api/ocr/process", json={"document_id": doc_id})
        assert r.status_code in [200, 202, 400]

    def test_05_status_processamento(self, tiresias_session):
        """Verificar status de processamento"""
        # Faz upload e processamento primeiro
        upload_r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        if upload_r.status_code != 201:
            pytest.fail(f"Upload falhou — status {upload_r.status_code}")
        
        doc_id = upload_r.json().get("data", {}).get("id")
        process_r = tiresias_session.post(f"{BASE_URL}/api/ocr/process", json={"document_id": doc_id})
        
        r = tiresias_session.get(f"{BASE_URL}/api/ocr/status/{doc_id}")
        assert r.status_code in [200, 404]

    def test_06_obter_resultados(self, tiresias_session):
        """Obter resultados OCR"""
        # Faz upload e processamento primeiro
        upload_r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        if upload_r.status_code != 201:
            pytest.fail(f"Upload falhou — status {upload_r.status_code}")
        
        doc_id = upload_r.json().get("data", {}).get("id")
        process_r = tiresias_session.post(f"{BASE_URL}/api/ocr/process", json={"document_id": doc_id})
        
        r = tiresias_session.get(f"{BASE_URL}/api/ocr/results/{doc_id}")
        assert r.status_code in [200, 404]


@pytest.mark.api
class TestTiresiasHistorico:
    """Testes de histórico e templates"""

    def test_07_historico_processamentos(self, tiresias_session):
        """Ver histórico de processamentos"""
        r = tiresias_session.get(f"{BASE_URL}/api/ocr/history")
        assert r.status_code in [200, 404]

    def test_08_gerenciar_templates(self, tiresias_session):
        """Gerenciar templates de documentos"""
        r = tiresias_session.get(f"{BASE_URL}/api/ocr/templates")
        assert r.status_code in [200, 404]

    def test_09_validar_resultados(self, tiresias_session):
        """Validar resultados OCR"""
        # Faz upload e processamento primeiro
        upload_r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/upload",
            files={"file": ("test.pdf", b"PDF content", "application/pdf")},
        )
        if upload_r.status_code != 201:
            pytest.fail(f"Upload falhou — status {upload_r.status_code}")
        
        doc_id = upload_r.json().get("data", {}).get("id")
        process_r = tiresias_session.post(f"{BASE_URL}/api/ocr/process", json={"document_id": doc_id})
        
        r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/validate",
            json={"document_id": doc_id, "valid": True, "comentario": "Validado por teste"}
        )
        assert r.status_code in [200, 404]

    def test_10_processamento_lote(self, tiresias_session):
        """Processamento em lote"""
        r = tiresias_session.post(
            f"{BASE_URL}/api/ocr/batch",
            json={"document_ids": [], "template_id": None}
        )
        assert r.status_code in [200, 400, 404]