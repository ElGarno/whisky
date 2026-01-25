"""DuckDB database operations for the Whisky app."""

import duckdb
import random
import string
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
            quantity INTEGER DEFAULT 1,
            current_fill_ml INTEGER,
            bottle_size_ml INTEGER DEFAULT 700,
            image_path VARCHAR,
            info_markdown TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: add quantity column if it doesn't exist
    try:
        conn.execute("ALTER TABLE whiskies ADD COLUMN quantity INTEGER DEFAULT 1")
    except:
        pass  # Column already exists

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasting_participants (
            id INTEGER PRIMARY KEY,
            tasting_id INTEGER,
            participant_name VARCHAR,
            pin_code VARCHAR(4),
            UNIQUE(tasting_id, participant_name),
            UNIQUE(tasting_id, pin_code)
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
               quantity: int = 1, current_fill_ml: int = 700, bottle_size_ml: int = 700,
               image_path: str = None) -> int:
    """Add a new whisky. Returns whisky ID."""
    conn = get_connection()

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM whiskies").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO whiskies (id, name, year, distillery_id, price, quantity, current_fill_ml,
                              bottle_size_ml, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [new_id, name, year, distillery_id, price, quantity, current_fill_ml, bottle_size_ml, image_path])

    conn.close()
    return new_id


def get_all_whiskies():
    """Get all whiskies with distillery info."""
    conn = get_connection()
    result = conn.execute("""
        SELECT w.id, w.name, w.year, d.name as distillery, w.price,
               w.current_fill_ml, w.bottle_size_ml, w.image_path, w.info_markdown,
               COALESCE(w.quantity, 1) as quantity
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
               w.price, w.current_fill_ml, w.bottle_size_ml, w.image_path, w.info_markdown,
               COALESCE(w.quantity, 1) as quantity
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
                  price: float = None, fill_ml: int = None, quantity: int = None):
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
    if quantity is not None:
        conn.execute("UPDATE whiskies SET quantity = ? WHERE id = ?", [quantity, whisky_id])
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
            COALESCE(SUM(COALESCE(quantity, 1)), 0) as total_bottles,
            COALESCE(SUM(price * COALESCE(quantity, 1)), 0) as total_value,
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


def get_whiskies_for_random_selection(attendee_count: int) -> list[tuple]:
    """
    Get whiskies eligible for random tasting selection.

    Args:
        attendee_count: Number of tasting attendees

    Returns:
        List of whisky tuples: (id, name, year, distillery, price,
                                current_fill_ml, bottle_size_ml, fill_pct)

    Business Logic:
        - If attendees > 5: exclude whiskies with fill_pct < 25%
        - Otherwise: include all whiskies
    """
    conn = get_connection()

    # Use separate queries to avoid string interpolation (SQL injection prevention)
    if attendee_count > 5:
        result = conn.execute("""
            SELECT
                w.id,
                w.name,
                w.year,
                d.name as distillery,
                w.price,
                w.current_fill_ml,
                w.bottle_size_ml,
                ROUND(w.current_fill_ml * 100.0 / NULLIF(w.bottle_size_ml, 0), 1) as fill_pct
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.id
            WHERE w.bottle_size_ml > 0
              AND (w.current_fill_ml * 100.0 / NULLIF(w.bottle_size_ml, 0)) >= 25
            ORDER BY w.created_at DESC
        """).fetchall()
    else:
        result = conn.execute("""
            SELECT
                w.id,
                w.name,
                w.year,
                d.name as distillery,
                w.price,
                w.current_fill_ml,
                w.bottle_size_ml,
                ROUND(w.current_fill_ml * 100.0 / NULLIF(w.bottle_size_ml, 0), 1) as fill_pct
            FROM whiskies w
            LEFT JOIN distilleries d ON w.distillery_id = d.id
            WHERE w.bottle_size_ml > 0
            ORDER BY w.created_at DESC
        """).fetchall()

    conn.close()
    return result


def get_participant_analytics():
    """
    Get analytics for all participants across all tastings.

    Returns:
        List of tuples: (participant_name, total_ratings, avg_score, min_score, max_score, score_stddev)
    """
    conn = get_connection()
    result = conn.execute("""
        SELECT
            participant_name,
            COUNT(*) as total_ratings,
            ROUND(AVG(score), 2) as avg_score,
            MIN(score) as min_score,
            MAX(score) as max_score,
            ROUND(STDDEV_SAMP(score), 2) as score_stddev
        FROM ratings
        GROUP BY participant_name
        ORDER BY total_ratings DESC
    """).fetchall()
    conn.close()
    return result


def get_participant_ratings(participant_name: str):
    """
    Get all ratings for a specific participant.

    Returns:
        List of tuples: (whisky_name, distillery, score, notes, tasting_name, date)
    """
    conn = get_connection()
    result = conn.execute("""
        SELECT
            w.name as whisky_name,
            d.name as distillery,
            r.score,
            r.notes,
            t.name as tasting_name,
            t.date
        FROM ratings r
        JOIN whiskies w ON r.whisky_id = w.id
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        JOIN tastings t ON r.tasting_id = t.id
        WHERE r.participant_name = ?
        ORDER BY r.score DESC
    """, [participant_name]).fetchall()
    conn.close()
    return result


def get_all_participants():
    """Get list of all unique participant names."""
    conn = get_connection()
    result = conn.execute("""
        SELECT DISTINCT participant_name
        FROM ratings
        ORDER BY participant_name
    """).fetchall()
    conn.close()
    return [r[0] for r in result]


def get_whiskies_with_regions():
    """Get all whiskies with their region information for collection health analysis."""
    conn = get_connection()
    result = conn.execute("""
        SELECT
            w.id,
            w.name,
            d.name as distillery,
            d.region,
            w.year,
            w.price,
            ROUND(w.current_fill_ml * 100.0 / NULLIF(w.bottle_size_ml, 0), 1) as fill_pct
        FROM whiskies w
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        ORDER BY w.created_at DESC
    """).fetchall()
    conn.close()
    return result


def add_guest_rating(whisky_id: int, guest_name: str, score: float, notes: str = None):
    """
    Add a guest rating (not associated with a tasting).
    Uses tasting_id = 0 to mark as guest rating.
    """
    conn = get_connection()

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM ratings").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO ratings (id, tasting_id, whisky_id, participant_name, score, notes)
        VALUES (?, 0, ?, ?, ?, ?)
    """, [new_id, whisky_id, guest_name, score, notes])

    conn.close()


def get_guest_ratings(whisky_id: int):
    """Get all guest ratings for a specific whisky."""
    conn = get_connection()
    result = conn.execute("""
        SELECT participant_name, score, notes, created_at
        FROM ratings
        WHERE whisky_id = ? AND tasting_id = 0
        ORDER BY created_at DESC
    """, [whisky_id]).fetchall()
    conn.close()
    return result


def get_whisky_avg_rating(whisky_id: int):
    """Get average rating for a whisky across all ratings."""
    conn = get_connection()
    result = conn.execute("""
        SELECT
            ROUND(AVG(score), 1) as avg_score,
            COUNT(*) as rating_count
        FROM ratings
        WHERE whisky_id = ?
    """, [whisky_id]).fetchone()
    conn.close()
    return result


# Tasting participant PIN operations
def create_participant_pins(tasting_id: int, participants: list) -> dict:
    """
    Create unique 4-digit PINs for tasting participants.

    Args:
        tasting_id: The tasting ID
        participants: List of participant names

    Returns:
        Dict mapping participant names to their PINs
    """
    conn = get_connection()
    pins = {}
    used_pins = set()

    for participant in participants:
        # Generate unique 4-digit PIN
        while True:
            pin = ''.join(random.choices(string.digits, k=4))
            if pin not in used_pins:
                used_pins.add(pin)
                break

        max_id = conn.execute(
            "SELECT COALESCE(MAX(id), 0) FROM tasting_participants"
        ).fetchone()[0]
        new_id = max_id + 1

        conn.execute("""
            INSERT INTO tasting_participants (id, tasting_id, participant_name, pin_code)
            VALUES (?, ?, ?, ?)
        """, [new_id, tasting_id, participant, pin])

        pins[participant] = pin

    conn.close()
    return pins


def validate_participant_pin(tasting_id: int, pin_code: str) -> str | None:
    """
    Validate a PIN for a tasting and return the participant name.

    Args:
        tasting_id: The tasting ID
        pin_code: The 4-digit PIN

    Returns:
        Participant name if valid, None otherwise
    """
    conn = get_connection()
    result = conn.execute("""
        SELECT participant_name
        FROM tasting_participants
        WHERE tasting_id = ? AND pin_code = ?
    """, [tasting_id, pin_code]).fetchone()
    conn.close()

    return result[0] if result else None


def get_participant_pins(tasting_id: int) -> list[tuple]:
    """
    Get all participant PINs for a tasting.

    Args:
        tasting_id: The tasting ID

    Returns:
        List of tuples: (participant_name, pin_code)
    """
    conn = get_connection()
    result = conn.execute("""
        SELECT participant_name, pin_code
        FROM tasting_participants
        WHERE tasting_id = ?
        ORDER BY participant_name
    """, [tasting_id]).fetchall()
    conn.close()
    return result


def delete_tasting_ratings(tasting_id: int) -> int:
    """
    Delete all ratings for a specific tasting.

    Args:
        tasting_id: The tasting ID

    Returns:
        Number of deleted ratings
    """
    conn = get_connection()
    # Count ratings before deletion
    count = conn.execute(
        "SELECT COUNT(*) FROM ratings WHERE tasting_id = ?", [tasting_id]
    ).fetchone()[0]

    conn.execute("DELETE FROM ratings WHERE tasting_id = ?", [tasting_id])
    conn.close()
    return count


def delete_tasting(tasting_id: int):
    """
    Delete a tasting and all associated data (ratings, participants).

    Args:
        tasting_id: The tasting ID
    """
    conn = get_connection()
    conn.execute("DELETE FROM ratings WHERE tasting_id = ?", [tasting_id])
    conn.execute("DELETE FROM tasting_participants WHERE tasting_id = ?", [tasting_id])
    conn.execute("DELETE FROM tastings WHERE id = ?", [tasting_id])
    conn.close()


def get_tasting(tasting_id: int):
    """Get a single tasting by ID."""
    conn = get_connection()
    result = conn.execute("""
        SELECT id, name, date, whisky_ids, participants, order_explanation, summary_markdown, status
        FROM tastings
        WHERE id = ?
    """, [tasting_id]).fetchone()
    conn.close()
    return result


# Initialize on import
init_db()
