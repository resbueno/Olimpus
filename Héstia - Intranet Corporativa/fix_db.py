from __future__ import annotations
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "hestia.db")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("UPDATE documents SET folder_id = NULL WHERE folder_id = '';")
print(f"Linhas afetadas: {c.rowcount}")
conn.commit()
conn.close()
