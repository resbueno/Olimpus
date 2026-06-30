from __future__ import annotations
"""
database.py — Camada de persistência SQLite do Héstia
Intranet Corporativa
"""

import sqlite3
import os
from datetime import datetime
from cryptography.fernet import Fernet

DB_PATH = os.path.join(os.path.dirname(__file__), "hestia.db")
KEY_PATH = os.path.join(os.path.dirname(__file__), "secret.key")


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


def encrypt_content(content: str) -> str:
    return _cipher().encrypt(content.encode()).decode()


def decrypt_content(token: str) -> str:
    return _cipher().decrypt(token.encode()).decode()


# ── Bootstrap ─────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS news (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            author_id   TEXT    NOT NULL,
            author_name TEXT    NOT NULL,
            pinned     INTEGER DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            content     TEXT,
            content_enc TEXT,
            folder_id   INTEGER,
            author_id   TEXT    NOT NULL,
            author_name TEXT    NOT NULL,
            version    INTEGER DEFAULT 1,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS document_folders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            parent_id INTEGER,
            author_id TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS document_versions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            version     INTEGER NOT NULL,
            content_enc TEXT,
            author_id   TEXT NOT NULL,
            author_name TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        );

        CREATE TABLE IF NOT EXISTS document_attachments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL,
            filename    TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            file_type   TEXT,
            file_size   INTEGER,
            author_id   TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        );

        CREATE TABLE IF NOT EXISTS folder_access (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_id  INTEGER NOT NULL,
            role_name  TEXT,
            dept_name  TEXT,
            FOREIGN KEY(folder_id) REFERENCES document_folders(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

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

        CREATE TABLE IF NOT EXISTS people (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT    NOT NULL UNIQUE,
            nome           TEXT    NOT NULL,
            email          TEXT,
            cargo          TEXT,
            departamento  TEXT,
            foto_url      TEXT,
            birthday      TEXT,
            start_date    TEXT,
            bio          TEXT,
            linkedin     TEXT,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS communities (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            description TEXT,
            owner_id     TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS community_members (
            community_id INTEGER NOT NULL,
            user_id   TEXT NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (community_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS community_messages (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            community_id INTEGER NOT NULL,
            author_id    TEXT NOT NULL,
            author_name  TEXT NOT NULL,
            message      TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            description TEXT,
            start_date   DATETIME NOT NULL,
            end_date   DATETIME,
            location   TEXT,
            meeting_link TEXT,
            owner_id   TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS kudos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            to_user_id  TEXT NOT NULL,
            from_user_id TEXT NOT NULL,
            message     TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ── News ────────────────────────────────────────────────────────────────────────

def list_news(limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM news
        ORDER BY pinned DESC, created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_news(news_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM news WHERE id = ?", (news_id,)).fetchone()
    conn.close()
    if row:
        item = dict(row)
        item["attachments"] = list_news_attachments(news_id)
        return item
    return None


def list_news_attachments(news_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM news_attachments WHERE news_id = ? ORDER BY created_at DESC", (news_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_news_attachment(news_id, filename, file_path, file_type, file_size, author_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO news_attachments (news_id, filename, file_path, file_type, file_size, author_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (news_id, filename, file_path, file_type, file_size, author_id))
    conn.commit()
    conn.close()


def create_news(title: str, content: str, author_id: str, author_name: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO news (title, content, author_id, author_name)
        VALUES (?, ?, ?, ?)
    """, (title, content, author_id, author_name))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_news(news_id: int, title: str, content: str):
    conn = get_conn()
    conn.execute("""
        UPDATE news
        SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (title, content, news_id))
    conn.commit()
    conn.close()


def delete_news(news_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM news WHERE id = ?", (news_id,))
    conn.commit()
    conn.close()


# ── Documents ─────────────────────────────────────────────────────────────────────────

def list_documents(folder_id=None) -> list:
    conn = get_conn()
    if folder_id:
        rows = conn.execute("""
            SELECT * FROM documents
            WHERE folder_id = ?
            ORDER BY title
        """, (folder_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM documents
            WHERE folder_id IS NULL
            ORDER BY title
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_document(doc_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_document(title: str, content: str, folder_id, author_id: str, author_name: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    content_enc = encrypt_content(content) if content else None
    c.execute("""
        INSERT INTO documents (title, content, content_enc, folder_id, author_id, author_name, version)
        VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (title, content, content_enc, folder_id, author_id, author_name))
    new_id = c.lastrowid
    # Salvar versão 1
    c.execute("""
        INSERT INTO document_versions (document_id, version, content_enc, author_id, author_name)
        VALUES (?, 1, ?, ?, ?)
    """, (new_id, content_enc, author_id, author_name))
    conn.commit()
    conn.close()
    return new_id


def update_document(doc_id: int, title: str, content: str, author_id: str, author_name: str):
    conn = get_conn()
    c = conn.cursor()
    row = c.execute("SELECT version FROM documents WHERE id = ?", (doc_id,)).fetchone()
    old_version = row[0] if row else 1
    new_version = old_version + 1
    content_enc = encrypt_content(content) if content else None
    
    # Atualiza documento principal
    c.execute("""
        UPDATE documents
        SET title = ?, content = ?, content_enc = ?, version = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (title, content, content_enc, new_version, doc_id))
    
    # Salva nova versão no histórico
    c.execute("""
        INSERT INTO document_versions (document_id, version, content_enc, author_id, author_name)
        VALUES (?, ?, ?, ?, ?)
    """, (doc_id, new_version, content_enc, author_id, author_name))
    
    conn.commit()
    conn.close()


def add_attachment(doc_id: int, filename: str, file_path: str, file_type: str, file_size: int, author_id: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO document_attachments (document_id, filename, file_path, file_type, file_size, author_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (doc_id, filename, file_path, file_type, file_size, author_id))
    conn.commit()
    conn.close()


def list_attachments(doc_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM document_attachments WHERE document_id = ?", (doc_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_versions(doc_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM document_versions WHERE document_id = ? ORDER BY version DESC", (doc_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]




def delete_document(doc_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()


# ── Folders ────────────────────────────────────────────────────────────────────

def list_folders(parent_id=None, user_roles=None, user_dept=None) -> list:
    conn = get_conn()
    
    # Busca todas as pastas no nível solicitado
    sql = "SELECT * FROM document_folders WHERE (parent_id IS ? OR parent_id = ?) ORDER BY name"
    rows = conn.execute(sql, (parent_id, parent_id)).fetchall()
    folders = [dict(r) for r in rows]
    
    # Se for admin, vê tudo
    if user_roles and "admin" in user_roles:
        conn.close()
        return folders

    visible_folders = []
    for f in folders:
        access_rows = conn.execute("SELECT role_name, dept_name FROM folder_access WHERE folder_id = ?", (f["id"],)).fetchall()
        if not access_rows:
            visible_folders.append(f) # Pública
            continue
            
        # Verifica se o usuário atende a QUALQUER uma das regras (Role AND Dept)
        can_see = False
        for rule in access_rows:
            role_match = not rule["role_name"] or (user_roles and rule["role_name"] in user_roles)
            dept_match = not rule["dept_name"] or (user_dept and rule["dept_name"] == user_dept)
            if role_match and dept_match:
                can_see = True
                break
        
        if can_see:
            visible_folders.append(f)

    conn.close()
    return visible_folders


def set_folder_access(folder_id: int, rules: list):
    """rules: lista de dicts [{'role': '...', 'dept': '...'}]"""
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM folder_access WHERE folder_id = ?", (folder_id,))
    for rule in rules:
        c.execute("""
            INSERT INTO folder_access (folder_id, role_name, dept_name)
            VALUES (?, ?, ?)
        """, (folder_id, rule.get("role"), rule.get("dept")))
    conn.commit()
    conn.close()


def get_folder_access(folder_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT role_name, dept_name FROM folder_access WHERE folder_id = ?", (folder_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_departments() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT departamento FROM people WHERE departamento IS NOT NULL AND departamento != ''").fetchall()
    conn.close()
    return [r[0] for r in rows]




def create_folder(name: str, parent_id, author_id: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO document_folders (name, parent_id, author_id)
        VALUES (?, ?, ?)
    """, (name, parent_id, author_id))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


# ── People ──────────────────────────────────────────────────────────────────────

def list_people(search: str = "") -> list:
    conn = get_conn()
    if search:
        rows = conn.execute("""
            SELECT * FROM people
            WHERE nome LIKE ? OR cargo LIKE ? OR departamento LIKE ?
            ORDER BY nome
        """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM people ORDER BY nome").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_person(user_id: str, nome: str, email: str, cargo: str, departamento: str, foto_url: str = None, birthday: str = None, bio: str = None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM people WHERE user_id = ?", (user_id,))
    existing = c.fetchone()
    if existing:
        c.execute("""
            UPDATE people
            SET nome = ?, email = ?, cargo = ?, departamento = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (nome, email, cargo, departamento, user_id))
    else:
        c.execute("""
            INSERT INTO people (user_id, nome, email, cargo, departamento)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, nome, email, cargo, departamento))
    conn.commit()
    conn.close()


def get_person(person_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_birthdays(days: int = 30) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM people
        WHERE birthday IS NOT NULL
        ORDER BY
            substr(birthday, 6, 2) || '-' || substr(birthday, 8, 2),
            nome
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Kudos ───────────────────────────────────────────────────────────────────────

def list_kudos(limit: int = 20) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT k.*, p.nome as to_nome, p2.nome as from_nome
        FROM kudos k
        LEFT JOIN people p ON k.to_user_id = p.user_id
        LEFT JOIN people p2 ON k.from_user_id = p2.user_id
        ORDER BY k.created_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_kudos(to_user_id: str, from_user_id: str, message: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO kudos (to_user_id, from_user_id, message)
        VALUES (?, ?, ?)
    """, (to_user_id, from_user_id, message))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


# ── Communities ───────────────────────────────────────────────────────────

def list_communities() -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT c.*,
            (SELECT COUNT(*) FROM community_members WHERE community_id = c.id) as member_count
        FROM communities c
        ORDER BY name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_community(community_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM communities WHERE id = ?", (community_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_community(name: str, description: str, owner_id: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO communities (name, description, owner_id)
        VALUES (?, ?, ?)
    """, (name, description, owner_id))
    conn.commit()
    new_id = c.lastrowid
    c.execute("""
        INSERT INTO community_members (community_id, user_id)
        VALUES (?, ?)
    """, (new_id, owner_id))
    conn.commit()
    conn.close()
    return new_id


def join_community(community_id: int, user_id: str):
    conn = get_conn()
    try:
        conn.execute("""
            INSERT INTO community_members (community_id, user_id)
            VALUES (?, ?)
        """, (community_id, user_id))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def leave_community(community_id: int, user_id: str):
    conn = get_conn()
    conn.execute("""
        DELETE FROM community_members
        WHERE community_id = ? AND user_id = ?
    """, (community_id, user_id))
    conn.commit()
    conn.close()


def update_community(community_id: int, name: str, description: str):
    conn = get_conn()
    conn.execute("""
        UPDATE communities
        SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (name, description, community_id))
    conn.commit()
    conn.close()


def delete_community(community_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM community_messages WHERE community_id = ?", (community_id,))
    conn.execute("DELETE FROM community_members WHERE community_id = ?", (community_id,))
    conn.execute("DELETE FROM communities WHERE id = ?", (community_id,))
    conn.commit()
    conn.close()


def list_community_messages(community_id: int) -> list:
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM community_messages
        WHERE community_id = ?
        ORDER BY created_at DESC
        LIMIT 50
    """, (community_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_community_message(community_id: int, author_id: str, author_name: str, message: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO community_messages (community_id, author_id, author_name, message)
        VALUES (?, ?, ?, ?)
    """, (community_id, author_id, author_name, message))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


# ── Events ────────────────────────────────────────────────────────────────────

def list_events(start: str = None, end: str = None) -> list:
    conn = get_conn()
    if start and end:
        rows = conn.execute("""
            SELECT * FROM events
            WHERE start_date >= ? AND start_date <= ?
            ORDER BY start_date
        """, (start, end)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM events
            ORDER BY start_date
            LIMIT 50
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_event(event_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_event(title: str, description: str, start_date: str, end_date: str, location: str, meeting_link: str, owner_id: str) -> int:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO events (title, description, start_date, end_date, location, meeting_link, owner_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, description, start_date, end_date, location, meeting_link, owner_id))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return new_id


def update_event(event_id: int, title: str, description: str, start_date: str, end_date: str, location: str, meeting_link: str):
    conn = get_conn()
    conn.execute("""
        UPDATE events
        SET title = ?, description = ?, start_date = ?, end_date = ?, location = ?, meeting_link = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (title, description, start_date, end_date, location, meeting_link, event_id))
    conn.commit()
    conn.close()


def delete_event(event_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()


# ── Stats ─────────────────────────────────────────────────────────────────

def get_global_stats() -> dict:
    conn = get_conn()
    stats = {}
    stats["total_news"] = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    stats["total_documents"] = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    stats["total_people"] = conn.execute("SELECT COUNT(*) FROM people").fetchone()[0]
    stats["total_communities"] = conn.execute("SELECT COUNT(*) FROM communities").fetchone()[0]
    stats["total_events"] = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    stats["total_kudos"] = conn.execute("SELECT COUNT(*) FROM kudos").fetchone()[0]
    conn.close()
    return stats

def get_settings() -> dict:
    conn = get_conn()
    rows = conn.execute('SELECT key, value FROM settings').fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

def update_setting(key: str, value: str):
    conn = get_conn()
    conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()
