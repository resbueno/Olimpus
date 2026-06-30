from __future__ import annotations
"""
database.py — Hermes: Gestão de Ativos
SQLite — Usuários, Ativos, Categorias, Localizações,
         Movimentações, Manutenções, Depreciações
"""
import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hermes.db")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS departamentos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            nome             TEXT    NOT NULL,
            atlas_empresa_id INTEGER,
            criado_em        TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            email           TEXT    UNIQUE NOT NULL,
            senha_hash      TEXT    NOT NULL DEFAULT '',
            role            TEXT    NOT NULL DEFAULT 'colaborador',
            departamento_id INTEGER,
            cargo           TEXT    DEFAULT '',
            ativo           INTEGER NOT NULL DEFAULT 1,
            atlas_id        INTEGER,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
        );

        CREATE TABLE IF NOT EXISTS categorias_ativo (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT    NOT NULL,
            descricao         TEXT    DEFAULT '',
            vida_util_anos    INTEGER NOT NULL DEFAULT 5,
            taxa_depreciacao  REAL    NOT NULL DEFAULT 20.0,
            ativo             INTEGER NOT NULL DEFAULT 1,
            criado_em         TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS localizacoes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            descricao       TEXT    DEFAULT '',
            departamento_id INTEGER,
            ativo           INTEGER NOT NULL DEFAULT 1,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
        );

        CREATE TABLE IF NOT EXISTS ativos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT    NOT NULL,
            numero_patrimonio TEXT    UNIQUE,
            categoria_id      INTEGER,
            localizacao_id    INTEGER,
            responsavel_id    INTEGER,
            status            TEXT    NOT NULL DEFAULT 'ativo'
                              CHECK(status IN ('ativo','inativo','em_manutencao','descartado')),
            valor_aquisicao   REAL    DEFAULT 0,
            data_aquisicao    TEXT,
            fornecedor        TEXT    DEFAULT '',
            numero_serie      TEXT    DEFAULT '',
            descricao         TEXT    DEFAULT '',
            criado_por        INTEGER,
            criado_em         TEXT    NOT NULL,
            FOREIGN KEY (categoria_id)   REFERENCES categorias_ativo(id),
            FOREIGN KEY (localizacao_id) REFERENCES localizacoes(id),
            FOREIGN KEY (responsavel_id) REFERENCES users(id),
            FOREIGN KEY (criado_por)     REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS movimentacoes (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id             INTEGER NOT NULL,
            de_localizacao_id    INTEGER,
            para_localizacao_id  INTEGER,
            de_responsavel_id    INTEGER,
            para_responsavel_id  INTEGER,
            motivo               TEXT    DEFAULT '',
            data_movimentacao    TEXT    NOT NULL,
            registrado_por       INTEGER,
            criado_em            TEXT    NOT NULL,
            FOREIGN KEY (ativo_id)             REFERENCES ativos(id),
            FOREIGN KEY (de_localizacao_id)    REFERENCES localizacoes(id),
            FOREIGN KEY (para_localizacao_id)  REFERENCES localizacoes(id),
            FOREIGN KEY (de_responsavel_id)    REFERENCES users(id),
            FOREIGN KEY (para_responsavel_id)  REFERENCES users(id),
            FOREIGN KEY (registrado_por)       REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS manutencoes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id         INTEGER NOT NULL,
            tipo             TEXT    NOT NULL DEFAULT 'corretiva'
                             CHECK(tipo IN ('preventiva','corretiva')),
            status           TEXT    NOT NULL DEFAULT 'solicitada'
                             CHECK(status IN ('solicitada','em_andamento','concluida','cancelada')),
            descricao        TEXT    DEFAULT '',
            custo            REAL    DEFAULT 0,
            data_solicitacao TEXT    NOT NULL,
            data_conclusao   TEXT,
            tecnico          TEXT    DEFAULT '',
            solicitado_por   INTEGER,
            criado_em        TEXT    NOT NULL,
            FOREIGN KEY (ativo_id)       REFERENCES ativos(id),
            FOREIGN KEY (solicitado_por) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS depreciacoes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id       INTEGER NOT NULL,
            ano            INTEGER NOT NULL,
            valor_depreciado REAL  NOT NULL DEFAULT 0,
            valor_residual   REAL  NOT NULL DEFAULT 0,
            criado_em      TEXT    NOT NULL,
            UNIQUE(ativo_id, ano),
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        );
    """)

    # Admin padrão
    if not get_user_by_email("admin@olimpus.local"):
        conn.execute(
            "INSERT INTO users (nome, email, senha_hash, role, ativo, criado_em) VALUES (?,?,?,?,1,?)",
            ("Administrador", "admin@olimpus.local", _hash("Hermes@2024"), "admin", _now()),
        )

    # Categorias padrão
    defaults = [
        ("Equipamentos de TI",   5,  20.0),
        ("Móveis e Utensílios",  10, 10.0),
        ("Veículos",              5,  20.0),
        ("Máquinas e Equipamentos", 10, 10.0),
        ("Software / Licenças",   3,  33.3),
        ("Outros",               5,  20.0),
    ]
    for nome, vida, taxa in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO categorias_ativo (nome, vida_util_anos, taxa_depreciacao, ativo, criado_em) "
            "SELECT ?,?,?,1,? WHERE NOT EXISTS (SELECT 1 FROM categorias_ativo WHERE nome=?)",
            (nome, vida, taxa, _now(), nome),
        )

    conn.commit()
    conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row(r):
    return dict(r) if r else None


def _rows(rs):
    return [dict(r) for r in rs]


# ── Usuários ─────────────────────────────────────────────────────────────────

def get_user(uid: int):
    conn = get_conn()
    r = conn.execute(
        "SELECT u.*, d.nome AS departamento_nome "
        "FROM users u LEFT JOIN departamentos d ON d.id=u.departamento_id WHERE u.id=?", (uid,)
    ).fetchone()
    conn.close()
    return _row(r)


def get_user_by_email(email: str):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
    conn.close()
    return _row(r)


def check_password(email: str, senha: str) -> bool:
    u = get_user_by_email(email)
    return bool(u and u["senha_hash"] == _hash(senha) and u["ativo"])


def list_users(ativo_only=True):
    conn = get_conn()
    q = ("SELECT u.*, d.nome AS departamento_nome "
         "FROM users u LEFT JOIN departamentos d ON d.id=u.departamento_id")
    if ativo_only:
        q += " WHERE u.ativo=1"
    q += " ORDER BY u.nome"
    rs = conn.execute(q).fetchall()
    conn.close()
    return _rows(rs)


def update_user(uid: int, data: dict):
    allowed = {"nome", "cargo", "role", "departamento_id", "ativo"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE users SET {sets} WHERE id=?", [*fields.values(), uid])
    conn.commit()
    conn.close()


def get_or_create_user_from_atlas(atlas_user: dict):
    email     = (atlas_user.get("email") or "").strip().lower()
    atlas_id  = atlas_user.get("id")
    nome      = atlas_user.get("nome", "")
    cargo     = atlas_user.get("cargo", "")
    empresa_id = atlas_user.get("empresa_id")

    dept_id = None
    if empresa_id:
        dept = _get_dept_by_atlas_id(empresa_id)
        if dept:
            dept_id = dept["id"]

    conn = get_conn()
    existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    # Resolve role: RBAC v4.0 (ADMIN_GERAL, ADMIN, GESTOR, USER) > legado > funcoes
    role_sistema = atlas_user.get("_role_sistema", "")
    funcoes = atlas_user.get("funcoes", [])
    rs = role_sistema.upper()
    if rs in ("ADMIN_GERAL", "ADMIN"):
        role = "admin"
    elif rs == "GESTOR":
        role = "gestor"
    elif rs == "USER":
        role = "colaborador"
    elif role_sistema in ("admin", "gestor", "colaborador"):
        role = role_sistema
    else:
        role = "admin" if "admin" in funcoes else \
               "gestor" if any(f in funcoes for f in ("gestor", "rh", "financeiro")) else \
               "colaborador"

    if existing:
        conn.execute(
            "UPDATE users SET nome=?, cargo=?, atlas_id=?, role=?,"
            " departamento_id=COALESCE(?,departamento_id) WHERE id=?",
            (nome, cargo, atlas_id, role, dept_id, existing["id"]),
        )
        conn.commit()
        uid = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO users (nome, email, senha_hash, role, cargo, departamento_id, atlas_id, ativo, criado_em) "
            "VALUES (?,?,?,?,?,?,?,1,?)",
            (nome, email, "", role, cargo, dept_id, atlas_id, _now()),
        )
        conn.commit()
        uid = cur.lastrowid
    conn.close()
    return get_user(uid)


# ── Departamentos ─────────────────────────────────────────────────────────────

def _get_dept_by_atlas_id(atlas_id: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM departamentos WHERE atlas_empresa_id=?", (atlas_id,)).fetchone()
    conn.close()
    return _row(r)


def get_or_create_dept_from_atlas(atlas_id: int, nome: str):
    existing = _get_dept_by_atlas_id(atlas_id)
    if existing:
        return existing
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO departamentos (nome, atlas_empresa_id, criado_em) VALUES (?,?,?)",
        (nome, atlas_id, _now()),
    )
    conn.commit()
    did = cur.lastrowid
    conn.close()
    return get_departamento(did)


def list_departamentos():
    conn = get_conn()
    rs = conn.execute("SELECT * FROM departamentos ORDER BY nome").fetchall()
    conn.close()
    return _rows(rs)


def get_departamento(did: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM departamentos WHERE id=?", (did,)).fetchone()
    conn.close()
    return _row(r)


def create_departamento(data: dict):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO departamentos (nome, criado_em) VALUES (?,?)", (data["nome"], _now())
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


# ── Categorias de Ativo ───────────────────────────────────────────────────────

def list_categorias(ativo_only=True):
    conn = get_conn()
    q = "SELECT * FROM categorias_ativo"
    if ativo_only:
        q += " WHERE ativo=1"
    q += " ORDER BY nome"
    rs = conn.execute(q).fetchall()
    conn.close()
    return _rows(rs)


def get_categoria(cid: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM categorias_ativo WHERE id=?", (cid,)).fetchone()
    conn.close()
    return _row(r)


def create_categoria(data: dict):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO categorias_ativo (nome, descricao, vida_util_anos, taxa_depreciacao, ativo, criado_em) "
        "VALUES (?,?,?,?,1,?)",
        (data["nome"], data.get("descricao", ""),
         int(data.get("vida_util_anos", 5)), float(data.get("taxa_depreciacao", 20.0)), _now()),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_categoria(cid: int, data: dict):
    allowed = {"nome", "descricao", "vida_util_anos", "taxa_depreciacao", "ativo"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE categorias_ativo SET {sets} WHERE id=?", [*fields.values(), cid])
    conn.commit()
    conn.close()


# ── Localizações ──────────────────────────────────────────────────────────────

def list_localizacoes(ativo_only=True):
    conn = get_conn()
    q = ("SELECT l.*, d.nome AS departamento_nome "
         "FROM localizacoes l LEFT JOIN departamentos d ON d.id=l.departamento_id")
    if ativo_only:
        q += " WHERE l.ativo=1"
    q += " ORDER BY l.nome"
    rs = conn.execute(q).fetchall()
    conn.close()
    return _rows(rs)


def get_localizacao(lid: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM localizacoes WHERE id=?", (lid,)).fetchone()
    conn.close()
    return _row(r)


def create_localizacao(data: dict):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO localizacoes (nome, descricao, departamento_id, ativo, criado_em) VALUES (?,?,?,1,?)",
        (data["nome"], data.get("descricao", ""), data.get("departamento_id"), _now()),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_localizacao(lid: int, data: dict):
    allowed = {"nome", "descricao", "departamento_id", "ativo"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE localizacoes SET {sets} WHERE id=?", [*fields.values(), lid])
    conn.commit()
    conn.close()


# ── Ativos ────────────────────────────────────────────────────────────────────

def _ativo_select():
    return (
        "SELECT a.*, "
        "c.nome AS categoria_nome, "
        "l.nome AS localizacao_nome, "
        "u.nome AS responsavel_nome "
        "FROM ativos a "
        "LEFT JOIN categorias_ativo c ON c.id=a.categoria_id "
        "LEFT JOIN localizacoes l ON l.id=a.localizacao_id "
        "LEFT JOIN users u ON u.id=a.responsavel_id "
    )


def list_ativos(status=None, categoria_id=None, localizacao_id=None, q_text=None, limit=300, offset=0):
    conn = get_conn()
    sql = _ativo_select() + "WHERE 1=1 "
    p: list = []
    if status:
        sql += "AND a.status=? "; p.append(status)
    if categoria_id:
        sql += "AND a.categoria_id=? "; p.append(categoria_id)
    if localizacao_id:
        sql += "AND a.localizacao_id=? "; p.append(localizacao_id)
    if q_text:
        sql += "AND (a.nome LIKE ? OR a.numero_patrimonio LIKE ? OR a.numero_serie LIKE ?) "
        p.extend([f"%{q_text}%", f"%{q_text}%", f"%{q_text}%"])
    sql += "ORDER BY a.nome LIMIT ? OFFSET ?"
    p.extend([limit, offset])
    rs = conn.execute(sql, p).fetchall()
    conn.close()
    return _rows(rs)


def get_ativo(aid: int):
    conn = get_conn()
    r = conn.execute(_ativo_select() + "WHERE a.id=?", (aid,)).fetchone()
    conn.close()
    return _row(r)


def create_ativo(data: dict, user_id: int):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO ativos (nome, numero_patrimonio, categoria_id, localizacao_id, responsavel_id, "
        "status, valor_aquisicao, data_aquisicao, fornecedor, numero_serie, descricao, criado_por, criado_em) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            data["nome"],
            data.get("numero_patrimonio") or None,
            data.get("categoria_id"),
            data.get("localizacao_id"),
            data.get("responsavel_id"),
            data.get("status", "ativo"),
            float(data.get("valor_aquisicao", 0)),
            data.get("data_aquisicao"),
            data.get("fornecedor", ""),
            data.get("numero_serie", ""),
            data.get("descricao", ""),
            user_id,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_ativo(aid: int, data: dict):
    allowed = {"nome", "numero_patrimonio", "categoria_id", "localizacao_id", "responsavel_id",
               "status", "valor_aquisicao", "data_aquisicao", "fornecedor", "numero_serie", "descricao"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE ativos SET {sets} WHERE id=?", [*fields.values(), aid])
    conn.commit()
    conn.close()


def delete_ativo(aid: int):
    conn = get_conn()
    conn.execute("DELETE FROM ativos WHERE id=?", (aid,))
    conn.commit()
    conn.close()


# ── Movimentações ─────────────────────────────────────────────────────────────

def list_movimentacoes(ativo_id=None, limit=100):
    conn = get_conn()
    sql = (
        "SELECT m.*, a.nome AS ativo_nome, a.numero_patrimonio, "
        "dl.nome AS de_local, pl.nome AS para_local, "
        "dr.nome AS de_resp, pr.nome AS para_resp, "
        "rb.nome AS registrado_nome "
        "FROM movimentacoes m "
        "LEFT JOIN ativos a ON a.id=m.ativo_id "
        "LEFT JOIN localizacoes dl ON dl.id=m.de_localizacao_id "
        "LEFT JOIN localizacoes pl ON pl.id=m.para_localizacao_id "
        "LEFT JOIN users dr ON dr.id=m.de_responsavel_id "
        "LEFT JOIN users pr ON pr.id=m.para_responsavel_id "
        "LEFT JOIN users rb ON rb.id=m.registrado_por "
    )
    p: list = []
    if ativo_id:
        sql += "WHERE m.ativo_id=? "; p.append(ativo_id)
    sql += "ORDER BY m.criado_em DESC LIMIT ?"
    p.append(limit)
    rs = conn.execute(sql, p).fetchall()
    conn.close()
    return _rows(rs)


def create_movimentacao(data: dict, user_id: int):
    ativo = get_ativo(data["ativo_id"])
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO movimentacoes (ativo_id, de_localizacao_id, para_localizacao_id, "
        "de_responsavel_id, para_responsavel_id, motivo, data_movimentacao, registrado_por, criado_em) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            data["ativo_id"],
            ativo["localizacao_id"] if ativo else None,
            data.get("para_localizacao_id"),
            ativo["responsavel_id"] if ativo else None,
            data.get("para_responsavel_id"),
            data.get("motivo", ""),
            data.get("data_movimentacao", _now()[:10]),
            user_id,
            _now(),
        ),
    )
    # Atualiza localização e responsável do ativo
    upd: dict = {}
    if data.get("para_localizacao_id") is not None:
        upd["localizacao_id"] = data["para_localizacao_id"]
    if data.get("para_responsavel_id") is not None:
        upd["responsavel_id"] = data["para_responsavel_id"]
    if upd:
        sets = ", ".join(f"{k}=?" for k in upd)
        conn.execute(f"UPDATE ativos SET {sets} WHERE id=?", [*upd.values(), data["ativo_id"]])
    conn.commit()
    conn.close()
    return cur.lastrowid


# ── Manutenções ───────────────────────────────────────────────────────────────

def list_manutencoes(ativo_id=None, status=None, limit=200):
    conn = get_conn()
    sql = (
        "SELECT m.*, a.nome AS ativo_nome, a.numero_patrimonio, u.nome AS solicitado_nome "
        "FROM manutencoes m "
        "LEFT JOIN ativos a ON a.id=m.ativo_id "
        "LEFT JOIN users u ON u.id=m.solicitado_por "
        "WHERE 1=1 "
    )
    p: list = []
    if ativo_id:
        sql += "AND m.ativo_id=? "; p.append(ativo_id)
    if status:
        sql += "AND m.status=? "; p.append(status)
    sql += "ORDER BY m.criado_em DESC LIMIT ?"
    p.append(limit)
    rs = conn.execute(sql, p).fetchall()
    conn.close()
    return _rows(rs)


def get_manutencao(mid: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM manutencoes WHERE id=?", (mid,)).fetchone()
    conn.close()
    return _row(r)


def create_manutencao(data: dict, user_id: int):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO manutencoes (ativo_id, tipo, status, descricao, custo, data_solicitacao, "
        "data_conclusao, tecnico, solicitado_por, criado_em) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            data["ativo_id"],
            data.get("tipo", "corretiva"),
            data.get("status", "solicitada"),
            data.get("descricao", ""),
            float(data.get("custo", 0)),
            data.get("data_solicitacao", _now()[:10]),
            data.get("data_conclusao"),
            data.get("tecnico", ""),
            user_id,
            _now(),
        ),
    )
    # Coloca ativo em manutenção se status for solicitada/em_andamento
    if data.get("status") in ("solicitada", "em_andamento"):
        conn.execute("UPDATE ativos SET status='em_manutencao' WHERE id=?", (data["ativo_id"],))
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_manutencao(mid: int, data: dict):
    allowed = {"tipo", "status", "descricao", "custo", "data_solicitacao", "data_conclusao", "tecnico"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE manutencoes SET {sets} WHERE id=?", [*fields.values(), mid])
    # Se concluída, volta ativo para status ativo
    if data.get("status") == "concluida":
        m = conn.execute("SELECT ativo_id FROM manutencoes WHERE id=?", (mid,)).fetchone()
        if m:
            conn.execute("UPDATE ativos SET status='ativo' WHERE id=? AND status='em_manutencao'",
                         (m["ativo_id"],))
    conn.commit()
    conn.close()


# ── Depreciação ───────────────────────────────────────────────────────────────

def calcular_depreciacao(ativo_id: int):
    """Calcula depreciação anual pelo método linear e salva/atualiza na tabela."""
    a = get_ativo(ativo_id)
    if not a or not a["valor_aquisicao"] or not a["data_aquisicao"]:
        return []
    cat = get_categoria(a["categoria_id"]) if a["categoria_id"] else None
    vida_util = cat["vida_util_anos"] if cat else 5
    taxa = (cat["taxa_depreciacao"] / 100) if cat else 0.2

    ano_aquisicao = int(a["data_aquisicao"][:4])
    valor = float(a["valor_aquisicao"])
    valor_residual = valor * 0.10  # 10% de valor residual
    depreciacao_anual = (valor - valor_residual) / vida_util

    conn = get_conn()
    resultado = []
    val_restante = valor
    for i in range(vida_util):
        ano = ano_aquisicao + i
        dep = min(depreciacao_anual, val_restante - valor_residual)
        val_restante -= dep
        conn.execute(
            "INSERT INTO depreciacoes (ativo_id, ano, valor_depreciado, valor_residual, criado_em) "
            "VALUES (?,?,?,?,?) ON CONFLICT(ativo_id, ano) "
            "DO UPDATE SET valor_depreciado=excluded.valor_depreciado, valor_residual=excluded.valor_residual",
            (ativo_id, ano, round(dep, 2), round(val_restante, 2), _now()),
        )
        resultado.append({"ano": ano, "valor_depreciado": round(dep, 2), "valor_residual": round(val_restante, 2)})
    conn.commit()
    conn.close()
    return resultado


def get_depreciacao(ativo_id: int):
    conn = get_conn()
    rs = conn.execute(
        "SELECT * FROM depreciacoes WHERE ativo_id=? ORDER BY ano", (ativo_id,)
    ).fetchall()
    conn.close()
    return _rows(rs)


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard():
    conn = get_conn()
    total       = conn.execute("SELECT COUNT(*) FROM ativos WHERE status!='descartado'").fetchone()[0]
    em_manut    = conn.execute("SELECT COUNT(*) FROM ativos WHERE status='em_manutencao'").fetchone()[0]
    descartados = conn.execute("SELECT COUNT(*) FROM ativos WHERE status='descartado'").fetchone()[0]
    valor_total = conn.execute("SELECT COALESCE(SUM(valor_aquisicao),0) FROM ativos WHERE status!='descartado'").fetchone()[0]

    por_cat = conn.execute(
        "SELECT c.nome, COUNT(a.id) AS qtd "
        "FROM ativos a LEFT JOIN categorias_ativo c ON c.id=a.categoria_id "
        "WHERE a.status!='descartado' "
        "GROUP BY a.categoria_id ORDER BY qtd DESC LIMIT 8"
    ).fetchall()

    movs_recentes = conn.execute(
        "SELECT m.*, a.nome AS ativo_nome, a.numero_patrimonio, "
        "pl.nome AS para_local, pr.nome AS para_resp "
        "FROM movimentacoes m "
        "LEFT JOIN ativos a ON a.id=m.ativo_id "
        "LEFT JOIN localizacoes pl ON pl.id=m.para_localizacao_id "
        "LEFT JOIN users pr ON pr.id=m.para_responsavel_id "
        "ORDER BY m.criado_em DESC LIMIT 5"
    ).fetchall()

    manut_abertas = conn.execute(
        "SELECT COUNT(*) FROM manutencoes WHERE status IN ('solicitada','em_andamento')"
    ).fetchone()[0]

    conn.close()
    return {
        "total_ativos":    total,
        "em_manutencao":   em_manut,
        "descartados":     descartados,
        "valor_total":     round(valor_total, 2),
        "manut_abertas":   manut_abertas,
        "por_categoria":   _rows(por_cat),
        "movs_recentes":   _rows(movs_recentes),
    }
