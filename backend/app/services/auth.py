import hashlib
import hmac
import secrets
import sqlite3

from fastapi import Depends, HTTPException, Request, status

from app.db.database import get_database

PASSWORD_SCRYPT_N = 2**14
SESSION_COOKIE_NAME = "staynest_session"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_SCRYPT_N,
        r=8,
        p=1,
    )
    return f"{salt.hex()}:{password_hash.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        salt_hex, hash_hex = encoded_hash.split(":", maxsplit=1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    actual_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_SCRYPT_N,
        r=8,
        p=1,
        dklen=len(expected_hash),
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def create_user(
    connection: sqlite3.Connection,
    *,
    name: str,
    email: str,
    phone: str,
    password: str,
    role: str,
) -> sqlite3.Row:
    cursor = connection.execute(
        """
        INSERT INTO users (name, email, phone, password_hash, role)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, email, phone, hash_password(password), role),
    )
    connection.commit()
    user = connection.execute(
        "SELECT id, name, email, phone, role, active FROM users WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if user is None:
        raise RuntimeError("Created user could not be loaded")
    return user


def create_session(
    connection: sqlite3.Connection, user_id: int
) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection.execute(
        """
        INSERT INTO sessions (token_hash, user_id, expires_at)
        VALUES (?, ?, datetime('now', '+7 days'))
        """,
        (token_hash, user_id),
    )
    connection.commit()
    return token


def delete_session(connection: sqlite3.Connection, token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
    connection.commit()


def get_current_user(
    request: Request,
    connection: sqlite3.Connection = Depends(get_database),
) -> sqlite3.Row:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue.",
        )

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    user = connection.execute(
        """
        SELECT users.id, users.name, users.email, users.phone, users.role, users.active
        FROM sessions
        JOIN users ON users.id = sessions.user_id
        WHERE sessions.token_hash = ?
            AND sessions.expires_at > CURRENT_TIMESTAMP
            AND users.active = 1
        """,
        (token_hash,),
    ).fetchone()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        )
    return user


def require_admin(
    user: sqlite3.Row = Depends(get_current_user),
) -> sqlite3.Row:
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required.",
        )
    return user
