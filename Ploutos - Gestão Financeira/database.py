from __future__ import annotations
"""
database.py — Ploutos: Gestão Financeira
SQLite — Usuários, Departamentos, Centro de Custos, Categorias,
         Lançamentos, Orçamentos
"""
import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ploutos.db")


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

        CREATE TABLE IF NOT EXISTS centro_custos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL,
            descricao TEXT    DEFAULT '',
            ativo     INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categorias (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nome           TEXT    NOT NULL,
            tipo           TEXT    NOT NULL CHECK(tipo IN ('receita','despesa')),
            centro_custo_id INTEGER,
            ativo          INTEGER NOT NULL DEFAULT 1,
            criado_em      TEXT    NOT NULL,
            FOREIGN KEY (centro_custo_id) REFERENCES centro_custos(id)
        );

        CREATE TABLE IF NOT EXISTS lancamentos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao        TEXT    NOT NULL,
            valor            REAL    NOT NULL,
            tipo             TEXT    NOT NULL CHECK(tipo IN ('receita','despesa')),
            status           TEXT    NOT NULL DEFAULT 'pendente'
                             CHECK(status IN ('pendente','pago','recebido','cancelado')),
            data_vencimento  TEXT    NOT NULL,
            data_pagamento   TEXT,
            categoria_id     INTEGER,
            favorecido       TEXT    DEFAULT '',
            observacao       TEXT    DEFAULT '',
            criado_por       INTEGER,
            criado_em        TEXT    NOT NULL,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id),
            FOREIGN KEY (criado_por)   REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS orcamentos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ano             INTEGER NOT NULL,
            mes             INTEGER NOT NULL,
            categoria_id    INTEGER NOT NULL,
            valor_planejado REAL    NOT NULL DEFAULT 0,
            criado_em       TEXT    NOT NULL,
            UNIQUE(ano, mes, categoria_id),
            FOREIGN KEY (categoria_id) REFERENCES categorias(id)
        );
    """)

    # Usuário admin padrão (fallback sem Atlas)
    if not get_user_by_email("admin@olimpus.local"):
        conn.execute(
            "INSERT INTO users (nome, email, senha_hash, role, ativo, criado_em) "
            "VALUES (?,?,?,?,1,?)",
            ("Administrador", "admin@olimpus.local", _hash("Ploutos@2024"),
             "admin", _now()),
        )

    # Categorias padrão
    conn.execute("""
        INSERT OR IGNORE INTO categorias (nome, tipo, ativo, criado_em)
        SELECT 'Vendas',          'receita', 1, ? WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE nome='Vendas')
    """, (_now(),))
    conn.execute("""
        INSERT OR IGNORE INTO categorias (nome, tipo, ativo, criado_em)
        SELECT 'Serviços Prestados', 'receita', 1, ? WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE nome='Serviços Prestados')
    """, (_now(),))
    conn.execute("""
        INSERT OR IGNORE INTO categorias (nome, tipo, ativo, criado_em)
        SELECT 'Folha de Pagamento', 'despesa', 1, ? WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE nome='Folha de Pagamento')
    """, (_now(),))
    conn.execute("""
        INSERT OR IGNORE INTO categorias (nome, tipo, ativo, criado_em)
        SELECT 'Fornecedores',   'despesa', 1, ? WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE nome='Fornecedores')
    """, (_now(),))
    conn.execute("""
        INSERT OR IGNORE INTO categorias (nome, tipo, ativo, criado_em)
        SELECT 'Impostos',       'despesa', 1, ? WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE nome='Impostos')
    """, (_now(),))
    conn.execute("""
        INSERT OR IGNORE INTO categorias (nome, tipo, ativo, criado_em)
        SELECT 'Despesas Gerais','despesa', 1, ? WHERE NOT EXISTS (SELECT 1 FROM categorias WHERE nome='Despesas Gerais')
    """, (_now(),))

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
        "FROM users u LEFT JOIN departamentos d ON d.id=u.departamento_id "
        "WHERE u.id=?", (uid,)
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


def list_users(departamento_id=None, ativo_only=True):
    conn = get_conn()
    q = ("SELECT u.*, d.nome AS departamento_nome "
         "FROM users u LEFT JOIN departamentos d ON d.id=u.departamento_id WHERE 1=1")
    p: list = []
    if ativo_only:
        q += " AND u.ativo=1"
    if departamento_id:
        q += " AND u.departamento_id=?"
        p.append(departamento_id)
    q += " ORDER BY u.nome"
    rs = conn.execute(q, p).fetchall()
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
    """Upsert: cria ou atualiza colaborador vindo do Atlas."""
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
    existing = conn.execute(
        "SELECT * FROM users WHERE email=?", (email,)
    ).fetchone()

    # Resolve role: RBAC v4.0 (ADMIN_GERAL, ADMIN, GESTOR, USER) > legado > funcoes
    role_sistema = atlas_user.get("_role_sistema", "")
    funcoes = atlas_user.get("funcoes", [])
    rs = role_sistema.upper()
    if rs in ("ADMIN_GERAL", "ADMIN"):
        role = "admin"
    elif rs == "GESTOR":
        role = "financeiro"
    elif rs == "USER":
        role = "colaborador"
    elif role_sistema in ("admin", "financeiro", "colaborador"):
        role = role_sistema
    else:
        role = "admin" if "admin" in funcoes else \
               "financeiro" if any(f in funcoes for f in ("financeiro", "finance", "rh", "gestor")) else \
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
    r = conn.execute(
        "SELECT * FROM departamentos WHERE atlas_empresa_id=?", (atlas_id,)
    ).fetchone()
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
        "INSERT INTO departamentos (nome, criado_em) VALUES (?,?)",
        (data["nome"], _now()),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_departamento(did: int, data: dict):
    if "nome" not in data:
        return
    conn = get_conn()
    conn.execute("UPDATE departamentos SET nome=? WHERE id=?", (data["nome"], did))
    conn.commit()
    conn.close()


def delete_departamento(did: int):
    conn = get_conn()
    conn.execute("DELETE FROM departamentos WHERE id=?", (did,))
    conn.commit()
    conn.close()


# ── Centro de Custos ──────────────────────────────────────────────────────────

def list_centro_custos(ativo_only=True):
    conn = get_conn()
    q = "SELECT * FROM centro_custos"
    if ativo_only:
        q += " WHERE ativo=1"
    q += " ORDER BY nome"
    rs = conn.execute(q).fetchall()
    conn.close()
    return _rows(rs)


def get_centro_custo(cid: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM centro_custos WHERE id=?", (cid,)).fetchone()
    conn.close()
    return _row(r)


def create_centro_custo(data: dict):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO centro_custos (nome, descricao, ativo, criado_em) VALUES (?,?,1,?)",
        (data["nome"], data.get("descricao", ""), _now()),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_centro_custo(cid: int, data: dict):
    allowed = {"nome", "descricao", "ativo"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE centro_custos SET {sets} WHERE id=?", [*fields.values(), cid])
    conn.commit()
    conn.close()


def delete_centro_custo(cid: int):
    conn = get_conn()
    conn.execute("DELETE FROM centro_custos WHERE id=?", (cid,))
    conn.commit()
    conn.close()


# ── Categorias ────────────────────────────────────────────────────────────────

def list_categorias(tipo=None, ativo_only=True):
    conn = get_conn()
    q = ("SELECT c.*, cc.nome AS centro_custo_nome "
         "FROM categorias c LEFT JOIN centro_custos cc ON cc.id=c.centro_custo_id "
         "WHERE 1=1")
    p: list = []
    if ativo_only:
        q += " AND c.ativo=1"
    if tipo:
        q += " AND c.tipo=?"
        p.append(tipo)
    q += " ORDER BY c.tipo, c.nome"
    rs = conn.execute(q, p).fetchall()
    conn.close()
    return _rows(rs)


def get_categoria(cid: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM categorias WHERE id=?", (cid,)).fetchone()
    conn.close()
    return _row(r)


def create_categoria(data: dict):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO categorias (nome, tipo, centro_custo_id, ativo, criado_em) VALUES (?,?,?,1,?)",
        (data["nome"], data["tipo"], data.get("centro_custo_id"), _now()),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_categoria(cid: int, data: dict):
    allowed = {"nome", "tipo", "centro_custo_id", "ativo"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE categorias SET {sets} WHERE id=?", [*fields.values(), cid])
    conn.commit()
    conn.close()


def delete_categoria(cid: int):
    conn = get_conn()
    conn.execute("DELETE FROM categorias WHERE id=?", (cid,))
    conn.commit()
    conn.close()


# ── Lançamentos ───────────────────────────────────────────────────────────────

def list_lancamentos(tipo=None, status=None, categoria_id=None,
                     data_inicio=None, data_fim=None, limit=200, offset=0):
    conn = get_conn()
    q = ("SELECT l.*, c.nome AS categoria_nome, c.tipo AS categoria_tipo "
         "FROM lancamentos l LEFT JOIN categorias c ON c.id=l.categoria_id WHERE 1=1")
    p: list = []
    if tipo:
        q += " AND l.tipo=?"; p.append(tipo)
    if status:
        q += " AND l.status=?"; p.append(status)
    if categoria_id:
        q += " AND l.categoria_id=?"; p.append(categoria_id)
    if data_inicio:
        q += " AND l.data_vencimento>=?"; p.append(data_inicio)
    if data_fim:
        q += " AND l.data_vencimento<=?"; p.append(data_fim)
    q += " ORDER BY l.data_vencimento DESC LIMIT ? OFFSET ?"
    p.extend([limit, offset])
    rs = conn.execute(q, p).fetchall()
    conn.close()
    return _rows(rs)


def get_lancamento(lid: int):
    conn = get_conn()
    r = conn.execute(
        "SELECT l.*, c.nome AS categoria_nome "
        "FROM lancamentos l LEFT JOIN categorias c ON c.id=l.categoria_id "
        "WHERE l.id=?", (lid,)
    ).fetchone()
    conn.close()
    return _row(r)


def create_lancamento(data: dict, user_id: int):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO lancamentos "
        "(descricao, valor, tipo, status, data_vencimento, data_pagamento, "
        " categoria_id, favorecido, observacao, criado_por, criado_em) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            data["descricao"],
            float(data["valor"]),
            data["tipo"],
            data.get("status", "pendente"),
            data["data_vencimento"],
            data.get("data_pagamento"),
            data.get("categoria_id"),
            data.get("favorecido", ""),
            data.get("observacao", ""),
            user_id,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid


def update_lancamento(lid: int, data: dict):
    allowed = {"descricao", "valor", "tipo", "status", "data_vencimento",
               "data_pagamento", "categoria_id", "favorecido", "observacao"}
    fields  = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    conn = get_conn()
    conn.execute(f"UPDATE lancamentos SET {sets} WHERE id=?", [*fields.values(), lid])
    conn.commit()
    conn.close()


def delete_lancamento(lid: int):
    conn = get_conn()
    conn.execute("DELETE FROM lancamentos WHERE id=?", (lid,))
    conn.commit()
    conn.close()


# ── Orçamentos ────────────────────────────────────────────────────────────────

def list_orcamentos(ano: int, mes: int):
    conn = get_conn()
    rs = conn.execute(
        "SELECT o.*, c.nome AS categoria_nome, c.tipo AS categoria_tipo "
        "FROM orcamentos o JOIN categorias c ON c.id=o.categoria_id "
        "WHERE o.ano=? AND o.mes=? ORDER BY c.tipo, c.nome",
        (ano, mes),
    ).fetchall()
    conn.close()
    return _rows(rs)


def upsert_orcamento(ano: int, mes: int, categoria_id: int, valor: float):
    conn = get_conn()
    conn.execute(
        "INSERT INTO orcamentos (ano, mes, categoria_id, valor_planejado, criado_em) "
        "VALUES (?,?,?,?,?) ON CONFLICT(ano,mes,categoria_id) "
        "DO UPDATE SET valor_planejado=excluded.valor_planejado",
        (ano, mes, categoria_id, valor, _now()),
    )
    conn.commit()
    conn.close()


# ── Dashboard / Resumos ───────────────────────────────────────────────────────

def get_dashboard(hoje: str, inicio_mes: str, fim_mes: str):
    conn = get_conn()

    # A receber no mês (receitas pendentes com vencimento no mês)
    a_receber = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM lancamentos "
        "WHERE tipo='receita' AND status='pendente' "
        "AND data_vencimento BETWEEN ? AND ?",
        (inicio_mes, fim_mes),
    ).fetchone()[0]

    # A pagar no mês (despesas pendentes com vencimento no mês)
    a_pagar = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM lancamentos "
        "WHERE tipo='despesa' AND status='pendente' "
        "AND data_vencimento BETWEEN ? AND ?",
        (inicio_mes, fim_mes),
    ).fetchone()[0]

    # Total recebido no mês
    recebido = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM lancamentos "
        "WHERE tipo='receita' AND status='recebido' "
        "AND data_pagamento BETWEEN ? AND ?",
        (inicio_mes, fim_mes),
    ).fetchone()[0]

    # Total pago no mês
    pago = conn.execute(
        "SELECT COALESCE(SUM(valor),0) FROM lancamentos "
        "WHERE tipo='despesa' AND status='pago' "
        "AND data_pagamento BETWEEN ? AND ?",
        (inicio_mes, fim_mes),
    ).fetchone()[0]

    # Vencidos (pendentes com data_vencimento < hoje)
    vencidos_pagar = conn.execute(
        "SELECT COUNT(*) FROM lancamentos "
        "WHERE tipo='despesa' AND status='pendente' AND data_vencimento<?",
        (hoje,),
    ).fetchone()[0]

    vencidos_receber = conn.execute(
        "SELECT COUNT(*) FROM lancamentos "
        "WHERE tipo='receita' AND status='pendente' AND data_vencimento<?",
        (hoje,),
    ).fetchone()[0]

    # Próximos 7 dias a pagar
    conn.execute("SELECT DATE(?)", (hoje,))  # validate
    proximos = conn.execute(
        "SELECT * FROM lancamentos "
        "WHERE tipo='despesa' AND status='pendente' "
        "AND data_vencimento BETWEEN ? AND DATE(?,'+7 days') "
        "ORDER BY data_vencimento LIMIT 10",
        (hoje, hoje),
    ).fetchall()

    conn.close()
    return {
        "a_receber":      round(a_receber, 2),
        "a_pagar":        round(a_pagar, 2),
        "recebido":       round(recebido, 2),
        "pago":           round(pago, 2),
        "saldo_mes":      round(recebido - pago, 2),
        "vencidos_pagar": vencidos_pagar,
        "vencidos_receber": vencidos_receber,
        "proximos_pagamentos": _rows(proximos),
    }


def get_fluxo_caixa(ano: int):
    """Retorna entradas e saídas realizadas mês a mês no ano."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT strftime('%m', data_pagamento) AS mes, tipo, COALESCE(SUM(valor),0) AS total "
        "FROM lancamentos "
        "WHERE status IN ('pago','recebido') AND strftime('%Y', data_pagamento)=? "
        "GROUP BY mes, tipo ORDER BY mes",
        (str(ano),),
    ).fetchall()
    conn.close()
    result = {str(m).zfill(2): {"receita": 0.0, "despesa": 0.0} for m in range(1, 13)}
    for r in rows:
        result[r["mes"]][r["tipo"]] = round(r["total"], 2)
    return result


def get_orcamento_realizado(ano: int, mes: int):
    """Compara orçado vs realizado por categoria no mês."""
    conn = get_conn()
    cats = conn.execute(
        "SELECT c.id, c.nome, c.tipo, "
        "COALESCE(o.valor_planejado,0) AS planejado, "
        "COALESCE(SUM(l.valor),0) AS realizado "
        "FROM categorias c "
        "LEFT JOIN orcamentos o ON o.categoria_id=c.id AND o.ano=? AND o.mes=? "
        "LEFT JOIN lancamentos l ON l.categoria_id=c.id "
        "   AND l.status IN ('pago','recebido') "
        "   AND strftime('%Y-%m', l.data_pagamento)=? "
        "WHERE c.ativo=1 "
        "GROUP BY c.id ORDER BY c.tipo, c.nome",
        (ano, mes, f"{ano}-{str(mes).zfill(2)}"),
    ).fetchall()
    conn.close()
    return _rows(cats)
