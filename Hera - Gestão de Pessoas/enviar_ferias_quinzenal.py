from __future__ import annotations
"""
enviar_ferias_quinzenal.py — Rotina de revisão de férias
Este script deve ser executado a cada 15 dias para notificar gestores sobre o status de férias da equipe.
"""
import sqlite3
import os
from datetime import datetime
from ferias_calc import FeriasCalculador

# Caminho do banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hera.db")

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def processar_relatorios():
    conn = get_conn()
    
    # Busca todos os gestores (usuários que são gestor_id de alguém)
    gestores = conn.execute("""
        SELECT DISTINCT g.id, g.nome, g.email 
        FROM users g
        JOIN users u ON u.gestor_id = g.id
        WHERE g.ativo = 1
    """).fetchall()
    
    print(f"[{datetime.now()}] Iniciando processamento de relatórios para {len(gestores)} gestores...")
    
    for gestor in gestores:
        # Busca subordinados
        subordinados = conn.execute("""
            SELECT id, nome, email, data_admissao 
            FROM users 
            WHERE gestor_id = ? AND ativo = 1
        """, (gestor["id"],)).fetchall()
        
        relatorio = []
        for sub in subordinados:
            # Busca histórico de férias
            ferias = conn.execute("SELECT status, data_inicio FROM ferias WHERE user_id=?", (sub["id"],)).fetchall()
            ferias_list = [dict(f) for f in ferias]
            
            status_info = FeriasCalculador.classificar_status_ferias(sub["data_admissao"], ferias_list)
            
            relatorio.append({
                "nome": sub["nome"],
                "status": status_info["status"],
                "alerta": status_info["classe"] in ("urgente", "vencendo")
            })
            
        # Simulação de envio de e-mail
        enviar_email_simulado(gestor, relatorio)
        
    conn.close()
    print(f"[{datetime.now()}] Processamento concluído.")

def enviar_email_simulado(gestor, relatorio):
    print(f"\n>>> ENVIANDO E-MAIL PARA: {gestor['nome']} ({gestor['email']})")
    print("-" * 50)
    print("Assunto: [Hera] Relatório Quinzenal de Revisão de Férias")
    print("\nOlá, seguem as atualizações de férias da sua equipe:\n")
    
    for item in relatorio:
        alerta = "[!] " if item["alerta"] else "    "
        print(f"{alerta}{item['nome'].ljust(30)} | Status: {item['status']}")
        
    print("-" * 50)

if __name__ == "__main__":
    processar_relatorios()
