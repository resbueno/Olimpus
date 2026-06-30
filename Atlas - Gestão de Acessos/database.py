from __future__ import annotations
"""
database.py — Atlas: Gestão de Acessos (IAM)
SQLite: Empresa, Departamento, Pessoa, Sistema, Role, Permissão, Auditoria

Versão 4.0 — DDD / RBAC
- Roles: USER, GESTOR, ADMIN, ADMIN_GERAL (hierarquia fixa)
- Permissões granulares por sistema
- Escopo: SELF, TEAM, COMPANY, GLOBAL
- Multi-tenant com isolamento por empresa_id
- Auditoria completa
"""
import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "atlas.db")

# ── Constantes ───────────────────────────────────────────────────────────────

ESCOPOS = ["SELF", "TEAM", "COMPANY", "GLOBAL"]
ESCOPO_NIVEL = {"SELF": 0, "TEAM": 1, "COMPANY": 2, "GLOBAL": 3}

PERMISSOES_DISPONIVEIS = [
    "visualizar", "criar", "editar", "excluir",
    "aprovar", "exportar", "importar", "configurar", "admin",
]

ROLES_PADRAO = [
    ("USER",        "Usuário padrão — acesso ao próprio escopo",  0),
    ("GESTOR",      "Gestor de equipe — acesso ao departamento",  1),
    ("ADMIN",       "Administrador da empresa",                   2),
    ("ADMIN_GERAL", "Administrador global — todas as empresas",   3),
]

# Mapa de compatibilidade: role → funcao legada
_ROLE_TO_FUNCAO = {
    "USER": "usuario",
    "GESTOR": "gestor",
    "ADMIN": "admin",
    "ADMIN_GERAL": "admin",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ── Schema & Inicialização ───────────────────────────────────────────────────

def init_db():
    conn = get_conn()
    conn.executescript("""
        -- Empresas
        CREATE TABLE IF NOT EXISTS empresas (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            nome                 TEXT    NOT NULL,
            razao_social         TEXT    NOT NULL DEFAULT '',
            cnpj                 TEXT    DEFAULT '',
            endereco_logradouro  TEXT    NOT NULL DEFAULT '',
            endereco_numero      TEXT    NOT NULL DEFAULT '',
            endereco_complemento TEXT    NOT NULL DEFAULT '',
            endereco_bairro      TEXT    NOT NULL DEFAULT '',
            endereco_cidade      TEXT    NOT NULL DEFAULT '',
            endereco_estado      TEXT    NOT NULL DEFAULT '',
            endereco_cep         TEXT    NOT NULL DEFAULT '',
            telefone             TEXT    NOT NULL DEFAULT '',
            email                TEXT    NOT NULL DEFAULT '',
            responsavel          TEXT    NOT NULL DEFAULT '',
            numero_contrato      TEXT    NOT NULL DEFAULT '',
            inicio_contrato      TEXT    NOT NULL DEFAULT '',
            vigencia_contrato    TEXT    NOT NULL DEFAULT '',
            ativo                INTEGER NOT NULL DEFAULT 1,
            criado_em            TEXT    NOT NULL
        );

        -- Departamentos
        CREATE TABLE IF NOT EXISTS departamentos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       TEXT    NOT NULL,
            empresa_id INTEGER,
            gestor_id  INTEGER,
            criado_em  TEXT    NOT NULL,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (gestor_id)  REFERENCES pessoas(id)
        );

        -- Pessoas (Usuários)
        CREATE TABLE IF NOT EXISTS pessoas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nome            TEXT    NOT NULL,
            email           TEXT    UNIQUE NOT NULL,
            senha_hash      TEXT    NOT NULL,
            cargo           TEXT    NOT NULL DEFAULT '',
            empresa_id      INTEGER,
            departamento_id INTEGER,
            ativo           INTEGER NOT NULL DEFAULT 1,
            trocar_senha    INTEGER NOT NULL DEFAULT 0,
            telefone        TEXT    NOT NULL DEFAULT '',
            data_nascimento TEXT    NOT NULL DEFAULT '',
            data_admissao   TEXT    NOT NULL DEFAULT '',
            salario         REAL    NOT NULL DEFAULT 0,
            foto_url        TEXT    NOT NULL DEFAULT '',
            gestor_id       INTEGER,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (empresa_id)      REFERENCES empresas(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (gestor_id)       REFERENCES pessoas(id)
        );

        -- Sistemas / Apps
        CREATE TABLE IF NOT EXISTS sistemas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            folder    TEXT    NOT NULL UNIQUE,
            nome      TEXT    NOT NULL,
            ativo     INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT    NOT NULL
        );

        -- Roles (Papéis RBAC)
        CREATE TABLE IF NOT EXISTS roles (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL UNIQUE,
            descricao TEXT    DEFAULT '',
            nivel     INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT    NOT NULL
        );

        -- Permissões
        CREATE TABLE IF NOT EXISTS permissoes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL UNIQUE,
            descricao TEXT    DEFAULT '',
            criado_em TEXT    NOT NULL
        );

        -- Role ↔ Permissão por sistema
        CREATE TABLE IF NOT EXISTS role_permissoes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id         INTEGER NOT NULL,
            sistema_folder  TEXT    NOT NULL,
            permissao_id    INTEGER NOT NULL,
            FOREIGN KEY (role_id)      REFERENCES roles(id)      ON DELETE CASCADE,
            FOREIGN KEY (permissao_id) REFERENCES permissoes(id) ON DELETE CASCADE,
            UNIQUE(role_id, sistema_folder, permissao_id)
        );

        -- Vínculo Usuário ↔ Role por sistema com escopo
        CREATE TABLE IF NOT EXISTS usuario_roles (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            pessoa_id      INTEGER NOT NULL,
            role_id        INTEGER NOT NULL,
            sistema_folder TEXT    NOT NULL,
            escopo         TEXT    NOT NULL DEFAULT 'SELF',
            criado_em      TEXT    NOT NULL,
            criado_por     INTEGER,
            FOREIGN KEY (pessoa_id)  REFERENCES pessoas(id) ON DELETE CASCADE,
            FOREIGN KEY (role_id)    REFERENCES roles(id)   ON DELETE CASCADE,
            FOREIGN KEY (criado_por) REFERENCES pessoas(id),
            UNIQUE(pessoa_id, sistema_folder)
        );

        -- Auditoria
        CREATE TABLE IF NOT EXISTS audit_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            acao        TEXT    NOT NULL,
            entidade    TEXT,
            entidade_id INTEGER,
            detalhe     TEXT,
            pessoa_id   INTEGER,
            empresa_id  INTEGER,
            ip          TEXT,
            criado_em   TEXT    NOT NULL
        );
    """)
    conn.commit()

    _run_migrations(conn)
    _seed_defaults(conn)
    _migrate_old_model(conn)
    _ensure_admin(conn)

    conn.close()


def _run_migrations(conn):
    """Adiciona colunas que podem não existir em bancos antigos."""
    for sql in [
        "ALTER TABLE departamentos ADD COLUMN gestor_id INTEGER REFERENCES pessoas(id)",
        "ALTER TABLE pessoas ADD COLUMN cargo           TEXT    NOT NULL DEFAULT ''",
        "ALTER TABLE pessoas ADD COLUMN trocar_senha    INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE pessoas ADD COLUMN departamento_id INTEGER REFERENCES departamentos(id)",
        "ALTER TABLE pessoas ADD COLUMN telefone        TEXT    NOT NULL DEFAULT ''",
        "ALTER TABLE pessoas ADD COLUMN data_nascimento TEXT    NOT NULL DEFAULT ''",
        "ALTER TABLE pessoas ADD COLUMN data_admissao   TEXT    NOT NULL DEFAULT ''",
        "ALTER TABLE pessoas ADD COLUMN salario         REAL    NOT NULL DEFAULT 0",
        "ALTER TABLE pessoas ADD COLUMN foto_url        TEXT    NOT NULL DEFAULT ''",
        "ALTER TABLE pessoas ADD COLUMN gestor_id       INTEGER REFERENCES pessoas(id)",
        "ALTER TABLE empresas ADD COLUMN razao_social        TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_logradouro TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_numero     TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_complemento TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_bairro     TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_cidade     TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_estado     TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN endereco_cep        TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN telefone            TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN email               TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN responsavel         TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN numero_contrato     TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN inicio_contrato     TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE empresas ADD COLUMN vigencia_contrato   TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE audit_logs ADD COLUMN empresa_id INTEGER",
    ]:
        try:
            conn.execute(sql)
            conn.commit()
        except Exception:
            pass


def _seed_defaults(conn):
    """Popula roles e permissões padrão."""
    now = _now()
    for nome, desc, nivel in ROLES_PADRAO:
        if not conn.execute("SELECT 1 FROM roles WHERE nome=?", (nome,)).fetchone():
            conn.execute(
                "INSERT INTO roles(nome,descricao,nivel,criado_em) VALUES(?,?,?,?)",
                (nome, desc, nivel, now),
            )
    for nome in PERMISSOES_DISPONIVEIS:
        if not conn.execute("SELECT 1 FROM permissoes WHERE nome=?", (nome,)).fetchone():
            conn.execute(
                "INSERT INTO permissoes(nome,descricao,criado_em) VALUES(?,?,?)",
                (nome, "", now),
            )
    conn.commit()


def _migrate_old_model(conn):
    """Migra dados de funcoes/pessoa_funcao/acessos antigos para o modelo RBAC."""
    try:
        old_count = conn.execute("SELECT COUNT(*) FROM pessoa_funcao").fetchone()[0]
    except Exception:
        return

    new_count = conn.execute("SELECT COUNT(*) FROM usuario_roles").fetchone()[0]
    if new_count > 0 or old_count == 0:
        return

    role_map = {r["nome"]: r["id"] for r in conn.execute("SELECT id,nome FROM roles").fetchall()}
    funcao_to_role = {"admin": "ADMIN_GERAL", "gestor": "GESTOR", "operador": "USER", "leitura": "USER"}
    funcao_to_escopo = {"admin": "GLOBAL", "gestor": "TEAM", "operador": "SELF", "leitura": "SELF"}

    now = _now()
    atlas_folder = "Atlas - Gestão de Acessos"

    rows = conn.execute("""
        SELECT pf.pessoa_id, f.nome as funcao_nome
        FROM pessoa_funcao pf JOIN funcoes f ON pf.funcao_id = f.id
    """).fetchall()

    for row in rows:
        role_nome = funcao_to_role.get(row["funcao_nome"], "USER")
        escopo = funcao_to_escopo.get(row["funcao_nome"], "SELF")
        role_id = role_map.get(role_nome)
        if role_id:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO usuario_roles"
                    "(pessoa_id,role_id,sistema_folder,escopo,criado_em) VALUES(?,?,?,?,?)",
                    (row["pessoa_id"], role_id, atlas_folder, escopo, now),
                )
            except Exception:
                pass

    # Migrar acessos por sistema
    try:
        acessos = conn.execute("""
            SELECT a.pessoa_id, a.sistema_folder, a.role_sistema, a.permitido
            FROM acessos a WHERE a.pessoa_id IS NOT NULL AND a.permitido = 1
        """).fetchall()
        user_role_id = role_map.get("USER")
        for ac in acessos:
            if not ac["pessoa_id"]:
                continue
            role_nome = (ac["role_sistema"] or "").upper()
            rid = role_map.get(role_nome, user_role_id)
            escopo = "COMPANY" if role_nome == "ADMIN" else ("TEAM" if role_nome == "GESTOR" else "SELF")
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO usuario_roles"
                    "(pessoa_id,role_id,sistema_folder,escopo,criado_em) VALUES(?,?,?,?,?)",
                    (ac["pessoa_id"], rid, ac["sistema_folder"], escopo, now),
                )
            except Exception:
                pass
    except Exception:
        pass

    conn.commit()


def _ensure_admin(conn):
    """Garante que o admin padrão existe com ADMIN_GERAL."""
    admin_email = "admin@olimpus.local"
    if not conn.execute("SELECT 1 FROM pessoas WHERE email=?", (admin_email,)).fetchone():
        conn.execute(
            "INSERT INTO pessoas(nome,email,senha_hash,empresa_id,criado_em) VALUES(?,?,?,?,?)",
            ("Administrador", admin_email, _hash("Atlas@2024"), None, _now()),
        )
        conn.commit()

    p = conn.execute("SELECT id FROM pessoas WHERE email=?", (admin_email,)).fetchone()
    r = conn.execute("SELECT id FROM roles WHERE nome='ADMIN_GERAL'").fetchone()
    if p and r:
        atlas_folder = "Atlas - Gestão de Acessos"
        if not conn.execute(
            "SELECT 1 FROM usuario_roles WHERE pessoa_id=? AND sistema_folder=?",
            (p["id"], atlas_folder),
        ).fetchone():
            conn.execute(
                "INSERT INTO usuario_roles(pessoa_id,role_id,sistema_folder,escopo,criado_em) VALUES(?,?,?,?,?)",
                (p["id"], r["id"], atlas_folder, "GLOBAL", _now()),
            )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# EMPRESAS
# ─────────────────────────────────────────────────────────────────────────────

_EMPRESA_FIELDS = [
    "nome", "razao_social", "cnpj",
    "endereco_logradouro", "endereco_numero", "endereco_complemento",
    "endereco_bairro", "endereco_cidade", "endereco_estado", "endereco_cep",
    "telefone", "email", "responsavel",
    "numero_contrato", "inicio_contrato", "vigencia_contrato",
    "ativo",
]


def list_empresas(ativo_only=False):
    conn = get_conn()
    q = """
        SELECT e.*,
               (SELECT COUNT(*) FROM pessoas WHERE empresa_id=e.id AND ativo=1) as total_pessoas
        FROM empresas e
    """
    if ativo_only:
        q += " WHERE e.ativo=1"
    q += " ORDER BY e.nome"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_empresa(eid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM empresas WHERE id=?", (eid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_empresa(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO empresas("
        "  nome, razao_social, cnpj,"
        "  endereco_logradouro, endereco_numero, endereco_complemento,"
        "  endereco_bairro, endereco_cidade, endereco_estado, endereco_cep,"
        "  telefone, email, responsavel,"
        "  numero_contrato, inicio_contrato, vigencia_contrato,"
        "  criado_em"
        ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            data["nome"],
            data.get("razao_social", ""),
            data.get("cnpj", ""),
            data.get("endereco_logradouro", ""),
            data.get("endereco_numero", ""),
            data.get("endereco_complemento", ""),
            data.get("endereco_bairro", ""),
            data.get("endereco_cidade", ""),
            data.get("endereco_estado", ""),
            data.get("endereco_cep", ""),
            data.get("telefone", ""),
            data.get("email", ""),
            data.get("responsavel", ""),
            data.get("numero_contrato", ""),
            data.get("inicio_contrato", ""),
            data.get("vigencia_contrato", ""),
            _now(),
        ),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_empresa(eid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in _EMPRESA_FIELDS:
        if f in data:
            fields.append(f"{f}=?")
            vals.append(data[f])
    if fields:
        vals.append(eid)
        conn.execute(f"UPDATE empresas SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_empresa(eid):
    conn = get_conn()
    conn.execute("UPDATE empresas SET ativo=0 WHERE id=?", (eid,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# DEPARTAMENTOS
# ─────────────────────────────────────────────────────────────────────────────

def list_departamentos(empresa_id=None):
    conn = get_conn()
    q = """
        SELECT d.*, e.nome as empresa_nome,
               g.nome as gestor_nome, g.email as gestor_email,
               (SELECT COUNT(*) FROM pessoas WHERE departamento_id=d.id AND ativo=1) as total_pessoas
        FROM departamentos d
        LEFT JOIN empresas e ON d.empresa_id=e.id
        LEFT JOIN pessoas  g ON d.gestor_id=g.id
    """
    w, v = [], []
    if empresa_id is not None:
        w.append("d.empresa_id=?")
        v.append(empresa_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " ORDER BY d.nome"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_departamento(did):
    conn = get_conn()
    r = conn.execute("""
        SELECT d.*, e.nome as empresa_nome,
               g.nome as gestor_nome, g.email as gestor_email
        FROM departamentos d
        LEFT JOIN empresas e ON d.empresa_id=e.id
        LEFT JOIN pessoas  g ON d.gestor_id=g.id
        WHERE d.id=?
    """, (did,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_departamento(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO departamentos(nome,empresa_id,gestor_id,criado_em) VALUES(?,?,?,?)",
        (data["nome"], data.get("empresa_id") or None, data.get("gestor_id") or None, _now()),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_departamento(did, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "empresa_id", "gestor_id"]:
        if f in data:
            val = data[f]
            if f in ("empresa_id", "gestor_id") and val == "":
                val = None
            fields.append(f"{f}=?")
            vals.append(val)
    if fields:
        vals.append(did)
        conn.execute(f"UPDATE departamentos SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_departamento(did):
    conn = get_conn()
    conn.execute("UPDATE pessoas SET departamento_id=NULL WHERE departamento_id=?", (did,))
    conn.execute("DELETE FROM departamentos WHERE id=?", (did,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# PESSOAS
# ─────────────────────────────────────────────────────────────────────────────

def _get_roles_de(pid, conn=None):
    """Retorna todas as roles atribuídas a uma pessoa:
    [{role_id, role_nome, role_nivel, sistema_folder, escopo}]
    """
    _close = conn is None
    if _close:
        conn = get_conn()
    r = conn.execute("""
        SELECT r.id as role_id, r.nome as role_nome, r.nivel as role_nivel,
               ur.sistema_folder, ur.escopo
        FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.pessoa_id = ?
        ORDER BY r.nivel DESC
    """, (pid,)).fetchall()
    if _close:
        conn.close()
    return [dict(x) for x in r]


def _get_max_role_nivel(pid, conn=None):
    """Retorna o nível máximo de role do usuário (0=USER, 3=ADMIN_GERAL)."""
    _close = conn is None
    if _close:
        conn = get_conn()
    r = conn.execute("""
        SELECT MAX(r.nivel) as max_nivel
        FROM usuario_roles ur JOIN roles r ON ur.role_id = r.id
        WHERE ur.pessoa_id = ?
    """, (pid,)).fetchone()
    if _close:
        conn.close()
    return (r["max_nivel"] or 0) if r else 0


def _roles_to_funcoes(roles):
    """Converte roles para lista de funcoes legadas (backward compat)."""
    funcoes = set()
    for r in roles:
        f = _ROLE_TO_FUNCAO.get(r["role_nome"], "usuario")
        funcoes.add(f)
    return sorted(funcoes)


def get_pessoa(pid):
    conn = get_conn()
    r = conn.execute("""
        SELECT p.*, e.nome as empresa_nome, d.nome as departamento_nome,
               g.nome as gestor_nome, g.email as gestor_email
        FROM pessoas p
        LEFT JOIN empresas      e ON p.empresa_id=e.id
        LEFT JOIN departamentos d ON p.departamento_id=d.id
        LEFT JOIN pessoas       g ON p.gestor_id=g.id
        WHERE p.id=?
    """, (pid,)).fetchone()
    conn.close()
    if not r:
        return None
    d = dict(r)
    roles = _get_roles_de(pid)
    d["roles"] = roles
    d["funcoes"] = [{"nome": f} for f in _roles_to_funcoes(roles)]
    return d


def get_pessoa_by_email(email):
    conn = get_conn()
    r = conn.execute("""
        SELECT p.*, e.nome as empresa_nome, d.nome as departamento_nome,
               g.nome as gestor_nome, g.email as gestor_email
        FROM pessoas p
        LEFT JOIN empresas      e ON p.empresa_id=e.id
        LEFT JOIN departamentos d ON p.departamento_id=d.id
        LEFT JOIN pessoas       g ON p.gestor_id=g.id
        WHERE p.email=?
    """, (email,)).fetchone()
    conn.close()
    if not r:
        return None
    d = dict(r)
    roles = _get_roles_de(d["id"])
    d["roles"] = roles
    d["funcoes"] = [{"nome": f} for f in _roles_to_funcoes(roles)]
    return d


def list_pessoas(ativo_only=True, empresa_id=None, departamento_id=None):
    conn = get_conn()
    q = """
        SELECT p.*, e.nome as empresa_nome,
               dep.nome as departamento_nome
        FROM pessoas p
        LEFT JOIN empresas      e   ON p.empresa_id=e.id
        LEFT JOIN departamentos dep ON p.departamento_id=dep.id
    """
    w, v = [], []
    if ativo_only:
        w.append("p.ativo=1")
    if empresa_id is not None:
        w.append("p.empresa_id=?")
        v.append(empresa_id)
    if departamento_id is not None:
        w.append("p.departamento_id=?")
        v.append(departamento_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " ORDER BY p.nome"
    rows = conn.execute(q, v).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        roles = _get_roles_de(d["id"], conn)
        d["roles"] = roles
        d["funcoes_nomes"] = ", ".join(_roles_to_funcoes(roles))
        result.append(d)
    conn.close()
    return result


def create_pessoa(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    trocar = 1 if data.get("trocar_senha") else 0
    c.execute(
        "INSERT INTO pessoas("
        "  nome, email, senha_hash, cargo, departamento_id,"
        "  empresa_id, telefone, data_nascimento, data_admissao, salario,"
        "  foto_url, trocar_senha, criado_em"
        ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            data["nome"],
            data["email"],
            _hash(data["senha"]),
            data.get("cargo") or "",
            data.get("departamento_id") or None,
            data.get("empresa_id") or None,
            data.get("telefone") or "",
            data.get("data_nascimento") or "",
            data.get("data_admissao") or "",
            float(data.get("salario") or 0),
            data.get("foto_url") or "",
            trocar,
            _now(),
        ),
    )
    conn.commit()
    pid = c.lastrowid

    # Atribuir role inicial se informada
    role_id = data.get("role_id")
    if role_id:
        atlas_folder = "Atlas - Gestão de Acessos"
        escopo = data.get("escopo", "SELF")
        conn.execute(
            "INSERT OR IGNORE INTO usuario_roles"
            "(pessoa_id,role_id,sistema_folder,escopo,criado_em,criado_por) VALUES(?,?,?,?,?,?)",
            (pid, int(role_id), atlas_folder, escopo, _now(), data.get("criado_por")),
        )
        conn.commit()

    conn.close()
    return pid


def update_pessoa(pid, data):
    conn = get_conn()
    fields, vals = [], []
    _nullable = {"empresa_id", "departamento_id", "gestor_id"}
    _all_fields = [
        "nome", "email", "cargo", "departamento_id", "gestor_id",
        "empresa_id", "ativo", "trocar_senha",
        "telefone", "data_nascimento", "data_admissao", "salario", "foto_url",
    ]
    for f in _all_fields:
        if f in data:
            fields.append(f"{f}=?")
            v = data[f]
            if f in _nullable and v == "":
                v = None
            if f == "salario":
                v = float(v or 0)
            vals.append(v)
    if data.get("senha"):
        fields.append("senha_hash=?")
        vals.append(_hash(data["senha"]))
    if fields:
        vals.append(pid)
        conn.execute(f"UPDATE pessoas SET {','.join(fields)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def delete_pessoa(pid):
    conn = get_conn()
    conn.execute("UPDATE pessoas SET ativo=0 WHERE id=?", (pid,))
    conn.commit()
    conn.close()


def check_password(email: str, pw: str) -> bool:
    p = get_pessoa_by_email(email)
    return bool(p and p["ativo"] and p["senha_hash"] == _hash(pw))


def change_password(pid, current, new_pw):
    p = get_pessoa(pid)
    if not p or p["senha_hash"] != _hash(current):
        return False, "Senha atual incorreta."
    if len(new_pw) < 6:
        return False, "Nova senha deve ter pelo menos 6 caracteres."
    conn = get_conn()
    conn.execute(
        "UPDATE pessoas SET senha_hash=?, trocar_senha=0 WHERE id=?",
        (_hash(new_pw), pid),
    )
    conn.commit()
    conn.close()
    return True, "Senha alterada com sucesso."


def bulk_import_pessoas(rows: list, criado_por: int = None) -> dict:
    criados = 0
    ignorados = 0
    erros = []
    for i, row in enumerate(rows, start=2):
        try:
            if get_pessoa_by_email(row["email"]):
                ignorados += 1
                continue
            create_pessoa({
                "nome":         row["nome"],
                "email":        row["email"],
                "cargo":        row.get("cargo") or "",
                "senha":        "Trocar123",
                "empresa_id":   row.get("empresa_id"),
                "role_id":      row.get("role_id"),
                "trocar_senha": 1,
            })
            criados += 1
        except Exception as e:
            erros.append({"linha": i, "email": row.get("email", ""), "motivo": str(e)})
    return {"criados": criados, "ignorados": ignorados, "erros": erros}


# ─────────────────────────────────────────────────────────────────────────────
# SISTEMAS
# ─────────────────────────────────────────────────────────────────────────────

def list_sistemas():
    conn = get_conn()
    r = conn.execute("SELECT * FROM sistemas ORDER BY nome").fetchall()
    conn.close()
    return [dict(x) for x in r]


def sync_sistemas(apps: list):
    conn = get_conn()
    for app in apps:
        folder = app["folder"]
        nome = app.get("name", folder)
        if conn.execute("SELECT 1 FROM sistemas WHERE folder=?", (folder,)).fetchone():
            conn.execute("UPDATE sistemas SET nome=? WHERE folder=?", (nome, folder))
        else:
            conn.execute(
                "INSERT INTO sistemas(folder,nome,criado_em) VALUES(?,?,?)",
                (folder, nome, _now()),
            )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# ROLES
# ─────────────────────────────────────────────────────────────────────────────

def list_roles():
    conn = get_conn()
    roles = [dict(x) for x in conn.execute(
        "SELECT * FROM roles ORDER BY nivel"
    ).fetchall()]
    for role in roles:
        role["total_usuarios"] = conn.execute(
            "SELECT COUNT(DISTINCT pessoa_id) FROM usuario_roles WHERE role_id=?",
            (role["id"],),
        ).fetchone()[0]
    conn.close()
    return roles


def get_role(rid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM roles WHERE id=?", (rid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def get_role_by_nome(nome):
    conn = get_conn()
    r = conn.execute("SELECT * FROM roles WHERE nome=?", (nome,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_role(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO roles(nome,descricao,nivel,criado_em) VALUES(?,?,?,?)",
        (data["nome"], data.get("descricao", ""), int(data.get("nivel", 0)), _now()),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_role(rid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "descricao", "nivel"]:
        if f in data:
            fields.append(f"{f}=?")
            vals.append(data[f])
    if fields:
        vals.append(rid)
        conn.execute(f"UPDATE roles SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_role(rid):
    conn = get_conn()
    conn.execute("DELETE FROM role_permissoes WHERE role_id=?", (rid,))
    conn.execute("DELETE FROM usuario_roles WHERE role_id=?", (rid,))
    conn.execute("DELETE FROM roles WHERE id=?", (rid,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# PERMISSÕES
# ─────────────────────────────────────────────────────────────────────────────

def list_permissoes():
    conn = get_conn()
    r = conn.execute("SELECT * FROM permissoes ORDER BY nome").fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_permissao(pid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM permissoes WHERE id=?", (pid,)).fetchone()
    conn.close()
    return dict(r) if r else None


# ─────────────────────────────────────────────────────────────────────────────
# ROLE ↔ PERMISSÕES POR SISTEMA
# ─────────────────────────────────────────────────────────────────────────────

def get_role_permissoes(role_id, sistema_folder=None):
    """Retorna permissões de uma role. Se sistema_folder, filtra por sistema.
    Formato: {sistema_folder: [perm1, perm2, ...]}
    """
    conn = get_conn()
    q = """
        SELECT rp.sistema_folder, p.nome as permissao_nome, p.id as permissao_id
        FROM role_permissoes rp
        JOIN permissoes p ON rp.permissao_id = p.id
        WHERE rp.role_id = ?
    """
    v = [role_id]
    if sistema_folder:
        q += " AND rp.sistema_folder = ?"
        v.append(sistema_folder)
    q += " ORDER BY rp.sistema_folder, p.nome"
    rows = conn.execute(q, v).fetchall()
    conn.close()

    result = {}
    for r in rows:
        sf = r["sistema_folder"]
        if sf not in result:
            result[sf] = []
        result[sf].append(r["permissao_nome"])
    return result


def set_role_permissoes(role_id, sistema_folder, permissao_nomes):
    """Define as permissões de uma role para um sistema específico.
    permissao_nomes: lista de nomes de permissão (ex: ["visualizar", "criar"])
    """
    conn = get_conn()
    conn.execute(
        "DELETE FROM role_permissoes WHERE role_id=? AND sistema_folder=?",
        (role_id, sistema_folder),
    )
    for nome in permissao_nomes:
        if nome not in PERMISSOES_DISPONIVEIS:
            continue
        perm = conn.execute("SELECT id FROM permissoes WHERE nome=?", (nome,)).fetchone()
        if perm:
            conn.execute(
                "INSERT OR IGNORE INTO role_permissoes(role_id,sistema_folder,permissao_id) VALUES(?,?,?)",
                (role_id, sistema_folder, perm["id"]),
            )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# USUARIO ↔ ROLES (Vínculo por sistema com escopo)
# ─────────────────────────────────────────────────────────────────────────────

def get_usuario_roles(pessoa_id, sistema_folder=None):
    """Retorna roles atribuídas a um usuário.
    [{role_id, role_nome, role_nivel, sistema_folder, escopo, criado_em}]
    """
    conn = get_conn()
    q = """
        SELECT ur.id, ur.sistema_folder, ur.escopo, ur.criado_em,
               r.id as role_id, r.nome as role_nome, r.nivel as role_nivel,
               s.nome as sistema_nome
        FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        LEFT JOIN sistemas s ON ur.sistema_folder = s.folder
        WHERE ur.pessoa_id = ?
    """
    v = [pessoa_id]
    if sistema_folder:
        q += " AND ur.sistema_folder = ?"
        v.append(sistema_folder)
    q += " ORDER BY r.nivel DESC, ur.sistema_folder"
    rows = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in rows]


def set_usuario_role(pessoa_id, role_id, sistema_folder, escopo="SELF", criado_por=None):
    """Define a role de um usuário para um sistema (substitui se já existir)."""
    if escopo not in ESCOPOS:
        escopo = "SELF"
    conn = get_conn()
    existing = conn.execute(
        "SELECT id FROM usuario_roles WHERE pessoa_id=? AND sistema_folder=?",
        (pessoa_id, sistema_folder),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE usuario_roles SET role_id=?, escopo=?, criado_por=? WHERE id=?",
            (role_id, escopo, criado_por, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO usuario_roles"
            "(pessoa_id,role_id,sistema_folder,escopo,criado_em,criado_por) VALUES(?,?,?,?,?,?)",
            (pessoa_id, role_id, sistema_folder, escopo, _now(), criado_por),
        )
    conn.commit()
    conn.close()


def delete_usuario_role(pessoa_id, sistema_folder):
    """Remove a role de um usuário para um sistema."""
    conn = get_conn()
    conn.execute(
        "DELETE FROM usuario_roles WHERE pessoa_id=? AND sistema_folder=?",
        (pessoa_id, sistema_folder),
    )
    conn.commit()
    conn.close()


def count_usuarios_com_role(role_id):
    """Conta quantos usuários têm uma determinada role."""
    conn = get_conn()
    r = conn.execute("SELECT COUNT(*) as cnt FROM usuario_roles WHERE role_id=?", (role_id,)).fetchone()
    conn.close()
    return r["cnt"] if r else 0


def list_usuario_roles_por_sistema(sistema_folder, empresa_id=None):
    """Lista todos os vínculos usuário-role para um sistema."""
    conn = get_conn()
    q = """
        SELECT ur.*, r.nome as role_nome, r.nivel as role_nivel,
               p.nome as pessoa_nome, p.email as pessoa_email, p.empresa_id
        FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        JOIN pessoas p ON ur.pessoa_id = p.id
        WHERE ur.sistema_folder = ? AND p.ativo = 1
    """
    v = [sistema_folder]
    if empresa_id is not None:
        q += " AND p.empresa_id = ?"
        v.append(empresa_id)
    q += " ORDER BY r.nivel DESC, p.nome"
    rows = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in rows]


# ─────────────────────────────────────────────────────────────────────────────
# RESOLUÇÃO DE ACESSO
# ─────────────────────────────────────────────────────────────────────────────

def resolve_acesso(pessoa_id: int, sistema_folder: str) -> bool:
    return resolve_acesso_completo(pessoa_id, sistema_folder)["permitido"]


def resolve_acesso_completo(pessoa_id: int, sistema_folder: str) -> dict:
    """Resolve o acesso de um usuário a um sistema.
    Retorna: {permitido, role, escopo, permissoes}

    Regras:
    1. ADMIN_GERAL tem acesso a tudo com todas as permissões
    2. Se o usuário tem role para o sistema → permitido com as permissões da role
    3. Herança: permissões da role incluem as de roles inferiores
    4. Sem role → sem acesso
    """
    conn = get_conn()

    # 1. Verificar se é ADMIN_GERAL (acesso global)
    admin_geral = conn.execute("""
        SELECT 1 FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.pessoa_id = ? AND r.nome = 'ADMIN_GERAL'
    """, (pessoa_id,)).fetchone()

    if admin_geral:
        conn.close()
        return {
            "permitido": True,
            "role": "ADMIN_GERAL",
            "escopo": "GLOBAL",
            "permissoes": PERMISSOES_DISPONIVEIS[:],
        }

    # 2. Verificar role específica para o sistema
    ur = conn.execute("""
        SELECT r.id as role_id, r.nome as role_nome, r.nivel as role_nivel, ur.escopo
        FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.pessoa_id = ? AND ur.sistema_folder = ?
    """, (pessoa_id, sistema_folder)).fetchone()

    if not ur:
        conn.close()
        return {"permitido": False, "role": None, "escopo": None, "permissoes": []}

    # 3. Obter permissões: role atual + roles de nível inferior (herança)
    perms = conn.execute("""
        SELECT DISTINCT p.nome
        FROM role_permissoes rp
        JOIN permissoes p ON rp.permissao_id = p.id
        JOIN roles r ON rp.role_id = r.id
        WHERE rp.sistema_folder = ? AND r.nivel <= ?
        ORDER BY p.nome
    """, (sistema_folder, ur["role_nivel"])).fetchall()

    conn.close()
    return {
        "permitido": True,
        "role": ur["role_nome"],
        "escopo": ur["escopo"],
        "permissoes": [p["nome"] for p in perms],
    }


def get_permissoes_usuario(pessoa_id: int, sistema_folder: str) -> list:
    """Retorna a lista de permissões do usuário para um sistema."""
    return resolve_acesso_completo(pessoa_id, sistema_folder)["permissoes"]


def get_sistemas_permitidos(pessoa_id: int) -> list:
    """Retorna a lista de sistemas permitidos para o usuário.
    Formato: [{folder, role, escopo}]
    """
    conn = get_conn()
    sistemas = [dict(s) for s in conn.execute(
        "SELECT folder FROM sistemas WHERE ativo=1"
    ).fetchall()]

    # Verificar se é ADMIN_GERAL
    admin_geral = conn.execute("""
        SELECT 1 FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.pessoa_id = ? AND r.nome = 'ADMIN_GERAL'
    """, (pessoa_id,)).fetchone()

    if admin_geral:
        conn.close()
        return [{"folder": s["folder"], "role": "ADMIN_GERAL", "escopo": "GLOBAL"} for s in sistemas]

    # Buscar roles do usuário por sistema
    roles = conn.execute("""
        SELECT ur.sistema_folder, r.nome as role_nome, ur.escopo
        FROM usuario_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.pessoa_id = ?
    """, (pessoa_id,)).fetchall()
    conn.close()

    role_map = {r["sistema_folder"]: r for r in roles}
    result = []
    for s in sistemas:
        folder = s["folder"]
        if folder in role_map:
            r = role_map[folder]
            result.append({"folder": folder, "role": r["role_nome"], "escopo": r["escopo"]})
    return result


def get_matriz_empresa(empresa_id):
    """Retorna a matriz de acesso para uma empresa: todos os sistemas vs todos os usuários."""
    conn = get_conn()
    sistemas = [dict(s) for s in conn.execute(
        "SELECT * FROM sistemas WHERE ativo=1 ORDER BY nome"
    ).fetchall()]
    pessoas = [dict(p) for p in conn.execute(
        "SELECT id, nome, email FROM pessoas WHERE empresa_id=? AND ativo=1 ORDER BY nome",
        (empresa_id,),
    ).fetchall()]

    for p in pessoas:
        roles = {}
        for ur in conn.execute("""
            SELECT ur.sistema_folder, r.nome as role_nome, ur.escopo
            FROM usuario_roles ur JOIN roles r ON ur.role_id = r.id
            WHERE ur.pessoa_id = ?
        """, (p["id"],)).fetchall():
            roles[ur["sistema_folder"]] = {"role": ur["role_nome"], "escopo": ur["escopo"]}
        p["roles_por_sistema"] = roles

    conn.close()
    return {"sistemas": sistemas, "pessoas": pessoas}


def get_matriz_pessoa(pessoa_id):
    """Retorna a matriz de acesso de uma pessoa: cada sistema com role e permissões."""
    conn = get_conn()
    sistemas = [dict(s) for s in conn.execute(
        "SELECT * FROM sistemas WHERE ativo=1 ORDER BY nome"
    ).fetchall()]
    conn.close()

    matriz = []
    for s in sistemas:
        acesso = resolve_acesso_completo(pessoa_id, s["folder"])
        matriz.append({
            "sistema_folder": s["folder"],
            "sistema_nome":   s["nome"],
            "permitido":      acesso["permitido"],
            "role":           acesso["role"],
            "escopo":         acesso["escopo"],
            "permissoes":     acesso["permissoes"],
        })
    return matriz


# ─────────────────────────────────────────────────────────────────────────────
# AUDITORIA
# ─────────────────────────────────────────────────────────────────────────────

def add_audit(acao, entidade=None, entidade_id=None, detalhe=None,
              pessoa_id=None, ip=None, empresa_id=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_logs(acao,entidade,entidade_id,detalhe,pessoa_id,empresa_id,ip,criado_em)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (acao, entidade, entidade_id, detalhe, pessoa_id, empresa_id, ip, _now()),
    )
    conn.commit()
    conn.close()


def list_audit(limit=200, pessoa_id=None, entidade=None, empresa_id=None):
    conn = get_conn()
    q = """
        SELECT a.*, p.nome as pessoa_nome, p.email as pessoa_email
        FROM audit_logs a
        LEFT JOIN pessoas p ON a.pessoa_id=p.id
    """
    w, v = [], []
    if pessoa_id:
        w.append("a.pessoa_id=?")
        v.append(pessoa_id)
    if entidade:
        w.append("a.entidade=?")
        v.append(entidade)
    if empresa_id:
        w.append("a.empresa_id=?")
        v.append(empresa_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += f" ORDER BY a.criado_em DESC LIMIT {int(limit)}"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def get_dashboard(empresa_id=None):
    conn = get_conn()
    if empresa_id:
        stats = {
            "total_empresas":      1,
            "total_departamentos": conn.execute("SELECT COUNT(*) FROM departamentos WHERE empresa_id=?", (empresa_id,)).fetchone()[0],
            "total_pessoas":       conn.execute("SELECT COUNT(*) FROM pessoas WHERE ativo=1 AND empresa_id=?", (empresa_id,)).fetchone()[0],
            "total_roles":         conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0],
            "total_sistemas":      conn.execute("SELECT COUNT(*) FROM sistemas WHERE ativo=1").fetchone()[0],
            "total_vinculos":      conn.execute(
                "SELECT COUNT(*) FROM usuario_roles ur JOIN pessoas p ON ur.pessoa_id=p.id WHERE p.empresa_id=?",
                (empresa_id,),
            ).fetchone()[0],
            "ultimos_eventos": [dict(x) for x in conn.execute("""
                SELECT a.*, p.nome as pessoa_nome FROM audit_logs a
                LEFT JOIN pessoas p ON a.pessoa_id=p.id
                WHERE a.empresa_id=? OR a.pessoa_id IN (SELECT id FROM pessoas WHERE empresa_id=?)
                ORDER BY a.criado_em DESC LIMIT 8
            """, (empresa_id, empresa_id)).fetchall()],
        }
    else:
        stats = {
            "total_empresas":      conn.execute("SELECT COUNT(*) FROM empresas WHERE ativo=1").fetchone()[0],
            "total_departamentos": conn.execute("SELECT COUNT(*) FROM departamentos").fetchone()[0],
            "total_pessoas":       conn.execute("SELECT COUNT(*) FROM pessoas WHERE ativo=1").fetchone()[0],
            "total_roles":         conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0],
            "total_sistemas":      conn.execute("SELECT COUNT(*) FROM sistemas WHERE ativo=1").fetchone()[0],
            "total_vinculos":      conn.execute("SELECT COUNT(*) FROM usuario_roles").fetchone()[0],
            "ultimos_eventos": [dict(x) for x in conn.execute("""
                SELECT a.*, p.nome as pessoa_nome FROM audit_logs a
                LEFT JOIN pessoas p ON a.pessoa_id=p.id
                ORDER BY a.criado_em DESC LIMIT 8
            """).fetchall()],
        }
    conn.close()
    return stats
