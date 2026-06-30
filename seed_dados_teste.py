# -*- coding: utf-8 -*-
from __future__ import annotations
"""
seed_dados_teste.py — Limpa todos os bancos e cria dados de teste completos no Olimpus.

Estrutura criada:
  - 1 empresa: Empresa Teste Ltda
  - 3 departamentos: TI, Financeiro, RH
  - 6 usuários (2/depto) com roles diferentes em cada app
  - Senha padrão: teste123
"""
import hashlib
import os
import sqlite3
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
NOW = datetime.now().isoformat(timespec="seconds")

def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def _conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

SENHA = "teste123"

# ─────────────────────────────────────────────────────────────────────────────
# 1. LIMPAR TODOS OS BANCOS
# ─────────────────────────────────────────────────────────────────────────────

def limpar_atlas():
    path = os.path.join(BASE, "Atlas - Gestão de Acessos", "atlas.db")
    conn = _conn(path)
    print("  [Atlas] Limpando...")

    # Remove logs de auditoria
    conn.execute("DELETE FROM audit_logs")
    # Remove acessos
    conn.execute("DELETE FROM acessos")
    # Remove tipos de acesso atribuídos
    conn.execute("DELETE FROM pessoa_tipo_acesso")
    # Remove tipos de acesso
    conn.execute("DELETE FROM tipos_acesso")
    conn.execute("DELETE FROM tipo_acesso_permissao")
    # Remove vínculos pessoa↔função (exceto admin)
    admin_id = conn.execute("SELECT id FROM pessoas WHERE email='admin@olimpus.local'").fetchone()
    if admin_id:
        conn.execute("DELETE FROM pessoa_funcao WHERE pessoa_id != ?", (admin_id["id"],))
    else:
        conn.execute("DELETE FROM pessoa_funcao")
    # Remove pessoas (exceto admin@olimpus.local)
    conn.execute("DELETE FROM pessoas WHERE email != 'admin@olimpus.local'")
    # Remove departamentos
    conn.execute("DELETE FROM departamentos")
    # Remove empresas
    conn.execute("DELETE FROM empresas")

    conn.commit()
    conn.close()
    print("  [Atlas] Limpo.")


def limpar_app_local(nome_pasta: str, db_name: str, tabelas: list):
    path = os.path.join(BASE, nome_pasta, db_name)
    if not os.path.exists(path):
        print(f"  [{nome_pasta}] Banco não encontrado, pulando.")
        return
    conn = _conn(path)
    print(f"  [{nome_pasta}] Limpando...")
    for tabela in tabelas:
        try:
            conn.execute(f"DELETE FROM {tabela}")
        except Exception as e:
            print(f"    Aviso ao limpar {tabela}: {e}")
    conn.commit()
    conn.close()
    print(f"  [{nome_pasta}] Limpo.")


def limpar_todos():
    print("\n=== PASSO 1: Limpando bancos de dados ===")
    limpar_atlas()

    # Apps com tabela local users + departamentos
    apps_locais = [
        ("Hera - Gestão de Pessoas",          "hera.db",    [
            "treinamento_inscricoes","treinamentos","pdi_acoes","pdi",
            "kudos","feedbacks","avaliacoes","ciclos_avaliacao",
            "ferias","onboarding_progresso","users","departamentos"
        ]),
        ("Ploutos - Gestão Financeira",        "ploutos.db", [
            "lancamentos","orcamentos","categorias","centro_custos",
            "users","departamentos"
        ]),
        ("Cronos - Ponto Eletrônico",          "cronos.db",  ["users","departamentos"]),
        ("Hércules - Gestão de Tarefas",       "hercules.db",["users","departamentos"]),
        ("Hermes - Gestão de Ativos",          "hermes.db",  ["users","departamentos"]),
    ]
    for pasta, db, tabelas in apps_locais:
        limpar_app_local(pasta, db, tabelas)

    # Apps sem tabela local — limpar dados derivados
    apps_sem_local = [
        ("Argos - Monitoração",                "monitor.db",  ["monitor_logs"]),
        ("Héstia - Intranet Corporativa",      "hestia.db",   ["posts","comentarios"]),
        ("Iris - Gestão de Formulários e Workflow", "iris.db",["respostas","formularios"]),
        ("Têmis – Gestão de Contratos",        "temis.db",    ["contratos"]),
        ("Oráculo - Hub de Notícias",          "oraculo.db",  ["noticias","comentarios"]),
        ("Tiresias – OCR",                     "tiresias.db", ["documentos"]),
    ]
    for pasta, db, tabelas in apps_sem_local:
        limpar_app_local(pasta, db, tabelas)

    print("=== Limpeza concluída ===\n")


# ─────────────────────────────────────────────────────────────────────────────
# 2. SEED — ATLAS
# ─────────────────────────────────────────────────────────────────────────────

# Folders dos sistemas (nomes reais no banco Atlas)
SYS_HERA   = "Hera - Gestão de Pessoas"
SYS_PLOUTOS = "Ploutos - Gestão Financeira"
SYS_CRONOS  = "Cronos - Ponto Eletrônico"
SYS_HERCULES= "Hércules - Gestão de Tarefas"
SYS_HERMES  = "Hermes - Gestão de Ativos"
SYS_ARGOS   = "Argos - Monitoração"
SYS_HESTIA  = "Héstia - Intranet Corporativa"
SYS_IRIS    = "Iris - Gestão de Formulários e Workflow"
SYS_ORACULO = "Oráculo - Hub de Notícias"
SYS_TEMIS   = "Têmis – Gestão de Contratos"
SYS_TIRESIAS= "Tiresias – OCR"


def seed_atlas():
    path = os.path.join(BASE, "Atlas - Gestão de Acessos", "atlas.db")
    conn = _conn(path)
    print("=== PASSO 2: Criando dados no Atlas ===")

    # ── Empresa ──────────────────────────────────────────────────────────────
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO empresas(
            nome, razao_social, cnpj,
            endereco_logradouro, endereco_numero, endereco_complemento,
            endereco_bairro, endereco_cidade, endereco_estado, endereco_cep,
            telefone, email, responsavel,
            numero_contrato, inicio_contrato, vigencia_contrato,
            ativo, criado_em
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        "Empresa Teste", "Empresa Teste Ltda",  "12.345.678/0001-99",
        "Rua das Acácias", "100", "Sala 5",
        "Centro", "São Paulo", "SP", "01001-000",
        "(11) 3000-0000", "contato@empresa.com.br", "João da Silva",
        "CONT-2026-001", "2026-01-01", "2027-12-31",
        1, NOW
    ))
    conn.commit()
    empresa_id = cur.lastrowid
    print(f"  Empresa criada  → id={empresa_id}")

    # ── Departamentos ────────────────────────────────────────────────────────
    deptos = ["TI", "Financeiro", "RH"]
    depto_ids = {}
    for nome in deptos:
        cur.execute(
            "INSERT INTO departamentos(nome, empresa_id, criado_em) VALUES(?,?,?)",
            (nome, empresa_id, NOW)
        )
        conn.commit()
        depto_ids[nome] = cur.lastrowid
        print(f"  Departamento '{nome}'  → id={depto_ids[nome]}")

    # ── Roles funcionais de Atlas ─────────────────────────────────────────────
    funcao_operador = conn.execute(
        "SELECT id FROM funcoes WHERE nome='operador'"
    ).fetchone()
    funcao_op_id = funcao_operador["id"] if funcao_operador else None

    # ── Usuários ─────────────────────────────────────────────────────────────
    #
    # roles_hera   : admin > rh > colaborador
    # roles_ploutos: admin > financeiro > colaborador
    #
    # user         | depto      | hera       | ploutos
    # -------------|------------|------------|------------
    # carlos.silva | TI         | admin      | financeiro
    # ana.santos   | TI         | rh         | colaborador
    # maria.oliveira| Financeiro| colaborador| admin
    # joao.costa   | Financeiro | rh         | financeiro
    # patricia.lima| RH         | rh         | colaborador
    # roberto.ferreira| RH      | colaborador| colaborador

    usuarios = [
        # nome, email, cargo, depto, role_hera, role_ploutos
        ("Carlos Silva",     "carlos.silva@empresa.com",    "Analista de TI",      "TI",         "admin",       "financeiro"),
        ("Ana Santos",       "ana.santos@empresa.com",      "Desenvolvedora",      "TI",         "rh",          "colaborador"),
        ("Maria Oliveira",   "maria.oliveira@empresa.com",  "Gerente Financeiro",  "Financeiro", "colaborador", "admin"),
        ("Joao Costa",       "joao.costa@empresa.com",      "Analista Financeiro", "Financeiro", "rh",          "financeiro"),
        ("Patricia Lima",    "patricia.lima@empresa.com",   "Analista de RH",      "RH",         "rh",          "colaborador"),
        ("Roberto Ferreira", "roberto.ferreira@empresa.com","Assistente de RH",    "RH",         "colaborador", "colaborador"),
    ]

    pessoa_ids = {}
    for nome, email, cargo, depto, role_hera, role_ploutos in usuarios:
        depto_id = depto_ids[depto]
        cur.execute("""
            INSERT INTO pessoas(
                nome, email, senha_hash, cargo,
                empresa_id, departamento_id,
                ativo, trocar_senha, criado_em
            ) VALUES(?,?,?,?,?,?,1,0,?)
        """, (nome, email, _hash(SENHA), cargo, empresa_id, depto_id, NOW))
        conn.commit()
        pid = cur.lastrowid
        pessoa_ids[email] = pid

        # Função padrão: operador (no Atlas)
        if funcao_op_id:
            conn.execute(
                "INSERT OR IGNORE INTO pessoa_funcao VALUES(?,?)",
                (pid, funcao_op_id)
            )

        # Acesso a todos os sistemas (libera via empresa regra + individual com role)
        for folder, role in [
            (SYS_HERA,    role_hera),
            (SYS_PLOUTOS, role_ploutos),
            (SYS_CRONOS,  "colaborador"),
            (SYS_HERCULES,"colaborador"),
            (SYS_HERMES,  "colaborador"),
            (SYS_ARGOS,   "membro"),
            (SYS_HESTIA,  "membro"),
            (SYS_IRIS,    "membro"),
            (SYS_ORACULO, "membro"),
            (SYS_TEMIS,   "membro"),
            (SYS_TIRESIAS,"membro"),
        ]:
            # Verifica se o sistema existe no banco
            sys_exists = conn.execute(
                "SELECT 1 FROM sistemas WHERE folder=?", (folder,)
            ).fetchone()
            if not sys_exists:
                # Insere o sistema se ainda não existe
                conn.execute(
                    "INSERT OR IGNORE INTO sistemas(folder,nome,ativo,criado_em) VALUES(?,?,1,?)",
                    (folder, folder.split(" - ")[-1].split(" – ")[-1], NOW)
                )

            conn.execute("""
                INSERT INTO acessos
                    (sistema_folder, pessoa_id, empresa_id, permitido, role_sistema, criado_em)
                VALUES(?,?,?,1,?,?)
            """, (folder, pid, empresa_id, role, NOW))

        conn.commit()
        print(f"  Usuário: {nome} ({depto}) → Hera:{role_hera}, Ploutos:{role_ploutos}")

    conn.close()
    print("=== Atlas seed concluído ===\n")
    return empresa_id, depto_ids, pessoa_ids


# ─────────────────────────────────────────────────────────────────────────────
# 3. SEED — HERA
# ─────────────────────────────────────────────────────────────────────────────

def seed_hera(depto_ids: dict, usuarios_info: list):
    path = os.path.join(BASE, "Hera - Gestão de Pessoas", "hera.db")
    if not os.path.exists(path):
        print("  [Hera] Banco não encontrado, pulando seed local.")
        return
    conn = _conn(path)
    print("=== PASSO 3: Seed local — Hera ===")

    # Departamentos
    hera_depto_ids = {}
    for nome in ["TI", "Financeiro", "RH"]:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO departamentos(nome, atlas_empresa_id, criado_em) VALUES(?,?,?)",
            (nome, 1, NOW)
        )
        conn.commit()
        hera_depto_ids[nome] = cur.lastrowid

    # Usuários
    for nome, email, cargo, depto, role_hera, role_ploutos, atlas_id in usuarios_info:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO users(
                nome, email, senha_hash, role, departamento_id, cargo, ativo, atlas_id, criado_em
            ) VALUES(?,?,?,?,?,?,1,?,?)
        """, (
            nome, email, _hash(SENHA), role_hera,
            hera_depto_ids[depto], cargo, atlas_id, NOW
        ))
        conn.commit()
        print(f"  [Hera] {nome} → role={role_hera}")

    conn.close()
    print("=== Hera seed concluído ===\n")


# ─────────────────────────────────────────────────────────────────────────────
# 4. SEED — PLOUTOS
# ─────────────────────────────────────────────────────────────────────────────

def seed_ploutos(usuarios_info: list):
    path = os.path.join(BASE, "Ploutos - Gestão Financeira", "ploutos.db")
    if not os.path.exists(path):
        print("  [Ploutos] Banco não encontrado, pulando seed local.")
        return
    conn = _conn(path)
    print("=== PASSO 4: Seed local — Ploutos ===")

    # Departamentos
    ploutos_depto_ids = {}
    for nome in ["TI", "Financeiro", "RH"]:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO departamentos(nome, atlas_empresa_id, criado_em) VALUES(?,?,?)",
            (nome, 1, NOW)
        )
        conn.commit()
        ploutos_depto_ids[nome] = cur.lastrowid

    # Centro de custo padrão
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO centro_custos(nome, descricao, ativo, criado_em) VALUES(?,?,1,?)",
        ("Geral", "Centro de custo geral", NOW)
    )
    conn.commit()
    cc_id = cur.lastrowid

    # Categorias padrão
    for nome, tipo in [
        ("Salários",       "despesa"),
        ("Fornecedores",   "despesa"),
        ("Impostos",       "despesa"),
        ("Serviços",       "receita"),
        ("Vendas",         "receita"),
    ]:
        conn.execute(
            "INSERT INTO categorias(nome, tipo, centro_custo_id, ativo, criado_em) VALUES(?,?,?,1,?)",
            (nome, tipo, cc_id, NOW)
        )
    conn.commit()

    # Usuários
    for nome, email, cargo, depto, role_hera, role_ploutos, atlas_id in usuarios_info:
        cur = conn.cursor()
        cur.execute("""
            INSERT OR REPLACE INTO users(
                nome, email, senha_hash, role, departamento_id, cargo, ativo, atlas_id, criado_em
            ) VALUES(?,?,?,?,?,?,1,?,?)
        """, (
            nome, email, _hash(SENHA), role_ploutos,
            ploutos_depto_ids[depto], cargo, atlas_id, NOW
        ))
        conn.commit()
        print(f"  [Ploutos] {nome} → role={role_ploutos}")

    conn.close()
    print("=== Ploutos seed concluído ===\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 60)
    print("   OLIMPUS -- SEED DE DADOS DE TESTE")
    print("=" * 60)

    limpar_todos()
    empresa_id, depto_ids, pessoa_ids = seed_atlas()

    # Monta lista de usuarios com atlas_id para seed local
    usuarios_base = [
        ("Carlos Silva",     "carlos.silva@empresa.com",    "Analista de TI",      "TI",         "admin",       "financeiro"),
        ("Ana Santos",       "ana.santos@empresa.com",      "Desenvolvedora",      "TI",         "rh",          "colaborador"),
        ("Maria Oliveira",   "maria.oliveira@empresa.com",  "Gerente Financeiro",  "Financeiro", "colaborador", "admin"),
        ("Joao Costa",       "joao.costa@empresa.com",      "Analista Financeiro", "Financeiro", "rh",          "financeiro"),
        ("Patricia Lima",    "patricia.lima@empresa.com",   "Analista de RH",      "RH",         "rh",          "colaborador"),
        ("Roberto Ferreira", "roberto.ferreira@empresa.com","Assistente de RH",    "RH",         "colaborador", "colaborador"),
    ]
    usuarios_info = [
        (nome, email, cargo, depto, role_h, role_p, pessoa_ids[email])
        for nome, email, cargo, depto, role_h, role_p in usuarios_base
    ]

    seed_hera(depto_ids, usuarios_info)
    seed_ploutos(usuarios_info)

    print("=" * 60)
    print("SEED CONCLUIDO!")
    print("=" * 60)
    print("  Empresa : Empresa Teste Ltda (CNPJ 12.345.678/0001-99)")
    print("  Departamentos: TI | Financeiro | RH")
    print("-" * 60)
    print(f"  {'Usuario':<36} {'Hera':<12} {'Ploutos'}")
    print("-" * 60)
    print(f"  {'carlos.silva@empresa.com':<36} {'admin':<12} financeiro")
    print(f"  {'ana.santos@empresa.com':<36} {'rh':<12} colaborador")
    print(f"  {'maria.oliveira@empresa.com':<36} {'colaborador':<12} admin")
    print(f"  {'joao.costa@empresa.com':<36} {'rh':<12} financeiro")
    print(f"  {'patricia.lima@empresa.com':<36} {'rh':<12} colaborador")
    print(f"  {'roberto.ferreira@empresa.com':<36} {'colaborador':<12} colaborador")
    print("-" * 60)
    print("  Senha padrao: teste123")
    print("  Admin Atlas : admin@olimpus.local / Atlas@2024")
    print("=" * 60)
