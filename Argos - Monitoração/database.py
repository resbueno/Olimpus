from __future__ import annotations
"""
database.py — Camada de persistência SQLite
"""

import sqlite3
import os
import base64
from datetime import datetime
from cryptography.fernet import Fernet

DB_PATH = os.path.join(os.path.dirname(__file__), "monitor.db")
KEY_PATH = os.path.join(os.path.dirname(__file__), "secret.key")
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "screenshots")


# ── Criptografia ─────────────────────────────────────────────────────────────

def _get_or_create_key() -> bytes:
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    return key


def _cipher() -> Fernet:
    return Fernet(_get_or_create_key())


def encrypt_password(password: str) -> str:
    return _cipher().encrypt(password.encode()).decode()


def decrypt_password(token: str) -> str:
    return _cipher().decrypt(token.encode()).decode()


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def init_db():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS monitored_urls (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id           INTEGER NOT NULL,
            name                 TEXT    NOT NULL,
            url                  TEXT    NOT NULL,
            username             TEXT    NOT NULL,
            password_enc         TEXT    NOT NULL,
            target_menu_selector TEXT    NOT NULL,
            interval_minutes     INTEGER NOT NULL,
            active               INTEGER DEFAULT 1,
            two_step_login       INTEGER DEFAULT 0,
            notify_emails        TEXT    DEFAULT '',
            notify_on_fail       INTEGER DEFAULT 1,
            notify_on_slow_ms    INTEGER DEFAULT NULL,
            created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS monitor_history (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id       INTEGER NOT NULL,
            monitor_id       INTEGER NOT NULL,
            status           TEXT,
            initial_load_ms  INTEGER,
            login_ms         INTEGER,
            service_load_ms  INTEGER,
            total_journey_ms INTEGER,
            error_message    TEXT,
            screenshot_path  TEXT,
            executed_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (monitor_id) REFERENCES monitored_urls(id)
        );
    """)
    conn.commit()
    # Migração: adiciona colunas em bases existentes
    migrations = [
        "ALTER TABLE monitor_history ADD COLUMN screenshot_path TEXT",
        "ALTER TABLE monitored_urls ADD COLUMN two_step_login INTEGER DEFAULT 0",
        "ALTER TABLE monitored_urls ADD COLUMN notify_emails TEXT DEFAULT ''",
        "ALTER TABLE monitored_urls ADD COLUMN notify_on_fail INTEGER DEFAULT 1",
        "ALTER TABLE monitored_urls ADD COLUMN notify_on_slow_ms INTEGER DEFAULT NULL",
        "ALTER TABLE monitored_urls ADD COLUMN company_id INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE monitor_history ADD COLUMN company_id INTEGER NOT NULL DEFAULT 1",
    ]
    for migration in migrations:
        try:
            conn.execute(migration)
            conn.commit()
        except Exception:
            # Column might already exist or other issue
            pass
    conn.close()


# ── monitored_urls ────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def list_monitors(active_only: bool = False) -> list:
    conn = get_conn()
    q = "SELECT * FROM monitored_urls"
    if active_only:
        q += " WHERE active = 1"
    q += " ORDER BY created_at DESC"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monitor(monitor_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM monitored_urls WHERE id = ?", (monitor_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_monitor(data: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO monitored_urls
            (name, url, username, password_enc, target_menu_selector, interval_minutes, active,
             two_step_login, notify_emails, notify_on_fail, notify_on_slow_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"],
        data["url"],
        data["username"],
        encrypt_password(data["password"]),
        data["target_menu_selector"],
        int(data["interval_minutes"]),
        int(data.get("active", 1)),
        int(data.get("two_step_login", 0)),
        data.get("notify_emails", ""),
        int(data.get("notify_on_fail", 1)),
        int(data["notify_on_slow_ms"]) if data.get("notify_on_slow_ms") else None,
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_monitor(monitor_id: int, data: dict) -> bool:
    conn = get_conn()
    fields, values = [], []
    mapping = {
        "name": "name",
        "url": "url",
        "username": "username",
        "target_menu_selector": "target_menu_selector",
        "interval_minutes": "interval_minutes",
        "active": "active",
        "two_step_login": "two_step_login",
        "notify_emails": "notify_emails",
        "notify_on_fail": "notify_on_fail",
    }
    # notify_on_slow_ms handled separately (allows null)
    if "notify_on_slow_ms" in data:
        fields.append("notify_on_slow_ms = ?")
        values.append(int(data["notify_on_slow_ms"]) if data["notify_on_slow_ms"] else None)
    for key, col in mapping.items():
        if key in data:
            fields.append(f"{col} = ?")
            values.append(data[key])
    if "password" in data and data["password"]:
        fields.append("password_enc = ?")
        values.append(encrypt_password(data["password"]))
    if not fields:
        conn.close()
        return False
    values.append(monitor_id)
    conn.execute(
        f"UPDATE monitored_urls SET {', '.join(fields)} WHERE id = ?", values
    )
    conn.commit()
    conn.close()
    return True


def delete_monitor(monitor_id: int) -> bool:
    conn = get_conn()
    conn.execute("DELETE FROM monitored_urls WHERE id = ?", (monitor_id,))
    conn.execute("DELETE FROM monitor_history WHERE monitor_id = ?", (monitor_id,))
    conn.commit()
    conn.close()
    return True


def toggle_monitor(monitor_id: int, active: bool) -> bool:
    conn = get_conn()
    conn.execute(
        "UPDATE monitored_urls SET active = ? WHERE id = ?",
        (1 if active else 0, monitor_id),
    )
    conn.commit()
    conn.close()
    return True


# ── monitor_history ────────────────────────────────────────────────────────────

def save_history(entry: dict) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO monitor_history
            (company_id, monitor_id, status, initial_load_ms, login_ms,
             service_load_ms, total_journey_ms, error_message, screenshot_path, executed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry.get("company_id", 1),
        entry["monitor_id"],
        entry.get("status", "UNKNOWN"),
        entry.get("initial_load_ms"),
        entry.get("login_ms"),
        entry.get("service_load_ms"),
        entry.get("total_journey_ms"),
        entry.get("error_message"),
        entry.get("screenshot_path"),
        entry.get("executed_at", datetime.now().isoformat()),
    ))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def get_history(monitor_id: int, limit: int = 50) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM monitor_history
        WHERE monitor_id = ?
        ORDER BY executed_at DESC
        LIMIT ?
    """, (monitor_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history_all(limit: int = 200) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT h.*, m.name as monitor_name
        FROM monitor_history h
        JOIN monitored_urls m ON h.monitor_id = m.id
        ORDER BY h.executed_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats(monitor_id: int) -> dict:
    conn = get_conn()
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) as fail,
            AVG(CASE WHEN status = 'SUCCESS' THEN total_journey_ms END) as avg_ms,
            MIN(CASE WHEN status = 'SUCCESS' THEN total_journey_ms END) as min_ms,
            MAX(CASE WHEN status = 'SUCCESS' THEN total_journey_ms END) as max_ms
        FROM monitor_history
        WHERE monitor_id = ?
    """, (monitor_id,)).fetchone()
    conn.close()
    d = dict(row) if row else {}
    total = d.get("total") or 0
    success = d.get("success") or 0
    d["availability"] = round((success / total * 100), 1) if total > 0 else None
    return d


def get_last_execution(monitor_id: int):
    conn = get_conn()
    row = conn.execute("""
        SELECT * FROM monitor_history
        WHERE monitor_id = ?
        ORDER BY executed_at DESC
        LIMIT 1
    """, (monitor_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
