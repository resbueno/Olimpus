from __future__ import annotations
"""
database.py — Cronos: Ponto Eletrônico (porta 5025)
SQLite — Registros, Jornadas, Banco de Horas, Fechamentos, Feriados
"""
import hashlib
import os
import sqlite3
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cronos.db")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _today() -> str:
    return date.today().isoformat()


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
            gestor_id       INTEGER,
            jornada_id      INTEGER,
            ativo           INTEGER NOT NULL DEFAULT 1,
            atlas_id        INTEGER,
            criado_em       TEXT    NOT NULL,
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (gestor_id)       REFERENCES users(id),
            FOREIGN KEY (jornada_id)      REFERENCES jornadas(id)
        );

        CREATE TABLE IF NOT EXISTS jornadas (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              TEXT    NOT NULL,
            tipo              TEXT    NOT NULL DEFAULT 'fixo',
            horario_entrada   TEXT    NOT NULL DEFAULT '08:00',
            horario_saida     TEXT    NOT NULL DEFAULT '17:00',
            intervalo_minutos INTEGER NOT NULL DEFAULT 60,
            carga_diaria_min  INTEGER NOT NULL DEFAULT 480,
            dias_semana       TEXT    NOT NULL DEFAULT '1,2,3,4,5',
            ativo             INTEGER NOT NULL DEFAULT 1,
            criado_em         TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS registros_ponto (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            data        TEXT    NOT NULL,
            tipo        TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL,
            origem      TEXT    NOT NULL DEFAULT 'web',
            latitude    REAL,
            longitude   REAL,
            observacao  TEXT    DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'ativo',
            criado_em   TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS ajustes_ponto (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id            INTEGER NOT NULL,
            data               TEXT    NOT NULL,
            tipo_ajuste        TEXT    NOT NULL,
            timestamp_original TEXT,
            timestamp_solicitado TEXT NOT NULL,
            motivo             TEXT    NOT NULL DEFAULT '',
            status             TEXT    NOT NULL DEFAULT 'pendente',
            aprovado_por       INTEGER,
            aprovado_em        TEXT,
            criado_em          TEXT    NOT NULL,
            FOREIGN KEY (user_id)      REFERENCES users(id),
            FOREIGN KEY (aprovado_por) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS feriados (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            data      TEXT    NOT NULL UNIQUE,
            descricao TEXT    NOT NULL,
            tipo      TEXT    NOT NULL DEFAULT 'nacional',
            criado_em TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS banco_horas (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL UNIQUE,
            saldo_minutos   INTEGER NOT NULL DEFAULT 0,
            atualizado_em   TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS banco_horas_lancamentos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            data        TEXT    NOT NULL,
            minutos     INTEGER NOT NULL,
            tipo        TEXT    NOT NULL DEFAULT 'credito',
            descricao   TEXT    DEFAULT '',
            aprovado_por INTEGER,
            criado_em   TEXT    NOT NULL,
            FOREIGN KEY (user_id)      REFERENCES users(id),
            FOREIGN KEY (aprovado_por) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS fechamentos (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            mes              INTEGER NOT NULL,
            ano              INTEGER NOT NULL,
            status           TEXT    NOT NULL DEFAULT 'aberto',
            total_dias       INTEGER NOT NULL DEFAULT 0,
            total_min_trab   INTEGER NOT NULL DEFAULT 0,
            total_min_extra  INTEGER NOT NULL DEFAULT 0,
            total_min_falta  INTEGER NOT NULL DEFAULT 0,
            total_min_noturno INTEGER NOT NULL DEFAULT 0,
            fechado_por      INTEGER,
            fechado_em       TEXT,
            criado_em        TEXT    NOT NULL,
            UNIQUE(user_id, mes, ano),
            FOREIGN KEY (user_id)     REFERENCES users(id),
            FOREIGN KEY (fechado_por) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS configuracoes (
            id                    INTEGER PRIMARY KEY,
            tolerancia_entrada    INTEGER NOT NULL DEFAULT 5,
            tolerancia_saida      INTEGER NOT NULL DEFAULT 5,
            inicio_noturno        TEXT    NOT NULL DEFAULT '22:00',
            fim_noturno           TEXT    NOT NULL DEFAULT '05:00',
            percentual_noturno    REAL    NOT NULL DEFAULT 20.0,
            percentual_extra_dia  REAL    NOT NULL DEFAULT 50.0,
            percentual_extra_fds  REAL    NOT NULL DEFAULT 100.0,
            percentual_extra_fer  REAL    NOT NULL DEFAULT 100.0,
            limite_extra_dia_min  INTEGER NOT NULL DEFAULT 120
        );
    """)
    conn.commit()

    # Migrations
    for sql in [
        "ALTER TABLE users ADD COLUMN jornada_id INTEGER REFERENCES jornadas(id)",
        "ALTER TABLE users ADD COLUMN gestor_id  INTEGER REFERENCES users(id)",
        "ALTER TABLE users ADD COLUMN atlas_id   INTEGER",
        "ALTER TABLE users ADD COLUMN cargo      TEXT DEFAULT ''",
        "ALTER TABLE departamentos ADD COLUMN atlas_empresa_id INTEGER",
        "ALTER TABLE users ADD COLUMN empresa_id INTEGER",
    ]:
        try:
            conn.execute(sql); conn.commit()
        except Exception:
            pass

    # Jornada padrão
    if not conn.execute("SELECT 1 FROM jornadas").fetchone():
        conn.execute(
            "INSERT INTO jornadas(nome,tipo,horario_entrada,horario_saida,"
            "intervalo_minutos,carga_diaria_min,dias_semana,criado_em) VALUES(?,?,?,?,?,?,?,?)",
            ("Jornada Padrão 8h", "fixo", "08:00", "17:00", 60, 480, "1,2,3,4,5", _now())
        )
        conn.commit()

    # Config padrão
    if not conn.execute("SELECT 1 FROM configuracoes").fetchone():
        conn.execute("INSERT INTO configuracoes(id) VALUES(1)")
        conn.commit()

    # Admin padrão
    if not conn.execute("SELECT 1 FROM users WHERE email='admin@olimpus.local'").fetchone():
        j = conn.execute("SELECT id FROM jornadas LIMIT 1").fetchone()
        conn.execute(
            "INSERT INTO users(nome,email,senha_hash,role,jornada_id,criado_em) VALUES(?,?,?,?,?,?)",
            ("Administrador", "admin@olimpus.local", _hash("Cronos@2024"),
             "admin", j[0] if j else None, _now())
        )
        conn.commit()

    # Feriados nacionais fixos do ano corrente
    ano = date.today().year
    feriados_nacionais = [
        (f"{ano}-01-01", "Confraternização Universal"),
        (f"{ano}-04-21", "Tiradentes"),
        (f"{ano}-05-01", "Dia do Trabalhador"),
        (f"{ano}-09-07", "Independência do Brasil"),
        (f"{ano}-10-12", "Nossa Senhora Aparecida"),
        (f"{ano}-11-02", "Finados"),
        (f"{ano}-11-15", "Proclamação da República"),
        (f"{ano}-12-25", "Natal"),
    ]
    for data_f, desc in feriados_nacionais:
        if not conn.execute("SELECT 1 FROM feriados WHERE data=?", (data_f,)).fetchone():
            conn.execute(
                "INSERT INTO feriados(data,descricao,tipo,criado_em) VALUES(?,?,?,?)",
                (data_f, desc, "nacional", _now())
            )
    conn.commit()
    conn.close()


# ── Helpers internos ───────────────────────────────────────────────────────────

def _map_atlas_role(funcoes: list, role_sistema: str = "") -> str:
    """
    Resolve a role do usuário no Cronos.
    Prioridade: role_sistema definida no Atlas > mapeamento por funç��es globais (fallback).
    Roles válidas no Cronos: admin > rh > gestor > colaborador.
    Compatível com RBAC v4.0 (ADMIN_GERAL, ADMIN, GESTOR, USER) e legado.
    """
    rs = role_sistema.upper()
    if rs in ("ADMIN_GERAL", "ADMIN"):
        return "admin"
    if rs == "GESTOR":
        return "gestor"
    if rs == "USER":
        return "colaborador"
    if role_sistema in ("admin", "rh", "gestor", "colaborador"):
        return role_sistema
    if "admin" in funcoes:
        return "admin"
    if any(f in funcoes for f in ("gestor", "editor", "operador")):
        return "rh"
    return "colaborador"


def _min_to_hhmm(minutos: int) -> str:
    """Converte minutos (pode ser negativo) para string ±HH:MM."""
    sinal = "-" if minutos < 0 else "+"
    m = abs(minutos)
    return f"{sinal}{m // 60:02d}:{m % 60:02d}"


def _parse_time(t: str) -> int:
    """HH:MM → minutos desde meia-noite."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _ts_to_min(ts: str) -> int:
    """ISO timestamp → minutos desde meia-noite."""
    t = ts[11:16]  # HH:MM
    return _parse_time(t)


# ── Motor de cálculo ───────────────────────────────────────────────────────────

def calcular_dia(user_id: int, data: str) -> dict:
    """
    Calcula totais de um dia para um colaborador:
    horas trabalhadas, extras, faltas, adicional noturno.
    Retorna dict com campos em minutos.
    """
    conn = get_conn()
    registros = conn.execute(
        "SELECT tipo, timestamp FROM registros_ponto "
        "WHERE user_id=? AND data=? AND status='ativo' ORDER BY timestamp",
        (user_id, data)
    ).fetchall()
    registros = [dict(r) for r in registros]

    user     = conn.execute("SELECT jornada_id FROM users WHERE id=?", (user_id,)).fetchone()
    jornada  = None
    if user and user["jornada_id"]:
        jornada = conn.execute("SELECT * FROM jornadas WHERE id=?", (user["jornada_id"],)).fetchone()
        jornada = dict(jornada)

    cfg      = conn.execute("SELECT * FROM configuracoes WHERE id=1").fetchone()
    cfg      = dict(cfg) if cfg else {}

    feriado  = conn.execute("SELECT 1 FROM feriados WHERE data=?", (data,)).fetchone()
    conn.close()

    carga_diaria = (jornada["carga_diaria_min"] if jornada else 480)
    intervalo_min = (jornada["intervalo_minutos"] if jornada else 60)

    # Identifica marcações por tipo
    tipos = {r["tipo"]: r["timestamp"] for r in registros}
    # Pode ter múltiplas saídas — pega a última
    entradas = [r["timestamp"] for r in registros if r["tipo"] == "entrada"]
    saidas   = [r["timestamp"] for r in registros if r["tipo"] == "saida"]
    int_ini  = [r["timestamp"] for r in registros if r["tipo"] == "intervalo_inicio"]
    int_fim  = [r["timestamp"] for r in registros if r["tipo"] == "intervalo_fim"]

    resultado = {
        "data":           data,
        "min_trabalhados": 0,
        "min_extra":       0,
        "min_falta":       0,
        "min_noturno":     0,
        "completo":        False,
        "registros":       len(registros),
    }

    if not entradas or not saidas:
        if entradas and not saidas:
            # Em andamento — calcula parcial
            entrada_ts = entradas[0]
            agora_min  = _parse_time(datetime.now().strftime("%H:%M"))
            entrada_min = _ts_to_min(entrada_ts)
            intervalo_real = 0
            if int_ini and int_fim:
                intervalo_real = _ts_to_min(int_fim[-1]) - _ts_to_min(int_ini[0])
            elif int_ini:
                intervalo_real = max(0, agora_min - _ts_to_min(int_ini[0]))
            resultado["min_trabalhados"] = max(0, agora_min - entrada_min - intervalo_real)
        else:
            # Falta (dia útil sem registro)
            d = date.fromisoformat(data)
            if jornada:
                dias_trab = [int(x) for x in jornada["dias_semana"].split(",")]
                if d.isoweekday() in dias_trab and not feriado:
                    resultado["min_falta"] = carga_diaria
        return resultado

    entrada_min = _ts_to_min(entradas[0])
    saida_min   = _ts_to_min(saidas[-1])
    if saida_min < entrada_min:
        saida_min += 1440  # virada de meia-noite

    # Intervalo efetivo
    intervalo_real = 0
    if int_ini and int_fim:
        intervalo_real = _ts_to_min(int_fim[-1]) - _ts_to_min(int_ini[0])
    elif not int_ini and not int_fim:
        # Sem marcação de intervalo: desconta automático se jornada > 6h
        bruto = saida_min - entrada_min
        if bruto > 360:
            intervalo_real = intervalo_min

    min_trab = max(0, saida_min - entrada_min - intervalo_real)
    resultado["min_trabalhados"] = min_trab
    resultado["completo"]        = True

    # Falta ou extra
    d_obj = date.fromisoformat(data)
    eh_fds = d_obj.isoweekday() in (6, 7)
    eh_feriado = bool(feriado)

    if eh_fds or eh_feriado:
        resultado["min_extra"] = min_trab
    else:
        if min_trab > carga_diaria:
            resultado["min_extra"] = min_trab - carga_diaria
        elif min_trab < carga_diaria:
            resultado["min_falta"] = carga_diaria - min_trab

    # Adicional noturno (padrão 22h–05h)
    inicio_not = _parse_time(cfg.get("inicio_noturno", "22:00"))  # 1320
    fim_not    = _parse_time(cfg.get("fim_noturno",    "05:00"))  # 300
    # Janela noturna: 22:00–29:00 (05:00 do dia seguinte)
    fim_not_ext = fim_not + 1440  # 300 + 1440 = 1740

    noturno = 0
    # Período trabalhado: entrada → saída (já ajustado p/ virada)
    for seg_ini, seg_fim in [(entrada_min, saida_min)]:
        # Interseção com janela noturna inicio_not..fim_not_ext
        if seg_fim > inicio_not:
            noturno += min(seg_fim, fim_not_ext) - max(seg_ini, inicio_not)
        # Também cobre o início do dia (antes das 05h)
        fim_manh = fim_not  # 300
        if seg_fim > 0 and seg_ini < fim_manh:
            noturno += min(seg_fim, fim_manh) - max(seg_ini, 0)

    resultado["min_noturno"] = max(0, noturno)
    return resultado


def resumo_mes(user_id: int, ano: int, mes: int) -> dict:
    """Calcula resumo do mês inteiro para um colaborador."""
    conn   = get_conn()
    user   = conn.execute("SELECT jornada_id FROM users WHERE id=?", (user_id,)).fetchone()
    jornada = None
    if user and user["jornada_id"]:
        jornada = conn.execute("SELECT * FROM jornadas WHERE id=?",
                               (user["jornada_id"],)).fetchone()
        jornada = dict(jornada)
    conn.close()

    primeiro = date(ano, mes, 1)
    if mes == 12:
        ultimo = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo = date(ano, mes + 1, 1) - timedelta(days=1)

    dias_trab = ([int(x) for x in jornada["dias_semana"].split(",")]
                 if jornada else [1, 2, 3, 4, 5])

    totais = {
        "total_dias":        0,
        "total_min_trab":    0,
        "total_min_extra":   0,
        "total_min_falta":   0,
        "total_min_noturno": 0,
        "dias_detail":       [],
    }

    cur = primeiro
    while cur <= ultimo:
        if cur.isoweekday() in dias_trab:
            d = cur.isoformat()
            r = calcular_dia(user_id, d)
            totais["total_dias"]        += 1
            totais["total_min_trab"]    += r["min_trabalhados"]
            totais["total_min_extra"]   += r["min_extra"]
            totais["total_min_falta"]   += r["min_falta"]
            totais["total_min_noturno"] += r["min_noturno"]
            totais["dias_detail"].append(r)
        cur += timedelta(days=1)

    return totais


# ── Users ──────────────────────────────────────────────────────────────────────

def get_user(uid):
    conn = get_conn()
    r = conn.execute("""
        SELECT u.*, d.nome as departamento_nome, j.nome as jornada_nome,
               g.nome as gestor_nome
        FROM users u
        LEFT JOIN departamentos d ON u.departamento_id=d.id
        LEFT JOIN jornadas j      ON u.jornada_id=j.id
        LEFT JOIN users g         ON u.gestor_id=g.id
        WHERE u.id=?
    """, (uid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def get_user_by_email(email):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    return dict(r) if r else None


def list_users(ativo_only=True, departamento_id=None, gestor_id=None, empresa_id=None):
    conn = get_conn()
    q = """
        SELECT u.id, u.nome, u.email, u.role, u.cargo, u.departamento_id,
               u.gestor_id, u.jornada_id, u.ativo, u.criado_em, u.empresa_id,
               d.nome as departamento_nome, j.nome as jornada_nome,
               g.nome as gestor_nome
        FROM users u
        LEFT JOIN departamentos d ON u.departamento_id=d.id
        LEFT JOIN jornadas j      ON u.jornada_id=j.id
        LEFT JOIN users g         ON u.gestor_id=g.id
    """
    w, v = [], []
    if ativo_only:      w.append("u.ativo=1")
    if empresa_id:      w.append("u.empresa_id=?");      v.append(empresa_id)
    if departamento_id: w.append("u.departamento_id=?"); v.append(departamento_id)
    if gestor_id:       w.append("u.gestor_id=?");       v.append(gestor_id)
    if w: q += " WHERE " + " AND ".join(w)
    q += " ORDER BY u.nome"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def update_user(uid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome", "cargo", "departamento_id", "gestor_id",
              "jornada_id", "role", "ativo"]:
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


def get_or_create_dept(empresa_id: int, empresa_nome: str) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM departamentos WHERE atlas_empresa_id=?", (empresa_id,)
    ).fetchone()
    if row:
        conn.execute("UPDATE departamentos SET nome=? WHERE id=?",
                     (empresa_nome, row[0]))
        conn.commit(); conn.close(); return row[0]
    row = conn.execute(
        "SELECT id FROM departamentos WHERE nome=? AND (atlas_empresa_id IS NULL OR atlas_empresa_id=0)",
        (empresa_nome,)
    ).fetchone()
    if row:
        conn.execute("UPDATE departamentos SET atlas_empresa_id=? WHERE id=?",
                     (empresa_id, row[0]))
        conn.commit(); conn.close(); return row[0]
    c = conn.cursor()
    c.execute("INSERT INTO departamentos(nome,atlas_empresa_id,criado_em) VALUES(?,?,?)",
              (empresa_nome, empresa_id, _now()))
    conn.commit(); nid = c.lastrowid; conn.close(); return nid


def get_or_create_user_from_atlas(atlas_user: dict) -> dict:
    email        = (atlas_user.get("email") or "").lower().strip()
    nome         = atlas_user.get("nome") or email
    role         = _map_atlas_role(
        atlas_user.get("funcoes") or [],
        atlas_user.get("_role_sistema", ""),
    )
    empresa_id   = atlas_user.get("empresa_id")
    empresa_nome = (atlas_user.get("empresa_nome") or "").strip()
    cargo        = (atlas_user.get("cargo") or "").strip()
    atlas_id     = atlas_user.get("id")

    dept_id = None
    if empresa_id and empresa_nome:
        dept_id = get_or_create_dept(empresa_id, empresa_nome)

    conn = get_conn()
    jornada_padrao = conn.execute(
        "SELECT id FROM jornadas WHERE ativo=1 ORDER BY id LIMIT 1"
    ).fetchone()
    jid = jornada_padrao[0] if jornada_padrao else None

    row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if row:
        u = dict(row)
        upd = {}
        if u["nome"] != nome:                                upd["nome"] = nome
        if u["role"] != role:                                upd["role"] = role
        if cargo and u.get("cargo") != cargo:                upd["cargo"] = cargo
        if dept_id and u.get("departamento_id") != dept_id:  upd["departamento_id"] = dept_id
        if atlas_id and u.get("atlas_id") != atlas_id:       upd["atlas_id"] = atlas_id
        if empresa_id and u.get("empresa_id") != empresa_id: upd["empresa_id"] = empresa_id
        if upd:
            flds = [f"{k}=?" for k in upd]
            conn.execute(f"UPDATE users SET {','.join(flds)} WHERE id=?",
                         list(upd.values()) + [u["id"]])
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
        "INSERT INTO users(nome,email,senha_hash,role,cargo,departamento_id,"
        "jornada_id,atlas_id,empresa_id,criado_em) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (nome, email, dummy, role, cargo, dept_id, jid, atlas_id, empresa_id, _now())
    )
    conn.commit(); uid = c.lastrowid; conn.close()
    # Inicializa banco de horas
    _init_banco_horas(uid)
    return get_user(uid)


def _init_banco_horas(user_id: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO banco_horas(user_id,saldo_minutos,atualizado_em)"
        " VALUES(?,0,?)", (user_id, _now())
    )
    conn.commit(); conn.close()


# ── Jornadas ──────────────────────────────────────────────────────────────────

def list_jornadas():
    conn = get_conn()
    r = conn.execute("""
        SELECT j.*, COUNT(u.id) as total_users
        FROM jornadas j LEFT JOIN users u ON u.jornada_id=j.id AND u.ativo=1
        GROUP BY j.id ORDER BY j.nome
    """).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_jornada(jid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM jornadas WHERE id=?", (jid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def create_jornada(data) -> int:
    conn = get_conn()
    c = conn.cursor()
    carga = data.get("carga_diaria_min")
    if not carga:
        h_ent = _parse_time(data.get("horario_entrada", "08:00"))
        h_sai = _parse_time(data.get("horario_saida",   "17:00"))
        carga = h_sai - h_ent - int(data.get("intervalo_minutos", 60))
    c.execute(
        "INSERT INTO jornadas(nome,tipo,horario_entrada,horario_saida,"
        "intervalo_minutos,carga_diaria_min,dias_semana,criado_em) VALUES(?,?,?,?,?,?,?,?)",
        (data["nome"], data.get("tipo","fixo"),
         data.get("horario_entrada","08:00"), data.get("horario_saida","17:00"),
         int(data.get("intervalo_minutos",60)), carga,
         data.get("dias_semana","1,2,3,4,5"), _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def update_jornada(jid, data):
    conn = get_conn()
    fields, vals = [], []
    for f in ["nome","tipo","horario_entrada","horario_saida",
              "intervalo_minutos","carga_diaria_min","dias_semana","ativo"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(jid)
        conn.execute(f"UPDATE jornadas SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


# ── Registros de Ponto ────────────────────────────────────────────────────────

_TIPO_ORDEM = {"entrada": 0, "intervalo_inicio": 1,
               "intervalo_fim": 2, "saida": 3}


def proximo_tipo(user_id: int, data: str) -> str | None:
    """Retorna o próximo tipo de registro esperado para o colaborador hoje."""
    conn = get_conn()
    registros = conn.execute(
        "SELECT tipo FROM registros_ponto "
        "WHERE user_id=? AND data=? AND status='ativo' ORDER BY timestamp",
        (user_id, data)
    ).fetchall()
    conn.close()
    tipos = [r[0] for r in registros]
    if not tipos:
        return "entrada"
    ultimo = tipos[-1]
    seq = ["entrada", "intervalo_inicio", "intervalo_fim", "saida"]
    if ultimo == "saida":
        return None  # jornada encerrada
    idx = seq.index(ultimo)
    return seq[idx + 1] if idx + 1 < len(seq) else None


def registrar_ponto(user_id: int, tipo: str, observacao="",
                    latitude=None, longitude=None) -> int:
    agora = datetime.now()
    conn  = get_conn()
    c     = conn.cursor()
    c.execute(
        "INSERT INTO registros_ponto(user_id,data,tipo,timestamp,origem,"
        "latitude,longitude,observacao,criado_em) VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, agora.strftime("%Y-%m-%d"), tipo,
         agora.isoformat(timespec="seconds"),
         "web", latitude, longitude, observacao, _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def list_registros(user_id=None, data=None, data_ini=None, data_fim=None, user_ids=None):
    conn = get_conn()
    q = """
        SELECT r.*, u.nome as user_nome
        FROM registros_ponto r JOIN users u ON r.user_id=u.id
    """
    w, v = [], []
    if user_id:  w.append("r.user_id=?");  v.append(user_id)
    elif user_ids is not None:
        if not user_ids:
            conn.close(); return []
        w.append(f"r.user_id IN ({','.join(['?']*len(user_ids))})"); v.extend(user_ids)
    if data:     w.append("r.data=?");     v.append(data)
    if data_ini: w.append("r.data>=?");   v.append(data_ini)
    if data_fim: w.append("r.data<=?");   v.append(data_fim)
    if w: q += " WHERE " + " AND ".join(w)
    q += " ORDER BY r.data, r.timestamp"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def get_registros_dia(user_id: int, data: str) -> list:
    return list_registros(user_id=user_id, data=data)


# ── Ajustes ───────────────────────────────────────────────────────────────────

def create_ajuste(data: dict) -> int:
    conn = get_conn()
    c    = conn.cursor()
    c.execute(
        "INSERT INTO ajustes_ponto(user_id,data,tipo_ajuste,timestamp_original,"
        "timestamp_solicitado,motivo,criado_em) VALUES(?,?,?,?,?,?,?)",
        (data["user_id"], data["data"], data["tipo_ajuste"],
         data.get("timestamp_original"), data["timestamp_solicitado"],
         data.get("motivo",""), _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def get_ajuste(aid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM ajustes_ponto WHERE id=?", (aid,)).fetchone()
    conn.close()
    return dict(r) if r else None


def list_ajustes(user_id=None, status=None, user_ids=None):
    conn = get_conn()
    q = """
        SELECT a.*, u.nome as user_nome, ap.nome as aprovado_por_nome
        FROM ajustes_ponto a
        JOIN users u ON a.user_id=u.id
        LEFT JOIN users ap ON a.aprovado_por=ap.id
    """
    w, v = [], []
    if user_id: w.append("a.user_id=?"); v.append(user_id)
    elif user_ids is not None:
        if not user_ids:
            conn.close(); return []
        w.append(f"a.user_id IN ({','.join(['?']*len(user_ids))})"); v.extend(user_ids)
    if status:  w.append("a.status=?");  v.append(status)
    if w: q += " WHERE " + " AND ".join(w)
    q += " ORDER BY a.criado_em DESC"
    r = conn.execute(q, v).fetchall()
    conn.close()
    return [dict(x) for x in r]


def aprovar_ajuste(aid: int, aprovado_por: int, status: str):
    conn = get_conn()
    aj = conn.execute("SELECT * FROM ajustes_ponto WHERE id=?", (aid,)).fetchone()
    if not aj:
        conn.close(); return
    conn.execute(
        "UPDATE ajustes_ponto SET status=?,aprovado_por=?,aprovado_em=? WHERE id=?",
        (status, aprovado_por, _now(), aid)
    )
    if status == "aprovado":
        # Aplica o ajuste: insere ou atualiza registro
        conn.execute(
            "UPDATE registros_ponto SET status='ajustado' "
            "WHERE user_id=? AND data=? AND tipo=?",
            (aj["user_id"], aj["data"], aj["tipo_ajuste"])
        )
        conn.execute(
            "INSERT INTO registros_ponto(user_id,data,tipo,timestamp,origem,observacao,criado_em)"
            " VALUES(?,?,?,?,?,?,?)",
            (aj["user_id"], aj["data"], aj["tipo_ajuste"],
             aj["timestamp_solicitado"], "ajuste",
             f"Ajuste aprovado por {aprovado_por}", _now())
        )
    conn.commit(); conn.close()


# ── Feriados ──────────────────────────────────────────────────────────────────

def list_feriados(ano=None):
    conn = get_conn()
    q = "SELECT * FROM feriados"
    if ano:
        q += f" WHERE data LIKE '{ano}-%'"
    q += " ORDER BY data"
    r = conn.execute(q).fetchall()
    conn.close()
    return [dict(x) for x in r]


def create_feriado(data: dict) -> int:
    conn = get_conn()
    c    = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO feriados(data,descricao,tipo,criado_em) VALUES(?,?,?,?)",
        (data["data"], data["descricao"], data.get("tipo","nacional"), _now())
    )
    conn.commit(); new_id = c.lastrowid; conn.close()
    return new_id


def delete_feriado(fid):
    conn = get_conn()
    conn.execute("DELETE FROM feriados WHERE id=?", (fid,))
    conn.commit(); conn.close()


# ── Banco de Horas ─────────────────────────────────────────────────────────────

def get_banco_horas(user_id: int) -> dict:
    _init_banco_horas(user_id)
    conn = get_conn()
    r    = conn.execute("SELECT * FROM banco_horas WHERE user_id=?",
                        (user_id,)).fetchone()
    conn.close()
    b = dict(r) if r else {"user_id": user_id, "saldo_minutos": 0}
    b["saldo_fmt"] = _min_to_hhmm(b["saldo_minutos"])
    return b


def list_lancamentos_banco(user_id: int, limit=30):
    conn = get_conn()
    r = conn.execute("""
        SELECT l.*, u.nome as aprovado_por_nome
        FROM banco_horas_lancamentos l
        LEFT JOIN users u ON l.aprovado_por=u.id
        WHERE l.user_id=?
        ORDER BY l.data DESC, l.criado_em DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    result = [dict(x) for x in r]
    for item in result:
        item["minutos_fmt"] = _min_to_hhmm(item["minutos"])
    return result


def lancar_banco_horas(user_id: int, minutos: int, tipo: str,
                       descricao: str, aprovado_por: int = None,
                       data_ref: str = None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO banco_horas_lancamentos(user_id,data,minutos,tipo,"
        "descricao,aprovado_por,criado_em) VALUES(?,?,?,?,?,?,?)",
        (user_id, data_ref or _today(), minutos, tipo,
         descricao, aprovado_por, _now())
    )
    conn.execute(
        "UPDATE banco_horas SET saldo_minutos=saldo_minutos+?,atualizado_em=?"
        " WHERE user_id=?",
        (minutos, _now(), user_id)
    )
    conn.commit(); conn.close()


def compensar_banco_horas(user_id: int, minutos: int,
                          descricao: str, aprovado_por: int, data_ref: str):
    """Debita horas do banco (compensação de folga)."""
    lancar_banco_horas(user_id, -abs(minutos), "compensacao",
                       descricao, aprovado_por, data_ref)


# ── Fechamentos ───────────────────────────────────────────────────────────────

def get_fechamento(user_id: int, mes: int, ano: int):
    conn = get_conn()
    r = conn.execute(
        "SELECT * FROM fechamentos WHERE user_id=? AND mes=? AND ano=?",
        (user_id, mes, ano)
    ).fetchone()
    conn.close()
    return dict(r) if r else None


def fechar_periodo(user_id: int, mes: int, ano: int,
                   fechado_por: int) -> dict:
    """Calcula o mês e persiste o fechamento. Credita extras no banco."""
    ex = get_fechamento(user_id, mes, ano)
    if ex and ex["status"] == "fechado":
        return {"erro": "Período já fechado."}

    resumo = resumo_mes(user_id, ano, mes)
    conn   = get_conn()

    if ex:
        conn.execute("""
            UPDATE fechamentos SET
              total_dias=?,total_min_trab=?,total_min_extra=?,
              total_min_falta=?,total_min_noturno=?,
              status='fechado',fechado_por=?,fechado_em=?
            WHERE user_id=? AND mes=? AND ano=?
        """, (resumo["total_dias"], resumo["total_min_trab"],
              resumo["total_min_extra"], resumo["total_min_falta"],
              resumo["total_min_noturno"],
              fechado_por, _now(), user_id, mes, ano))
    else:
        conn.execute("""
            INSERT INTO fechamentos(user_id,mes,ano,status,total_dias,
              total_min_trab,total_min_extra,total_min_falta,
              total_min_noturno,fechado_por,fechado_em,criado_em)
            VALUES(?,?,?,'fechado',?,?,?,?,?,?,?,?)
        """, (user_id, mes, ano,
              resumo["total_dias"], resumo["total_min_trab"],
              resumo["total_min_extra"], resumo["total_min_falta"],
              resumo["total_min_noturno"],
              fechado_por, _now(), _now()))
    conn.commit(); conn.close()

    # Credita horas extras no banco de horas
    if resumo["total_min_extra"] > 0:
        lancar_banco_horas(
            user_id, resumo["total_min_extra"], "credito",
            f"Horas extras — {mes:02d}/{ano}", fechado_por,
            f"{ano}-{mes:02d}-01"
        )

    return {**resumo, "status": "fechado", "mes": mes, "ano": ano}


def list_fechamentos(user_id=None, ano=None, user_ids=None):
    conn = get_conn()
    q = """
        SELECT f.*, u.nome as user_nome
        FROM fechamentos f JOIN users u ON f.user_id=u.id
    """
    w, v = [], []
    if user_id: w.append("f.user_id=?"); v.append(user_id)
    elif user_ids is not None:
        if not user_ids:
            conn.close(); return []
        w.append(f"f.user_id IN ({','.join(['?']*len(user_ids))})"); v.extend(user_ids)
    if ano: w.append("f.ano=?"); v.append(ano)
    if w: q += " WHERE " + " AND ".join(w)
    q += " ORDER BY f.ano DESC, f.mes DESC"
    r = conn.execute(q, v).fetchall()
    conn.close()
    result = [dict(x) for x in r]
    for item in result:
        item["total_trab_fmt"]   = _min_to_hhmm(item["total_min_trab"])
        item["total_extra_fmt"]  = _min_to_hhmm(item["total_min_extra"])
        item["total_falta_fmt"]  = _min_to_hhmm(item["total_min_falta"])
    return result


# ── Configurações ─────────────────────────────────────────────────────────────

def get_config():
    conn = get_conn()
    r    = conn.execute("SELECT * FROM configuracoes WHERE id=1").fetchone()
    conn.close()
    return dict(r) if r else {}


def update_config(data: dict):
    conn = get_conn()
    fields, vals = [], []
    for f in ["tolerancia_entrada","tolerancia_saida","inicio_noturno",
              "fim_noturno","percentual_noturno","percentual_extra_dia",
              "percentual_extra_fds","percentual_extra_fer","limite_extra_dia_min"]:
        if f in data:
            fields.append(f"{f}=?"); vals.append(data[f])
    if fields:
        vals.append(1)
        conn.execute(f"UPDATE configuracoes SET {','.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard_stats(user_id: int) -> dict:
    hoje    = _today()
    mes     = date.today().month
    ano     = date.today().year
    user    = get_user(user_id)

    reg_hoje = get_registros_dia(user_id, hoje)
    prox     = proximo_tipo(user_id, hoje)
    calc     = calcular_dia(user_id, hoje)
    banco    = get_banco_horas(user_id)

    conn = get_conn()
    ajustes_pend = conn.execute(
        "SELECT COUNT(*) FROM ajustes_ponto WHERE status='pendente'"
        + (" AND user_id=?" if user["role"] == "colaborador" else ""),
        (user_id,) if user["role"] == "colaborador" else ()
    ).fetchone()[0]
    conn.close()

    return {
        "hoje":           hoje,
        "user":           user,
        "registros_hoje": reg_hoje,
        "proximo_tipo":   prox,
        "calc_hoje":      calc,
        "banco_horas":    banco,
        "ajustes_pendentes": ajustes_pend,
    }
