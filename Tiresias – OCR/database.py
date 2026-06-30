from __future__ import annotations
"""
database.py — Tiresias OCR · Persistência SQLite
"""
import hashlib
import os
import sqlite3
from datetime import date

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "tiresias.db")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS documentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_original   TEXT NOT NULL,
            nome_final      TEXT,
            tipo            TEXT DEFAULT 'desconhecido',
            status          TEXT DEFAULT 'pendente',
            ocr_texto       TEXT,
            campos          TEXT DEFAULT '{}',
            validacoes      TEXT DEFAULT '[]',
            caminho_entrada TEXT,
            caminho_final   TEXT,
            regra_id        INTEGER,
            observacao      TEXT,
            hash_sha256     TEXT,
            duplicata_de    INTEGER,
            criado_em       TEXT DEFAULT (datetime('now','localtime')),
            processado_em   TEXT
        );

        CREATE TABLE IF NOT EXISTS regras (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT NOT NULL,
            tipo_doc        TEXT DEFAULT 'generico',
            palavras_chave  TEXT DEFAULT '[]',
            pasta_destino   TEXT DEFAULT '',
            prefixo_nome    TEXT DEFAULT '',
            exportar_sqlite INTEGER DEFAULT 0,
            ativo           INTEGER DEFAULT 1,
            criado_em       TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT
        );
        """)
        # Migração — colunas adicionadas em versões posteriores
        existing = {r[1] for r in c.execute("PRAGMA table_info(documentos)").fetchall()}
        if "hash_sha256" not in existing:
            c.execute("ALTER TABLE documentos ADD COLUMN hash_sha256 TEXT")
        if "duplicata_de" not in existing:
            c.execute("ALTER TABLE documentos ADD COLUMN duplicata_de INTEGER")
        # Índice sempre via CREATE INDEX (não pode estar no executescript com tabela antiga)
        c.execute("CREATE INDEX IF NOT EXISTS idx_doc_hash ON documentos (hash_sha256)")

        defaults = {
            "pasta_entrada":    "",
            "pasta_saida":      "",
            "idioma_ocr":       "por",
            "validar_cpf_cnpj": "1",
            "renomear_arquivos":"1",
            "exportar_sqlite":  "0",
            "ocr_engine":       "tesseract",
            "monitorar_pasta":  "0",
        }
        for k, v in defaults.items():
            c.execute(
                "INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)",
                (k, v)
            )


# ── Hash / duplicata ──────────────────────────────────────────────────────────

def sha256_file(path: str, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def find_by_hash(hash_sha256: str) -> dict | None:
    """Retorna o documento mais antigo com esse hash, ou None."""
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM documentos WHERE hash_sha256 = ? ORDER BY id ASC LIMIT 1",
            (hash_sha256,),
        ).fetchone()
        return dict(row) if row else None


# ── Documentos ────────────────────────────────────────────────────────────────

def add_doc(nome_original: str, caminho_entrada: str = "",
            tipo: str = "desconhecido", observacao: str = "",
            hash_sha256: str = "", duplicata_de: int | None = None) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO documentos"
            " (nome_original, caminho_entrada, tipo, observacao, hash_sha256, duplicata_de)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (nome_original, caminho_entrada, tipo, observacao,
             hash_sha256 or None, duplicata_de),
        )
        return cur.lastrowid


def get_doc(doc_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM documentos WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None


def list_docs(status: str = "", tipo: str = "", q: str = "",
              limit: int = 100, offset: int = 0) -> list[dict]:
    sql, params = "SELECT * FROM documentos WHERE 1=1", []
    if status:
        sql += " AND status = ?";         params.append(status)
    if tipo:
        sql += " AND tipo = ?";           params.append(tipo)
    if q:
        sql += " AND nome_original LIKE ?"; params.append(f"%{q}%")
    sql += " ORDER BY criado_em DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def update_doc(doc_id: int, **kwargs):
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [doc_id]
    with _conn() as c:
        c.execute(f"UPDATE documentos SET {cols} WHERE id = ?", vals)


def delete_doc(doc_id: int):
    with _conn() as c:
        c.execute("DELETE FROM documentos WHERE id = ?", (doc_id,))


def get_stats() -> dict:
    today = date.today().isoformat()
    with _conn() as c:
        hoje      = c.execute("SELECT COUNT(*) FROM documentos WHERE criado_em >= ?", (today,)).fetchone()[0]
        em_fila   = c.execute("SELECT COUNT(*) FROM documentos WHERE status IN ('pendente','processando')").fetchone()[0]
        concluidos= c.execute("SELECT COUNT(*) FROM documentos WHERE status = 'concluido'").fetchone()[0]
        erros     = c.execute("SELECT COUNT(*) FROM documentos WHERE status = 'erro'").fetchone()[0]
        total     = c.execute("SELECT COUNT(*) FROM documentos").fetchone()[0]
    taxa = round(concluidos / total * 100, 1) if total else 0
    return {
        "hoje": hoje, "em_fila": em_fila, "concluidos": concluidos,
        "erros": erros, "total": total, "taxa_sucesso": taxa,
    }


# ── Regras ────────────────────────────────────────────────────────────────────

def list_regras(ativo: bool | None = None) -> list[dict]:
    sql, params = "SELECT * FROM regras", []
    if ativo is not None:
        sql += " WHERE ativo = ?"; params.append(1 if ativo else 0)
    sql += " ORDER BY id"
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def get_regra(regra_id: int) -> dict | None:
    with _conn() as c:
        row = c.execute("SELECT * FROM regras WHERE id = ?", (regra_id,)).fetchone()
        return dict(row) if row else None


def add_regra(nome, tipo_doc, palavras_chave, pasta_destino,
              prefixo_nome, exportar_sqlite, ativo=1) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO regras (nome, tipo_doc, palavras_chave, pasta_destino,"
            " prefixo_nome, exportar_sqlite, ativo) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (nome, tipo_doc, palavras_chave, pasta_destino,
             prefixo_nome, exportar_sqlite, ativo),
        )
        return cur.lastrowid


def update_regra(regra_id: int, **kwargs):
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [regra_id]
    with _conn() as c:
        c.execute(f"UPDATE regras SET {cols} WHERE id = ?", vals)


def delete_regra(regra_id: int):
    with _conn() as c:
        c.execute("DELETE FROM regras WHERE id = ?", (regra_id,))


# ── Configurações ─────────────────────────────────────────────────────────────

def get_config() -> dict:
    with _conn() as c:
        rows = c.execute("SELECT chave, valor FROM configuracoes").fetchall()
        return {r["chave"]: r["valor"] for r in rows}


def set_config(data: dict):
    with _conn() as c:
        for k, v in data.items():
            c.execute(
                "INSERT OR REPLACE INTO configuracoes (chave, valor) VALUES (?, ?)",
                (k, str(v)),
            )


init_db()
