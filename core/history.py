import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

JUZZYAI_DIR  = os.path.expanduser("~/.juzzyai")
DB_FILE      = os.path.join(JUZZYAI_DIR, "history.db")
CSV_FILE     = os.path.expanduser("~/.juzzyai_history.csv")  # старый файл для миграции

MAX_SESSIONS = 100
MAX_ROWS     = 5000


# ─── Инициализация ────────────────────────────────────────────────────────────

def _init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp  TEXT    NOT NULL,
            session_id TEXT    NOT NULL,
            role       TEXT    NOT NULL,
            content    TEXT    NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_session ON messages(session_id)")
    conn.commit()


@contextmanager
def _get_conn():
    os.makedirs(JUZZYAI_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        _init_db(conn)
        _migrate_csv(conn)
        yield conn
    finally:
        conn.close()


# ─── Миграция из CSV ──────────────────────────────────────────────────────────

def _migrate_csv(conn: sqlite3.Connection):
    """Если есть старый CSV — переносим данные в SQLite и удаляем его."""
    if not os.path.exists(CSV_FILE):
        return

    # Проверяем — уже мигрировали?
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    if count > 0:
        # данные уже есть — просто удаляем CSV
        os.remove(CSV_FILE)
        return

    import csv
    try:
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [
                (r["timestamp"], r["session_id"], r["role"], r["content"])
                for r in reader
                if all(k in r for k in ("timestamp", "session_id", "role", "content"))
            ]
        if rows:
            conn.executemany(
                "INSERT INTO messages (timestamp, session_id, role, content) VALUES (?,?,?,?)",
                rows
            )
            conn.commit()
        os.remove(CSV_FILE)
        print(f"\033[33m→ Migrated {len(rows)} messages from CSV to SQLite\033[0m")
    except Exception as e:
        print(f"\033[33m⚠ CSV migration failed: {e}\033[0m")


# ─── Публичный API ────────────────────────────────────────────────────────────

def save_message(session_id: str, role: str, content: str):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (timestamp, session_id, role, content) VALUES (?,?,?,?)",
            (datetime.now().isoformat(), session_id, role, content)
        )
        conn.commit()
        _rotate(conn)


def load_session(session_id: str) -> list:
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,)
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def list_sessions() -> list:
    with _get_conn() as conn:
        rows = conn.execute("""
            SELECT session_id, MAX(timestamp) as last_message
            FROM messages
            GROUP BY session_id
            ORDER BY last_message DESC
        """).fetchall()
    return [{"session_id": r["session_id"], "last_message": r["last_message"]} for r in rows]


# ─── Ротация ──────────────────────────────────────────────────────────────────

def _rotate(conn: sqlite3.Connection):
    """Удаляем старейшие сессии если превышен лимит."""
    total_rows = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM messages").fetchone()[0]

    if total_rows <= MAX_ROWS and total_sessions <= MAX_SESSIONS:
        return

    # Получаем сессии от старейшей к новейшей
    sessions = conn.execute("""
        SELECT session_id, MIN(timestamp) as first_ts
        FROM messages
        GROUP BY session_id
        ORDER BY first_ts ASC
    """).fetchall()

    sessions_to_delete = []
    remaining_sessions = total_sessions
    remaining_rows = total_rows

    for row in sessions:
        if remaining_rows <= MAX_ROWS and remaining_sessions <= MAX_SESSIONS:
            break
        sid = row["session_id"]
        count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (sid,)
        ).fetchone()[0]
        sessions_to_delete.append(sid)
        remaining_sessions -= 1
        remaining_rows -= count

    if sessions_to_delete:
        conn.execute(
            f"DELETE FROM messages WHERE session_id IN ({','.join('?' * len(sessions_to_delete))})",
            sessions_to_delete
        )
        conn.commit()