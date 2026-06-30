# -*- coding: utf-8 -*-
from __future__ import annotations
"""
seed_tipos_acesso.py — Cria tipos de acesso e distribui entre os 6 usuários de teste.

Tipos criados:
  1. Administrador do Sistema  — permissão total em todos os apps
  2. Gestor de RH              — gestão completa no Hera, aprovação no Cronos
  3. Analista Financeiro       — gestão completa no Ploutos
  4. Supervisor Operacional    — aprovação e gestão em Hércules, Iris e Cronos
  5. Operador de TI            — configuração em Atlas, Argos, Tiresias e Hermes
  6. Colaborador Padrão        — acesso básico de leitura/registro em todos

Distribuição:
  carlos.silva       → Administrador do Sistema + Operador de TI
  ana.santos         → Gestor de RH + Operador de TI
  maria.oliveira     → Administrador do Sistema + Analista Financeiro
  joao.costa         → Analista Financeiro + Gestor de RH
  patricia.lima      → Gestor de RH + Supervisor Operacional
  roberto.ferreira   → Colaborador Padrão + Supervisor Operacional
"""
import sqlite3
import os
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
NOW  = datetime.now().isoformat(timespec="seconds")

DB   = os.path.join(BASE, "Atlas - Gestão de Acessos", "atlas.db")

# Folders dos sistemas
SYS = {
    "atlas":    "Atlas - Gestão de Acessos",
    "hera":     "Hera - Gestão de Pessoas",
    "ploutos":  "Ploutos - Gestão Financeira",
    "cronos":   "Cronos - Ponto Eletrônico",
    "hercules": "Hércules - Gestão de Tarefas",
    "hermes":   "Hermes - Gestão de Ativos",
    "hestia":   "Héstia - Intranet Corporativa",
    "iris":     "Iris - Gestão de Formulários e Workflow",
    "oraculo":  "Oráculo - Hub de Notícias",
    "temis":    "Têmis – Gestão de Contratos",
    "tiresias": "Tiresias – OCR",
    "argos":    "Argos - Monitoração",
}

ALL_PERMS    = ["visualizar","criar","editar","excluir","aprovar","exportar","importar","configurar","admin"]
LEITURA      = ["visualizar"]
BASICO       = ["visualizar","criar"]
OPERACAO     = ["visualizar","criar","editar"]
GESTAO       = ["visualizar","criar","editar","excluir","aprovar","exportar","importar"]
CONFIGURACAO = ["visualizar","configurar"]
TOTAL        = ["visualizar","criar","editar","excluir","aprovar","exportar","importar","configurar","admin"]

# ─────────────────────────────────────────────────────────────────────────────
# Definição dos tipos de acesso
# formato: { sistema_folder: [permissoes] }
# ─────────────────────────────────────────────────────────────────────────────

TIPOS = [
    {
        "nome":     "Administrador do Sistema",
        "descricao":"Acesso total a todos os apps — criação, edição, exclusão, aprovação e configuração",
        "permissoes": {
            SYS["atlas"]:    TOTAL,
            SYS["hera"]:     TOTAL,
            SYS["ploutos"]:  TOTAL,
            SYS["cronos"]:   TOTAL,
            SYS["hercules"]: TOTAL,
            SYS["hermes"]:   TOTAL,
            SYS["hestia"]:   TOTAL,
            SYS["iris"]:     TOTAL,
            SYS["oraculo"]:  TOTAL,
            SYS["temis"]:    TOTAL,
            SYS["tiresias"]: TOTAL,
            SYS["argos"]:    TOTAL,
        },
    },
    {
        "nome":     "Gestor de RH",
        "descricao":"Gestão completa no Hera (pessoas, férias, avaliações); aprovação no Cronos; leitura nos demais",
        "permissoes": {
            SYS["hera"]:     GESTAO,
            SYS["cronos"]:   ["visualizar","aprovar","exportar"],
            SYS["oraculo"]:  ["visualizar","criar"],
            SYS["ploutos"]:  LEITURA,
            SYS["hercules"]: LEITURA,
            SYS["hestia"]:   LEITURA,
            SYS["iris"]:     ["visualizar","aprovar"],
            SYS["hermes"]:   LEITURA,
            SYS["temis"]:    LEITURA,
            SYS["tiresias"]: LEITURA,
            SYS["argos"]:    LEITURA,
        },
    },
    {
        "nome":     "Analista Financeiro",
        "descricao":"Gestão completa no Ploutos (lançamentos, orçamentos, relatórios); leitura nos demais",
        "permissoes": {
            SYS["ploutos"]:  GESTAO + ["configurar"],
            SYS["cronos"]:   LEITURA,
            SYS["hera"]:     LEITURA,
            SYS["hercules"]: LEITURA,
            SYS["hestia"]:   LEITURA,
            SYS["iris"]:     LEITURA,
            SYS["oraculo"]:  LEITURA,
            SYS["temis"]:    ["visualizar","criar","editar"],
            SYS["hermes"]:   LEITURA,
            SYS["tiresias"]: LEITURA,
            SYS["argos"]:    LEITURA,
        },
    },
    {
        "nome":     "Supervisor Operacional",
        "descricao":"Aprovação e gestão em Hércules, Iris e Cronos; criação de conteúdo no Oráculo e Héstia",
        "permissoes": {
            SYS["hercules"]: ["visualizar","criar","editar","aprovar","exportar"],
            SYS["iris"]:     ["visualizar","criar","editar","aprovar","exportar"],
            SYS["cronos"]:   ["visualizar","criar","editar","aprovar"],
            SYS["oraculo"]:  ["visualizar","criar","editar","exportar"],
            SYS["hestia"]:   ["visualizar","criar","editar"],
            SYS["temis"]:    ["visualizar","aprovar"],
            SYS["hera"]:     LEITURA,
            SYS["ploutos"]:  LEITURA,
            SYS["hermes"]:   LEITURA,
            SYS["tiresias"]: LEITURA,
            SYS["argos"]:    LEITURA,
        },
    },
    {
        "nome":     "Operador de TI",
        "descricao":"Configuração de infraestrutura: Atlas, Argos e Tiresias; gestão de ativos no Hermes",
        "permissoes": {
            SYS["atlas"]:    ["visualizar","configurar","exportar","importar"],
            SYS["argos"]:    ["visualizar","configurar","criar","editar","excluir"],
            SYS["tiresias"]: ["visualizar","criar","editar","configurar","importar"],
            SYS["hermes"]:   ["visualizar","criar","editar","excluir","exportar","importar"],
            SYS["hera"]:     LEITURA,
            SYS["ploutos"]:  LEITURA,
            SYS["cronos"]:   LEITURA,
            SYS["hercules"]: LEITURA,
            SYS["hestia"]:   LEITURA,
            SYS["iris"]:     LEITURA,
            SYS["oraculo"]:  LEITURA,
            SYS["temis"]:    LEITURA,
        },
    },
    {
        "nome":     "Colaborador Padrão",
        "descricao":"Acesso básico: leitura geral, registro de ponto no Cronos e criação de tarefas no Hércules",
        "permissoes": {
            SYS["hera"]:     LEITURA,
            SYS["ploutos"]:  LEITURA,
            SYS["cronos"]:   ["visualizar","criar"],          # registrar ponto
            SYS["hercules"]: ["visualizar","criar","editar"], # criar e mover tarefas
            SYS["hestia"]:   ["visualizar","criar"],          # publicar no mural
            SYS["iris"]:     ["visualizar","criar"],          # preencher formulários
            SYS["oraculo"]:  LEITURA,
            SYS["hermes"]:   LEITURA,
            SYS["temis"]:    LEITURA,
            SYS["tiresias"]: LEITURA,
            SYS["argos"]:    LEITURA,
        },
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Distribuição: email → [nomes dos tipos]
# Cada usuário recebe 2 tipos distintos
# ─────────────────────────────────────────────────────────────────────────────

DISTRIBUICAO = {
    "carlos.silva@empresa.com":    ["Administrador do Sistema", "Operador de TI"],
    "ana.santos@empresa.com":      ["Gestor de RH",             "Operador de TI"],
    "maria.oliveira@empresa.com":  ["Administrador do Sistema", "Analista Financeiro"],
    "joao.costa@empresa.com":      ["Analista Financeiro",      "Gestor de RH"],
    "patricia.lima@empresa.com":   ["Gestor de RH",             "Supervisor Operacional"],
    "roberto.ferreira@empresa.com":["Colaborador Padrão",       "Supervisor Operacional"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    return conn


def limpar_tipos_existentes(conn):
    conn.execute("DELETE FROM pessoa_tipo_acesso")
    conn.execute("DELETE FROM tipo_acesso_permissao")
    conn.execute("DELETE FROM tipos_acesso")
    conn.commit()
    print("  Tipos de acesso anteriores removidos.")


def criar_tipos(conn) -> dict:
    """Cria todos os tipos e retorna {nome: id}."""
    nome_id = {}
    for t in TIPOS:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tipos_acesso(nome, descricao, criado_em) VALUES(?,?,?)",
            (t["nome"], t["descricao"], NOW)
        )
        conn.commit()
        tid = cur.lastrowid
        nome_id[t["nome"]] = tid

        # Permissões por sistema
        perms_validas = {"visualizar","criar","editar","excluir","aprovar",
                         "exportar","importar","configurar","admin"}
        for folder, perms in t["permissoes"].items():
            for p in perms:
                if p in perms_validas:
                    conn.execute(
                        "INSERT INTO tipo_acesso_permissao"
                        "(tipo_acesso_id, sistema_folder, permissao) VALUES(?,?,?)",
                        (tid, folder, p)
                    )
        conn.commit()

        total_perms = sum(len(v) for v in t["permissoes"].values())
        print(f"  Tipo criado: '{t['nome']}' (id={tid}, {total_perms} permissões)")

    return nome_id


def distribuir(conn, nome_id: dict):
    """Atribui tipos de acesso às pessoas."""
    admin = conn.execute(
        "SELECT id FROM pessoas WHERE email='admin@olimpus.local'"
    ).fetchone()
    criado_por = admin["id"] if admin else None

    print()
    for email, tipos_nomes in DISTRIBUICAO.items():
        pessoa = conn.execute(
            "SELECT id, nome FROM pessoas WHERE email=?", (email,)
        ).fetchone()
        if not pessoa:
            print(f"  AVISO: pessoa '{email}' não encontrada, pulando.")
            continue

        pid = pessoa["id"]
        atribuidos = []

        for nome_tipo in tipos_nomes:
            tid = nome_id.get(nome_tipo)
            if not tid:
                print(f"  AVISO: tipo '{nome_tipo}' não encontrado, pulando.")
                continue

            # Busca os sistemas que este tipo cobre
            folders = conn.execute(
                "SELECT DISTINCT sistema_folder FROM tipo_acesso_permissao WHERE tipo_acesso_id=?",
                (tid,)
            ).fetchall()

            # Atribui para cada sistema
            for row in folders:
                conn.execute(
                    "INSERT OR IGNORE INTO pessoa_tipo_acesso"
                    "(pessoa_id, sistema_folder, tipo_acesso_id, criado_em, criado_por)"
                    " VALUES(?,?,?,?,?)",
                    (pid, row["sistema_folder"], tid, NOW, criado_por)
                )

            atribuidos.append(nome_tipo)

        conn.commit()
        print(f"  {pessoa['nome']:<22} → {' + '.join(atribuidos)}")


def resumo(conn, nome_id: dict):
    print()
    print("=" * 62)
    print("RESUMO — TIPOS DE ACESSO POR USUARIO")
    print("=" * 62)
    for email in DISTRIBUICAO:
        pessoa = conn.execute(
            "SELECT id, nome FROM pessoas WHERE email=?", (email,)
        ).fetchone()
        if not pessoa:
            continue
        tipos = conn.execute("""
            SELECT DISTINCT ta.nome
            FROM pessoa_tipo_acesso pta
            JOIN tipos_acesso ta ON pta.tipo_acesso_id = ta.id
            WHERE pta.pessoa_id = ?
            ORDER BY ta.nome
        """, (pessoa["id"],)).fetchall()
        nomes = [t["nome"] for t in tipos]
        print(f"  {pessoa['nome']:<22} {email:<34}")
        for n in nomes:
            print(f"    - {n}")

    print()
    print("PERMISSOES POR TIPO (resumo):")
    print("-" * 62)
    for tipo in TIPOS:
        tid = nome_id[tipo["nome"]]
        total = conn.execute(
            "SELECT COUNT(*) FROM tipo_acesso_permissao WHERE tipo_acesso_id=?", (tid,)
        ).fetchone()[0]
        sistemas = conn.execute(
            "SELECT COUNT(DISTINCT sistema_folder) FROM tipo_acesso_permissao WHERE tipo_acesso_id=?", (tid,)
        ).fetchone()[0]
        print(f"  {tipo['nome']:<30} {sistemas} sistemas  {total} permissoes")
    print("=" * 62)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 62)
    print("OLIMPUS -- SEED DE TIPOS DE ACESSO")
    print("=" * 62)

    conn = get_conn()

    print("\n[1] Limpando tipos anteriores...")
    limpar_tipos_existentes(conn)

    print("\n[2] Criando tipos de acesso...")
    nome_id = criar_tipos(conn)

    print("\n[3] Distribuindo entre os usuarios...")
    distribuir(conn, nome_id)

    resumo(conn, nome_id)
    conn.close()
    print("\nConcluido!")
