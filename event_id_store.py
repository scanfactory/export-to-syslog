import sqlite3
import os
from typing import Set, Dict, Any, Optional
from datetime import datetime, timezone
from config import EVENT_ID_FILE


def _get_db_connection() -> sqlite3.Connection:
    """Создает подключение к БД и инициализирует таблицу если нужно."""

    db_dir = os.path.dirname(EVENT_ID_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(EVENT_ID_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            event_type TEXT,
            source TEXT,
            user TEXT,
            priority INTEGER,
            facility INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON events(source)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON events(created_at)")
    conn.commit()
    return conn


def load_event_ids() -> Set[str]:
    """Загружает множество ID обработанных событий из БД."""
    conn = _get_db_connection()
    cursor = conn.execute("SELECT id FROM events")
    ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return ids


def event_exists(event_id: str) -> bool:
    """Проверяет существование события по ID."""
    conn = _get_db_connection()
    cursor = conn.execute("SELECT 1 FROM events WHERE id = ? LIMIT 1", (event_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def store_event_id(event_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    """
    Сохраняет ID обработанного события в БД с метаданными.

    Args:
        event_id: Уникальный ID события
        metadata: Метаданные события (без полей info/details)
    """
    if metadata is None:
        metadata = {}

    conn = _get_db_connection()
    conn.execute("""
        INSERT OR IGNORE INTO events
        (id, timestamp, event_type, source, user, priority, facility, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        metadata.get("timestamp", ""),
        metadata.get("event_type", ""),
        metadata.get("source", ""),
        metadata.get("user", ""),
        metadata.get("priority", 0),
        metadata.get("facility", 0),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()


def cleanup_old_events(days: int = 30) -> int:
    """
    Удаляет события старше указанного количества дней.

    Args:
        days: Количество дней для хранения событий

    Returns:
        Количество удаленных записей
    """
    from datetime import timedelta
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    conn = _get_db_connection()
    cursor = conn.execute("DELETE FROM events WHERE created_at < ?", (cutoff_date,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count


def get_stats() -> Dict[str, Any]:
    """Возвращает статистику по хранилищу событий."""
    conn = _get_db_connection()

    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    by_source = {}
    cursor = conn.execute("SELECT source, COUNT(*) FROM events GROUP BY source")
    for row in cursor.fetchall():
        by_source[row[0] or "unknown"] = row[1]

    conn.close()

    return {
        "total_events": total,
        "by_source": by_source
    }
