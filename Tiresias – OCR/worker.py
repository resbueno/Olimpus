from __future__ import annotations
"""
worker.py — Tiresias OCR · Motor de processamento de documentos
Executa em thread de background; consome fila de documentos.
Degrada graciosamente se pytesseract/OpenCV não estiverem instalados.
"""
import json
import logging
import os
import queue
import re
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Dependências opcionais ────────────────────────────────────────────────────

_TESS_KNOWN_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",  # Windows
    "/opt/homebrew/bin/tesseract",                     # macOS Apple Silicon
    "/usr/local/bin/tesseract",                        # macOS Intel
    "/usr/bin/tesseract",                              # Linux
]

def _find_tesseract_bin():
    """Retorna o caminho do binário tesseract ou None."""
    import shutil as _sh
    found = _sh.which("tesseract")
    if found:
        return found
    import os as _o
    for p in _TESS_KNOWN_PATHS:
        if _o.path.isfile(p):
            return p
    return None

try:
    import pytesseract
    from PIL import Image
    import os as _os
    _tbin = _find_tesseract_bin()
    if _tbin:
        pytesseract.pytesseract.tesseract_cmd = _tbin
    # TESSDATA_PREFIX — garante que os idiomas customizados sejam encontrados
    _TESS_DATA = _os.path.join(_os.path.expanduser("~"), "tessdata")
    if _os.path.isdir(_TESS_DATA) and not _os.environ.get("TESSDATA_PREFIX"):
        _os.environ["TESSDATA_PREFIX"] = _TESS_DATA
    PYTESSERACT_OK = True
except ImportError:
    PYTESSERACT_OK = False
    logger.warning("pytesseract/Pillow não instalados — OCR desabilitado.")


def probe_tesseract() -> bool:
    """Re-detecta o binário tesseract em runtime (chamado após instalação)."""
    if not PYTESSERACT_OK:
        return False
    tbin = _find_tesseract_bin()
    if tbin:
        pytesseract.pytesseract.tesseract_cmd = tbin
        return True
    return False

try:
    import cv2
    import numpy as np
    CV2_OK = True
except ImportError:
    CV2_OK = False

try:
    from validate_docbr import CPF as _CPF, CNPJ as _CNPJ
    _cpf_v  = _CPF()
    _cnpj_v = _CNPJ()
    DOCBR_OK = True
except ImportError:
    DOCBR_OK = False

try:
    import fitz   # PyMuPDF
    PYMUPDF_OK = True
except ImportError:
    PYMUPDF_OK = False

# ── Estado global ─────────────────────────────────────────────────────────────

doc_queue: queue.Queue = queue.Queue()
_worker_thread         = None
_watchdog_observer     = None

# ── Padrões regex BR ──────────────────────────────────────────────────────────

_CPF_RE   = re.compile(r'\b\d{3}[.\-]?\d{3}[.\-]?\d{3}[.\-]?\d{2}\b')
_CNPJ_RE  = re.compile(r'\b\d{2}[.\-]?\d{3}[.\-]?\d{3}[\/]?\d{4}[.\-]?\d{2}\b')
_DATA_RE  = re.compile(r'\b\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4}\b')
_VALOR_RE = re.compile(r'R\$\s*[\d.,]+')
_NF_RE    = re.compile(r'(?:N[Ffºo°]|NOTA FISCAL)\s*[:\-]?\s*(\d{4,9})', re.I)

_TIPO_KW = {
    "nf":       ["nota fiscal", "nf-e", "nfe", "danfe", "fatura"],
    "contrato": ["contrato", "instrumento particular", "cláusula", "contratante"],
    "holerite": ["holerite", "contracheque", "folha de pagamento", "salário", "inss", "fgts"],
    "cnh":      ["carteira nacional", "habilitacao", "habilitação", "detran", "denatran"],
    "recibo":   ["recibo", "quitação", "quitacao", "recebemos de", "recebi de"],
}


# ── Status do OCR engine ──────────────────────────────────────────────────────

def ocr_status() -> str:
    if not PYTESSERACT_OK:
        return "sem pytesseract"
    try:
        pytesseract.get_tesseract_version()
        return "ok"
    except Exception:
        # Tenta re-detectar o binário (pode ter sido instalado após o início do servidor)
        if probe_tesseract():
            try:
                pytesseract.get_tesseract_version()
                return "ok"
            except Exception:
                pass
        return "sem tesseract"


# ── Pré-processamento de imagem ───────────────────────────────────────────────

def _preprocess(pil_img):
    if CV2_OK:
        arr  = np.array(pil_img.convert("RGB"))
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(thresh)
    return pil_img.convert("L")


# ── Conversão PDF → imagens ───────────────────────────────────────────────────

def _pdf_to_images(path: str) -> list:
    if not PYMUPDF_OK:
        return []
    import io
    doc, imgs = fitz.open(path), []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        imgs.append(Image.open(io.BytesIO(pix.tobytes("png"))))
    doc.close()
    return imgs


# ── OCR ──────────────────────────────────────────────────────────────────────

def _do_ocr(path: str, lang: str = "por") -> str:
    if not PYTESSERACT_OK:
        return "[OCR indisponível — instale pytesseract e o Tesseract-OCR]"
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        images = _pdf_to_images(path)
        if not images:
            return "[PDF: instale pymupdf (pip install pymupdf) para processar PDFs]"
    else:
        try:
            images = [Image.open(path)]
        except Exception as e:
            return f"[Erro ao abrir imagem: {e}]"

    parts = []
    for img in images:
        img = _preprocess(img)
        try:
            text = pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 6")
            parts.append(text)
        except Exception as e:
            parts.append(f"[Erro OCR: {e}]")
    return "\n\n─── Página ───\n\n".join(parts)


# ── Extração de campos ────────────────────────────────────────────────────────

def _extract_fields(text: str) -> dict:
    fields: dict = {}
    cpfs   = list(dict.fromkeys(_CPF_RE.findall(text)))
    cnpjs  = list(dict.fromkeys(_CNPJ_RE.findall(text)))
    datas  = list(dict.fromkeys(_DATA_RE.findall(text)))
    valores= list(dict.fromkeys(_VALOR_RE.findall(text)))
    nf_num = _NF_RE.findall(text)
    if cpfs:    fields["cpf"]      = cpfs[:4]
    if cnpjs:   fields["cnpj"]     = cnpjs[:4]
    if datas:   fields["datas"]    = datas[:6]
    if valores: fields["valores"]  = valores[:6]
    if nf_num:  fields["numero_nf"]= nf_num[0]
    return fields


# ── Validações ────────────────────────────────────────────────────────────────

def _validate_fields(fields: dict) -> list:
    results = []
    for cpf in fields.get("cpf", []):
        ok = _cpf_v.validate(cpf) if DOCBR_OK else (len(re.sub(r"\D", "", cpf)) == 11)
        results.append({"campo": "CPF", "valor": cpf, "valido": ok,
                        "msg": "CPF válido" if ok else "CPF inválido"})
    for cnpj in fields.get("cnpj", []):
        ok = _cnpj_v.validate(cnpj) if DOCBR_OK else (len(re.sub(r"\D", "", cnpj)) == 14)
        results.append({"campo": "CNPJ", "valor": cnpj, "valido": ok,
                        "msg": "CNPJ válido" if ok else "CNPJ inválido"})
    return results


# ── Classificação de tipo ─────────────────────────────────────────────────────

def _classify(text: str, hint: str = "") -> str:
    if hint and hint not in ("desconhecido", "generico", ""):
        return hint
    tl = text.lower()
    scores = {t: sum(1 for kw in kws if kw in tl) for t, kws in _TIPO_KW.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "generico"


# ── Aplicação de regras ───────────────────────────────────────────────────────

def _apply_rules(doc_id: int, tipo: str, text: str):
    import database as db
    for regra in db.list_regras(ativo=True):
        if regra["tipo_doc"] not in ("generico", tipo):
            continue
        kws = json.loads(regra.get("palavras_chave", "[]") or "[]")
        if kws and not any(kw.lower() in text.lower() for kw in kws):
            continue

        pasta = regra.get("pasta_destino", "").strip()
        if pasta and os.path.isdir(pasta):
            doc = db.get_doc(doc_id)
            src = doc.get("caminho_entrada", "") if doc else ""
            if src and os.path.exists(src):
                prefixo  = regra.get("prefixo_nome", "") or ""
                nome_base= Path(src).name
                nome_final = f"{prefixo}{datetime.now().strftime('%Y-%m-%d')}_{nome_base}" if prefixo else nome_base
                dst = os.path.join(pasta, nome_final)
                try:
                    shutil.move(src, dst)
                    db.update_doc(doc_id, caminho_final=dst, nome_final=nome_final, regra_id=regra["id"])
                    logger.info(f"Doc {doc_id} movido → {dst} (regra: {regra['nome']})")
                except Exception as e:
                    logger.error(f"Erro ao mover doc {doc_id}: {e}")
        break  # primeira regra que bate


# ── Processamento principal ───────────────────────────────────────────────────

def process_file(doc_id: int, path: str, tipo_hint: str = "", lang: str = "por"):
    import database as db
    db.update_doc(doc_id, status="processando")
    try:
        text      = _do_ocr(path, lang)
        fields    = _extract_fields(text)
        validacoes= _validate_fields(fields)
        tipo      = _classify(text, tipo_hint)
        db.update_doc(
            doc_id,
            status        = "concluido",
            tipo          = tipo,
            ocr_texto     = text,
            campos        = json.dumps(fields, ensure_ascii=False),
            validacoes    = json.dumps(validacoes, ensure_ascii=False),
            processado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        _apply_rules(doc_id, tipo, text)
        logger.info(f"Doc {doc_id} concluído — tipo: {tipo}")
    except Exception as e:
        logger.error(f"Erro ao processar doc {doc_id}: {e}", exc_info=True)
        db.update_doc(
            doc_id,
            status        = "erro",
            observacao    = str(e),
            processado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


# ── Loop do worker ────────────────────────────────────────────────────────────

def _worker_loop():
    logger.info("Worker OCR iniciado.")
    while True:
        try:
            item = doc_queue.get(timeout=5)
            if item is None:
                break
            doc_id, path, tipo_hint, lang = item
            logger.info(f"Processando doc {doc_id}: {path}")
            process_file(doc_id, path, tipo_hint, lang)
            doc_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)


def start_worker():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_thread = threading.Thread(
        target=_worker_loop, daemon=True, name="tiresias-worker"
    )
    _worker_thread.start()


def enqueue(doc_id: int, path: str, tipo_hint: str = "", lang: str = "por"):
    doc_queue.put((doc_id, path, tipo_hint, lang))


# ── Watchdog ──────────────────────────────────────────────────────────────────

def start_watchdog(pasta: str):
    global _watchdog_observer
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logger.warning("watchdog não instalado — monitoramento de pasta desabilitado.")
        return

    if not os.path.isdir(pasta):
        logger.warning(f"Pasta de entrada não existe: {pasta}")
        return

    import database as db
    _EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}

    class Handler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            path = event.src_path
            if Path(path).suffix.lower() not in _EXTS:
                return
            time.sleep(0.5)
            logger.info(f"Watchdog: {path}")
            cfg    = db.get_config()
            lang   = cfg.get("idioma_ocr", "por")
            doc_id = db.add_doc(nome_original=Path(path).name, caminho_entrada=path)
            enqueue(doc_id, path, "", lang)

    if _watchdog_observer:
        try:
            _watchdog_observer.stop()
        except Exception:
            pass

    _watchdog_observer = Observer()
    _watchdog_observer.schedule(Handler(), pasta, recursive=False)
    _watchdog_observer.daemon = True
    _watchdog_observer.start()
    logger.info(f"Watchdog ativo em: {pasta}")
