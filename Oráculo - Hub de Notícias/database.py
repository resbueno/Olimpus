from __future__ import annotations
"""
database.py — Persistência SQLite do Oráculo
"""
import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "oraculo.db")


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
        CREATE TABLE IF NOT EXISTS departments (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            nome                TEXT    NOT NULL,
            descricao           TEXT    DEFAULT '',
            email_responsavel   TEXT    DEFAULT '',
            horario_newsletter  TEXT    NOT NULL DEFAULT '08:00',
            criado_em           TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            email           TEXT    UNIQUE NOT NULL,
            senha_hash      TEXT    NOT NULL,
            role            TEXT    NOT NULL DEFAULT 'leitor',
            departamento_id INTEGER,
            ativo           INTEGER NOT NULL DEFAULT 1,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departments(id)
        );
        CREATE TABLE IF NOT EXISTS categories (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT    NOT NULL UNIQUE,
            cor  TEXT    NOT NULL DEFAULT '#2563eb'
        );
        CREATE TABLE IF NOT EXISTS department_categories (
            departamento_id INTEGER NOT NULL,
            categoria_id    INTEGER NOT NULL,
            PRIMARY KEY (departamento_id, categoria_id),
            FOREIGN KEY (departamento_id) REFERENCES departments(id) ON DELETE CASCADE,
            FOREIGN KEY (categoria_id)    REFERENCES categories(id)  ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS news_sources (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT    NOT NULL,
            url           TEXT    NOT NULL,
            tipo          TEXT    NOT NULL DEFAULT 'rss',
            ativo         INTEGER NOT NULL DEFAULT 1,
            ultima_coleta TEXT,
            criado_em     TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS news (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo       TEXT    NOT NULL,
            resumo       TEXT    DEFAULT '',
            conteudo     TEXT    DEFAULT '',
            url          TEXT    DEFAULT '',
            fonte_id     INTEGER,
            publicado_em TEXT,
            coletado_em  TEXT    NOT NULL,
            relevancia   REAL    NOT NULL DEFAULT 0.5,
            FOREIGN KEY (fonte_id) REFERENCES news_sources(id)
        );
        CREATE TABLE IF NOT EXISTS news_categories (
            news_id      INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            PRIMARY KEY (news_id, categoria_id),
            FOREIGN KEY (news_id)      REFERENCES news(id)       ON DELETE CASCADE,
            FOREIGN KEY (categoria_id) REFERENCES categories(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS kpis (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            descricao       TEXT    DEFAULT '',
            unidade         TEXT    DEFAULT '',
            departamento_id INTEGER,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departments(id)
        );
        CREATE TABLE IF NOT EXISTS kpi_values (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            kpi_id    INTEGER NOT NULL,
            valor     REAL    NOT NULL,
            data      TEXT    NOT NULL,
            fonte     TEXT    DEFAULT '',
            criado_em TEXT    NOT NULL,
            FOREIGN KEY (kpi_id) REFERENCES kpis(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS insights (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo          TEXT    NOT NULL,
            descricao       TEXT    NOT NULL,
            impacto         TEXT    NOT NULL DEFAULT 'medio',
            correlacao_tipo TEXT    DEFAULT '',
            news_id         INTEGER,
            kpi_id          INTEGER,
            departamento_id INTEGER,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (news_id)         REFERENCES news(id),
            FOREIGN KEY (kpi_id)          REFERENCES kpis(id),
            FOREIGN KEY (departamento_id) REFERENCES departments(id)
        );
        CREATE TABLE IF NOT EXISTS newsletters (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            departamento_id INTEGER NOT NULL,
            conteudo_json   TEXT    NOT NULL,
            gerado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departments(id)
        );
        CREATE TABLE IF NOT EXISTS newsletter_dispatches (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            newsletter_id  INTEGER NOT NULL,
            enviado_em     TEXT,
            status         TEXT    NOT NULL DEFAULT 'pendente',
            destinatarios  INTEGER DEFAULT 0,
            mensagem_erro  TEXT    DEFAULT '',
            FOREIGN KEY (newsletter_id) REFERENCES newsletters(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS smtp_config (
            id        INTEGER PRIMARY KEY,
            host      TEXT    NOT NULL DEFAULT '',
            porta     INTEGER NOT NULL DEFAULT 587,
            usuario   TEXT    NOT NULL DEFAULT '',
            senha     TEXT    NOT NULL DEFAULT '',
            use_tls   INTEGER NOT NULL DEFAULT 1,
            remetente TEXT    NOT NULL DEFAULT '',
            ativo     INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()

    # Seed departamento e admin padrão
    if not conn.execute("SELECT 1 FROM departments").fetchone():
        conn.execute(
            "INSERT INTO departments(nome,descricao,email_responsavel,criado_em) VALUES(?,?,?,?)",
            ("TI", "Tecnologia da Informação", "ti@empresa.local", _now())
        )
        conn.commit()
    dept_id = conn.execute("SELECT id FROM departments LIMIT 1").fetchone()[0]

    if not conn.execute("SELECT 1 FROM users WHERE email='admin@olimpus.local'").fetchone():
        conn.execute(
            "INSERT INTO users(nome,email,senha_hash,role,departamento_id,criado_em) VALUES(?,?,?,?,?,?)",
            ("Administrador", "admin@olimpus.local", _hash("Oraculo@2024"), "admin", dept_id, _now())
        )
        conn.commit()

    # Migration: adiciona atlas_empresa_id na tabela departments (versões antigas)
    try:
        conn.execute("ALTER TABLE departments ADD COLUMN atlas_empresa_id INTEGER")
        conn.commit()
    except Exception:
        pass  # coluna já existe

    # SMTP config row
    if not conn.execute("SELECT 1 FROM smtp_config").fetchone():
        conn.execute("INSERT INTO smtp_config(id) VALUES(1)")
        conn.commit()

    # Categorias padrão
    default_cats = [
        ("Negócios",    "#2563eb"),
        ("Tecnologia",  "#7c3aed"),
        ("Mercado",     "#0284c7"),
        ("RH",          "#16a34a"),
        ("Jurídico",    "#d97706"),
        ("Finanças",    "#dc2626"),
    ]
    for nome, cor in default_cats:
        if not conn.execute("SELECT 1 FROM categories WHERE nome=?", (nome,)).fetchone():
            conn.execute("INSERT INTO categories(nome,cor) VALUES(?,?)", (nome, cor))
    conn.commit()
    conn.close()


# ── Users ──────────────────────────────────────────────────────────────────────

def get_user(uid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def get_user_by_email(email):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(r) if r else None


def list_users(active_only=True):
    conn = get_conn()
    q = """
        SELECT u.id,u.nome,u.email,u.role,u.ativo,u.criado_em,u.departamento_id,
               d.nome as departamento_nome
        FROM users u LEFT JOIN departments d ON u.departamento_id=d.id
    """
    if active_only:
        q += " WHERE u.ativo=1"
    r = conn.execute(q + " ORDER BY u.nome").fetchall()
    conn.close()
    return [dict(x) for x in r]


def create_user(data) -> int:
    senha = data.get("senha") or ""
    senha_hash = _hash(senha) if senha else hashlib.sha256(os.urandom(32)).hexdigest()
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users(nome,email,senha_hash,role,departamento_id,criado_em) VALUES(?,?,?,?,?,?)",
        (data["nome"], data["email"], senha_hash,
         data.get("role", "leitor"), data.get("departamento_id") or None, _now())
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_user(uid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "email", "role", "ativo", "departamento_id"]:
        if f in data:
            fields.append(f"{f}=?")
            vals.append(data[f])
    if data.get("senha"):
        fields.append("senha_hash=?")
        vals.append(_hash(data["senha"]))
    if fields:
        vals.append(uid)
        conn.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_user(uid):
    conn = get_conn()
    conn.execute("UPDATE users SET ativo=0 WHERE id=?", (uid,))
    conn.commit()
    conn.close()


def check_password(email, pw) -> bool:
    u = get_user_by_email(email)
    return bool(u and u["ativo"] and u["senha_hash"] == _hash(pw))


def _map_atlas_role(funcoes: list, role_sistema: str = "") -> str:
    """Roles válidas no Oráculo: admin > editor > leitor.
    Compatível com RBAC v4.0 e legado."""
    rs = role_sistema.upper()
    if rs in ("ADMIN_GERAL", "ADMIN"):
        return "admin"
    if rs == "GESTOR":
        return "editor"
    if rs == "USER":
        return "leitor"
    if role_sistema in ("admin", "editor", "leitor"):
        return role_sistema
    if "admin" in funcoes:
        return "admin"
    if "editor" in funcoes or "gestor" in funcoes or "operador" in funcoes:
        return "editor"
    return "leitor"


# Mapeamento automático nome-de-departamento → categoria do Oráculo
_DEPT_TO_CAT = {
    "ti":                    "Tecnologia",
    "t.i":                   "Tecnologia",
    "t.i.":                  "Tecnologia",
    "tecnologia":            "Tecnologia",
    "informatica":           "Tecnologia",
    "informática":           "Tecnologia",
    "desenvolvimento":       "Tecnologia",
    "devops":                "Tecnologia",
    "sistemas":              "Tecnologia",
    "financeiro":            "Finanças",
    "financas":              "Finanças",
    "finanças":              "Finanças",
    "contabilidade":         "Finanças",
    "controladoria":         "Finanças",
    "tesouraria":            "Finanças",
    "fiscal":                "Finanças",
    "rh":                    "RH",
    "recursos humanos":      "RH",
    "dp":                    "RH",
    "departamento pessoal":  "RH",
    "pessoal":               "RH",
    "gente e gestao":        "RH",
    "gente e gestão":        "RH",
    "juridico":              "Jurídico",
    "jurídico":              "Jurídico",
    "legal":                 "Jurídico",
    "compliance":            "Jurídico",
    "comercial":             "Negócios",
    "vendas":                "Negócios",
    "negocios":              "Negócios",
    "negócios":              "Negócios",
    "business":              "Negócios",
    "relacionamento":        "Negócios",
    "marketing":             "Mercado",
    "mercado":               "Mercado",
    "comunicacao":           "Mercado",
    "comunicação":           "Mercado",
    "growth":                "Mercado",
}


def _auto_assign_dept_categories(dept_id: int, dept_nome: str, conn):
    """
    Atribui categorias automaticamente a um departamento recém-criado
    com base no nome, se ainda não tiver nenhuma categoria.
    """
    existing = conn.execute(
        "SELECT 1 FROM department_categories WHERE departamento_id=?", (dept_id,)
    ).fetchone()
    if existing:
        return  # já tem categorias — não sobrescreve

    nome = dept_nome.lower().strip()
    # Remove prefixos comuns
    for prefix in ("departamento de ", "depto. de ", "setor de ", "área de ",
                   "gerência de ", "gerencia de ", "diretoria de "):
        if nome.startswith(prefix):
            nome = nome[len(prefix):]
            break

    matched_cat = _DEPT_TO_CAT.get(nome)
    if not matched_cat:
        for key, cat in _DEPT_TO_CAT.items():
            if key in nome:
                matched_cat = cat
                break

    if matched_cat:
        cat_row = conn.execute(
            "SELECT id FROM categories WHERE nome=?", (matched_cat,)
        ).fetchone()
        if cat_row:
            conn.execute(
                "INSERT OR IGNORE INTO department_categories(departamento_id,categoria_id)"
                " VALUES(?,?)",
                (dept_id, cat_row[0])
            )


def get_or_create_dept_from_atlas_empresa(empresa_id: int, empresa_nome: str) -> int:
    """
    Upsert de departamento a partir de uma empresa do Atlas.
    Identificação prioritária por atlas_empresa_id; fallback por nome.
    Retorna o id local do departamento.
    """
    conn = get_conn()
    # 1. Busca por atlas_empresa_id
    row = conn.execute(
        "SELECT id FROM departments WHERE atlas_empresa_id=?", (empresa_id,)
    ).fetchone()
    if row:
        conn.execute("UPDATE departments SET nome=? WHERE id=?", (empresa_nome, row[0]))
        conn.commit(); conn.close()
        return row[0]
    # 2. Fallback por nome (depts criados antes da integração)
    row = conn.execute(
        "SELECT id FROM departments WHERE nome=? AND (atlas_empresa_id IS NULL OR atlas_empresa_id=0)",
        (empresa_nome,)
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE departments SET atlas_empresa_id=? WHERE id=?", (empresa_id, row[0])
        )
        conn.commit()
        _auto_assign_dept_categories(row[0], empresa_nome, conn)
        conn.commit(); conn.close()
        return row[0]
    # 3. Cria novo
    c = conn.cursor()
    c.execute(
        "INSERT INTO departments(nome,atlas_empresa_id,criado_em) VALUES(?,?,?)",
        (empresa_nome, empresa_id, _now())
    )
    conn.commit()
    new_id = c.lastrowid
    _auto_assign_dept_categories(new_id, empresa_nome, conn)
    conn.commit(); conn.close()
    return new_id


def get_or_create_user_from_atlas(atlas_user: dict) -> dict:
    email        = (atlas_user.get("email") or "").lower().strip()
    nome         = atlas_user.get("nome") or email
    role         = _map_atlas_role(atlas_user.get("funcoes") or [], atlas_user.get("_role_sistema", ""))
    empresa_id   = atlas_user.get("empresa_id")
    empresa_nome = (atlas_user.get("empresa_nome") or "").strip()

    # Auto-sincroniza departamento a partir da empresa do Atlas
    dept_id = None
    if empresa_id and empresa_nome:
        dept_id = get_or_create_dept_from_atlas_empresa(empresa_id, empresa_nome)

    conn = get_conn()
    row  = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row:
        u = dict(row)
        updates = {}
        if u["nome"] != nome:
            updates["nome"] = nome
        if u["role"] != role:
            updates["role"] = role
        if dept_id and u.get("departamento_id") != dept_id:
            updates["departamento_id"] = dept_id
        if updates:
            fields = [f"{k}=?" for k in updates]
            vals   = list(updates.values()) + [u["id"]]
            conn.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", vals)
            conn.commit()
            u.update(updates)
        if not u["ativo"]:
            conn.execute("UPDATE users SET ativo=1 WHERE id=?", (u["id"],))
            conn.commit(); u["ativo"] = 1
        conn.close()
        return u

    dummy = hashlib.sha256(os.urandom(32)).hexdigest()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users(nome,email,senha_hash,role,departamento_id,criado_em) VALUES(?,?,?,?,?,?)",
        (nome, email, dummy, role, dept_id, _now())
    )
    conn.commit()
    uid = c.lastrowid; conn.close()
    return get_user(uid)


def change_password(uid, current, new_pw):
    u = get_user(uid)
    if not u or u["senha_hash"] != _hash(current):
        return False, "Senha atual incorreta."
    if len(new_pw) < 6:
        return False, "Nova senha deve ter pelo menos 6 caracteres."
    conn = get_conn()
    conn.execute("UPDATE users SET senha_hash=? WHERE id=?", (_hash(new_pw), uid))
    conn.commit(); conn.close()
    return True, "Senha alterada com sucesso."


# ── Departments ────────────────────────────────────────────────────────────────

def list_departments():
    conn = get_conn()
    rows = conn.execute("""
        SELECT d.*, COUNT(DISTINCT u.id) as total_usuarios,
               GROUP_CONCAT(c.id,   '||') as cat_ids,
               GROUP_CONCAT(c.nome, '||') as cat_nomes,
               GROUP_CONCAT(c.cor,  '||') as cat_cores
        FROM departments d
        LEFT JOIN users u ON u.departamento_id=d.id AND u.ativo=1
        LEFT JOIN department_categories dc ON dc.departamento_id=d.id
        LEFT JOIN categories c ON dc.categoria_id=c.id
        GROUP BY d.id ORDER BY d.nome
    """).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        ids   = (d.pop("cat_ids",   None) or "").split("||")
        nomes = (d.pop("cat_nomes", None) or "").split("||")
        cores = (d.pop("cat_cores", None) or "").split("||")
        d["categorias"] = [
            {"id": int(i), "nome": n, "cor": c}
            for i, n, c in zip(ids, nomes, cores) if i
        ]
        result.append(d)
    return result


def get_department(did):
    conn = get_conn()
    r = conn.execute("SELECT * FROM departments WHERE id=?", (did,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_department(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO departments(nome,descricao,email_responsavel,horario_newsletter,criado_em) VALUES(?,?,?,?,?)",
        (data["nome"], data.get("descricao", ""), data.get("email_responsavel", ""),
         data.get("horario_newsletter", "08:00"), _now())
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_department(did, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "descricao", "email_responsavel", "horario_newsletter"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(did)
        conn.execute(f"UPDATE departments SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_department(did):
    conn = get_conn()
    conn.execute("UPDATE users SET departamento_id=NULL WHERE departamento_id=?", (did,))
    conn.execute("DELETE FROM departments WHERE id=?", (did,))
    conn.commit(); conn.close()


def get_department_categories(did):
    conn = get_conn()
    r = conn.execute("""
        SELECT c.* FROM categories c
        JOIN department_categories dc ON dc.categoria_id=c.id
        WHERE dc.departamento_id=?
    """, (did,)).fetchall()
    conn.close()
    return [dict(x) for x in r]


def set_department_categories(did, cat_ids: list):
    conn = get_conn()
    conn.execute("DELETE FROM department_categories WHERE departamento_id=?", (did,))
    for cid in cat_ids:
        conn.execute(
            "INSERT OR IGNORE INTO department_categories(departamento_id,categoria_id) VALUES(?,?)",
            (did, cid)
        )
    conn.commit(); conn.close()


# ── Categories ─────────────────────────────────────────────────────────────────

def list_categories():
    conn = get_conn()
    r = conn.execute("""
        SELECT c.*, COUNT(DISTINCT nc.news_id) as total_noticias
        FROM categories c LEFT JOIN news_categories nc ON nc.categoria_id=c.id
        GROUP BY c.id ORDER BY c.nome
    """).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_category(cid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_category(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO categories(nome,cor) VALUES(?,?)", (data["nome"], data.get("cor", "#2563eb")))
    conn.commit()
    new_id = c.lastrowid; conn.close()
    return new_id


def update_category(cid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "cor"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(cid)
        conn.execute(f"UPDATE categories SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_category(cid):
    conn = get_conn()
    conn.execute("DELETE FROM categories WHERE id=?", (cid,))
    conn.commit(); conn.close()


# ── News Sources ───────────────────────────────────────────────────────────────

def list_sources():
    conn = get_conn()
    r = conn.execute("SELECT * FROM news_sources ORDER BY nome").fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_source(sid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM news_sources WHERE id=?", (sid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_source(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO news_sources(nome,url,tipo,ativo,criado_em) VALUES(?,?,?,?,?)",
        (data["nome"], data["url"], data.get("tipo", "rss"), 1, _now())
    )
    conn.commit()
    new_id = c.lastrowid; conn.close()
    return new_id


def update_source(sid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "url", "tipo", "ativo"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(sid)
        conn.execute(f"UPDATE news_sources SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_source(sid):
    conn = get_conn()
    conn.execute("UPDATE news SET fonte_id=NULL WHERE fonte_id=?", (sid,))
    conn.execute("DELETE FROM news_sources WHERE id=?", (sid,))
    conn.commit(); conn.close()


def update_source_last_fetch(sid):
    conn = get_conn()
    conn.execute("UPDATE news_sources SET ultima_coleta=? WHERE id=?", (_now(), sid))
    conn.commit(); conn.close()


# ── News ───────────────────────────────────────────────────────────────────────

_NSEL = """
    SELECT n.*, s.nome as fonte_nome,
           GROUP_CONCAT(c.nome, '||') as categorias_nomes,
           GROUP_CONCAT(c.cor,  '||') as categorias_cores,
           GROUP_CONCAT(c.id,   '||') as categorias_ids
    FROM news n
    LEFT JOIN news_sources s ON n.fonte_id=s.id
    LEFT JOIN news_categories nc ON nc.news_id=n.id
    LEFT JOIN categories c ON nc.categoria_id=c.id
    GROUP BY n.id
"""


def _parse_cats(row: dict) -> dict:
    """Converte os GROUP_CONCAT em lista de objetos."""
    nomes = (row.pop("categorias_nomes", None) or "").split("||")
    cores  = (row.pop("categorias_cores", None) or "").split("||")
    ids    = (row.pop("categorias_ids",   None) or "").split("||")
    row["categorias"] = [
        {"id": int(i), "nome": n, "cor": c}
        for i, n, c in zip(ids, nomes, cores) if i
    ]
    return row


def list_news(filters=None, limit=100):
    conn = get_conn()
    q = _NSEL
    w, v = [], []
    if filters:
        if filters.get("categoria_id"):
            w.append("nc.categoria_id=?"); v.append(filters["categoria_id"])
        if filters.get("fonte_id"):
            w.append("n.fonte_id=?"); v.append(filters["fonte_id"])
        if filters.get("min_relevancia"):
            w.append("n.relevancia>=?"); v.append(filters["min_relevancia"])
        if filters.get("desde"):
            w.append("n.coletado_em>=?"); v.append(filters["desde"])
    if w:
        q = q.replace("GROUP BY n.id", f"WHERE {' AND '.join(w)} GROUP BY n.id")
    q += f" ORDER BY n.coletado_em DESC LIMIT {int(limit)}"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [_parse_cats(dict(x)) for x in r]


def get_news(nid):
    conn = get_conn()
    r = conn.execute(_NSEL + " WHERE n.id=?", (nid,)).fetchone()
    conn.close()
    return _parse_cats(dict(r)) if r else None


def news_url_exists(url: str) -> bool:
    conn = get_conn()
    r = conn.execute("SELECT 1 FROM news WHERE url=?", (url,)).fetchone()
    conn.close()
    return bool(r)


def create_news(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO news(titulo,resumo,conteudo,url,fonte_id,publicado_em,coletado_em,relevancia)
           VALUES(?,?,?,?,?,?,?,?)""",
        (data["titulo"], data.get("resumo", ""), data.get("conteudo", ""),
         data.get("url", ""), data.get("fonte_id") or None,
         data.get("publicado_em") or _now()[:10],
         _now(), data.get("relevancia", 0.5))
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_news(nid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["titulo", "resumo", "conteudo", "url", "relevancia", "fonte_id"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(nid)
        conn.execute(f"UPDATE news SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_news(nid):
    conn = get_conn()
    conn.execute("DELETE FROM news_categories WHERE news_id=?", (nid,))
    conn.execute("DELETE FROM news WHERE id=?", (nid,))
    conn.commit(); conn.close()


def set_news_categories(nid, cat_ids: list):
    conn = get_conn()
    conn.execute("DELETE FROM news_categories WHERE news_id=?", (nid,))
    for cid in cat_ids:
        conn.execute(
            "INSERT OR IGNORE INTO news_categories(news_id,categoria_id) VALUES(?,?)",
            (nid, cid)
        )
    conn.commit(); conn.close()


def get_news_for_newsletter(departamento_id: int, since: str):
    """Retorna notícias relevantes para o departamento desde 'since' (ISO)."""
    conn = get_conn()
    # Tenta filtrar pelas categorias do departamento
    dept_cats = conn.execute(
        "SELECT categoria_id FROM department_categories WHERE departamento_id=?",
        (departamento_id,)
    ).fetchall()

    if dept_cats:
        placeholders = ",".join("?" * len(dept_cats))
        cat_ids = [r[0] for r in dept_cats]
        r = conn.execute(f"""
            SELECT DISTINCT n.id, n.titulo, n.resumo, n.url, n.relevancia, n.publicado_em,
                            GROUP_CONCAT(c.nome,'||') as categorias_nomes
            FROM news n
            JOIN news_categories nc ON nc.news_id=n.id AND nc.categoria_id IN ({placeholders})
            LEFT JOIN news_categories nc2 ON nc2.news_id=n.id
            LEFT JOIN categories c ON nc2.categoria_id=c.id
            WHERE n.coletado_em>=? AND n.relevancia>=0.5
            GROUP BY n.id
            ORDER BY n.relevancia DESC, n.coletado_em DESC LIMIT 5
        """, cat_ids + [since]).fetchall()
    else:
        # Departamento sem categorias configuradas — não inclui notícias na newsletter.
        # Administrador deve definir as categorias de interesse do departamento.
        conn.close()
        return []

    conn.close()
    return [dict(x) for x in r]


# ── KPIs ───────────────────────────────────────────────────────────────────────

def list_kpis(departamento_id=None):
    conn = get_conn()
    q = """
        SELECT k.*, d.nome as departamento_nome,
               (SELECT kv.valor FROM kpi_values kv WHERE kv.kpi_id=k.id ORDER BY kv.data DESC LIMIT 1) as ultimo_valor,
               (SELECT kv.data  FROM kpi_values kv WHERE kv.kpi_id=k.id ORDER BY kv.data DESC LIMIT 1) as ultima_data
        FROM kpis k LEFT JOIN departments d ON k.departamento_id=d.id
    """
    if departamento_id:
        q += f" WHERE k.departamento_id={int(departamento_id)}"
    q += " ORDER BY k.nome"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_kpi(kid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM kpis WHERE id=?", (kid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_kpi(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO kpis(nome,descricao,unidade,departamento_id,criado_em) VALUES(?,?,?,?,?)",
        (data["nome"], data.get("descricao", ""), data.get("unidade", ""),
         data.get("departamento_id") or None, _now())
    )
    conn.commit()
    new_id = c.lastrowid; conn.close()
    return new_id


def update_kpi(kid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "descricao", "unidade", "departamento_id"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(kid)
        conn.execute(f"UPDATE kpis SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_kpi(kid):
    conn = get_conn()
    conn.execute("DELETE FROM kpi_values WHERE kpi_id=?", (kid,))
    conn.execute("DELETE FROM kpis WHERE id=?", (kid,))
    conn.commit(); conn.close()


def list_kpi_values(kid, limit=20):
    conn = get_conn()
    r = conn.execute(
        "SELECT * FROM kpi_values WHERE kpi_id=? ORDER BY data DESC LIMIT ?",
        (kid, limit)
    ).fetchall()
    conn.close()
    return [dict(x) for x in r]


def add_kpi_value(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO kpi_values(kpi_id,valor,data,fonte,criado_em) VALUES(?,?,?,?,?)",
        (data["kpi_id"], data["valor"], data.get("data", _now()[:10]),
         data.get("fonte", ""), _now())
    )
    conn.commit()
    new_id = c.lastrowid; conn.close()
    return new_id


def get_kpi_values_for_newsletter(departamento_id: int, since: str):
    conn = get_conn()
    r = conn.execute("""
        SELECT k.nome, k.unidade, kv.valor, kv.data
        FROM kpi_values kv
        JOIN kpis k ON kv.kpi_id=k.id
        WHERE k.departamento_id=? AND kv.data>=?
        ORDER BY kv.data DESC LIMIT 5
    """, (departamento_id, since[:10])).fetchall()
    conn.close()
    return [dict(x) for x in r]


# ── Insights ───────────────────────────────────────────────────────────────────

def list_insights(departamento_id=None):
    conn = get_conn()
    q = """
        SELECT i.*, d.nome as departamento_nome,
               n.titulo as news_titulo, k.nome as kpi_nome
        FROM insights i
        LEFT JOIN departments d ON i.departamento_id=d.id
        LEFT JOIN news n ON i.news_id=n.id
        LEFT JOIN kpis k ON i.kpi_id=k.id
    """
    if departamento_id:
        q += f" WHERE i.departamento_id={int(departamento_id)}"
    q += " ORDER BY CASE i.impacto WHEN 'alto' THEN 0 WHEN 'medio' THEN 1 ELSE 2 END, i.criado_em DESC"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_insight(iid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM insights WHERE id=?", (iid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_insight(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """INSERT INTO insights(titulo,descricao,impacto,correlacao_tipo,
                                news_id,kpi_id,departamento_id,criado_em)
           VALUES(?,?,?,?,?,?,?,?)""",
        (data["titulo"], data["descricao"], data.get("impacto", "medio"),
         data.get("correlacao_tipo", ""),
         data.get("news_id") or None, data.get("kpi_id") or None,
         data.get("departamento_id") or None, _now())
    )
    conn.commit()
    new_id = c.lastrowid; conn.close()
    return new_id


def update_insight(iid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["titulo", "descricao", "impacto", "correlacao_tipo",
              "news_id", "kpi_id", "departamento_id"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f] if data[f] != "" else None)
    if fields:
        vals.append(iid)
        conn.execute(f"UPDATE insights SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_insight(iid):
    conn = get_conn()
    conn.execute("DELETE FROM insights WHERE id=?", (iid,))
    conn.commit(); conn.close()


def get_insights_for_newsletter(departamento_id: int, since: str):
    conn = get_conn()
    r = conn.execute("""
        SELECT titulo, descricao, impacto, correlacao_tipo
        FROM insights
        WHERE departamento_id=? AND criado_em>=?
        ORDER BY CASE impacto WHEN 'alto' THEN 0 WHEN 'medio' THEN 1 ELSE 2 END
        LIMIT 3
    """, (departamento_id, since)).fetchall()
    conn.close()
    return [dict(x) for x in r]


# ── Newsletters ────────────────────────────────────────────────────────────────

def list_newsletters(departamento_id=None, limit=50):
    conn = get_conn()
    q = """
        SELECT nl.id, nl.departamento_id, nl.gerado_em, d.nome as departamento_nome,
               nd.status, nd.enviado_em, nd.destinatarios
        FROM newsletters nl
        JOIN departments d ON nl.departamento_id=d.id
        LEFT JOIN newsletter_dispatches nd ON nd.newsletter_id=nl.id
    """
    if departamento_id:
        q += f" WHERE nl.departamento_id={int(departamento_id)}"
    q += f" ORDER BY nl.gerado_em DESC LIMIT {int(limit)}"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_newsletter(nlid):
    conn = get_conn()
    nl = conn.execute("""
        SELECT nl.*, d.nome as departamento_nome
        FROM newsletters nl JOIN departments d ON nl.departamento_id=d.id
        WHERE nl.id=?
    """, (nlid,)).fetchone()
    if not nl:
        conn.close(); return None
    result = dict(nl)
    dispatch = conn.execute(
        "SELECT * FROM newsletter_dispatches WHERE newsletter_id=? ORDER BY id DESC LIMIT 1",
        (nlid,)
    ).fetchone()
    result["dispatch"] = dict(dispatch) if dispatch else None
    conn.close()
    return result


def create_newsletter(departamento_id: int, conteudo_json: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO newsletters(departamento_id,conteudo_json,gerado_em) VALUES(?,?,?)",
        (departamento_id, conteudo_json, _now())
    )
    conn.commit()
    nlid = c.lastrowid
    # Cria dispatch pendente
    conn.execute(
        "INSERT INTO newsletter_dispatches(newsletter_id,status) VALUES(?,?)",
        (nlid, "pendente")
    )
    conn.commit(); conn.close()
    return nlid


def update_dispatch(newsletter_id: int, status: str, destinatarios=0, erro=""):
    conn = get_conn()
    conn.execute("""
        UPDATE newsletter_dispatches
        SET status=?, enviado_em=?, destinatarios=?, mensagem_erro=?
        WHERE newsletter_id=?
    """, (status, _now() if status == "enviado" else None,
          destinatarios, erro, newsletter_id))
    conn.commit(); conn.close()


# ── SMTP ───────────────────────────────────────────────────────────────────────

def get_smtp_config():
    conn = get_conn()
    r = conn.execute("SELECT * FROM smtp_config WHERE id=1").fetchone()
    conn.close()
    return dict(r) if r else {}


def update_smtp_config(data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["host", "porta", "usuario", "senha", "use_tls", "remetente", "ativo"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        conn.execute(f"UPDATE smtp_config SET {','.join(fields)} WHERE id=1", vals)
        conn.commit()
    conn.close()


# ── Dashboard ──────────────────────────────────────────────────────────────────

def get_dashboard_stats():
    conn = get_conn()
    stats = {
        "total_noticias":  conn.execute("SELECT COUNT(*) FROM news").fetchone()[0],
        "total_fontes":    conn.execute("SELECT COUNT(*) FROM news_sources WHERE ativo=1").fetchone()[0],
        "total_insights":  conn.execute("SELECT COUNT(*) FROM insights").fetchone()[0],
        "total_kpis":      conn.execute("SELECT COUNT(*) FROM kpis").fetchone()[0],
        "newsletters_hoje": conn.execute(
            "SELECT COUNT(*) FROM newsletters WHERE gerado_em>=?",
            (datetime.now().strftime("%Y-%m-%d"),)
        ).fetchone()[0],
        "total_usuarios":  conn.execute("SELECT COUNT(*) FROM users WHERE ativo=1").fetchone()[0],
    }
    # Notícias recentes (últimas 5)
    recentes = conn.execute("""
        SELECT n.id, n.titulo, n.resumo, n.relevancia, n.coletado_em, s.nome as fonte_nome
        FROM news n LEFT JOIN news_sources s ON n.fonte_id=s.id
        ORDER BY n.coletado_em DESC LIMIT 5
    """).fetchall()
    stats["noticias_recentes"] = [dict(x) for x in recentes]

    # Insights recentes (últimos 5)
    insights = conn.execute("""
        SELECT i.id, i.titulo, i.impacto, i.criado_em, d.nome as departamento_nome
        FROM insights i LEFT JOIN departments d ON i.departamento_id=d.id
        ORDER BY i.criado_em DESC LIMIT 5
    """).fetchall()
    stats["insights_recentes"] = [dict(x) for x in insights]

    # KPIs por departamento
    kpis_dept = conn.execute("""
        SELECT d.nome, COUNT(k.id) as total
        FROM departments d LEFT JOIN kpis k ON k.departamento_id=d.id
        GROUP BY d.id ORDER BY total DESC LIMIT 5
    """).fetchall()
    stats["kpis_por_dept"] = [dict(x) for x in kpis_dept]

    conn.close()
    return stats
