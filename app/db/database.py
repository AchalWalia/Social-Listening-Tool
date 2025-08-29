from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.config import DB_PATH

# Use in-memory database to avoid disk I/O issues
_connection_cache: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    global _connection_cache
    if _connection_cache is None:
        # Use in-memory database to avoid disk I/O errors
        _connection_cache = sqlite3.connect(":memory:", check_same_thread=False, timeout=30)
        _connection_cache.row_factory = sqlite3.Row
        # Improve concurrency and robustness
        cursor = _connection_cache.cursor()
        try:
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass
        _ensure_schema(_connection_cache)
    return _connection_cache


def _ensure_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            domain TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            source TEXT NOT NULL,               -- e.g., 'Google Play', 'Reddit', 'Apple App Store', 'YouTube'
            source_ref TEXT,                    -- e.g., app id, subreddit, video id
            content TEXT NOT NULL,
            author TEXT,
            date TEXT,
            rating REAL,
            url TEXT,
            sentiment_label TEXT,               -- 'POSITIVE' | 'NEGATIVE'
            sentiment_score REAL,               -- 0..1 confidence
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_id, source, url, content) ON CONFLICT IGNORE,
            FOREIGN KEY(company_id) REFERENCES companies(id)
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mentions_company ON mentions(company_id);
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_mentions_company_source ON mentions(company_id, source);
        """
    )
    # New: app profiles for store ratings
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS app_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            platform TEXT NOT NULL,             -- 'Google Play' | 'Apple App Store'
            app_id TEXT NOT NULL,
            title TEXT,
            rating REAL,                        -- average rating (0..5)
            ratings_count INTEGER,              -- total ratings count
            url TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(company_id, platform, app_id)
        );
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_app_profiles_company_platform ON app_profiles(company_id, platform);
        """
    )
    connection.commit()


def get_or_create_company(connection: sqlite3.Connection, name: str, domain: Optional[str]) -> int:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM companies WHERE name = ? AND IFNULL(domain, '') = IFNULL(?, '')",
        (name, domain),
    )
    row = cursor.fetchone()
    if row:
        return int(row[0])
    cursor.execute(
        "INSERT INTO companies(name, domain) VALUES (?, ?)",
        (name, domain),
    )
    connection.commit()
    return int(cursor.lastrowid)


def insert_mentions(connection: sqlite3.Connection, company_id: int, rows: Iterable[Dict[str, Any]]) -> int:
    cursor = connection.cursor()
    to_insert: List[Tuple[Any, ...]] = []
    for r in rows:
        to_insert.append(
            (
                company_id,
                r.get("source"),
                r.get("source_ref"),
                r.get("content"),
                r.get("author"),
                r.get("date"),
                r.get("rating"),
                r.get("url"),
            )
        )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO mentions (
            company_id, source, source_ref, content, author, date, rating, url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        to_insert,
    )
    connection.commit()
    return cursor.rowcount or 0


def upsert_app_profile(
    connection: sqlite3.Connection,
    company_id: int,
    platform: str,
    app_id: str,
    title: Optional[str],
    rating: Optional[float],
    ratings_count: Optional[int],
    url: Optional[str],
) -> None:
    cursor = connection.cursor()
    cursor.execute(
        """
        INSERT INTO app_profiles(company_id, platform, app_id, title, rating, ratings_count, url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(company_id, platform, app_id) DO UPDATE SET
            title=excluded.title,
            rating=excluded.rating,
            ratings_count=excluded.ratings_count,
            url=excluded.url,
            updated_at=CURRENT_TIMESTAMP
        """,
        (company_id, platform, app_id, title, rating, ratings_count, url),
    )
    connection.commit()


def get_platform_rating_summary(connection: sqlite3.Connection, company_id: int) -> Dict[str, Dict[str, float]]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT platform,
               SUM(COALESCE(rating, 0) * COALESCE(ratings_count, 0)) AS weighted_sum,
               SUM(COALESCE(ratings_count, 0)) AS total_count,
               COUNT(*) AS apps
        FROM app_profiles
        WHERE company_id = ? AND rating IS NOT NULL
        GROUP BY platform
        """,
        (company_id,),
    )
    summary: Dict[str, Dict[str, float]] = {}
    for row in cursor.fetchall():
        platform = str(row[0])
        weighted_sum = float(row[1] or 0.0)
        total_count = int(row[2] or 0)
        apps = int(row[3] or 0)
        if total_count > 0:
            avg = weighted_sum / total_count
        else:
            # Fallback: simple mean if counts are missing
            cursor.execute(
                "SELECT AVG(rating) FROM app_profiles WHERE company_id = ? AND platform = ? AND rating IS NOT NULL",
                (company_id, platform),
            )
            avg = float(cursor.fetchone()[0] or 0.0)
        summary[platform] = {"avg_rating": round(avg, 2), "ratings_count": total_count, "apps": apps}
    return summary


def fetch_mentions_dataframe(connection: sqlite3.Connection, company_id: int, source: Optional[str] = None):
    import pandas as pd  # local import to avoid global dependency at import time

    if source and source != "All Sources":
        query = "SELECT * FROM mentions WHERE company_id = ? AND source = ? ORDER BY date DESC"
        params: Tuple[Any, ...] = (company_id, source)
    else:
        query = "SELECT * FROM mentions WHERE company_id = ? ORDER BY date DESC"
        params = (company_id,)
    df = pd.read_sql_query(query, connection, params=params)
    return df


def fetch_unlabeled_texts(connection: sqlite3.Connection, company_id: int, limit: int = 256) -> List[Tuple[int, str]]:
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT id, content FROM mentions
        WHERE company_id = ? AND sentiment_label IS NULL
        LIMIT ?
        """,
        (company_id, limit),
    )
    return [(int(r[0]), str(r[1])) for r in cursor.fetchall()]


def update_sentiments(connection: sqlite3.Connection, labeled: List[Tuple[int, str, float]]) -> None:
    cursor = connection.cursor()
    cursor.executemany(
        "UPDATE mentions SET sentiment_label = ?, sentiment_score = ? WHERE id = ?",
        [(label, float(score), int(_id)) for _id, label, score in labeled],
    )
    connection.commit() 