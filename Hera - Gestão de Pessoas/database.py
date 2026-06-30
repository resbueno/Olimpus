from __future__ import annotations
"""
database.py — Hera: Gestão de Pessoas
SQLite — Colaboradores, Onboarding, Férias, Avaliações, Feedbacks, Kudos, PDI, Treinamentos
"""
import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hera.db")


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
            data_admissao   TEXT    DEFAULT '',
            gestor_id       INTEGER,
            foto_url        TEXT    DEFAULT '',
            ativo           INTEGER NOT NULL DEFAULT 1,
            atlas_id        INTEGER,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (gestor_id)       REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS onboarding_etapas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo      TEXT    NOT NULL,
            descricao   TEXT    DEFAULT '',
            ordem       INTEGER NOT NULL DEFAULT 0,
            obrigatoria INTEGER NOT NULL DEFAULT 1,
            ativo       INTEGER NOT NULL DEFAULT 1,
            criado_em   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS onboarding_progresso (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            etapa_id     INTEGER NOT NULL,
            concluida    INTEGER NOT NULL DEFAULT 0,
            concluida_em TEXT,
            observacao   TEXT    DEFAULT '',
            UNIQUE(user_id, etapa_id),
            FOREIGN KEY (user_id)  REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (etapa_id) REFERENCES onboarding_etapas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ferias (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            data_inicio  TEXT    NOT NULL,
            data_fim     TEXT    NOT NULL,
            dias         INTEGER NOT NULL DEFAULT 0,
            status       TEXT    NOT NULL DEFAULT 'pendente',
            aprovado_por INTEGER,
            aprovado_em  TEXT,
            observacao   TEXT    DEFAULT '',
            fracionado   INTEGER NOT NULL DEFAULT 0,
            criado_em    TEXT    NOT NULL,
            FOREIGN KEY (user_id)      REFERENCES users(id),
            FOREIGN KEY (aprovado_por) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ferias_periodos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ferias_id     INTEGER NOT NULL,
            sequencia     INTEGER NOT NULL,
            data_inicio   TEXT    NOT NULL,
            data_fim      TEXT    NOT NULL,
            duracao_dias  INTEGER NOT NULL,
            status        TEXT    NOT NULL DEFAULT 'pendente',
            criado_em     TEXT    NOT NULL,
            FOREIGN KEY (ferias_id) REFERENCES ferias(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ciclos_avaliacao (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo      TEXT    NOT NULL,
            descricao   TEXT    DEFAULT '',
            tipo        TEXT    NOT NULL DEFAULT '360',
            data_inicio TEXT    NOT NULL,
            data_fim    TEXT    NOT NULL,
            ativo       INTEGER NOT NULL DEFAULT 1,
            criado_em   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS avaliacoes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ciclo_id        INTEGER NOT NULL,
            avaliado_id     INTEGER NOT NULL,
            avaliador_id    INTEGER NOT NULL,
            tipo_avaliador  TEXT    NOT NULL DEFAULT 'par',
            nota_geral      REAL,
            pontos_fortes   TEXT    DEFAULT '',
            pontos_melhoria TEXT    DEFAULT '',
            enviada         INTEGER NOT NULL DEFAULT 0,
            enviada_em      TEXT,
            criado_em       TEXT    NOT NULL,
            UNIQUE(ciclo_id, avaliado_id, avaliador_id),
            FOREIGN KEY (ciclo_id)     REFERENCES ciclos_avaliacao(id),
            FOREIGN KEY (avaliado_id)  REFERENCES users(id),
            FOREIGN KEY (avaliador_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feedbacks (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            de_user_id     INTEGER NOT NULL,
            para_user_id   INTEGER NOT NULL,
            texto          TEXT    NOT NULL,
            tipo           TEXT    NOT NULL DEFAULT 'positivo',
            visivel_gestor INTEGER NOT NULL DEFAULT 1,
            criado_em      TEXT    NOT NULL,
            FOREIGN KEY (de_user_id)   REFERENCES users(id),
            FOREIGN KEY (para_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS kudos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            de_user_id    INTEGER NOT NULL,
            para_user_id  INTEGER NOT NULL,
            mensagem      TEXT    NOT NULL,
            valor         TEXT    NOT NULL DEFAULT 'colaboracao',
            criado_em     TEXT    NOT NULL,
            FOREIGN KEY (de_user_id)   REFERENCES users(id),
            FOREIGN KEY (para_user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS pdi (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            titulo         TEXT    NOT NULL,
            objetivo       TEXT    DEFAULT '',
            periodo_inicio TEXT    NOT NULL,
            periodo_fim    TEXT    NOT NULL,
            status         TEXT    NOT NULL DEFAULT 'ativo',
            criado_em      TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS pdi_acoes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            pdi_id       INTEGER NOT NULL,
            descricao    TEXT    NOT NULL,
            prazo        TEXT    NOT NULL,
            status       TEXT    NOT NULL DEFAULT 'pendente',
            concluida_em TEXT,
            criado_em    TEXT    NOT NULL,
            FOREIGN KEY (pdi_id) REFERENCES pdi(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS treinamentos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo        TEXT    NOT NULL,
            descricao     TEXT    DEFAULT '',
            carga_horaria INTEGER DEFAULT 0,
            modalidade    TEXT    NOT NULL DEFAULT 'online',
            link          TEXT    DEFAULT '',
            ativo         INTEGER NOT NULL DEFAULT 1,
            criado_em     TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS treinamento_inscricoes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            treinamento_id INTEGER NOT NULL,
            user_id        INTEGER NOT NULL,
            status         TEXT    NOT NULL DEFAULT 'inscrito',
            nota           REAL,
            concluido_em   TEXT,
            criado_em      TEXT    NOT NULL,
            UNIQUE(treinamento_id, user_id),
            FOREIGN KEY (treinamento_id) REFERENCES treinamentos(id),
            FOREIGN KEY (user_id)        REFERENCES users(id)
        );
    """)
    conn.commit()

    # Migrations — colunas adicionadas em versões posteriores
    for sql in [
        "ALTER TABLE users ADD COLUMN foto_url TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN atlas_id INTEGER",
        "ALTER TABLE users ADD COLUMN data_admissao TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN gestor_id INTEGER REFERENCES users(id)",
        "ALTER TABLE users ADD COLUMN cargo TEXT DEFAULT ''",
        "ALTER TABLE departamentos ADD COLUMN atlas_empresa_id INTEGER",
        "ALTER TABLE users ADD COLUMN salario_mensal REAL DEFAULT 0",
        "ALTER TABLE ferias ADD COLUMN aprovado_em TEXT",
        "ALTER TABLE ferias ADD COLUMN fracionado INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN empresa_id INTEGER",
    ]:
        try:
            conn.execute(sql); conn.commit()
        except Exception:
            pass

    # Etapas de onboarding padrão
    etapas_padrao = [
        (1, "Documentação e contratos",    "Assinar contrato CLT/PJ e entregar documentos ao RH", 1),
        (2, "Configuração de acessos",     "Criar e-mail corporativo e liberar sistemas internos", 1),
        (3, "Kit boas-vindas",             "Entregar equipamentos, crachá e acessos físicos",      1),
        (4, "Apresentação da equipe",      "Reunião de integração com o time e gestor direto",     1),
        (5, "Treinamento de cultura",      "Apresentação de missão, valores e cultura da empresa", 1),
        (6, "Treinamento de ferramentas",  "Capacitação nas ferramentas do dia a dia",             0),
        (7, "Reunião de alinhamento",      "Alinhar expectativas, metas e plano dos 30 primeiros dias", 1),
        (8, "Check-in 30 dias",            "Avaliação de integração após 30 dias na empresa",      1),
    ]
    for ordem, titulo, desc, obrig in etapas_padrao:
        if not conn.execute("SELECT 1 FROM onboarding_etapas WHERE titulo=?", (titulo,)).fetchone():
            conn.execute(
                "INSERT INTO onboarding_etapas(titulo,descricao,ordem,obrigatoria,criado_em)"
                " VALUES(?,?,?,?,?)",
                (titulo, desc, ordem, obrig, _now())
            )

    # Admin padrão
    if not conn.execute("SELECT 1 FROM users WHERE email='admin@olimpus.local'").fetchone():
        conn.execute(
            "INSERT INTO users(nome,email,senha_hash,role,criado_em) VALUES(?,?,?,?,?)",
            ("Administrador RH", "admin@olimpus.local", _hash("Hera@2024"), "admin", _now())
        )
    conn.commit()
    conn.close()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _map_atlas_role(tipos_acesso: list = None, funcoes: list = None, role_sistema: str = "") -> str:
    """
    Resolve a role do usuário no Hera.
    Prioridade:
      1. role_sistema do Atlas RBAC v4.0 (ADMIN_GERAL, ADMIN, GESTOR, USER)
      2. role_sistema legado (admin, rh, colaborador)
      3. Funções globais do Atlas (fallback)
    Roles válidas no Hera: admin > rh > colaborador.
    """
    rs = role_sistema.upper()
    if rs in ("ADMIN_GERAL", "ADMIN"):
        return "admin"
    if rs == "GESTOR":
        return "rh"
    if rs == "USER":
        return "colaborador"
    if role_sistema in ("admin", "rh", "colaborador"):
        return role_sistema
    funcoes = funcoes or []
    if "admin" in funcoes:
        return "admin"
    if any(f in funcoes for f in ("gestor", "editor", "operador")):
        return "rh"
    return "colaborador"


# ── Users ──────────────────────────────────────────────────────────────────────

def get_user(uid):
    conn = get_conn()
    r = conn.execute("""
        SELECT u.*, d.nome as departamento_nome,
               g.nome as gestor_nome, g.email as gestor_email
        FROM users u
        LEFT JOIN departamentos d ON u.departamento_id=d.id
        LEFT JOIN users g ON u.gestor_id=g.id
        WHERE u.id=?
    """, (uid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def get_user_by_email(email):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(r) if r else None


def get_user_by_atlas_id(atlas_id: int):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE atlas_id=?", (atlas_id,)).fetchone()
    conn.close()
    return dict(r) if r else None


def is_gestor(uid: int) -> bool:
    conn = get_conn()
    r = conn.execute("SELECT 1 FROM users WHERE gestor_id=? LIMIT 1", (uid,)).fetchone()
    conn.close()
    return bool(r)


def list_users(ativo_only=True, departamento_id=None, empresa_id=None,
               gestor_id=None, ids=None):
    conn = get_conn()
    q = """
        SELECT u.id, u.nome, u.email, u.role, u.cargo, u.data_admissao,
               u.departamento_id, u.empresa_id, u.gestor_id, u.foto_url, u.ativo, u.criado_em,
               d.nome as departamento_nome,
               g.nome as gestor_nome
        FROM users u
        LEFT JOIN departamentos d ON u.departamento_id=d.id
        LEFT JOIN users g ON u.gestor_id=g.id
    """
    w, v = [], []
    if ativo_only:
        w.append("u.ativo=1")
    if departamento_id:
        w.append("u.departamento_id=?"); v.append(departamento_id)
    if empresa_id:
        w.append("u.empresa_id=?"); v.append(empresa_id)
    if gestor_id is not None:
        w.append("u.gestor_id=?"); v.append(gestor_id)
    if ids is not None:
        if not ids:
            conn.close(); return []
        ph = ",".join("?" * len(ids))
        w.append(f"u.id IN ({ph})"); v.extend(ids)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " ORDER BY u.nome"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def update_user(uid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "cargo", "departamento_id", "gestor_id",
              "data_admissao", "foto_url", "role", "ativo", "salario_mensal"]:
        if f in data:
            fields.append(f"{f}=?")
            vals.append(data[f] if data[f] != "" else None)
    if data.get("senha"):
        fields.append("senha_hash=?"); vals.append(_hash(data["senha"]))
    if fields:
        vals.append(uid)
        conn.execute(f"UPDATE users SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def check_password(email, pw) -> bool:
    u = get_user_by_email(email)
    return bool(u and u["ativo"] and u["senha_hash"] == _hash(pw))


def get_or_create_dept_from_atlas(empresa_id: int, empresa_nome: str) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM departamentos WHERE atlas_empresa_id=?", (empresa_id,)
    ).fetchone()
    if row:
        conn.execute("UPDATE departamentos SET nome=? WHERE id=?", (empresa_nome, row[0]))
        conn.commit(); conn.close()
        return row[0]
    row = conn.execute(
        "SELECT id FROM departamentos WHERE nome=? AND (atlas_empresa_id IS NULL OR atlas_empresa_id=0)",
        (empresa_nome,)
    ).fetchone()
    if row:
        conn.execute("UPDATE departamentos SET atlas_empresa_id=? WHERE id=?",
                     (empresa_id, row[0]))
        conn.commit(); conn.close()
        return row[0]
    c = conn.cursor()
    c.execute(
        "INSERT INTO departamentos(nome,atlas_empresa_id,criado_em) VALUES(?,?,?)",
        (empresa_nome, empresa_id, _now())
    )
    conn.commit()
    new_id = c.lastrowid; conn.close()
    return new_id


def _resolve_gestor_local(atlas_gestor_id):
    """Dado o atlas_id do gestor, retorna o id local do gestor no Hera (ou None)."""
    if not atlas_gestor_id:
        return None
    g = get_user_by_atlas_id(atlas_gestor_id)
    return g["id"] if g else None


def get_or_create_user_from_atlas(atlas_user: dict) -> dict:
    email        = (atlas_user.get("email") or "").lower().strip()
    nome         = atlas_user.get("nome") or email
    tipos_acesso = atlas_user.get("tipos_acesso") or []
    funcoes      = atlas_user.get("funcoes") or []
    role         = _map_atlas_role(
        tipos_acesso,
        funcoes,
        atlas_user.get("_role_sistema", ""),
    )
    empresa_id        = atlas_user.get("empresa_id")
    empresa_nome      = (atlas_user.get("empresa_nome") or "").strip()
    cargo             = (atlas_user.get("cargo") or "").strip()
    atlas_id          = atlas_user.get("id")
    salario           = float(atlas_user.get("salario") or 0) or 0.0
    atlas_gestor_id   = atlas_user.get("gestor_id")   # ID do gestor no Atlas
    gestor_local_id   = _resolve_gestor_local(atlas_gestor_id)

    dept_id = None
    if empresa_id and empresa_nome:
        dept_id = get_or_create_dept_from_atlas(empresa_id, empresa_nome)

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row:
        u = dict(row)
        upd = {}
        if u["nome"] != nome:                                    upd["nome"] = nome
        if u["role"] != role:                                    upd["role"] = role
        if cargo and u.get("cargo") != cargo:                    upd["cargo"] = cargo
        if dept_id and u.get("departamento_id") != dept_id:     upd["departamento_id"] = dept_id
        if atlas_id and u.get("atlas_id") != atlas_id:          upd["atlas_id"] = atlas_id
        if u.get("salario_mensal") != salario:                   upd["salario_mensal"] = salario
        if empresa_id and u.get("empresa_id") != empresa_id:    upd["empresa_id"] = empresa_id
        # Sincroniza gestor_id se o Atlas enviou o campo
        if "gestor_id" in atlas_user:
            novo_gestor = gestor_local_id  # None se sem gestor ou gestor ainda não sincronizado
            if u.get("gestor_id") != novo_gestor:
                upd["gestor_id"] = novo_gestor
        if upd:
            flds = [f"{k}=?" for k in upd]
            vals = list(upd.values()) + [u["id"]]
            conn.execute(f"UPDATE users SET {','.join(flds)} WHERE id=?", vals)
            conn.commit()
        if not u["ativo"]:
            conn.execute("UPDATE users SET ativo=1 WHERE id=?", (u["id"],))
            conn.commit()
        conn.close()
        return get_user(u["id"])

    import os as _os
    dummy = hashlib.sha256(_os.urandom(32)).hexdigest()
    c = conn.cursor()
    c.execute(
        "INSERT INTO users(nome,email,senha_hash,role,cargo,departamento_id,empresa_id,atlas_id,salario_mensal,criado_em)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (nome, email, dummy, role, cargo, dept_id, empresa_id or None, atlas_id, salario, _now())
    )
    conn.commit()
    uid = c.lastrowid; conn.close()
    # Inicializa progresso de onboarding
    _init_onboarding(uid)
    return get_user(uid)


def _init_onboarding(user_id: int):
    """Cria entradas de progresso de onboarding para todas as etapas ativas."""
    conn = get_conn()
    etapas = conn.execute(
        "SELECT id FROM onboarding_etapas WHERE ativo=1"
    ).fetchall()
    for e in etapas:
        conn.execute(
            "INSERT OR IGNORE INTO onboarding_progresso(user_id,etapa_id) VALUES(?,?)",
            (user_id, e[0])
        )
    conn.commit(); conn.close()


# ── Departamentos ──────────────────────────────────────────────────────────────

def list_departamentos(empresa_id=None):
    conn = get_conn()
    q = """
        SELECT d.*, COUNT(DISTINCT u.id) as total_colaboradores
        FROM departamentos d
        LEFT JOIN users u ON u.departamento_id=d.id AND u.ativo=1
    """
    w, v = [], []
    if empresa_id is not None:
        w.append("d.atlas_empresa_id=?"); v.append(empresa_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " GROUP BY d.id ORDER BY d.nome"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_departamento(did):
    conn = get_conn()
    r = conn.execute("SELECT * FROM departamentos WHERE id=?", (did,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_departamento(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO departamentos(nome,criado_em) VALUES(?,?)",
              (data["nome"], _now()))
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_departamento(did, data):
    conn = get_conn()
    if "nome" in data:
        conn.execute("UPDATE departamentos SET nome=? WHERE id=?", (data["nome"], did))
        conn.commit()
    conn.close()


def delete_departamento(did):
    conn = get_conn()
    conn.execute("UPDATE users SET departamento_id=NULL WHERE departamento_id=?", (did,))
    conn.execute("DELETE FROM departamentos WHERE id=?", (did,))
    conn.commit(); conn.close()


# ── Onboarding ─────────────────────────────────────────────────────────────────

def list_onboarding_etapas(ativo_only=True):
    conn = get_conn()
    q = "SELECT * FROM onboarding_etapas"
    if ativo_only:
        q += " WHERE ativo=1"
    q += " ORDER BY ordem"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def create_onboarding_etapa(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO onboarding_etapas(titulo,descricao,ordem,obrigatoria,criado_em)"
        " VALUES(?,?,?,?,?)",
        (data["titulo"], data.get("descricao", ""),
         data.get("ordem", 0), 1 if data.get("obrigatoria", True) else 0, _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_onboarding_etapa(eid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["titulo", "descricao", "ordem", "obrigatoria", "ativo"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(eid)
        conn.execute(f"UPDATE onboarding_etapas SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def get_onboarding_progresso(user_id: int):
    conn = get_conn()
    r = conn.execute("""
        SELECT e.id as etapa_id, e.titulo, e.descricao, e.ordem, e.obrigatoria,
               p.concluida, p.concluida_em, p.observacao
        FROM onboarding_etapas e
        LEFT JOIN onboarding_progresso p ON p.etapa_id=e.id AND p.user_id=?
        WHERE e.ativo=1
        ORDER BY e.ordem
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(x) for x in r]


def update_onboarding_progresso(user_id: int, etapa_id: int, concluida: bool, observacao=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO onboarding_progresso(user_id,etapa_id,concluida,concluida_em,observacao)
        VALUES(?,?,?,?,?)
        ON CONFLICT(user_id,etapa_id) DO UPDATE SET
            concluida=excluded.concluida,
            concluida_em=excluded.concluida_em,
            observacao=excluded.observacao
    """, (user_id, etapa_id, 1 if concluida else 0,
          _now() if concluida else None, observacao))
    conn.commit(); conn.close()


# ── Férias ────────────────────────────────────────────────────────────────────

def list_ferias(user_id=None, status=None, gestor_id=None, user_ids=None):
    conn = get_conn()
    q = """
        SELECT f.*, u.nome as user_nome, u.email as user_email, u.gestor_id,
               ap.nome as aprovado_por_nome
        FROM ferias f
        JOIN users u ON f.user_id=u.id
        LEFT JOIN users ap ON f.aprovado_por=ap.id
    """
    w, v = [], []
    if user_id:
        w.append("f.user_id=?"); v.append(user_id)
    if gestor_id:
        w.append("u.gestor_id=?"); v.append(gestor_id)
    if status:
        w.append("f.status=?"); v.append(status)
    if user_ids is not None:
        if not user_ids:
            conn.close(); return []
        placeholders = ",".join("?" * len(user_ids))
        w.append(f"f.user_id IN ({placeholders})")
        v.extend(user_ids)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " ORDER BY f.criado_em DESC"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def list_ferias_equipe(gestor_id: int):
    """Retorna o status de férias de todos os subordinados de um gestor."""
    conn = get_conn()
    equipe = conn.execute(
        "SELECT id, nome, email, data_admissao, cargo FROM users WHERE gestor_id=? AND ativo=1",
        (gestor_id,)
    ).fetchall()

    from ferias_calc import FeriasCalculador
    resultado = []

    for colab in equipe:
        colab_dict = dict(colab)
        # Busca histórico de férias do colaborador para classificar o status
        ferias = conn.execute(
            "SELECT status, data_inicio FROM ferias WHERE user_id=?",
            (colab_dict["id"],)
        ).fetchall()
        ferias_list = [dict(f) for f in ferias]

        status_info = FeriasCalculador.classificar_status_ferias(
            colab_dict["data_admissao"], ferias_list
        )
        colab_dict.update(status_info)
        resultado.append(colab_dict)

    conn.close()
    return resultado


def create_ferias(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ferias(user_id,data_inicio,data_fim,dias,observacao,criado_em)"
        " VALUES(?,?,?,?,?,?)",
        (data["user_id"], data["data_inicio"], data["data_fim"],
         data.get("dias", 0), data.get("observacao", ""), _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_ferias_status(fid: int, status: str, aprovado_por: int):
    conn = get_conn()
    conn.execute(
        "UPDATE ferias SET status=?, aprovado_por=?, aprovado_em=? WHERE id=?",
        (status, aprovado_por, _now(), fid)
    )
    conn.commit(); conn.close()


def get_ferias(fid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM ferias WHERE id=?", (fid,)).fetchone()
    if not r:
        conn.close(); return None
    f = dict(r)
    # Carrega períodos se fracionado
    if f["fracionado"]:
        periodos = conn.execute(
            "SELECT * FROM ferias_periodos WHERE ferias_id=? ORDER BY sequencia",
            (fid,)
        ).fetchall()
        f["periodos"] = [dict(p) for p in periodos]
    conn.close()
    return f


def create_ferias_periodos(ferias_id: int, periodos: list):
    """Cria períodos fracionados para uma solicitação de férias."""
    conn = get_conn()
    for i, periodo in enumerate(periodos, 1):
        conn.execute(
            "INSERT INTO ferias_periodos(ferias_id,sequencia,data_inicio,data_fim,duracao_dias,criado_em)"
            " VALUES(?,?,?,?,?,?)",
            (ferias_id, i, periodo["data_inicio"], periodo["data_fim"],
             periodo["duracao_dias"], _now())
        )
    # Marca a solicitação como fracionada
    conn.execute("UPDATE ferias SET fracionado=1 WHERE id=?", (ferias_id,))
    conn.commit()
    conn.close()


# ── Ciclos de Avaliação ────────────────────────────────────────────────────────

def list_ciclos(ativo_only=False):
    conn = get_conn()
    q = """
        SELECT c.*, COUNT(DISTINCT a.id) as total_avaliacoes
        FROM ciclos_avaliacao c
        LEFT JOIN avaliacoes a ON a.ciclo_id=c.id
    """
    if ativo_only:
        q += " WHERE c.ativo=1"
    q += " GROUP BY c.id ORDER BY c.data_inicio DESC"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_ciclo(cid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM ciclos_avaliacao WHERE id=?", (cid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_ciclo(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO ciclos_avaliacao(titulo,descricao,tipo,data_inicio,data_fim,criado_em)"
        " VALUES(?,?,?,?,?,?)",
        (data["titulo"], data.get("descricao", ""), data.get("tipo", "360"),
         data["data_inicio"], data["data_fim"], _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_ciclo(cid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["titulo", "descricao", "data_inicio", "data_fim", "ativo"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(cid)
        conn.execute(f"UPDATE ciclos_avaliacao SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


# ── Avaliações ─────────────────────────────────────────────────────────────────

def list_avaliacoes(ciclo_id=None, avaliado_id=None, avaliador_id=None):
    conn = get_conn()
    q = """
        SELECT a.*,
               av.nome as avaliado_nome, av.email as avaliado_email,
               ar.nome as avaliador_nome, ar.email as avaliador_email
        FROM avaliacoes a
        JOIN users av ON a.avaliado_id=av.id
        JOIN users ar ON a.avaliador_id=ar.id
    """
    w, v = [], []
    if ciclo_id:
        w.append("a.ciclo_id=?"); v.append(ciclo_id)
    if avaliado_id:
        w.append("a.avaliado_id=?"); v.append(avaliado_id)
    if avaliador_id:
        w.append("a.avaliador_id=?"); v.append(avaliador_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def upsert_avaliacao(data) -> int:
    conn = get_conn()
    ex = conn.execute(
        "SELECT id FROM avaliacoes WHERE ciclo_id=? AND avaliado_id=? AND avaliador_id=?",
        (data["ciclo_id"], data["avaliado_id"], data["avaliador_id"])
    ).fetchone()
    if ex:
        conn.execute("""
            UPDATE avaliacoes SET nota_geral=?,pontos_fortes=?,pontos_melhoria=?,
            tipo_avaliador=?,enviada=?,enviada_em=? WHERE id=?
        """, (data.get("nota_geral"), data.get("pontos_fortes", ""),
              data.get("pontos_melhoria", ""), data.get("tipo_avaliador", "par"),
              1 if data.get("enviada") else 0,
              _now() if data.get("enviada") else None, ex[0]))
        conn.commit(); new_id = ex[0]
    else:
        c = conn.cursor()
        c.execute("""
            INSERT INTO avaliacoes(ciclo_id,avaliado_id,avaliador_id,tipo_avaliador,
                nota_geral,pontos_fortes,pontos_melhoria,enviada,enviada_em,criado_em)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (data["ciclo_id"], data["avaliado_id"], data["avaliador_id"],
              data.get("tipo_avaliador", "par"), data.get("nota_geral"),
              data.get("pontos_fortes", ""), data.get("pontos_melhoria", ""),
              1 if data.get("enviada") else 0,
              _now() if data.get("enviada") else None, _now()))
        conn.commit(); new_id = c.lastrowid
    conn.close()
    return new_id


# ── Feedbacks ─────────────────────────────────────────────────────────────────

def list_feedbacks(para_user_id=None, de_user_id=None, limit=50):
    conn = get_conn()
    q = """
        SELECT f.*, d.nome as de_nome, p.nome as para_nome
        FROM feedbacks f
        JOIN users d ON f.de_user_id=d.id
        JOIN users p ON f.para_user_id=p.id
    """
    w, v = [], []
    if para_user_id:
        w.append("f.para_user_id=?"); v.append(para_user_id)
    if de_user_id:
        w.append("f.de_user_id=?"); v.append(de_user_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += f" ORDER BY f.criado_em DESC LIMIT {int(limit)}"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def create_feedback(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedbacks(de_user_id,para_user_id,texto,tipo,visivel_gestor,criado_em)"
        " VALUES(?,?,?,?,?,?)",
        (data["de_user_id"], data["para_user_id"], data["texto"],
         data.get("tipo", "positivo"), 1 if data.get("visivel_gestor", True) else 0, _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def delete_feedback(fid):
    conn = get_conn()
    conn.execute("DELETE FROM feedbacks WHERE id=?", (fid,))
    conn.commit(); conn.close()


# ── Kudos ─────────────────────────────────────────────────────────────────────

def list_kudos(para_user_id=None, limit=50):
    conn = get_conn()
    q = """
        SELECT k.*, d.nome as de_nome, p.nome as para_nome
        FROM kudos k
        JOIN users d ON k.de_user_id=d.id
        JOIN users p ON k.para_user_id=p.id
    """
    if para_user_id:
        q += f" WHERE k.para_user_id={int(para_user_id)}"
    q += f" ORDER BY k.criado_em DESC LIMIT {int(limit)}"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def list_kudos_feed(limit=30):
    conn = get_conn()
    r = conn.execute("""
        SELECT k.*, d.nome as de_nome, p.nome as para_nome,
               d.cargo as de_cargo, p.cargo as para_cargo
        FROM kudos k
        JOIN users d ON k.de_user_id=d.id
        JOIN users p ON k.para_user_id=p.id
        ORDER BY k.criado_em DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(x) for x in r]


def create_kudos(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO kudos(de_user_id,para_user_id,mensagem,valor,criado_em)"
        " VALUES(?,?,?,?,?)",
        (data["de_user_id"], data["para_user_id"], data["mensagem"],
         data.get("valor", "colaboracao"), _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


# ── PDI ───────────────────────────────────────────────────────────────────────

def list_pdi(user_id=None):
    conn = get_conn()
    q = """
        SELECT p.*, u.nome as user_nome,
               COUNT(a.id) as total_acoes,
               SUM(CASE WHEN a.status='concluido' THEN 1 ELSE 0 END) as acoes_concluidas
        FROM pdi p
        JOIN users u ON p.user_id=u.id
        LEFT JOIN pdi_acoes a ON a.pdi_id=p.id
    """
    if user_id:
        q += f" WHERE p.user_id={int(user_id)}"
    q += " GROUP BY p.id ORDER BY p.criado_em DESC"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_pdi(pid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM pdi WHERE id=?", (pid,)).fetchone()
    if not r:
        conn.close(); return None
    p = dict(r)
    acoes = conn.execute(
        "SELECT * FROM pdi_acoes WHERE pdi_id=? ORDER BY prazo", (pid,)
    ).fetchall()
    p["acoes"] = [dict(a) for a in acoes]
    conn.close()
    return p


def create_pdi(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO pdi(user_id,titulo,objetivo,periodo_inicio,periodo_fim,criado_em)"
        " VALUES(?,?,?,?,?,?)",
        (data["user_id"], data["titulo"], data.get("objetivo", ""),
         data["periodo_inicio"], data["periodo_fim"], _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_pdi(pid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["titulo", "objetivo", "periodo_inicio", "periodo_fim", "status"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(pid)
        conn.execute(f"UPDATE pdi SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def create_pdi_acao(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO pdi_acoes(pdi_id,descricao,prazo,criado_em) VALUES(?,?,?,?)",
        (data["pdi_id"], data["descricao"], data["prazo"], _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_pdi_acao(aid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["descricao", "prazo", "status"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if data.get("status") == "concluido":
        fields.append("concluida_em=?"); vals.append(_now())
    if fields:
        vals.append(aid)
        conn.execute(f"UPDATE pdi_acoes SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_pdi_acao(aid):
    conn = get_conn()
    conn.execute("DELETE FROM pdi_acoes WHERE id=?", (aid,))
    conn.commit(); conn.close()


# ── Treinamentos ──────────────────────────────────────────────────────────────

def list_treinamentos(ativo_only=True):
    conn = get_conn()
    q = """
        SELECT t.*, COUNT(DISTINCT i.user_id) as total_inscritos,
               SUM(CASE WHEN i.status='concluido' THEN 1 ELSE 0 END) as total_concluidos
        FROM treinamentos t
        LEFT JOIN treinamento_inscricoes i ON i.treinamento_id=t.id
    """
    if ativo_only:
        q += " WHERE t.ativo=1"
    q += " GROUP BY t.id ORDER BY t.titulo"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_treinamento(tid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM treinamentos WHERE id=?", (tid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_treinamento(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO treinamentos(titulo,descricao,carga_horaria,modalidade,link,criado_em)"
        " VALUES(?,?,?,?,?,?)",
        (data["titulo"], data.get("descricao", ""), data.get("carga_horaria", 0),
         data.get("modalidade", "online"), data.get("link", ""), _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_treinamento(tid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["titulo", "descricao", "carga_horaria", "modalidade", "link", "ativo"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(tid)
        conn.execute(f"UPDATE treinamentos SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def delete_treinamento(tid):
    conn = get_conn()
    conn.execute("DELETE FROM treinamento_inscricoes WHERE treinamento_id=?", (tid,))
    conn.execute("DELETE FROM treinamentos WHERE id=?", (tid,))
    conn.commit(); conn.close()


def inscrever_treinamento(treinamento_id: int, user_id: int) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO treinamento_inscricoes(treinamento_id,user_id,criado_em)"
        " VALUES(?,?,?)",
        (treinamento_id, user_id, _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_inscricao(treinamento_id: int, user_id: int, data: dict):
    conn = get_conn()
    fields, vals = [], []
    for f in ["status", "nota"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if data.get("status") == "concluido":
        fields.append("concluido_em=?"); vals.append(_now())
    if fields:
        vals += [treinamento_id, user_id]
        conn.execute(
            f"UPDATE treinamento_inscricoes SET {','.join(fields)}"
            " WHERE treinamento_id=? AND user_id=?", vals
        )
        conn.commit()
    conn.close()


def list_inscricoes(treinamento_id=None, user_id=None):
    conn = get_conn()
    q = """
        SELECT i.*, u.nome as user_nome, t.titulo as treinamento_titulo
        FROM treinamento_inscricoes i
        JOIN users u ON i.user_id=u.id
        JOIN treinamentos t ON i.treinamento_id=t.id
    """
    w, v = [], []
    if treinamento_id:
        w.append("i.treinamento_id=?"); v.append(treinamento_id)
    if user_id:
        w.append("i.user_id=?"); v.append(user_id)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " ORDER BY i.criado_em DESC"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard_stats(empresa_id=None, departamento_id=None):
    conn = get_conn()
    # Monta filtro de usuários visíveis
    u_filter = "u.ativo=1"
    u_vals   = []
    if empresa_id:
        u_filter += " AND u.empresa_id=?"; u_vals.append(empresa_id)
    elif departamento_id:
        u_filter += " AND u.departamento_id=?"; u_vals.append(departamento_id)

    uid_subq = f"SELECT id FROM users WHERE {u_filter}"

    stats = {
        "total_colaboradores": conn.execute(
            f"SELECT COUNT(*) FROM users WHERE {u_filter}", u_vals).fetchone()[0],
        "total_departamentos": conn.execute(
            "SELECT COUNT(*) FROM departamentos").fetchone()[0],
        "ferias_pendentes": conn.execute(
            f"SELECT COUNT(*) FROM ferias WHERE status='pendente'"
            f" AND user_id IN ({uid_subq})", u_vals).fetchone()[0],
        "avaliacoes_abertas": conn.execute(
            "SELECT COUNT(*) FROM ciclos_avaliacao WHERE ativo=1").fetchone()[0],
        "treinamentos_ativos": conn.execute(
            "SELECT COUNT(*) FROM treinamentos WHERE ativo=1").fetchone()[0],
        "kudos_mes": conn.execute(
            f"SELECT COUNT(*) FROM kudos WHERE criado_em >= ?"
            f" AND (de_user_id IN ({uid_subq}) OR para_user_id IN ({uid_subq}))",
            [datetime.now().strftime("%Y-%m-01")] + u_vals + u_vals
        ).fetchone()[0],
    }
    # Aniversariantes do mês (data_admissao)
    mes_atual = datetime.now().strftime("-%m-")
    stats["aniversariantes"] = [dict(x) for x in conn.execute(f"""
        SELECT nome, cargo, departamento_id,
               (SELECT nome FROM departamentos WHERE id=u.departamento_id) as departamento_nome,
               data_admissao
        FROM users u WHERE {u_filter} AND data_admissao LIKE ?
        ORDER BY substr(data_admissao,9,2)
    """, u_vals + [f"%{mes_atual}%"]).fetchall()]
    # Kudos recentes (visíveis)
    stats["kudos_recentes"] = [dict(x) for x in conn.execute(f"""
        SELECT k.mensagem, k.valor, k.criado_em,
               d.nome as de_nome, p.nome as para_nome
        FROM kudos k
        JOIN users d ON k.de_user_id=d.id
        JOIN users p ON k.para_user_id=p.id
        WHERE k.para_user_id IN ({uid_subq}) OR k.de_user_id IN ({uid_subq})
        ORDER BY k.criado_em DESC LIMIT 5
    """, u_vals + u_vals).fetchall()]
    conn.close()
    return stats
