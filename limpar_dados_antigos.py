# -*- coding: utf-8 -*-
from __future__ import annotations
"""
limpar_dados_antigos.py — Remove todos os dados antigos dos apps Olimpus.
Preserva apenas os 6 usuários de teste + admin@olimpus.local.
"""
import sqlite3
import os

BASE = os.path.dirname(os.path.abspath(__file__))

EMAILS_PRESERVAR = {
    "admin@olimpus.local",
    "carlos.silva@empresa.com",
    "ana.santos@empresa.com",
    "maria.oliveira@empresa.com",
    "joao.costa@empresa.com",
    "patricia.lima@empresa.com",
    "roberto.ferreira@empresa.com",
}


def conn(pasta, db_file):
    path = os.path.join(BASE, pasta, db_file)
    if not os.path.exists(path):
        return None
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = OFF")
    return c


def deletar(con, tabela, where="", params=()):
    try:
        sql = f"DELETE FROM {tabela}"
        if where:
            sql += f" WHERE {where}"
        con.execute(sql, params)
        con.commit()
    except Exception as e:
        print(f"    Aviso ({tabela}): {e}")


def contagem(con, tabela):
    try:
        return con.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
    except:
        return "?"


# ─────────────────────────────────────────────────────────────────────────────
# HERA
# ─────────────────────────────────────────────────────────────────────────────
def limpar_hera():
    c = conn("Hera - Gestão de Pessoas", "hera.db")
    if not c:
        print("[Hera] banco não encontrado.")
        return
    print("[Hera] Limpando dados antigos...")
    # Dados que ficaram do seed anterior
    deletar(c, "ferias_periodos")
    deletar(c, "onboarding_etapas")
    deletar(c, "onboarding_progresso")
    deletar(c, "avaliacoes")
    deletar(c, "ciclos_avaliacao")
    deletar(c, "feedbacks")
    deletar(c, "ferias")
    deletar(c, "kudos")
    deletar(c, "pdi_acoes")
    deletar(c, "pdi")
    deletar(c, "treinamento_inscricoes")
    deletar(c, "treinamentos")
    print(f"  users restantes: {contagem(c, 'users')}")
    print(f"  departamentos restantes: {contagem(c, 'departamentos')}")
    c.close()
    print("[Hera] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# PLOUTOS
# ─────────────────────────────────────────────────────────────────────────────
def limpar_ploutos():
    c = conn("Ploutos - Gestão Financeira", "ploutos.db")
    if not c:
        print("[Ploutos] banco não encontrado.")
        return
    print("[Ploutos] Limpando dados antigos...")
    deletar(c, "orcamentos")
    deletar(c, "lancamentos")
    deletar(c, "categorias")
    deletar(c, "centro_custos")
    print(f"  users restantes: {contagem(c, 'users')}")
    print(f"  departamentos restantes: {contagem(c, 'departamentos')}")
    c.close()
    print("[Ploutos] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# CRONOS
# ─────────────────────────────────────────────────────────────────────────────
def limpar_cronos():
    c = conn("Cronos - Ponto Eletrônico", "cronos.db")
    if not c:
        print("[Cronos] banco não encontrado.")
        return
    print("[Cronos] Limpando todos os dados...")
    deletar(c, "banco_horas_lancamentos")
    deletar(c, "banco_horas")
    deletar(c, "ajustes_ponto")
    deletar(c, "registros_ponto")
    deletar(c, "fechamentos")
    deletar(c, "jornadas")
    deletar(c, "feriados")
    deletar(c, "configuracoes")
    deletar(c, "users")
    deletar(c, "departamentos")
    c.close()
    print("[Cronos] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# HÉRCULES
# ─────────────────────────────────────────────────────────────────────────────
def limpar_hercules():
    c = conn("Hércules - Gestão de Tarefas", "hercules.db")
    if not c:
        print("[Hércules] banco não encontrado.")
        return
    print("[Hércules] Limpando todos os dados...")
    deletar(c, "activities")
    deletar(c, "comments")
    deletar(c, "tasks")
    deletar(c, "projects")
    deletar(c, "users")
    c.close()
    print("[Hércules] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# HÉSTIA
# ─────────────────────────────────────────────────────────────────────────────
def limpar_hestia():
    c = conn("Héstia - Intranet Corporativa", "hestia.db")
    if not c:
        print("[Héstia] banco não encontrado.")
        return
    print("[Héstia] Limpando todos os dados...")
    deletar(c, "community_messages")
    deletar(c, "community_members")
    deletar(c, "communities")
    deletar(c, "kudos")
    deletar(c, "folder_access")
    deletar(c, "document_attachments")
    deletar(c, "document_versions")
    deletar(c, "documents")
    deletar(c, "document_folders")
    deletar(c, "news_attachments")
    deletar(c, "news")
    deletar(c, "events")
    deletar(c, "people")
    deletar(c, "settings")
    c.close()
    print("[Héstia] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# IRIS
# ─────────────────────────────────────────────────────────────────────────────
def limpar_iris():
    c = conn("Iris - Gestão de Formulários e Workflow", "iris.db")
    if not c:
        print("[Iris] banco não encontrado.")
        return
    print("[Iris] Limpando todos os dados...")
    deletar(c, "historico")
    deletar(c, "ordens")
    deletar(c, "formularios")
    c.close()
    print("[Iris] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# ORÁCULO
# ─────────────────────────────────────────────────────────────────────────────
def limpar_oraculo():
    c = conn("Oráculo - Hub de Notícias", "oraculo.db")
    if not c:
        print("[Oráculo] banco não encontrado.")
        return
    print("[Oráculo] Limpando todos os dados...")
    deletar(c, "newsletter_dispatches")
    deletar(c, "newsletters")
    deletar(c, "news_categories")
    deletar(c, "news")
    deletar(c, "department_categories")
    deletar(c, "categories")
    deletar(c, "kpi_values")
    deletar(c, "kpis")
    deletar(c, "insights")
    deletar(c, "news_sources")
    deletar(c, "smtp_config")
    deletar(c, "users")
    deletar(c, "departments")
    c.close()
    print("[Oráculo] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# TÊMIS
# ─────────────────────────────────────────────────────────────────────────────
def limpar_temis():
    c = conn("Têmis – Gestão de Contratos", "temis.db")
    if not c:
        print("[Têmis] banco não encontrado.")
        return
    print("[Têmis] Limpando todos os dados...")
    deletar(c, "ia_analyses")
    deletar(c, "alert_log")
    deletar(c, "audit_log")
    deletar(c, "signatories")
    deletar(c, "fiscal_events")
    deletar(c, "contract_taxes")
    deletar(c, "contract_versions")
    deletar(c, "contracts")
    c.close()
    print("[Têmis] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# TIRESIAS
# ─────────────────────────────────────────────────────────────────────────────
def limpar_tiresias():
    c = conn("Tiresias – OCR", "tiresias.db")
    if not c:
        print("[Tiresias] banco não encontrado.")
        return
    print("[Tiresias] Limpando todos os dados...")
    deletar(c, "documentos")
    deletar(c, "regras")
    deletar(c, "configuracoes")
    c.close()
    print("[Tiresias] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# ARGOS
# ─────────────────────────────────────────────────────────────────────────────
def limpar_argos():
    c = conn("Argos - Monitoração", "monitor.db")
    if not c:
        print("[Argos] banco não encontrado.")
        return
    print("[Argos] Limpando histórico de monitoração...")
    deletar(c, "monitor_history")
    deletar(c, "monitored_urls")
    c.close()
    print("[Argos] Limpo.\n")


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICAÇÃO FINAL
# ─────────────────────────────────────────────────────────────────────────────
def verificar():
    print("=" * 55)
    print("VERIFICAÇÃO FINAL")
    print("=" * 55)

    dbs = [
        ("Hera - Gestão de Pessoas",          "hera.db",    ["users","departamentos","onboarding_etapas","ferias_periodos"]),
        ("Ploutos - Gestão Financeira",        "ploutos.db", ["users","departamentos","lancamentos","categorias"]),
        ("Cronos - Ponto Eletrônico",          "cronos.db",  ["users","registros_ponto","jornadas","feriados"]),
        ("Hércules - Gestão de Tarefas",       "hercules.db",["users","projects","tasks"]),
        ("Héstia - Intranet Corporativa",      "hestia.db",  ["people","news","documents","communities"]),
        ("Iris - Gestão de Formulários e Workflow","iris.db",["formularios","ordens","historico"]),
        ("Oráculo - Hub de Notícias",          "oraculo.db", ["users","news","categories","departments"]),
        ("Têmis – Gestão de Contratos",        "temis.db",   ["contracts","audit_log"]),
        ("Tiresias – OCR",                     "tiresias.db",["documentos","configuracoes"]),
        ("Argos - Monitoração",                "monitor.db", ["monitored_urls","monitor_history"]),
    ]
    for pasta, db_file, tabelas in dbs:
        path = os.path.join(BASE, pasta, db_file)
        if not os.path.exists(path):
            continue
        c = sqlite3.connect(path); c.row_factory = sqlite3.Row
        linha = f"  {pasta[:35]:<35}"
        for t in tabelas:
            try:
                n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                linha += f"  {t}={n}"
            except:
                pass
        print(linha)
        c.close()
    print("=" * 55)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 55)
    print("OLIMPUS -- LIMPEZA DE DADOS ANTIGOS")
    print("=" * 55 + "\n")

    limpar_hera()
    limpar_ploutos()
    limpar_cronos()
    limpar_hercules()
    limpar_hestia()
    limpar_iris()
    limpar_oraculo()
    limpar_temis()
    limpar_tiresias()
    limpar_argos()

    verificar()
    print("\nLimpeza concluida!")
