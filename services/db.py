"""DuckDB database operations for the Whisky app."""

import duckdb
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent.parent / "data" / "whisky.duckdb"


def get_connection():
    """Get a DuckDB connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def init_db():
    """Initialize database schema."""
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS distilleries (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE,
            region VARCHAR,
            country VARCHAR,
            latitude DOUBLE,
            longitude DOUBLE,
            logo_path VARCHAR
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS whiskies (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            year INTEGER,
            distillery_id INTEGER,
            price DECIMAL(10,2),
            current_fill_ml INTEGER,
            bottle_size_ml INTEGER DEFAULT 700,
            image_path VARCHAR,
            info_markdown TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tastings (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            date DATE,
            whisky_ids INTEGER[],
            order_explanation TEXT,
            participants VARCHAR[],
            summary_markdown TEXT,
            status VARCHAR DEFAULT 'active'
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY,
            tasting_id INTEGER,
            whisky_id INTEGER,
            participant_name VARCHAR,
            score DECIMAL(3,1),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.close()


# Distillery operations
def get_or_create_distillery(name: str, region: str = None, country: str = None,
                              latitude: float = None, longitude: float = None) -> int:
    """Get existing distillery or create new one. Returns distillery ID."""
    conn = get_connection()

    result = conn.execute(
        "SELECT id FROM distilleries WHERE name = ?", [name]
    ).fetchone()

    if result:
        conn.close()
        return result[0]

    # Get next ID
    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM distilleries").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO distilleries (id, name, region, country, latitude, longitude)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [new_id, name, region, country, latitude, longitude])

    conn.close()
    return new_id


def get_all_distilleries():
    """Get all distilleries with coordinates."""
    conn = get_connection()
    result = conn.execute("""
        SELECT id, name, region, country, latitude, longitude, logo_path
        FROM distilleries
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """).fetchall()
    conn.close()
    return result


def update_distillery_location(distillery_id: int, latitude: float, longitude: float):
    """Update distillery coordinates."""
    conn = get_connection()
    conn.execute("""
        UPDATE distilleries SET latitude = ?, longitude = ? WHERE id = ?
    """, [latitude, longitude, distillery_id])
    conn.close()


# Whisky operations
def add_whisky(name: str, year: int, distillery_id: int, price: float = None,
               current_fill_ml: int = 700, bottle_size_ml: int = 700,
               image_path: str = None) -> int:
    """Add a new whisky. Returns whisky ID."""
    conn = get_connection()

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM whiskies").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO whiskies (id, name, year, distillery_id, price, current_fill_ml,
                              bottle_size_ml, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [new_id, name, year, distillery_id, price, current_fill_ml, bottle_size_ml, image_path])

    conn.close()
    return new_id


def get_all_whiskies():
    """Get all whiskies with distillery info."""
    conn = get_connection()
    result = conn.execute("""
        SELECT w.id, w.name, w.year, d.name as distillery, w.price,
               w.current_fill_ml, w.bottle_size_ml, w.image_path, w.info_markdown
        FROM whiskies w
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        ORDER BY w.created_at DESC
    """).fetchall()
    conn.close()
    return result


def get_whisky(whisky_id: int):
    """Get a single whisky by ID."""
    conn = get_connection()
    result = conn.execute("""
        SELECT w.id, w.name, w.year, d.name as distillery, d.id as distillery_id,
               w.price, w.current_fill_ml, w.bottle_size_ml, w.image_path, w.info_markdown
        FROM whiskies w
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        WHERE w.id = ?
    """, [whisky_id]).fetchone()
    conn.close()
    return result


def update_whisky_info(whisky_id: int, info_markdown: str):
    """Update whisky info markdown."""
    conn = get_connection()
    conn.execute("""
        UPDATE whiskies SET info_markdown = ? WHERE id = ?
    """, [info_markdown, whisky_id])
    conn.close()


def update_whisky_fill(whisky_id: int, fill_ml: int):
    """Update whisky fill level."""
    conn = get_connection()
    conn.execute("""
        UPDATE whiskies SET current_fill_ml = ? WHERE id = ?
    """, [fill_ml, whisky_id])
    conn.close()


def update_whisky(whisky_id: int, name: str = None, year: int = None,
                  price: float = None, fill_ml: int = None):
    """Update whisky details."""
    conn = get_connection()
    if name is not None:
        conn.execute("UPDATE whiskies SET name = ? WHERE id = ?", [name, whisky_id])
    if year is not None:
        conn.execute("UPDATE whiskies SET year = ? WHERE id = ?", [year, whisky_id])
    if price is not None:
        conn.execute("UPDATE whiskies SET price = ? WHERE id = ?", [price, whisky_id])
    if fill_ml is not None:
        conn.execute("UPDATE whiskies SET current_fill_ml = ? WHERE id = ?", [fill_ml, whisky_id])
    conn.close()


def delete_whisky(whisky_id: int):
    """Delete a whisky from the collection."""
    conn = get_connection()
    conn.execute("DELETE FROM whiskies WHERE id = ?", [whisky_id])
    conn.close()


def get_whisky_stats():
    """Get statistics about the whisky collection."""
    conn = get_connection()

    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            COALESCE(SUM(price), 0) as total_value,
            COALESCE(MIN(price), 0) as min_price,
            COALESCE(MAX(price), 0) as max_price,
            COALESCE(AVG(price), 0) as avg_price,
            COALESCE(MIN(year), 0) as oldest_year,
            COALESCE(MAX(year), 0) as newest_year
        FROM whiskies
        WHERE price IS NOT NULL
    """).fetchone()

    conn.close()
    return stats


def get_age_distribution():
    """Get whisky count by age/year."""
    conn = get_connection()
    result = conn.execute("""
        SELECT year, COUNT(*) as count
        FROM whiskies
        WHERE year IS NOT NULL
        GROUP BY year
        ORDER BY year
    """).fetchall()
    conn.close()
    return result


def get_fill_levels():
    """Get fill level info for all whiskies."""
    conn = get_connection()
    result = conn.execute("""
        SELECT w.name, w.current_fill_ml, w.bottle_size_ml,
               ROUND(w.current_fill_ml * 100.0 / w.bottle_size_ml, 1) as fill_pct
        FROM whiskies w
        ORDER BY fill_pct ASC
    """).fetchall()
    conn.close()
    return result


# Tasting operations
def create_tasting(name: str, whisky_ids: list, participants: list,
                   order_explanation: str = None) -> int:
    """Create a new tasting session."""
    conn = get_connection()

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM tastings").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO tastings (id, name, date, whisky_ids, participants, order_explanation, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, [new_id, name, date.today(), whisky_ids, participants, order_explanation])

    conn.close()
    return new_id


def get_active_tasting():
    """Get the currently active tasting."""
    conn = get_connection()
    result = conn.execute("""
        SELECT id, name, date, whisky_ids, participants, order_explanation, summary_markdown
        FROM tastings
        WHERE status = 'active'
        ORDER BY date DESC
        LIMIT 1
    """).fetchone()
    conn.close()
    return result


def get_all_tastings():
    """Get all tastings."""
    conn = get_connection()
    result = conn.execute("""
        SELECT id, name, date, whisky_ids, participants, status, summary_markdown
        FROM tastings
        ORDER BY date DESC
    """).fetchall()
    conn.close()
    return result


def complete_tasting(tasting_id: int, summary_markdown: str):
    """Mark tasting as completed with AI summary."""
    conn = get_connection()
    conn.execute("""
        UPDATE tastings SET status = 'completed', summary_markdown = ? WHERE id = ?
    """, [summary_markdown, tasting_id])
    conn.close()


# Rating operations
def add_rating(tasting_id: int, whisky_id: int, participant_name: str,
               score: float, notes: str = None):
    """Add a rating for a whisky in a tasting."""
    conn = get_connection()

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM ratings").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO ratings (id, tasting_id, whisky_id, participant_name, score, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [new_id, tasting_id, whisky_id, participant_name, score, notes])

    conn.close()


def get_tasting_ratings(tasting_id: int):
    """Get all ratings for a tasting."""
    conn = get_connection()
    result = conn.execute("""
        SELECT r.id, r.whisky_id, w.name as whisky_name, r.participant_name, r.score, r.notes
        FROM ratings r
        JOIN whiskies w ON r.whisky_id = w.id
        WHERE r.tasting_id = ?
        ORDER BY w.name, r.participant_name
    """, [tasting_id]).fetchall()
    conn.close()
    return result


def get_rating_exists(tasting_id: int, whisky_id: int, participant_name: str) -> bool:
    """Check if a rating already exists."""
    conn = get_connection()
    result = conn.execute("""
        SELECT 1 FROM ratings
        WHERE tasting_id = ? AND whisky_id = ? AND participant_name = ?
    """, [tasting_id, whisky_id, participant_name]).fetchone()
    conn.close()
    return result is not None


# Initialize on import
init_db()
