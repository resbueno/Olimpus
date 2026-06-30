from __future__ import annotations
"""
database.py — Iris · Persistência SQLite
"""
import json
import os
import sqlite3
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "iris.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS formularios (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            descricao     TEXT DEFAULT '',
            categoria     TEXT DEFAULT 'generico',
            campos        TEXT DEFAULT '[]',
            etapas        TEXT DEFAULT '[]',
            grupos_acesso TEXT DEFAULT '[]',
            ativo         INTEGER DEFAULT 1,
            criado_em     TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS ordens (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            numero          TEXT NOT NULL,
            formulario_id   INTEGER,
            titulo          TEXT NOT NULL,
            status          TEXT DEFAULT 'aberta',
            etapa_atual     INTEGER DEFAULT 0,
            dados           TEXT DEFAULT '{}',
            criado_por_nome TEXT DEFAULT '',
            atribuido_a     TEXT DEFAULT '',
            prioridade      TEXT DEFAULT 'normal',
            observacao      TEXT DEFAULT '',
            criado_em       TEXT DEFAULT (datetime('now','localtime')),
            atualizado_em   TEXT DEFAULT (datetime('now','localtime')),
            concluida_em    TEXT
        );

        CREATE TABLE IF NOT EXISTS historico (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ordem_id     INTEGER NOT NULL,
            acao         TEXT NOT NULL,
            etapa_de     TEXT DEFAULT '',
            etapa_para   TEXT DEFAULT '',
            comentario   TEXT DEFAULT '',
            usuario_nome TEXT DEFAULT '',
            criado_em    TEXT DEFAULT (datetime('now','localtime'))
        );
        """)
        # Migração — colunas adicionadas em versões posteriores
        existing = {r[1] for r in c.execute("PRAGMA table_info(formularios)").fetchall()}
        if "grupos_acesso" not in existing:
            c.execute("ALTER TABLE formularios ADD COLUMN grupos_acesso TEXT DEFAULT '[]'")

        existing_o = {r[1] for r in c.execute("PRAGMA table_info(ordens)").fetchall()}
        if "nome_contato" not in existing_o:
            c.execute("ALTER TABLE ordens ADD COLUMN nome_contato TEXT DEFAULT ''")
        if "email_contato" not in existing_o:
            c.execute("ALTER TABLE ordens ADD COLUMN email_contato TEXT DEFAULT ''")

        if c.execute("SELECT COUNT(*) FROM formularios").fetchone()[0] == 0:
            _seed_templates(c)


def _seed_templates(c):
    # grupos_acesso: quem pode ver/criar OS deste tipo (vazio = todos)
    # etapas.responsavel: qual função do Atlas pode agir nesta etapa (vazio = qualquer um)
    templates = [
        {
            "nome": "Manutenção Corretiva",
            "descricao": "Solicitação de manutenção de equipamentos ou instalações",
            "categoria": "manutencao",
            "grupos_acesso": [],   # qualquer usuário pode abrir
            "campos": [
                {"id": "local",       "label": "Local / Área",                "tipo": "text",     "obrigatorio": True},
                {"id": "equipamento", "label": "Equipamento / item afetado",  "tipo": "text",     "obrigatorio": True},
                {"id": "problema",    "label": "Descrição do problema",        "tipo": "textarea", "obrigatorio": True},
                {"id": "risco",       "label": "Risco imediato à segurança?", "tipo": "checkbox", "obrigatorio": False},
            ],
            "etapas": [
                {"nome": "Solicitação", "responsavel": ""},
                {"nome": "Aprovação",   "responsavel": "Gerência"},
                {"nome": "Execução",    "responsavel": "Manutenção"},
                {"nome": "Validação",   "responsavel": ""},
                {"nome": "Concluída",   "responsavel": ""},
            ],
        },
        {
            "nome": "Suporte de TI",
            "descricao": "Solicitação de suporte técnico ou acesso a sistemas",
            "categoria": "ti",
            "grupos_acesso": [],
            "campos": [
                {"id": "tipo",      "label": "Tipo de solicitação", "tipo": "select",   "obrigatorio": True,
                 "opcoes": ["Acesso a sistema", "Hardware", "Software", "Rede", "Outro"]},
                {"id": "descricao", "label": "Descrição detalhada", "tipo": "textarea", "obrigatorio": True},
                {"id": "sistema",   "label": "Sistema / equipamento afetado", "tipo": "text", "obrigatorio": False},
            ],
            "etapas": [
                {"nome": "Solicitação", "responsavel": ""},
                {"nome": "Triagem",     "responsavel": "TI"},
                {"nome": "Atendimento", "responsavel": "TI"},
                {"nome": "Concluída",   "responsavel": "TI"},
            ],
        },
        {
            "nome": "Requisição de Compras",
            "descricao": "Solicitação de compra de materiais ou serviços",
            "categoria": "compras",
            "grupos_acesso": ["Compras", "Financeiro", "Gerência", "admin"],
            "campos": [
                {"id": "item",          "label": "Item / Serviço",       "tipo": "text",     "obrigatorio": True},
                {"id": "quantidade",    "label": "Quantidade",           "tipo": "number",   "obrigatorio": True},
                {"id": "valor",         "label": "Valor estimado (R$)",  "tipo": "number",   "obrigatorio": False},
                {"id": "justificativa", "label": "Justificativa",        "tipo": "textarea", "obrigatorio": True},
                {"id": "fornecedor",    "label": "Fornecedor sugerido",  "tipo": "text",     "obrigatorio": False},
                {"id": "necessidade",   "label": "Data necessária",      "tipo": "date",     "obrigatorio": False},
            ],
            "etapas": [
                {"nome": "Solicitação",          "responsavel": ""},
                {"nome": "Aprovação Gerência",   "responsavel": "Gerência"},
                {"nome": "Aprovação Financeiro", "responsavel": "Financeiro"},
                {"nome": "Compra",               "responsavel": "Compras"},
                {"nome": "Recebimento",          "responsavel": ""},
                {"nome": "Concluída",            "responsavel": ""},
            ],
        },
    ]
    for t in templates:
        c.execute(
            "INSERT INTO formularios (nome, descricao, categoria, campos, etapas, grupos_acesso)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (t["nome"], t["descricao"], t["categoria"],
             json.dumps(t["campos"], ensure_ascii=False),
             json.dumps(t["etapas"], ensure_ascii=False),
             json.dumps(t["grupos_acesso"], ensure_ascii=False)),
        )


# ── Formulários ───────────────────────────────────────────────────────────────

def list_formularios(ativo=None):
    sql, p = "SELECT * FROM formularios", []
    if ativo is not None:
        sql += " WHERE ativo=?"; p.append(1 if ativo else 0)
    sql += " ORDER BY nome"
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, p).fetchall()]


def get_formulario(fid: int):
    with _conn() as c:
        r = c.execute("SELECT * FROM formularios WHERE id=?", (fid,)).fetchone()
        return dict(r) if r else None


def add_formulario(nome, descricao, categoria, campos, etapas,
                   grupos_acesso=None) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO formularios"
            " (nome,descricao,categoria,campos,etapas,grupos_acesso) VALUES (?,?,?,?,?,?)",
            (nome, descricao, categoria,
             json.dumps(campos, ensure_ascii=False),
             json.dumps(etapas, ensure_ascii=False),
             json.dumps(grupos_acesso or [], ensure_ascii=False)),
        )
        return cur.lastrowid


def update_formulario(fid: int, **kw):
    if not kw: return
    cols = ", ".join(f"{k}=?" for k in kw)
    with _conn() as c:
        c.execute(f"UPDATE formularios SET {cols} WHERE id=?", list(kw.values()) + [fid])


def delete_formulario(fid: int):
    with _conn() as c:
        c.execute("DELETE FROM formularios WHERE id=?", (fid,))


# ── Ordens ────────────────────────────────────────────────────────────────────

def _next_numero() -> str:
    with _conn() as c:
        n = c.execute("SELECT COUNT(*) FROM ordens").fetchone()[0]
        return f"OS-{n + 1:04d}"


def add_ordem(formulario_id, titulo, dados, criado_por_nome,
              atribuido_a, prioridade, observacao,
              nome_contato="", email_contato="") -> tuple[int, str]:
    numero = _next_numero()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO ordens"
            " (numero,formulario_id,titulo,dados,criado_por_nome,atribuido_a,prioridade,observacao,nome_contato,email_contato)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (numero, formulario_id, titulo,
             json.dumps(dados, ensure_ascii=False),
             criado_por_nome, atribuido_a, prioridade, observacao,
             nome_contato, email_contato),
        )
        return cur.lastrowid, numero


def get_ordem(oid: int):
    with _conn() as c:
        r = c.execute("SELECT * FROM ordens WHERE id=?", (oid,)).fetchone()
        return dict(r) if r else None


def list_ordens(status="", prioridade="", q="", limit=100, offset=0):
    sql, p = "SELECT * FROM ordens WHERE 1=1", []
    if status:     sql += " AND status=?";                         p.append(status)
    if prioridade: sql += " AND prioridade=?";                     p.append(prioridade)
    if q:          sql += " AND (titulo LIKE ? OR numero LIKE ?)"; p += [f"%{q}%", f"%{q}%"]
    sql += " ORDER BY criado_em DESC LIMIT ? OFFSET ?"
    p += [limit, offset]
    with _conn() as c:
        return [dict(r) for r in c.execute(sql, p).fetchall()]


def update_ordem(oid: int, **kw):
    if not kw: return
    cols = ", ".join(f"{k}=?" for k in kw)
    with _conn() as c:
        c.execute(
            f"UPDATE ordens SET {cols}, atualizado_em=datetime('now','localtime') WHERE id=?",
            list(kw.values()) + [oid],
        )


def delete_ordem(oid: int):
    with _conn() as c:
        c.execute("DELETE FROM ordens WHERE id=?", (oid,))
        c.execute("DELETE FROM historico WHERE ordem_id=?", (oid,))


def get_stats() -> dict:
    today = date.today().isoformat()
    with _conn() as c:
        abertas    = c.execute("SELECT COUNT(*) FROM ordens WHERE status='aberta'").fetchone()[0]
        andamento  = c.execute("SELECT COUNT(*) FROM ordens WHERE status='em_andamento'").fetchone()[0]
        aguardando = c.execute("SELECT COUNT(*) FROM ordens WHERE status='aguardando'").fetchone()[0]
        conc_hoje  = c.execute(
            "SELECT COUNT(*) FROM ordens WHERE status='concluida' AND concluida_em >= ?",
            (today,),
        ).fetchone()[0]
        total      = c.execute("SELECT COUNT(*) FROM ordens").fetchone()[0]
        concluidas = c.execute("SELECT COUNT(*) FROM ordens WHERE status='concluida'").fetchone()[0]
    taxa = round(concluidas / total * 100, 1) if total else 0
    return {
        "abertas": abertas, "em_andamento": andamento, "aguardando": aguardando,
        "concluidas_hoje": conc_hoje, "total": total, "taxa": taxa,
    }


# ── Histórico ─────────────────────────────────────────────────────────────────

def add_historico(ordem_id, acao, etapa_de="", etapa_para="",
                  comentario="", usuario_nome=""):
    with _conn() as c:
        c.execute(
            "INSERT INTO historico"
            " (ordem_id,acao,etapa_de,etapa_para,comentario,usuario_nome)"
            " VALUES (?,?,?,?,?,?)",
            (ordem_id, acao, etapa_de, etapa_para, comentario, usuario_nome),
        )


def list_historico(ordem_id: int):
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM historico WHERE ordem_id=? ORDER BY criado_em ASC",
            (ordem_id,),
        ).fetchall()]


init_db()
