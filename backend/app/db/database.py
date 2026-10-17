import sqlite3
from collections.abc import Generator
from pathlib import Path

from fastapi import Request

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "data" / "hostel.db"

STARTER_ROOMS = (
    (
        "Private room",
        "private",
        "Your own space to unwind and recharge.",
        12000,
        "A LITTLE MORE YOU-TIME",
    ),
    (
        "Shared room",
        "shared",
        "A friendly space with room for connection.",
        8500,
        "GOOD COMPANY INCLUDED",
    ),
    (
        "Corner suite",
        "suite",
        "A bit more space for all your next steps.",
        15000,
        "A LITTLE ROOM TO STRETCH",
    ),
)


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(
        database_path,
        timeout=5,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    room_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    monthly_rent INTEGER NOT NULL CHECK (monthly_rent >= 0),
                    available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1)),
                    tag TEXT NOT NULL
                )
                """
            )
            room_table = connection.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'rooms'"
            ).fetchone()["sql"]
            if "room_type TEXT NOT NULL UNIQUE" in room_table:
                connection.execute(
                    """
                    CREATE TABLE rooms_replacement (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        room_type TEXT NOT NULL,
                        description TEXT NOT NULL,
                        monthly_rent INTEGER NOT NULL CHECK (monthly_rent >= 0),
                        available INTEGER NOT NULL DEFAULT 1 CHECK (available IN (0, 1)),
                        tag TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO rooms_replacement
                    SELECT id, name, room_type, description, monthly_rent, available, tag
                    FROM rooms
                    """
                )
                connection.execute("DROP TABLE rooms")
                connection.execute("ALTER TABLE rooms_replacement RENAME TO rooms")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inquiries (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    phone TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('resident', 'admin')),
                    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    room_id INTEGER NOT NULL REFERENCES rooms(id),
                    move_in_date TEXT,
                    message TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'approved', 'rejected')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    amount INTEGER NOT NULL CHECK (amount > 0),
                    billing_period TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'due'
                        CHECK (status IN ('due', 'paid')),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS notices (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    author_id INTEGER NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS maintenance_requests (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open', 'in_progress', 'resolved')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            room_count = connection.execute(
                "SELECT COUNT(*) FROM rooms"
            ).fetchone()[0]
            if room_count == 0:
                connection.executemany(
                    """
                    INSERT INTO rooms
                        (name, room_type, description, monthly_rent, tag)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    STARTER_ROOMS,
                )
    finally:
        connection.close()


def get_database(request: Request) -> Generator[sqlite3.Connection, None, None]:
    connection = connect(request.app.state.database_path)
    try:
        yield connection
    finally:
        connection.close()
