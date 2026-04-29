import sqlite3
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from config import settings

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db_conn():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS listings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                url TEXT,
                seller_id TEXT,
                seller_type TEXT,
                images_count INTEGER DEFAULT 0,
                location TEXT,
                category TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new'
            );

            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_term TEXT NOT NULL,
                price REAL NOT NULL,
                listing_id TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                url TEXT,
                score INTEGER NOT NULL,
                expected_profit REAL NOT NULL,
                rolling_average REAL NOT NULL,
                price_delta_percent REAL NOT NULL,
                location TEXT,
                images_count INTEGER DEFAULT 0,
                age_minutes REAL,
                alerted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_action TEXT
            );

            CREATE TABLE IF NOT EXISTS search_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                category_id TEXT,
                max_price REAL,
                min_price REAL,
                active INTEGER DEFAULT 1,
                custom_threshold REAL
            );

            CREATE TABLE IF NOT EXISTS blacklist (
                seller_id TEXT PRIMARY KEY,
                reason TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS watchlist (
                seller_id TEXT PRIMARY KEY,
                note TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_listings_seen_at ON listings(seen_at);
            CREATE INDEX IF NOT EXISTS idx_listings_seller_id ON listings(seller_id);
            CREATE INDEX IF NOT EXISTS idx_price_history_search_term ON price_history(search_term);
            CREATE INDEX IF NOT EXISTS idx_price_history_seen_at ON price_history(seen_at);
            CREATE INDEX IF NOT EXISTS idx_alerts_listing_id ON alerts(listing_id);
            CREATE INDEX IF NOT EXISTS idx_alerts_alerted_at ON alerts(alerted_at);
            CREATE INDEX IF NOT EXISTS idx_alerts_score ON alerts(score);
        """)
    logger.info("Database initialized")


def migrate():
    """Add new columns to existing tables if they don't exist."""
    with db_conn() as conn:
        cursor = conn.execute("PRAGMA table_info(listings)")
        listing_cols = {row["name"] for row in cursor.fetchall()}

        migrations = {
            "listings": [
                ("seller_type", "TEXT"),
                ("status", "TEXT DEFAULT 'new'"),
            ],
            "alerts": [
                ("location", "TEXT"),
                ("images_count", "INTEGER DEFAULT 0"),
                ("age_minutes", "REAL"),
                ("title", "TEXT DEFAULT ''"),
                ("url", "TEXT DEFAULT ''"),
                ("price", "REAL DEFAULT 0"),
                ("rolling_average", "REAL DEFAULT 0"),
                ("price_delta_percent", "REAL DEFAULT 0"),
            ],
        }

        for table, columns in migrations.items():
            cursor = conn.execute(f"PRAGMA table_info({table})")
            existing = {row["name"] for row in cursor.fetchall()}
            for col_name, col_def in columns:
                if col_name not in existing:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                    logger.info(f"Migrated: added {col_name} to {table}")


def seed_default_profiles():
    with db_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM search_profiles").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO search_profiles (name, query, active) VALUES (?, ?, 1)",
                [
                    ("Nintendo Switch", "Nintendo Switch"),
                    ("Lego Technic", "Lego Technic"),
                    ("iPhone", "iPhone"),
                ],
            )
            logger.info("Seeded 3 default search profiles")


def upsert_listing(listing: dict) -> bool:
    """Returns True if this is a new listing."""
    with db_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM listings WHERE id = ?", (listing["id"],)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE listings SET price=?, seen_at=? WHERE id=?",
                (listing["price"], datetime.utcnow(), listing["id"]),
            )
            return False
        conn.execute(
            """INSERT INTO listings
               (id, title, price, url, seller_id, seller_type, images_count, location, category, seen_at, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                listing["id"],
                listing["title"],
                listing["price"],
                listing.get("url"),
                listing.get("seller_id"),
                listing.get("seller_type"),
                listing.get("images_count", 0),
                listing.get("location"),
                listing.get("category"),
                datetime.utcnow(),
                "new",
            ),
        )
        return True


def add_price_history(search_term: str, price: float, listing_id: Optional[str] = None):
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO price_history (search_term, price, listing_id, seen_at) VALUES (?, ?, ?, ?)",
            (search_term, price, listing_id, datetime.utcnow()),
        )


def get_price_history(search_term: str, days: int = 30) -> List[dict]:
    with db_conn() as conn:
        rows = conn.execute(
            """SELECT price, seen_at FROM price_history
               WHERE search_term = ?
               AND seen_at >= datetime('now', ? || ' days')
               ORDER BY seen_at ASC""",
            (search_term, f"-{days}"),
        ).fetchall()
        return [dict(r) for r in rows]


def was_recently_alerted(listing_id: str, cooldown_hours: int) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            """SELECT id FROM alerts WHERE listing_id = ?
               AND alerted_at >= datetime('now', ? || ' hours')""",
            (listing_id, f"-{cooldown_hours}"),
        ).fetchone()
        return row is not None


def save_alert(alert: dict):
    with db_conn() as conn:
        conn.execute(
            """INSERT INTO alerts
               (listing_id, title, price, url, score, expected_profit, rolling_average,
                price_delta_percent, location, images_count, age_minutes, alerted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert["listing_id"],
                alert["title"],
                alert["price"],
                alert.get("url"),
                alert["score"],
                alert["expected_profit"],
                alert["rolling_average"],
                alert["price_delta_percent"],
                alert.get("location"),
                alert.get("images_count", 0),
                alert.get("age_minutes"),
                datetime.utcnow(),
            ),
        )


def get_alerts(
    page: int = 0,
    page_size: int = 20,
    min_score: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user_action: Optional[str] = None,
) -> List[dict]:
    filters = []
    params: list = []
    if min_score is not None:
        filters.append("score >= ?")
        params.append(min_score)
    if date_from:
        filters.append("alerted_at >= ?")
        params.append(date_from)
    if date_to:
        filters.append("alerted_at <= ?")
        params.append(date_to)
    if user_action:
        filters.append("user_action = ?")
        params.append(user_action)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [page_size, page * page_size]

    with db_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM alerts {where} ORDER BY alerted_at DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_alert_by_id(alert_id: int) -> Optional[dict]:
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        return dict(row) if row else None


def update_alert_action(alert_id: int, user_action: str):
    with db_conn() as conn:
        conn.execute(
            "UPDATE alerts SET user_action = ? WHERE id = ?",
            (user_action, alert_id),
        )


def get_profiles() -> List[dict]:
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM search_profiles ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_active_profiles() -> List[dict]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM search_profiles WHERE active = 1 ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]


def create_profile(profile: dict) -> int:
    with db_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO search_profiles (name, query, category_id, max_price, min_price, active, custom_threshold)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                profile["name"],
                profile["query"],
                profile.get("category_id"),
                profile.get("max_price"),
                profile.get("min_price"),
                1 if profile.get("active", True) else 0,
                profile.get("custom_threshold"),
            ),
        )
        return cursor.lastrowid


def update_profile(profile_id: int, updates: dict):
    fields = []
    params = []
    for key in ("name", "query", "category_id", "max_price", "min_price", "active", "custom_threshold"):
        if key in updates:
            fields.append(f"{key} = ?")
            val = updates[key]
            if key == "active":
                val = 1 if val else 0
            params.append(val)
    if not fields:
        return
    params.append(profile_id)
    with db_conn() as conn:
        conn.execute(
            f"UPDATE search_profiles SET {', '.join(fields)} WHERE id = ?", params
        )


def delete_profile(profile_id: int):
    with db_conn() as conn:
        conn.execute("DELETE FROM search_profiles WHERE id = ?", (profile_id,))


def get_blacklist() -> List[dict]:
    with db_conn() as conn:
        rows = conn.execute("SELECT * FROM blacklist ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]


def is_blacklisted(seller_id: str) -> bool:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT seller_id FROM blacklist WHERE seller_id = ?", (seller_id,)
        ).fetchone()
        return row is not None


def add_to_blacklist(seller_id: str, reason: Optional[str] = None):
    with db_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO blacklist (seller_id, reason, added_at) VALUES (?, ?, ?)",
            (seller_id, reason, datetime.utcnow()),
        )


def remove_from_blacklist(seller_id: str):
    with db_conn() as conn:
        conn.execute("DELETE FROM blacklist WHERE seller_id = ?", (seller_id,))


def get_seller_listing_count(seller_id: str) -> int:
    with db_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) FROM listings WHERE seller_id = ?
               AND seen_at >= datetime('now', '-7 days')""",
            (seller_id,),
        ).fetchone()
        return row[0] if row else 0


def get_stats() -> dict:
    with db_conn() as conn:
        today_seen = conn.execute(
            "SELECT COUNT(*) FROM listings WHERE seen_at >= date('now')"
        ).fetchone()[0]
        today_alerts = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE alerted_at >= date('now')"
        ).fetchone()[0]
        week_alerts = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE alerted_at >= date('now', '-7 days')"
        ).fetchone()[0]
        total_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        best_margin = conn.execute(
            """SELECT MAX(expected_profit) FROM alerts WHERE alerted_at >= date('now')"""
        ).fetchone()[0]
        total_profit = conn.execute(
            """SELECT COALESCE(SUM(expected_profit), 0) FROM alerts
               WHERE user_action = 'interested'"""
        ).fetchone()[0]
        top_terms = conn.execute(
            """SELECT search_term, COUNT(*) as cnt FROM price_history
               WHERE seen_at >= date('now', '-7 days')
               GROUP BY search_term ORDER BY cnt DESC LIMIT 5"""
        ).fetchall()
        return {
            "today_seen": today_seen,
            "today_alerts": today_alerts,
            "week_alerts": week_alerts,
            "total_alerts": total_alerts,
            "best_margin_today": best_margin,
            "total_profit_interested": total_profit,
            "top_search_terms": [dict(r) for r in top_terms],
        }
