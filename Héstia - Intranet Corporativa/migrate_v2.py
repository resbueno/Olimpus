from __future__ import annotations
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hestia.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Adicionar dept_name em folder_access
    try:
        c.execute("ALTER TABLE folder_access ADD COLUMN dept_name TEXT;")
        print("Coluna dept_name adicionada em folder_access.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("Coluna dept_name já existe.")
        else:
            print(f"Erro ao adicionar coluna: {e}")

    # 2. Criar tabela de anexos de notícias se não existir
    c.execute("""
        CREATE TABLE IF NOT EXISTS news_attachments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id     INTEGER NOT NULL,
            filename    TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            file_type   TEXT,
            file_size   INTEGER,
            author_id   TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(news_id) REFERENCES news(id)
        );
    """)
    print("Tabela news_attachments garantida.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    migrate()
