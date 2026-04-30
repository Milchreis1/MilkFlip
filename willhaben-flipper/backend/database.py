import psycopg2
import psycopg2.extras
import logging
from datetime import datetime, timezone
from typing import Optional, List
from contextlib import contextmanager

from config import settings

logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(settings.DATABASE_URL)


@contextmanager
def db_conn():
    conn = get_connection()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                yield cur
    finally:
        conn.close()


def init_db():
    with db_conn() as cur:
        cur.execute("""
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
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id SERIAL PRIMARY KEY,
                search_term TEXT NOT NULL,
                price REAL NOT NULL,
                listing_id TEXT,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
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
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_profiles (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                query TEXT NOT NULL,
                category_id TEXT,
                max_price REAL,
                min_price REAL,
                active INTEGER DEFAULT 1,
                custom_threshold REAL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                seller_id TEXT PRIMARY KEY,
                reason TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                seller_id TEXT PRIMARY KEY,
                note TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_seen_at ON listings(seen_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_listings_seller_id ON listings(seller_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_history_search_term ON price_history(search_term)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_history_seen_at ON price_history(seen_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_listing_id ON alerts(listing_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_alerted_at ON alerts(alerted_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_score ON alerts(score)")
    logger.info("Database initialized")


def migrate():
    """Add new columns to existing tables if they don't exist."""
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

    with db_conn() as cur:
        for table, columns in migrations.items():
            cur.execute(
                """SELECT column_name FROM information_schema.columns
                   WHERE table_name = %s AND table_schema = 'public'""",
                (table,),
            )
            existing = {row["column_name"] for row in cur.fetchall()}
            for col_name, col_def in columns:
                if col_name not in existing:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                    logger.info(f"Migrated: added {col_name} to {table}")


def seed_default_profiles():
    with db_conn() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM search_profiles")
        count = cur.fetchone()["cnt"]
        if count == 0:
            cur.executemany(
                "INSERT INTO search_profiles (name, query, active) VALUES (%s, %s, 1)",
                [
                    ("Nintendo Switch", "Nintendo Switch"),
                    ("Lego Technic", "Lego Technic"),
                    ("iPhone", "iPhone"),
                ],
            )
            logger.info("Seeded 3 default search profiles")


def upsert_listing(listing: dict) -> bool:
    """Returns True if this is a new listing."""
    with db_conn() as cur:
        cur.execute("SELECT id FROM listings WHERE id = %s", (listing["id"],))
        existing = cur.fetchone()
        if existing:
            cur.execute(
                "UPDATE listings SET price=%s, seen_at=%s WHERE id=%s",
                (listing["price"], datetime.now(timezone.utc), listing["id"]),
            )
            return False
        cur.execute(
            """INSERT INTO listings
               (id, title, price, url, seller_id, seller_type, images_count, location, category, seen_at, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
                datetime.now(timezone.utc),
                "new",
            ),
        )
        return True


def add_price_history(search_term: str, price: float, listing_id: Optional[str] = None):
    with db_conn() as cur:
        cur.execute(
            "INSERT INTO price_history (search_term, price, listing_id, seen_at) VALUES (%s, %s, %s, %s)",
            (search_term, price, listing_id, datetime.now(timezone.utc)),
        )


def get_price_history(search_term: str, days: int = 30) -> List[dict]:
    with db_conn() as cur:
        cur.execute(
            """SELECT price, seen_at FROM price_history
               WHERE search_term = %s
               AND seen_at >= NOW() - INTERVAL '1 day' * %s
               ORDER BY seen_at ASC""",
            (search_term, days),
        )
        return [dict(r) for r in cur.fetchall()]


def get_price_history_by_listing(listing_id: str) -> List[dict]:
    with db_conn() as cur:
        cur.execute(
            """SELECT price, seen_at FROM price_history
               WHERE listing_id = %s
               ORDER BY seen_at ASC""",
            (listing_id,),
        )
        return [dict(r) for r in cur.fetchall()]


def was_recently_alerted(listing_id: str, cooldown_hours: int) -> bool:
    with db_conn() as cur:
        cur.execute(
            """SELECT id FROM alerts WHERE listing_id = %s
               AND alerted_at >= NOW() - INTERVAL '1 hour' * %s""",
            (listing_id, cooldown_hours),
        )
        return cur.fetchone() is not None


def save_alert(alert: dict):
    with db_conn() as cur:
        cur.execute(
            """INSERT INTO alerts
               (listing_id, title, price, url, score, expected_profit, rolling_average,
                price_delta_percent, location, images_count, age_minutes, alerted_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
                datetime.now(timezone.utc),
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
        filters.append("score >= %s")
        params.append(min_score)
    if date_from:
        filters.append("alerted_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("alerted_at <= %s")
        params.append(date_to)
    if user_action:
        filters.append("user_action = %s")
        params.append(user_action)

    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params += [page_size, page * page_size]

    with db_conn() as cur:
        cur.execute(
            f"SELECT * FROM alerts {where} ORDER BY alerted_at DESC LIMIT %s OFFSET %s",
            params,
        )
        return [dict(r) for r in cur.fetchall()]


def get_alert_by_id(alert_id: int) -> Optional[dict]:
    with db_conn() as cur:
        cur.execute("SELECT * FROM alerts WHERE id = %s", (alert_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_alert_action(alert_id: int, user_action: str):
    with db_conn() as cur:
        cur.execute(
            "UPDATE alerts SET user_action = %s WHERE id = %s",
            (user_action, alert_id),
        )


def get_profiles() -> List[dict]:
    with db_conn() as cur:
        cur.execute("SELECT * FROM search_profiles ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def get_active_profiles() -> List[dict]:
    with db_conn() as cur:
        cur.execute("SELECT * FROM search_profiles WHERE active = 1 ORDER BY id")
        return [dict(r) for r in cur.fetchall()]


def create_profile(profile: dict) -> int:
    with db_conn() as cur:
        cur.execute(
            """INSERT INTO search_profiles (name, query, category_id, max_price, min_price, active, custom_threshold)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
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
        return cur.fetchone()["id"]


def update_profile(profile_id: int, updates: dict):
    fields = []
    params = []
    for key in ("name", "query", "category_id", "max_price", "min_price", "active", "custom_threshold"):
        if key in updates:
            fields.append(f"{key} = %s")
            val = updates[key]
            if key == "active":
                val = 1 if val else 0
            params.append(val)
    if not fields:
        return
    params.append(profile_id)
    with db_conn() as cur:
        cur.execute(
            f"UPDATE search_profiles SET {', '.join(fields)} WHERE id = %s", params
        )


def delete_profile(profile_id: int):
    with db_conn() as cur:
        cur.execute("DELETE FROM search_profiles WHERE id = %s", (profile_id,))


def get_blacklist() -> List[dict]:
    with db_conn() as cur:
        cur.execute("SELECT * FROM blacklist ORDER BY added_at DESC")
        return [dict(r) for r in cur.fetchall()]


def is_blacklisted(seller_id: str) -> bool:
    with db_conn() as cur:
        cur.execute("SELECT seller_id FROM blacklist WHERE seller_id = %s", (seller_id,))
        return cur.fetchone() is not None


def add_to_blacklist(seller_id: str, reason: Optional[str] = None):
    with db_conn() as cur:
        cur.execute(
            "INSERT INTO blacklist (seller_id, reason, added_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (seller_id, reason, datetime.now(timezone.utc)),
        )


def remove_from_blacklist(seller_id: str):
    with db_conn() as cur:
        cur.execute("DELETE FROM blacklist WHERE seller_id = %s", (seller_id,))


def mark_listing_inactive(listing_id: str):
    with db_conn() as cur:
        cur.execute(
            "UPDATE listings SET status = 'inactive' WHERE id = %s",
            (listing_id,),
        )


def get_stale_active_listings(older_than_hours: int = 24) -> List[dict]:
    """Return listings that haven't been seen recently and are not yet inactive."""
    with db_conn() as cur:
        cur.execute(
            """SELECT id, url, title FROM listings
               WHERE seen_at < NOW() - INTERVAL '1 hour' * %s
               AND status != 'inactive'
               ORDER BY seen_at ASC
               LIMIT 100""",
            (older_than_hours,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_seller_listing_count(seller_id: str) -> int:
    with db_conn() as cur:
        cur.execute(
            """SELECT COUNT(*) AS cnt FROM listings WHERE seller_id = %s
               AND seen_at >= NOW() - INTERVAL '7 days'""",
            (seller_id,),
        )
        row = cur.fetchone()
        return row["cnt"] if row else 0


def get_stats() -> dict:
    with db_conn() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM listings WHERE seen_at >= CURRENT_DATE")
        today_seen = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) AS cnt FROM alerts WHERE alerted_at >= CURRENT_DATE")
        today_alerts = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) AS cnt FROM alerts WHERE alerted_at >= CURRENT_DATE - INTERVAL '7 days'")
        week_alerts = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(*) AS cnt FROM alerts")
        total_alerts = cur.fetchone()["cnt"]

        cur.execute("SELECT MAX(expected_profit) AS max_profit FROM alerts WHERE alerted_at >= CURRENT_DATE")
        best_margin = cur.fetchone()["max_profit"]

        cur.execute(
            "SELECT COALESCE(SUM(expected_profit), 0) AS total_profit FROM alerts WHERE user_action = 'interested'"
        )
        total_profit = cur.fetchone()["total_profit"]

        cur.execute(
            """SELECT search_term, COUNT(*) AS cnt FROM price_history
               WHERE seen_at >= CURRENT_DATE - INTERVAL '7 days'
               GROUP BY search_term ORDER BY cnt DESC LIMIT 5"""
        )
        top_terms = [dict(r) for r in cur.fetchall()]

        return {
            "today_seen": today_seen,
            "today_alerts": today_alerts,
            "week_alerts": week_alerts,
            "total_alerts": total_alerts,
            "best_margin_today": best_margin,
            "total_profit_interested": total_profit,
            "top_search_terms": top_terms,
        }
