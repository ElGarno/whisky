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

    # Whisky cards - consistent card definitions for all users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whisky_cards (
            id INTEGER PRIMARY KEY,
            whisky_id INTEGER UNIQUE,
            card_rarity VARCHAR DEFAULT 'common',
            card_design JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # User unlocked cards - tracks which cards each user has unlocked
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_cards (
            id INTEGER PRIMARY KEY,
            user_name VARCHAR,
            card_id INTEGER,
            whisky_id INTEGER,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rating_id INTEGER,
            UNIQUE(user_name, whisky_id)
        )
    """)

    # Achievement definitions
    conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY,
            code VARCHAR UNIQUE,
            name VARCHAR,
            description TEXT,
            icon VARCHAR,
            category VARCHAR,
            requirement_type VARCHAR,
            requirement_value INTEGER,
            requirement_extra JSON,
            points INTEGER DEFAULT 10
        )
    """)

    # User unlocked achievements
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            id INTEGER PRIMARY KEY,
            user_name VARCHAR,
            achievement_id INTEGER,
            unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            progress INTEGER DEFAULT 0,
            UNIQUE(user_name, achievement_id)
        )
    """)

    # Barcode mapping - maps EAN barcodes to whiskies
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whisky_barcodes (
            id INTEGER PRIMARY KEY,
            barcode VARCHAR UNIQUE,
            whisky_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Initialize default achievements if empty
    _init_default_achievements(conn)

    conn.close()


def _init_default_achievements(conn):
    """Initialize default achievement definitions."""
    existing = conn.execute("SELECT COUNT(*) FROM achievements").fetchone()[0]
    if existing > 0:
        return

    achievements = [
        # First steps
        (1, 'first_taste', 'Erster Schluck', 'Probiere deinen ersten Whisky', '🥃', 'beginner', 'total_tastings', 1, None, 10),
        (2, 'getting_started', 'Einsteiger', 'Probiere 5 verschiedene Whiskys', '🌟', 'beginner', 'total_tastings', 5, None, 25),
        (3, 'enthusiast', 'Enthusiast', 'Probiere 25 verschiedene Whiskys', '⭐', 'collector', 'total_tastings', 25, None, 100),
        (4, 'connoisseur', 'Kenner', 'Probiere 50 verschiedene Whiskys', '🏆', 'collector', 'total_tastings', 50, None, 250),
        (5, 'master', 'Meister', 'Probiere 100 verschiedene Whiskys', '👑', 'collector', 'total_tastings', 100, None, 500),

        # Region specialists
        (10, 'islay_explorer', 'Islay Entdecker', 'Probiere 5 Whiskys aus Islay', '🏝️', 'region', 'region_count', 5, '{"region": "Islay"}', 50),
        (11, 'islay_master', 'Islay Meister', 'Probiere 15 Whiskys aus Islay', '🔥', 'region', 'region_count', 15, '{"region": "Islay"}', 150),
        (12, 'speyside_explorer', 'Speyside Entdecker', 'Probiere 5 Whiskys aus Speyside', '🌸', 'region', 'region_count', 5, '{"region": "Speyside"}', 50),
        (13, 'speyside_master', 'Speyside Meister', 'Probiere 15 Whiskys aus Speyside', '🍯', 'region', 'region_count', 15, '{"region": "Speyside"}', 150),
        (14, 'highland_explorer', 'Highland Entdecker', 'Probiere 5 Whiskys aus Highland', '⛰️', 'region', 'region_count', 5, '{"region": "Highland"}', 50),
        (15, 'lowland_explorer', 'Lowland Entdecker', 'Probiere 5 Whiskys aus Lowland', '🌾', 'region', 'region_count', 5, '{"region": "Lowland"}', 50),
        (16, 'campbeltown_explorer', 'Campbeltown Entdecker', 'Probiere 3 Whiskys aus Campbeltown', '⚓', 'region', 'region_count', 3, '{"region": "Campbeltown"}', 75),
        (17, 'islands_explorer', 'Inseln Entdecker', 'Probiere 5 Whiskys von den Inseln', '🌊', 'region', 'region_count', 5, '{"region": "Islands"}', 50),

        # Diversity achievements
        (20, 'world_traveler', 'Weltreisender', 'Probiere Whiskys aus 3 verschiedenen Regionen', '🌍', 'diversity', 'unique_regions', 3, None, 50),
        (21, 'globe_trotter', 'Globetrotter', 'Probiere Whiskys aus 5 verschiedenen Regionen', '✈️', 'diversity', 'unique_regions', 5, None, 100),
        (22, 'distillery_hopper', 'Brennerei-Hopper', 'Probiere Whiskys von 10 verschiedenen Brennereien', '🏭', 'diversity', 'unique_distilleries', 10, None, 75),
        (23, 'distillery_collector', 'Brennerei-Sammler', 'Probiere Whiskys von 25 verschiedenen Brennereien', '🗺️', 'diversity', 'unique_distilleries', 25, None, 200),

        # Time-based achievements
        (30, 'monthly_taster', 'Monatlicher Verkoster', 'Probiere 5 verschiedene Whiskys in einem Monat', '📅', 'time', 'monthly_tastings', 5, None, 50),
        (31, 'weekly_warrior', 'Wöchentlicher Krieger', 'Probiere 3 verschiedene Whiskys in einer Woche', '⚔️', 'time', 'weekly_tastings', 3, None, 30),

        # Special achievements
        (40, 'vintage_hunter', 'Vintage Jäger', 'Probiere einen Whisky älter als 18 Jahre', '🎖️', 'special', 'whisky_age', 18, None, 75),
        (41, 'antique_collector', 'Antiquitäten-Sammler', 'Probiere einen Whisky älter als 25 Jahre', '🏺', 'special', 'whisky_age', 25, None, 150),
        (42, 'high_scorer', 'Hohe Ansprüche', 'Gib einem Whisky 10 Punkte', '💯', 'special', 'perfect_score', 1, None, 25),
        (43, 'critical_eye', 'Kritisches Auge', 'Bewerte 10 Whiskys mit detaillierten Notizen', '🔍', 'special', 'detailed_notes', 10, None, 50),
    ]

    for ach in achievements:
        conn.execute("""
            INSERT INTO achievements (id, code, name, description, icon, category, requirement_type, requirement_value, requirement_extra, points)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ach)


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


# Card operations
def get_or_create_card(whisky_id: int) -> int:
    """Get or create a card for a whisky. Returns card ID."""
    conn = get_connection()

    result = conn.execute(
        "SELECT id FROM whisky_cards WHERE whisky_id = ?", [whisky_id]
    ).fetchone()

    if result:
        conn.close()
        return result[0]

    # Create new card with rarity based on whisky properties
    whisky = get_whisky(whisky_id)
    if whisky:
        # Determine rarity based on price and age
        price = whisky[5] or 0
        year = whisky[2] or 2020
        age = 2024 - year if year else 0

        if price > 200 or age > 25:
            rarity = 'legendary'
        elif price > 100 or age > 18:
            rarity = 'epic'
        elif price > 50 or age > 12:
            rarity = 'rare'
        else:
            rarity = 'common'
    else:
        rarity = 'common'

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM whisky_cards").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO whisky_cards (id, whisky_id, card_rarity)
        VALUES (?, ?, ?)
    """, [new_id, whisky_id, rarity])

    conn.close()
    return new_id


def unlock_card(user_name: str, whisky_id: int, rating_id: int = None) -> tuple:
    """
    Unlock a card for a user. Returns (card_id, is_new_unlock, rarity).
    """
    conn = get_connection()

    # Check if already unlocked
    existing = conn.execute("""
        SELECT uc.id, wc.card_rarity FROM user_cards uc
        JOIN whisky_cards wc ON uc.card_id = wc.id
        WHERE uc.user_name = ? AND uc.whisky_id = ?
    """, [user_name, whisky_id]).fetchone()

    if existing:
        conn.close()
        return (existing[0], False, existing[1])

    # Get or create the card
    card_id = get_or_create_card(whisky_id)

    # Get card rarity
    rarity = conn.execute(
        "SELECT card_rarity FROM whisky_cards WHERE id = ?", [card_id]
    ).fetchone()[0]

    # Unlock for user
    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM user_cards").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO user_cards (id, user_name, card_id, whisky_id, rating_id)
        VALUES (?, ?, ?, ?, ?)
    """, [new_id, user_name, card_id, whisky_id, rating_id])

    conn.close()
    return (card_id, True, rarity)


def get_user_cards(user_name: str) -> list:
    """Get all unlocked cards for a user."""
    conn = get_connection()
    result = conn.execute("""
        SELECT
            uc.id, uc.whisky_id, wc.card_rarity, uc.unlocked_at,
            w.name as whisky_name, d.name as distillery, d.region,
            w.year, w.image_path
        FROM user_cards uc
        JOIN whisky_cards wc ON uc.card_id = wc.id
        JOIN whiskies w ON uc.whisky_id = w.id
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        WHERE uc.user_name = ?
        ORDER BY uc.unlocked_at DESC
    """, [user_name]).fetchall()
    conn.close()
    return result


def get_user_card_stats(user_name: str) -> dict:
    """Get card statistics for a user."""
    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM user_cards WHERE user_name = ?", [user_name]
    ).fetchone()[0]

    by_rarity = conn.execute("""
        SELECT wc.card_rarity, COUNT(*)
        FROM user_cards uc
        JOIN whisky_cards wc ON uc.card_id = wc.id
        WHERE uc.user_name = ?
        GROUP BY wc.card_rarity
    """, [user_name]).fetchall()

    all_whiskies = conn.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]

    conn.close()

    return {
        'total': total,
        'all_whiskies': all_whiskies,
        'by_rarity': dict(by_rarity)
    }


# Achievement operations
def get_all_achievements() -> list:
    """Get all achievement definitions."""
    conn = get_connection()
    result = conn.execute("""
        SELECT id, code, name, description, icon, category,
               requirement_type, requirement_value, requirement_extra, points
        FROM achievements
        ORDER BY category, points
    """).fetchall()
    conn.close()
    return result


def get_user_achievements(user_name: str) -> list:
    """Get all unlocked achievements for a user."""
    conn = get_connection()
    result = conn.execute("""
        SELECT
            ua.id, a.code, a.name, a.description, a.icon,
            a.category, a.points, ua.unlocked_at, ua.progress
        FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.id
        WHERE ua.user_name = ?
        ORDER BY ua.unlocked_at DESC
    """, [user_name]).fetchall()
    conn.close()
    return result


def get_user_achievement_progress(user_name: str) -> list:
    """Get achievement progress for a user (including not-yet-unlocked)."""
    conn = get_connection()
    result = conn.execute("""
        SELECT
            a.id, a.code, a.name, a.description, a.icon, a.category,
            a.requirement_type, a.requirement_value, a.requirement_extra, a.points,
            ua.unlocked_at, COALESCE(ua.progress, 0) as progress
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_name = ?
        ORDER BY a.category, a.points
    """, [user_name]).fetchall()
    conn.close()
    return result


def unlock_achievement(user_name: str, achievement_id: int) -> bool:
    """Unlock an achievement for a user. Returns True if newly unlocked."""
    conn = get_connection()

    # Check if already unlocked
    existing = conn.execute("""
        SELECT id FROM user_achievements
        WHERE user_name = ? AND achievement_id = ? AND unlocked_at IS NOT NULL
    """, [user_name, achievement_id]).fetchone()

    if existing:
        conn.close()
        return False

    # Check for existing progress entry
    progress_entry = conn.execute("""
        SELECT id FROM user_achievements
        WHERE user_name = ? AND achievement_id = ?
    """, [user_name, achievement_id]).fetchone()

    if progress_entry:
        conn.execute("""
            UPDATE user_achievements
            SET unlocked_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, [progress_entry[0]])
    else:
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM user_achievements").fetchone()[0]
        new_id = max_id + 1

        conn.execute("""
            INSERT INTO user_achievements (id, user_name, achievement_id, unlocked_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, [new_id, user_name, achievement_id])

    conn.close()
    return True


def update_achievement_progress(user_name: str, achievement_id: int, progress: int):
    """Update progress for an achievement."""
    conn = get_connection()

    existing = conn.execute("""
        SELECT id FROM user_achievements
        WHERE user_name = ? AND achievement_id = ?
    """, [user_name, achievement_id]).fetchone()

    if existing:
        conn.execute("""
            UPDATE user_achievements SET progress = ? WHERE id = ?
        """, [progress, existing[0]])
    else:
        max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM user_achievements").fetchone()[0]
        new_id = max_id + 1

        conn.execute("""
            INSERT INTO user_achievements (id, user_name, achievement_id, progress)
            VALUES (?, ?, ?, ?)
        """, [new_id, user_name, achievement_id, progress])

    conn.close()


def get_user_tasting_stats(user_name: str) -> dict:
    """Get tasting statistics for achievement checking."""
    conn = get_connection()

    # Total unique whiskies tasted
    total_tastings = conn.execute("""
        SELECT COUNT(DISTINCT whisky_id) FROM ratings WHERE participant_name = ?
    """, [user_name]).fetchone()[0]

    # Unique regions
    unique_regions = conn.execute("""
        SELECT COUNT(DISTINCT d.region)
        FROM ratings r
        JOIN whiskies w ON r.whisky_id = w.id
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        WHERE r.participant_name = ? AND d.region IS NOT NULL
    """, [user_name]).fetchone()[0]

    # Unique distilleries
    unique_distilleries = conn.execute("""
        SELECT COUNT(DISTINCT w.distillery_id)
        FROM ratings r
        JOIN whiskies w ON r.whisky_id = w.id
        WHERE r.participant_name = ?
    """, [user_name]).fetchone()[0]

    # Region counts
    region_counts = conn.execute("""
        SELECT d.region, COUNT(DISTINCT r.whisky_id) as count
        FROM ratings r
        JOIN whiskies w ON r.whisky_id = w.id
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        WHERE r.participant_name = ? AND d.region IS NOT NULL
        GROUP BY d.region
    """, [user_name]).fetchall()

    # Monthly tastings (current month)
    monthly_tastings = conn.execute("""
        SELECT COUNT(DISTINCT whisky_id)
        FROM ratings
        WHERE participant_name = ?
        AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
    """, [user_name]).fetchone()[0]

    # Weekly tastings (current week)
    weekly_tastings = conn.execute("""
        SELECT COUNT(DISTINCT whisky_id)
        FROM ratings
        WHERE participant_name = ?
        AND created_at >= DATE_TRUNC('week', CURRENT_DATE)
    """, [user_name]).fetchone()[0]

    # Max whisky age tasted
    max_age = conn.execute("""
        SELECT MAX(2024 - w.year)
        FROM ratings r
        JOIN whiskies w ON r.whisky_id = w.id
        WHERE r.participant_name = ? AND w.year IS NOT NULL
    """, [user_name]).fetchone()[0] or 0

    # Perfect scores (10)
    perfect_scores = conn.execute("""
        SELECT COUNT(*) FROM ratings
        WHERE participant_name = ? AND score = 10
    """, [user_name]).fetchone()[0]

    # Detailed notes count
    detailed_notes = conn.execute("""
        SELECT COUNT(*) FROM ratings
        WHERE participant_name = ? AND notes IS NOT NULL AND LENGTH(notes) > 20
    """, [user_name]).fetchone()[0]

    conn.close()

    return {
        'total_tastings': total_tastings,
        'unique_regions': unique_regions,
        'unique_distilleries': unique_distilleries,
        'region_counts': dict(region_counts),
        'monthly_tastings': monthly_tastings,
        'weekly_tastings': weekly_tastings,
        'max_age': max_age,
        'perfect_scores': perfect_scores,
        'detailed_notes': detailed_notes
    }


def check_and_unlock_achievements(user_name: str) -> list:
    """Check all achievements and unlock any that are completed. Returns list of newly unlocked."""
    import json

    stats = get_user_tasting_stats(user_name)
    achievements = get_all_achievements()
    newly_unlocked = []

    for ach in achievements:
        ach_id, code, name, desc, icon, category, req_type, req_value, req_extra, points = ach

        # Check if already unlocked
        conn = get_connection()
        already_unlocked = conn.execute("""
            SELECT 1 FROM user_achievements
            WHERE user_name = ? AND achievement_id = ? AND unlocked_at IS NOT NULL
        """, [user_name, ach_id]).fetchone()
        conn.close()

        if already_unlocked:
            continue

        # Check requirements
        unlocked = False
        progress = 0

        if req_type == 'total_tastings':
            progress = stats['total_tastings']
            unlocked = progress >= req_value

        elif req_type == 'unique_regions':
            progress = stats['unique_regions']
            unlocked = progress >= req_value

        elif req_type == 'unique_distilleries':
            progress = stats['unique_distilleries']
            unlocked = progress >= req_value

        elif req_type == 'region_count':
            extra = json.loads(req_extra) if req_extra else {}
            region = extra.get('region', '')
            progress = stats['region_counts'].get(region, 0)
            unlocked = progress >= req_value

        elif req_type == 'monthly_tastings':
            progress = stats['monthly_tastings']
            unlocked = progress >= req_value

        elif req_type == 'weekly_tastings':
            progress = stats['weekly_tastings']
            unlocked = progress >= req_value

        elif req_type == 'whisky_age':
            progress = stats['max_age']
            unlocked = progress >= req_value

        elif req_type == 'perfect_score':
            progress = stats['perfect_scores']
            unlocked = progress >= req_value

        elif req_type == 'detailed_notes':
            progress = stats['detailed_notes']
            unlocked = progress >= req_value

        # Update progress
        update_achievement_progress(user_name, ach_id, progress)

        # Unlock if completed
        if unlocked:
            unlock_achievement(user_name, ach_id)
            newly_unlocked.append({
                'id': ach_id,
                'code': code,
                'name': name,
                'description': desc,
                'icon': icon,
                'points': points
            })

    return newly_unlocked


def get_user_total_points(user_name: str) -> int:
    """Get total achievement points for a user."""
    conn = get_connection()
    result = conn.execute("""
        SELECT COALESCE(SUM(a.points), 0)
        FROM user_achievements ua
        JOIN achievements a ON ua.achievement_id = a.id
        WHERE ua.user_name = ? AND ua.unlocked_at IS NOT NULL
    """, [user_name]).fetchone()[0]
    conn.close()
    return result


# Barcode operations
def get_whisky_by_barcode(barcode: str) -> tuple | None:
    """Get whisky by EAN barcode."""
    conn = get_connection()
    result = conn.execute("""
        SELECT w.id, w.name, w.year, d.name as distillery, d.id as distillery_id,
               w.price, w.current_fill_ml, w.bottle_size_ml, w.image_path, w.info_markdown
        FROM whisky_barcodes wb
        JOIN whiskies w ON wb.whisky_id = w.id
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        WHERE wb.barcode = ?
    """, [barcode]).fetchone()
    conn.close()
    return result


def add_whisky_barcode(barcode: str, whisky_id: int):
    """Add a barcode mapping for a whisky."""
    conn = get_connection()

    max_id = conn.execute("SELECT COALESCE(MAX(id), 0) FROM whisky_barcodes").fetchone()[0]
    new_id = max_id + 1

    conn.execute("""
        INSERT INTO whisky_barcodes (id, barcode, whisky_id)
        VALUES (?, ?, ?)
        ON CONFLICT (barcode) DO UPDATE SET whisky_id = ?
    """, [new_id, barcode, whisky_id, whisky_id])

    conn.close()


def get_all_barcodes() -> list:
    """Get all barcode mappings."""
    conn = get_connection()
    result = conn.execute("""
        SELECT wb.barcode, w.id, w.name, d.name as distillery
        FROM whisky_barcodes wb
        JOIN whiskies w ON wb.whisky_id = w.id
        LEFT JOIN distilleries d ON w.distillery_id = d.id
        ORDER BY w.name
    """).fetchall()
    conn.close()
    return result


# Initialize on import
init_db()
