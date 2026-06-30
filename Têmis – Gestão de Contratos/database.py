from __future__ import annotations
"""
database.py — Camada de persistência SQLite do Têmis
Fases 1-4: contratos, fiscal, IA, alertas
"""

import os
import sqlite3
from datetime import datetime, timedelta

from cryptography.fernet import Fernet

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "temis.db")
KEY_PATH  = os.path.join(BASE_DIR, "temis.key")
FILES_DIR = os.path.join(BASE_DIR, "contratos")

STATUSES = ["rascunho", "revisao", "aprovacao", "assinatura", "vigente", "encerrado", "cancelado"]

TRIBUTOS = ["ISS", "ICMS", "PIS", "COFINS", "IRPJ", "CSLL", "INSS", "IRRF", "ISSQN", "Outro"]

# ── Criptografia ──────────────────────────────────────────────────────────────

def _get_or_create_key() -> bytes:
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    return key


def _cipher() -> Fernet:
    return Fernet(_get_or_create_key())


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(FILES_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS contracts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo           TEXT    NOT NULL,
            tipo             TEXT    NOT NULL DEFAULT 'Prestação de Serviços',
            numero_contrato  TEXT,
            objeto           TEXT,
            valor            REAL,
            moeda            TEXT    DEFAULT 'BRL',
            contraparte      TEXT,
            contraparte_cnpj TEXT,
            data_inicio      TEXT,
            data_fim         TEXT,
            dias_alerta      INTEGER DEFAULT 60,
            status           TEXT    DEFAULT 'rascunho',
            arquivo_path     TEXT,
            arquivo_nome     TEXT,
            criado_por       TEXT,
            criado_em        TEXT    DEFAULT CURRENT_TIMESTAMP,
            atualizado_em    TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS contract_versions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id     INTEGER NOT NULL,
            numero_versao   INTEGER NOT NULL,
            arquivo_path    TEXT,
            arquivo_nome    TEXT,
            observacoes     TEXT,
            criado_por      TEXT,
            criado_em       TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        );

        CREATE TABLE IF NOT EXISTS signatories (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id  INTEGER NOT NULL,
            nome         TEXT    NOT NULL,
            email        TEXT    NOT NULL,
            papel        TEXT    DEFAULT 'signatário',
            ordem        INTEGER DEFAULT 1,
            status       TEXT    DEFAULT 'pendente',
            assinado_em  TEXT,
            token        TEXT,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id  INTEGER,
            acao         TEXT    NOT NULL,
            usuario      TEXT,
            detalhes     TEXT,
            criado_em    TEXT    DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS contract_taxes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id     INTEGER NOT NULL,
            tributo         TEXT    NOT NULL,
            modalidade      TEXT    DEFAULT 'retenção',
            aliquota        REAL,
            base_calculo    TEXT    DEFAULT 'valor_contrato',
            valor_previsto  REAL,
            valor_realizado REAL,
            centro_custo    TEXT,
            natureza        TEXT,
            responsavel     TEXT    DEFAULT 'tomador',
            observacoes     TEXT,
            criado_por      TEXT,
            criado_em       TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        );

        CREATE TABLE IF NOT EXISTS fiscal_events (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id     INTEGER NOT NULL,
            tax_id          INTEGER,
            tipo            TEXT    NOT NULL,
            descricao       TEXT,
            data_prevista   TEXT    NOT NULL,
            data_realizada  TEXT,
            valor_previsto  REAL,
            valor_realizado REAL,
            status          TEXT    DEFAULT 'pendente',
            competencia     TEXT,
            observacoes     TEXT,
            criado_por      TEXT,
            criado_em       TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id),
            FOREIGN KEY (tax_id)      REFERENCES contract_taxes(id)
        );

        CREATE TABLE IF NOT EXISTS ia_analyses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id     INTEGER NOT NULL UNIQUE,
            score_risco     INTEGER,
            resumo          TEXT,
            riscos          TEXT,
            clausulas_faltantes TEXT,
            recomendacoes   TEXT,
            raw_response    TEXT,
            analisado_em    TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contract_id) REFERENCES contracts(id)
        );

        CREATE TABLE IF NOT EXISTS alert_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id     INTEGER,
            tipo_alerta     TEXT,
            destinatarios   TEXT,
            assunto         TEXT,
            status          TEXT    DEFAULT 'enviado',
            erro            TEXT,
            enviado_em      TEXT    DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


# ── Conexão ───────────────────────────────────────────────────────────────────

def _conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


# ── Contracts ─────────────────────────────────────────────────────────────────

def list_contracts(status: str = None, search: str = None) -> list:
    conn = _conn()
    q = "SELECT * FROM contracts WHERE 1=1"
    params = []
    if status:
        q += " AND status = ?"
        params.append(status)
    if search:
        like = f"%{search}%"
        q += " AND (titulo LIKE ? OR contraparte LIKE ? OR numero_contrato LIKE ? OR objeto LIKE ?)"
        params.extend([like, like, like, like])
    q += " ORDER BY criado_em DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contract(contract_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_contract(data: dict, usuario: str) -> int:
    conn = _conn()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
        INSERT INTO contracts
            (titulo, tipo, numero_contrato, objeto, valor, moeda,
             contraparte, contraparte_cnpj, data_inicio, data_fim,
             dias_alerta, status, arquivo_path, arquivo_nome, criado_por, criado_em, atualizado_em)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data.get("titulo", ""),
        data.get("tipo", "Prestação de Serviços"),
        data.get("numero_contrato", ""),
        data.get("objeto", ""),
        data.get("valor") or None,
        data.get("moeda", "BRL"),
        data.get("contraparte", ""),
        data.get("contraparte_cnpj", ""),
        data.get("data_inicio") or None,
        data.get("data_fim") or None,
        int(data.get("dias_alerta", 60)),
        data.get("status", "rascunho"),
        data.get("arquivo_path") or None,
        data.get("arquivo_nome") or None,
        usuario, now, now,
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    _audit(new_id, "criou contrato", usuario, f"Título: {data.get('titulo')}")
    return new_id


def update_contract(contract_id: int, data: dict, usuario: str) -> bool:
    conn = _conn()
    fields, values = [], []
    mapping = {
        "titulo": "titulo", "tipo": "tipo", "numero_contrato": "numero_contrato",
        "objeto": "objeto", "valor": "valor", "moeda": "moeda",
        "contraparte": "contraparte", "contraparte_cnpj": "contraparte_cnpj",
        "data_inicio": "data_inicio", "data_fim": "data_fim",
        "dias_alerta": "dias_alerta", "status": "status",
        "arquivo_path": "arquivo_path", "arquivo_nome": "arquivo_nome",
    }
    for key, col in mapping.items():
        if key in data:
            fields.append(f"{col} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return False
    fields.append("atualizado_em = ?")
    values.append(datetime.now().isoformat())
    values.append(contract_id)
    conn.execute(f"UPDATE contracts SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    _audit(contract_id, "atualizou contrato", usuario, str({k: v for k, v in data.items() if k != "objeto"}))
    return True


def delete_contract(contract_id: int, usuario: str) -> bool:
    conn = _conn()
    contract = get_contract(contract_id)
    for t in ["signatories", "contract_versions", "contract_taxes", "fiscal_events",
              "ia_analyses", "alert_log"]:
        conn.execute(f"DELETE FROM {t} WHERE contract_id = ?", (contract_id,))
    conn.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
    conn.commit()
    conn.close()
    _audit(None, "excluiu contrato", usuario, f"ID {contract_id}: {contract.get('titulo') if contract else ''}")
    return True


def advance_status(contract_id: int, novo_status: str, usuario: str) -> bool:
    if novo_status not in STATUSES:
        return False
    conn = _conn()
    conn.execute(
        "UPDATE contracts SET status = ?, atualizado_em = ? WHERE id = ?",
        (novo_status, datetime.now().isoformat(), contract_id),
    )
    conn.commit()
    conn.close()
    _audit(contract_id, f"status → {novo_status}", usuario, "")
    return True


# ── Versions ──────────────────────────────────────────────────────────────────

def add_version(contract_id: int, arquivo_path: str, arquivo_nome: str, observacoes: str, usuario: str) -> int:
    conn = _conn()
    c = conn.cursor()
    last = conn.execute(
        "SELECT MAX(numero_versao) FROM contract_versions WHERE contract_id = ?", (contract_id,)
    ).fetchone()[0] or 0
    c.execute("""
        INSERT INTO contract_versions (contract_id, numero_versao, arquivo_path, arquivo_nome, observacoes, criado_por)
        VALUES (?,?,?,?,?,?)
    """, (contract_id, last + 1, arquivo_path, arquivo_nome, observacoes, usuario))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    _audit(contract_id, f"adicionou versão {last + 1}", usuario, arquivo_nome)
    return new_id


def list_versions(contract_id: int) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM contract_versions WHERE contract_id = ? ORDER BY numero_versao DESC",
        (contract_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Signatories ───────────────────────────────────────────────────────────────

def list_signatories(contract_id: int) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM signatories WHERE contract_id = ? ORDER BY ordem",
        (contract_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_signatory(contract_id: int, data: dict, usuario: str) -> int:
    import secrets
    conn = _conn()
    c = conn.cursor()
    token = secrets.token_urlsafe(32)
    c.execute("""
        INSERT INTO signatories (contract_id, nome, email, papel, ordem, status, token)
        VALUES (?,?,?,?,?,?,?)
    """, (
        contract_id, data["nome"], data["email"],
        data.get("papel", "signatário"),
        int(data.get("ordem", 1)),
        "pendente", token,
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    _audit(contract_id, "adicionou signatário", usuario, f"{data['nome']} <{data['email']}>")
    return new_id


def remove_signatory(signatory_id: int, usuario: str):
    conn = _conn()
    row = conn.execute("SELECT * FROM signatories WHERE id = ?", (signatory_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM signatories WHERE id = ?", (signatory_id,))
        conn.commit()
        _audit(dict(row)["contract_id"], "removeu signatário", usuario, dict(row)["nome"])
    conn.close()


def sign_contract(token: str) -> dict:
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM signatories WHERE token = ? AND status = 'pendente'", (token,)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "Token inválido ou já utilizado."}
    sig = dict(row)
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE signatories SET status = 'assinado', assinado_em = ?, token = NULL WHERE id = ?",
        (now, sig["id"]),
    )
    conn.commit()
    pending = conn.execute(
        "SELECT COUNT(*) FROM signatories WHERE contract_id = ? AND status = 'pendente'",
        (sig["contract_id"],),
    ).fetchone()[0]
    if pending == 0:
        conn.execute(
            "UPDATE contracts SET status = 'vigente', atualizado_em = ? WHERE id = ? AND status = 'assinatura'",
            (now, sig["contract_id"]),
        )
        conn.commit()
    conn.close()
    _audit(sig["contract_id"], "assinou contrato", sig["nome"], f"Signatário: {sig['email']}")
    return {"ok": True, "nome": sig["nome"], "contract_id": sig["contract_id"]}


# ── Audit Log ─────────────────────────────────────────────────────────────────

def _audit(contract_id, acao: str, usuario: str, detalhes: str = ""):
    conn = _conn()
    conn.execute(
        "INSERT INTO audit_log (contract_id, acao, usuario, detalhes) VALUES (?,?,?,?)",
        (contract_id, acao, usuario or "sistema", detalhes or ""),
    )
    conn.commit()
    conn.close()


def get_audit_log(contract_id: int = None, limit: int = 100) -> list:
    conn = _conn()
    if contract_id:
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE contract_id = ? ORDER BY criado_em DESC LIMIT ?",
            (contract_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT a.*, c.titulo as contract_titulo FROM audit_log a "
            "LEFT JOIN contracts c ON a.contract_id = c.id "
            "ORDER BY a.criado_em DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Contract Taxes (Módulo Fiscal) ────────────────────────────────────────────

def list_taxes(contract_id: int) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM contract_taxes WHERE contract_id = ? ORDER BY tributo",
        (contract_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_tax(contract_id: int, data: dict, usuario: str) -> int:
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO contract_taxes
            (contract_id, tributo, modalidade, aliquota, base_calculo,
             valor_previsto, valor_realizado, centro_custo, natureza, responsavel, observacoes, criado_por)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        contract_id,
        data.get("tributo", ""), data.get("modalidade", "retenção"),
        data.get("aliquota") or None, data.get("base_calculo", "valor_contrato"),
        data.get("valor_previsto") or None, data.get("valor_realizado") or None,
        data.get("centro_custo", ""), data.get("natureza", ""),
        data.get("responsavel", "tomador"), data.get("observacoes", ""), usuario,
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    _audit(contract_id, "adicionou tributo", usuario, f"{data.get('tributo')} {data.get('aliquota', '')}%")
    return new_id


def update_tax(tax_id: int, data: dict, usuario: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT * FROM contract_taxes WHERE id = ?", (tax_id,)).fetchone()
    if not row:
        conn.close()
        return False
    fields, values = [], []
    for key in ["tributo", "modalidade", "aliquota", "base_calculo", "valor_previsto",
                "valor_realizado", "centro_custo", "natureza", "responsavel", "observacoes"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return False
    values.append(tax_id)
    conn.execute(f"UPDATE contract_taxes SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    cid = dict(row)["contract_id"]
    conn.close()
    _audit(cid, "atualizou tributo", usuario, str(data))
    return True


def delete_tax(tax_id: int, usuario: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT * FROM contract_taxes WHERE id = ?", (tax_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM fiscal_events WHERE tax_id = ?", (tax_id,))
        conn.execute("DELETE FROM contract_taxes WHERE id = ?", (tax_id,))
        conn.commit()
        _audit(dict(row)["contract_id"], "removeu tributo", usuario, dict(row)["tributo"])
    conn.close()
    return True


def get_fiscal_summary(contract_id: int) -> dict:
    conn = _conn()
    taxes = conn.execute(
        "SELECT * FROM contract_taxes WHERE contract_id = ?", (contract_id,)
    ).fetchall()
    events = conn.execute(
        "SELECT * FROM fiscal_events WHERE contract_id = ? ORDER BY data_prevista",
        (contract_id,),
    ).fetchall()
    today = datetime.today().date().isoformat()

    total_prev  = sum((r["valor_previsto"] or 0) for r in taxes)
    total_real  = sum((r["valor_realizado"] or 0) for r in taxes)
    vencidos    = [e for e in events if dict(e)["data_prevista"] < today and dict(e)["status"] == "pendente"]
    a_vencer    = [e for e in events
                   if today <= dict(e)["data_prevista"] <= (
                       datetime.today().date() + timedelta(days=15)
                   ).isoformat() and dict(e)["status"] == "pendente"]
    conn.close()
    return {
        "taxes":         [dict(r) for r in taxes],
        "events":        [dict(r) for r in events],
        "total_previsto": total_prev,
        "total_realizado": total_real,
        "divergencia":   total_real - total_prev,
        "eventos_vencidos": len(vencidos),
        "eventos_a_vencer_15d": len(a_vencer),
    }


# ── Fiscal Events ─────────────────────────────────────────────────────────────

def list_fiscal_events(contract_id: int) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT fe.*, ct.tributo FROM fiscal_events fe "
        "LEFT JOIN contract_taxes ct ON fe.tax_id = ct.id "
        "WHERE fe.contract_id = ? ORDER BY fe.data_prevista",
        (contract_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_fiscal_event(contract_id: int, data: dict, usuario: str) -> int:
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO fiscal_events
            (contract_id, tax_id, tipo, descricao, data_prevista,
             valor_previsto, competencia, observacoes, criado_por)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        contract_id,
        data.get("tax_id") or None,
        data.get("tipo", ""), data.get("descricao", ""),
        data.get("data_prevista", ""),
        data.get("valor_previsto") or None,
        data.get("competencia", ""), data.get("observacoes", ""), usuario,
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    _audit(contract_id, "adicionou evento fiscal", usuario, f"{data.get('tipo')} em {data.get('data_prevista')}")
    return new_id


def update_fiscal_event(event_id: int, data: dict, usuario: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT * FROM fiscal_events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return False
    fields, values = [], []
    for key in ["tipo", "descricao", "data_prevista", "data_realizada",
                "valor_previsto", "valor_realizado", "status", "competencia", "observacoes"]:
        if key in data:
            fields.append(f"{key} = ?")
            values.append(data[key])
    if not fields:
        conn.close()
        return False
    values.append(event_id)
    conn.execute(f"UPDATE fiscal_events SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    cid = dict(row)["contract_id"]
    conn.close()
    _audit(cid, "atualizou evento fiscal", usuario, str(data))
    return True


def delete_fiscal_event(event_id: int, usuario: str) -> bool:
    conn = _conn()
    row = conn.execute("SELECT * FROM fiscal_events WHERE id = ?", (event_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM fiscal_events WHERE id = ?", (event_id,))
        conn.commit()
        _audit(dict(row)["contract_id"], "removeu evento fiscal", usuario, dict(row)["descricao"])
    conn.close()
    return True


# ── IA Analysis ───────────────────────────────────────────────────────────────

def save_analysis(contract_id: int, analysis: dict):
    import json
    conn = _conn()
    conn.execute("""
        INSERT INTO ia_analyses
            (contract_id, score_risco, resumo, riscos, clausulas_faltantes, recomendacoes, raw_response, analisado_em)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(contract_id) DO UPDATE SET
            score_risco = excluded.score_risco, resumo = excluded.resumo,
            riscos = excluded.riscos, clausulas_faltantes = excluded.clausulas_faltantes,
            recomendacoes = excluded.recomendacoes, raw_response = excluded.raw_response,
            analisado_em = excluded.analisado_em
    """, (
        contract_id,
        analysis.get("score_risco"),
        analysis.get("resumo", ""),
        json.dumps(analysis.get("riscos", []), ensure_ascii=False),
        json.dumps(analysis.get("clausulas_faltantes", []), ensure_ascii=False),
        json.dumps(analysis.get("recomendacoes", []), ensure_ascii=False),
        analysis.get("raw_response", ""),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_analysis(contract_id: int):
    import json
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM ia_analyses WHERE contract_id = ?", (contract_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for key in ["riscos", "clausulas_faltantes", "recomendacoes"]:
        try:
            d[key] = json.loads(d[key] or "[]")
        except Exception:
            d[key] = []
    return d


# ── Alert Log ─────────────────────────────────────────────────────────────────

def log_alert(contract_id, tipo: str, destinatarios: str, assunto: str, status: str = "enviado", erro: str = ""):
    conn = _conn()
    conn.execute(
        "INSERT INTO alert_log (contract_id, tipo_alerta, destinatarios, assunto, status, erro) VALUES (?,?,?,?,?,?)",
        (contract_id, tipo, destinatarios, assunto, status, erro),
    )
    conn.commit()
    conn.close()


def get_alert_log(contract_id: int = None, limit: int = 100) -> list:
    conn = _conn()
    if contract_id:
        rows = conn.execute(
            "SELECT * FROM alert_log WHERE contract_id = ? ORDER BY enviado_em DESC LIMIT ?",
            (contract_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT al.*, c.titulo FROM alert_log al "
            "LEFT JOIN contracts c ON al.contract_id = c.id "
            "ORDER BY al.enviado_em DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Alertas / Vencimentos ─────────────────────────────────────────────────────

def get_expiring_contracts(days: int = 60) -> list:
    today = datetime.today().date()
    cutoff = (today + timedelta(days=days)).isoformat()
    today_str = today.isoformat()
    conn = _conn()
    rows = conn.execute("""
        SELECT *, CAST(julianday(data_fim) - julianday('now') AS INTEGER) as dias_restantes
        FROM contracts
        WHERE data_fim IS NOT NULL
          AND data_fim >= ? AND data_fim <= ?
          AND status IN ('vigente','assinatura','aprovacao')
        ORDER BY data_fim ASC
    """, (today_str, cutoff)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expired_contracts() -> list:
    today = datetime.today().date().isoformat()
    conn = _conn()
    rows = conn.execute("""
        SELECT *, CAST(julianday('now') - julianday(data_fim) AS INTEGER) as dias_vencidos
        FROM contracts
        WHERE data_fim IS NOT NULL AND data_fim < ?
          AND status IN ('vigente','assinatura')
        ORDER BY data_fim ASC
    """, (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_pending_signatures() -> list:
    conn = _conn()
    rows = conn.execute("""
        SELECT s.*, c.titulo, c.numero_contrato, c.contraparte
        FROM signatories s
        JOIN contracts c ON s.contract_id = c.id
        WHERE s.status = 'pendente' AND c.status = 'assinatura'
        ORDER BY c.id, s.ordem
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_overdue_fiscal_events() -> list:
    today = datetime.today().date().isoformat()
    conn = _conn()
    rows = conn.execute("""
        SELECT fe.*, c.titulo, c.numero_contrato, c.contraparte
        FROM fiscal_events fe
        JOIN contracts c ON fe.contract_id = c.id
        WHERE fe.status = 'pendente' AND fe.data_prevista < ?
        ORDER BY fe.data_prevista
    """, (today,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_upcoming_fiscal_events(days: int = 7) -> list:
    today = datetime.today().date()
    cutoff = (today + timedelta(days=days)).isoformat()
    today_str = today.isoformat()
    conn = _conn()
    rows = conn.execute("""
        SELECT fe.*, c.titulo, c.numero_contrato, c.contraparte
        FROM fiscal_events fe
        JOIN contracts c ON fe.contract_id = c.id
        WHERE fe.status = 'pendente'
          AND fe.data_prevista >= ? AND fe.data_prevista <= ?
        ORDER BY fe.data_prevista
    """, (today_str, cutoff)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    conn = _conn()
    total     = conn.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    vigentes  = conn.execute("SELECT COUNT(*) FROM contracts WHERE status = 'vigente'").fetchone()[0]
    rascunhos = conn.execute("SELECT COUNT(*) FROM contracts WHERE status = 'rascunho'").fetchone()[0]
    pendentes = conn.execute("SELECT COUNT(*) FROM contracts WHERE status IN ('revisao','aprovacao','assinatura')").fetchone()[0]
    valor_total = conn.execute("SELECT SUM(valor) FROM contracts WHERE status = 'vigente'").fetchone()[0] or 0
    conn.close()
    expiring = get_expiring_contracts(60)
    expired  = get_expired_contracts()
    overdue_fiscal = get_overdue_fiscal_events()
    return {
        "total": total,
        "vigentes": vigentes,
        "rascunhos": rascunhos,
        "pendentes": pendentes,
        "valor_vigentes": valor_total,
        "a_vencer_60d": len(expiring),
        "vencidos": len(expired),
        "fiscal_vencidos": len(overdue_fiscal),
    }
