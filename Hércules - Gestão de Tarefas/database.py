from __future__ import annotations
"""
database.py — Persistência SQLite do Hércules
"""
import hashlib
import os
import sqlite3
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), "hercules.db")


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
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT    NOT NULL,
            email      TEXT    UNIQUE NOT NULL,
            senha_hash TEXT    NOT NULL,
            role       TEXT    NOT NULL DEFAULT 'membro',
            ativo      INTEGER NOT NULL DEFAULT 1,
            criado_em  TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS projects (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT    NOT NULL,
            descricao  TEXT    DEFAULT '',
            cor        TEXT    NOT NULL DEFAULT '#2563eb',
            criado_por INTEGER,
            criado_em  TEXT    NOT NULL,
            FOREIGN KEY (criado_por) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo         TEXT    NOT NULL,
            descricao      TEXT    DEFAULT '',
            status         TEXT    NOT NULL DEFAULT 'pendente',
            prioridade     TEXT    NOT NULL DEFAULT 'media',
            prazo          TEXT,
            projeto_id     INTEGER,
            responsavel_id INTEGER,
            criado_por     INTEGER,
            criado_em      TEXT    NOT NULL,
            atualizado_em  TEXT    NOT NULL,
            FOREIGN KEY (projeto_id)     REFERENCES projects(id),
            FOREIGN KEY (responsavel_id) REFERENCES users(id),
            FOREIGN KEY (criado_por)     REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            conteudo  TEXT    NOT NULL,
            tarefa_id INTEGER NOT NULL,
            autor_id  INTEGER NOT NULL,
            criado_em TEXT    NOT NULL,
            FOREIGN KEY (tarefa_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (autor_id)  REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS activities (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo       TEXT    NOT NULL,
            descricao  TEXT    NOT NULL,
            tarefa_id  INTEGER,
            usuario_id INTEGER,
            criado_em  TEXT    NOT NULL,
            FOREIGN KEY (tarefa_id)  REFERENCES tasks(id) ON DELETE SET NULL,
            FOREIGN KEY (usuario_id) REFERENCES users(id)
        );
    """)
    conn.commit()
    # Migrations — adicionar colunas de escopo (ignorar se já existirem)
    for sql in [
        "ALTER TABLE users ADD COLUMN empresa_id INTEGER",
        "ALTER TABLE users ADD COLUMN departamento_id INTEGER",
        "ALTER TABLE projects ADD COLUMN empresa_id INTEGER",
        "ALTER TABLE projects ADD COLUMN departamento_id INTEGER",
        "ALTER TABLE tasks ADD COLUMN empresa_id INTEGER",
        "ALTER TABLE tasks ADD COLUMN departamento_id INTEGER",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass
    if not conn.execute("SELECT 1 FROM users WHERE email='admin@olimpus.local'").fetchone():
        conn.execute(
            "INSERT INTO users(nome,email,senha_hash,role,criado_em) VALUES(?,?,?,?,?)",
            ("Administrador", "admin@olimpus.local", _hash("Hercules@2024"), "admin", _now())
        )
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
    q = "SELECT id,nome,email,role,ativo,criado_em FROM users"
    if active_only:
        q += " WHERE ativo=1"
    r = conn.execute(q + " ORDER BY nome").fetchall()
    conn.close()
    return [dict(x) for x in r]


def create_user(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    # Senha vazia gera hash aleatório (usuário só acessa via Atlas)
    senha = data.get("senha") or ""
    senha_hash = _hash(senha) if senha else hashlib.sha256(os.urandom(32)).hexdigest()
    c.execute(
        "INSERT INTO users(nome,email,senha_hash,role,criado_em) VALUES(?,?,?,?,?)",
        (data["nome"], data["email"], senha_hash, data.get("role", "membro"), _now())
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_user(uid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "email", "role", "ativo"]:
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
    """
    Resolve a role do usuário no Hércules.
    Prioridade: RBAC v4.0 > role legada > funções globais (fallback).
    Roles válidas: admin > gestor > membro.
    """
    rs = role_sistema.upper()
    if rs in ("ADMIN_GERAL", "ADMIN"):
        return "admin"
    if rs == "GESTOR":
        return "gestor"
    if rs == "USER":
        return "membro"
    if role_sistema in ("admin", "gestor", "membro"):
        return role_sistema
    if "admin" in funcoes:
        return "admin"
    if "gestor" in funcoes:
        return "gestor"
    return "membro"


def get_or_create_user_from_atlas(atlas_user: dict) -> dict:
    """
    Encontra ou cria um usuário local a partir dos dados do Atlas.
    Sincroniza nome e role sempre que faz login.
    """
    email = (atlas_user.get("email") or "").lower().strip()
    nome  = atlas_user.get("nome") or email
    role  = _map_atlas_role(
        atlas_user.get("funcoes") or [],
        atlas_user.get("_role_sistema", ""),
    )

    conn = get_conn()
    row  = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()

    if row:
        u = dict(row)
        # Sincroniza nome e role com o que veio do Atlas
        upd_fields, upd_vals = [], []
        if u["nome"] != nome:
            upd_fields.append("nome=?"); upd_vals.append(nome)
        if u["role"] != role:
            upd_fields.append("role=?"); upd_vals.append(role)
        if atlas_user.get("empresa_id") and u.get("empresa_id") != atlas_user["empresa_id"]:
            upd_fields.append("empresa_id=?"); upd_vals.append(atlas_user["empresa_id"])
        if atlas_user.get("departamento_id") and u.get("departamento_id") != atlas_user["departamento_id"]:
            upd_fields.append("departamento_id=?"); upd_vals.append(atlas_user["departamento_id"])
        if upd_fields:
            upd_vals.append(u["id"])
            conn.execute(f"UPDATE users SET {','.join(upd_fields)} WHERE id=?", upd_vals)
            conn.commit()
            u["nome"] = nome
            u["role"] = role
            if atlas_user.get("empresa_id"):
                u["empresa_id"] = atlas_user["empresa_id"]
            if atlas_user.get("departamento_id"):
                u["departamento_id"] = atlas_user["departamento_id"]
        # Garante que está ativo
        if not u["ativo"]:
            conn.execute("UPDATE users SET ativo=1 WHERE id=?", (u["id"],))
            conn.commit()
            u["ativo"] = 1
        conn.close()
        return u

    # Cria novo usuário — senha não gerenciada localmente (hash aleatório)
    dummy_hash = hashlib.sha256(os.urandom(32)).hexdigest()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users(nome,email,senha_hash,role,empresa_id,departamento_id,criado_em) VALUES(?,?,?,?,?,?,?)",
        (nome, email, dummy_hash, role, atlas_user.get("empresa_id"), atlas_user.get("departamento_id"), _now())
    )
    conn.commit()
    uid = c.lastrowid
    conn.close()
    return get_user(uid)


def change_password(uid, current, new_pw):
    u = get_user(uid)
    if not u or u["senha_hash"] != _hash(current):
        return False, "Senha atual incorreta."
    if len(new_pw) < 6:
        return False, "Nova senha deve ter pelo menos 6 caracteres."
    conn = get_conn()
    conn.execute("UPDATE users SET senha_hash=? WHERE id=?", (_hash(new_pw), uid))
    conn.commit()
    conn.close()
    return True, "Senha alterada com sucesso."


# ── Scope helpers ──────────────────────────────────────────────────────────────

def _task_scope_clause(empresa_id=None, departamento_id=None, user_id=None):
    """Retorna (clause_sql, params) para filtrar tarefas pelo escopo do usuário."""
    if empresa_id:
        return "t.empresa_id=?", [empresa_id]
    if departamento_id:
        return (
            "(t.departamento_id=? OR t.responsavel_id IN "
            "(SELECT id FROM users WHERE departamento_id=? AND ativo=1))",
            [departamento_id, departamento_id]
        )
    if user_id is not None:
        return "(t.responsavel_id=? OR t.criado_por=?)", [user_id, user_id]
    return "1=1", []


def _project_scope_clause(empresa_id=None, departamento_id=None, user_id=None):
    """Retorna (clause_sql, params) para filtrar projetos pelo escopo do usuário."""
    if empresa_id:
        return "p.empresa_id=?", [empresa_id]
    if departamento_id:
        return (
            "(p.departamento_id=? OR EXISTS("
            "SELECT 1 FROM tasks t2 WHERE t2.projeto_id=p.id AND ("
            "t2.departamento_id=? OR t2.responsavel_id IN "
            "(SELECT id FROM users WHERE departamento_id=? AND ativo=1))))",
            [departamento_id, departamento_id, departamento_id]
        )
    if user_id is not None:
        return (
            "(p.criado_por=? OR EXISTS("
            "SELECT 1 FROM tasks t2 WHERE t2.projeto_id=p.id AND "
            "(t2.responsavel_id=? OR t2.criado_por=?)))",
            [user_id, user_id, user_id]
        )
    return "1=1", []


# ── Projects ───────────────────────────────────────────────────────────────────

def list_projects(empresa_id=None, departamento_id=None, user_id=None):
    conn = get_conn()
    clause, params = _project_scope_clause(empresa_id, departamento_id, user_id)
    q = f"""
        SELECT p.*, u.nome as criado_por_nome,
               COUNT(DISTINCT t.id) as total_tarefas
        FROM projects p
        LEFT JOIN users u ON p.criado_por=u.id
        LEFT JOIN tasks t ON t.projeto_id=p.id
        WHERE {clause}
        GROUP BY p.id ORDER BY p.nome
    """
    r = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_project(pid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_project(data, uid, empresa_id=None, departamento_id=None) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO projects(nome,descricao,cor,criado_por,empresa_id,departamento_id,criado_em) VALUES(?,?,?,?,?,?,?)",
        (data["nome"], data.get("descricao", ""), data.get("cor", "#2563eb"),
         uid, empresa_id, departamento_id, _now())
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_project(pid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "descricao", "cor"]:
        if f in data:
            fields.append(f"{f}=?")
            vals.append(data[f])
    if fields:
        vals.append(pid)
        conn.execute(f"UPDATE projects SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_project(pid):
    conn = get_conn()
    conn.execute("UPDATE tasks SET projeto_id=NULL WHERE projeto_id=?", (pid,))
    conn.execute("DELETE FROM projects WHERE id=?", (pid,))
    conn.commit()
    conn.close()


# ── Tasks ──────────────────────────────────────────────────────────────────────

_TSEL = """
    SELECT t.*, p.nome as projeto_nome, p.cor as projeto_cor,
           r.nome as responsavel_nome, c.nome as criador_nome
    FROM tasks t
    LEFT JOIN projects p ON t.projeto_id=p.id
    LEFT JOIN users r    ON t.responsavel_id=r.id
    LEFT JOIN users c    ON t.criado_por=c.id
"""


def list_tasks(filters=None, empresa_id=None, departamento_id=None, user_id=None):
    conn = get_conn()
    scope_clause, scope_params = _task_scope_clause(empresa_id, departamento_id, user_id)
    q = _TSEL
    w, v = [scope_clause], list(scope_params)
    if filters:
        if filters.get("projeto_id"):
            w.append("t.projeto_id=?"); v.append(filters["projeto_id"])
        if filters.get("status"):
            w.append("t.status=?"); v.append(filters["status"])
        if filters.get("prioridade"):
            w.append("t.prioridade=?"); v.append(filters["prioridade"])
        if filters.get("responsavel_id"):
            w.append("t.responsavel_id=?"); v.append(filters["responsavel_id"])
    q += " WHERE " + " AND ".join(w)
    q += " ORDER BY t.criado_em DESC"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_task(tid):
    conn = get_conn()
    r = conn.execute(_TSEL + " WHERE t.id=?", (tid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_task(data, uid, empresa_id=None, departamento_id=None) -> int:
    now = _now()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks(titulo,descricao,status,prioridade,prazo,
                          projeto_id,responsavel_id,criado_por,
                          empresa_id,departamento_id,criado_em,atualizado_em)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        data["titulo"], data.get("descricao", ""),
        data.get("status", "pendente"), data.get("prioridade", "media"),
        data.get("prazo") or None,
        data.get("projeto_id") or None, data.get("responsavel_id") or None,
        uid, empresa_id, departamento_id, now, now
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_task(tid, data):
    conn = get_conn()
    fields, vals = ["atualizado_em=?"], [_now()]
    for f in ["titulo", "descricao", "status", "prioridade", "prazo", "projeto_id", "responsavel_id"]:
        if f in data:
            fields.append(f"{f}=?")
            vals.append(data[f] if data[f] != "" else None)
    vals.append(tid)
    conn.execute(f"UPDATE tasks SET {','.join(fields)} WHERE id=?", vals)
    conn.commit()
    conn.close()
    return get_task(tid)


def delete_task(tid):
    conn = get_conn()
    conn.execute("DELETE FROM comments WHERE tarefa_id=?", (tid,))
    conn.execute("DELETE FROM activities WHERE tarefa_id=?", (tid,))
    conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
    conn.commit()
    conn.close()


# ── Comments ───────────────────────────────────────────────────────────────────

def list_comments(tid):
    conn = get_conn()
    r = conn.execute("""
        SELECT c.*, u.nome as autor_nome FROM comments c
        JOIN users u ON c.autor_id=u.id
        WHERE c.tarefa_id=? ORDER BY c.criado_em
    """, (tid,)).fetchall()
    conn.close()
    return [dict(x) for x in r]


def add_comment(tid, uid, text) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO comments(conteudo,tarefa_id,autor_id,criado_em) VALUES(?,?,?,?)",
        (text, tid, uid, _now())
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def delete_comment(cid, uid, is_admin) -> bool:
    conn = get_conn()
    r = conn.execute("SELECT autor_id FROM comments WHERE id=?", (cid,)).fetchone()
    if not r:
        conn.close()
        return False
    if not is_admin and r["autor_id"] != uid:
        conn.close()
        return False
    conn.execute("DELETE FROM comments WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return True


# ── Activities ─────────────────────────────────────────────────────────────────

def add_activity(tipo, desc, tid, uid):
    conn = get_conn()
    conn.execute(
        "INSERT INTO activities(tipo,descricao,tarefa_id,usuario_id,criado_em) VALUES(?,?,?,?,?)",
        (tipo, desc, tid, uid, _now())
    )
    conn.commit()
    conn.close()


def list_activities(limit=50, task_id=None, empresa_id=None, departamento_id=None, user_id=None):
    conn = get_conn()
    if task_id:
        r = conn.execute("""
            SELECT a.*, u.nome as usuario_nome, t.titulo as tarefa_titulo
            FROM activities a
            LEFT JOIN users u ON a.usuario_id=u.id
            LEFT JOIN tasks t ON a.tarefa_id=t.id
            WHERE a.tarefa_id=? ORDER BY a.criado_em DESC
        """, (task_id,)).fetchall()
    else:
        tc, tp = _task_scope_clause(empresa_id, departamento_id, user_id)
        # Filtra atividades cujas tarefas são visíveis no escopo (atividades sem tarefa sempre visíveis)
        scope_filter = f"(a.tarefa_id IS NULL OR EXISTS(SELECT 1 FROM tasks t WHERE t.id=a.tarefa_id AND {tc}))"
        r = conn.execute(f"""
            SELECT a.*, u.nome as usuario_nome, t.titulo as tarefa_titulo
            FROM activities a
            LEFT JOIN users u ON a.usuario_id=u.id
            LEFT JOIN tasks t ON a.tarefa_id=t.id
            WHERE {scope_filter}
            ORDER BY a.criado_em DESC LIMIT ?
        """, tp + [limit]).fetchall()
    conn.close()
    return [dict(x) for x in r]


# ── Dashboard ──────────────────────────────────────────────────────────────────

def get_dashboard_stats(empresa_id=None, departamento_id=None, user_id=None):
    conn = get_conn()
    today = date.today().isoformat()
    tc, tp = _task_scope_clause(empresa_id, departamento_id, user_id)

    stats = {
        "total":        conn.execute(f"SELECT COUNT(*) FROM tasks t WHERE {tc}", tp).fetchone()[0],
        "pendentes":    conn.execute(f"SELECT COUNT(*) FROM tasks t WHERE {tc} AND t.status='pendente'", tp).fetchone()[0],
        "em_andamento": conn.execute(f"SELECT COUNT(*) FROM tasks t WHERE {tc} AND t.status='em_andamento'", tp).fetchone()[0],
        "concluidas":   conn.execute(f"SELECT COUNT(*) FROM tasks t WHERE {tc} AND t.status='concluida'", tp).fetchone()[0],
        "atrasadas":    conn.execute(f"SELECT COUNT(*) FROM tasks t WHERE {tc} AND t.prazo<? AND t.status!='concluida'", tp + [today]).fetchone()[0],
        "projetos":     conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
        "usuarios":     conn.execute("SELECT COUNT(*) FROM users WHERE ativo=1").fetchone()[0],
    }
    by_user = conn.execute(f"""
        SELECT u.id, u.nome, COUNT(*) as total,
               SUM(CASE WHEN t.status='concluida' THEN 1 ELSE 0 END) as concluidas
        FROM tasks t JOIN users u ON t.responsavel_id=u.id
        WHERE {tc}
        GROUP BY u.id ORDER BY total DESC LIMIT 5
    """, tp).fetchall()
    stats["por_usuario"] = [dict(x) for x in by_user]

    upcoming = conn.execute(f"""
        SELECT t.id, t.titulo, t.prazo, t.prioridade, t.status,
               u.nome as responsavel_nome, p.nome as projeto_nome, p.cor as projeto_cor
        FROM tasks t
        LEFT JOIN users u ON t.responsavel_id=u.id
        LEFT JOIN projects p ON t.projeto_id=p.id
        WHERE {tc} AND t.prazo IS NOT NULL AND t.status != 'concluida'
        ORDER BY t.prazo ASC LIMIT 5
    """, tp).fetchall()
    stats["proximos_prazos"] = [dict(x) for x in upcoming]
    conn.close()
    return stats
