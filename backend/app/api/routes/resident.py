import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.database import get_database
from app.schemas.public import (
    BookingCreate,
    BookingResponse,
    MaintenanceCreate,
    MaintenanceResponse,
    NoticeResponse,
    ProfileUpdate,
    UserResponse,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/resident", tags=["resident"])


def require_resident(user: sqlite3.Row = Depends(get_current_user)) -> sqlite3.Row:
    if user["role"] != "resident":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resident access is required.",
        )
    return user


@router.get("/bookings", response_model=list[BookingResponse])
def list_my_bookings(
    user: sqlite3.Row = Depends(require_resident),
    connection: sqlite3.Connection = Depends(get_database),
) -> list[BookingResponse]:
    rows = connection.execute(
        """
        SELECT bookings.*, rooms.name AS room_name
        FROM bookings
        JOIN rooms ON rooms.id = bookings.room_id
        WHERE bookings.user_id = ?
        ORDER BY bookings.id DESC
        """,
        (user["id"],),
    ).fetchall()
    return [
        BookingResponse(
            id=row["id"],
            room_id=row["room_id"],
            room_name=row["room_name"],
            move_in_date=row["move_in_date"],
            message=row["message"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.post("/bookings", response_model=BookingResponse, status_code=201)
def request_booking(
    booking: BookingCreate,
    user: sqlite3.Row = Depends(require_resident),
    connection: sqlite3.Connection = Depends(get_database),
) -> BookingResponse:
    room = connection.execute(
        "SELECT id, name FROM rooms WHERE id = ? AND available = 1",
        (booking.room_id,),
    ).fetchone()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That room is not available for booking.",
        )
    cursor = connection.execute(
        """
        INSERT INTO bookings (user_id, room_id, move_in_date, message)
        VALUES (?, ?, ?, ?)
        """,
        (
            user["id"],
            booking.room_id,
            booking.move_in_date.isoformat() if booking.move_in_date else None,
            booking.message,
        ),
    )
    connection.commit()
    row = connection.execute(
        """
        SELECT bookings.*, rooms.name AS room_name
        FROM bookings
        JOIN rooms ON rooms.id = bookings.room_id
        WHERE bookings.id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return BookingResponse(
        id=row["id"],
        room_id=row["room_id"],
        room_name=row["room_name"],
        move_in_date=row["move_in_date"],
        message=row["message"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.get("/maintenance", response_model=list[MaintenanceResponse])
def list_my_maintenance_requests(
    user: sqlite3.Row = Depends(require_resident),
    connection: sqlite3.Connection = Depends(get_database),
) -> list[MaintenanceResponse]:
    rows = connection.execute(
        """
        SELECT * FROM maintenance_requests
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        (user["id"],),
    ).fetchall()
    return [
        MaintenanceResponse(
            id=row["id"],
            user_id=row["user_id"],
            category=row["category"],
            description=row["description"],
            status=row["status"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.post("/maintenance", response_model=MaintenanceResponse, status_code=201)
def create_maintenance_request(
    request_data: MaintenanceCreate,
    user: sqlite3.Row = Depends(require_resident),
    connection: sqlite3.Connection = Depends(get_database),
) -> MaintenanceResponse:
    cursor = connection.execute(
        """
        INSERT INTO maintenance_requests (user_id, category, description)
        VALUES (?, ?, ?)
        """,
        (user["id"], request_data.category, request_data.description),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM maintenance_requests WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return MaintenanceResponse(
        id=row["id"],
        user_id=row["user_id"],
        category=row["category"],
        description=row["description"],
        status=row["status"],
        created_at=row["created_at"],
    )


@router.get("/payments")
def list_my_payments(
    user: sqlite3.Row = Depends(require_resident),
    connection: sqlite3.Connection = Depends(get_database),
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT id, amount, billing_period, due_date, status, note, created_at
        FROM payments
        WHERE user_id = ?
        ORDER BY due_date DESC, id DESC
        """,
        (user["id"],),
    ).fetchall()
    return [dict(row) for row in rows]


@router.get(
    "/notices",
    response_model=list[NoticeResponse],
    dependencies=[Depends(require_resident)],
)
def list_notices(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[NoticeResponse]:
    rows = connection.execute(
        """
        SELECT notices.*, users.name AS author_name
        FROM notices
        JOIN users ON users.id = notices.author_id
        ORDER BY notices.id DESC
        """
    ).fetchall()
    return [
        NoticeResponse(
            id=row["id"],
            title=row["title"],
            message=row["message"],
            author_name=row["author_name"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/profile", response_model=UserResponse)
def get_profile(user: sqlite3.Row = Depends(require_resident)) -> UserResponse:
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        phone=user["phone"],
        role=user["role"],
        active=bool(user["active"]),
    )


@router.patch("/profile", response_model=UserResponse)
def update_profile(
    profile: ProfileUpdate,
    user: sqlite3.Row = Depends(require_resident),
    connection: sqlite3.Connection = Depends(get_database),
) -> UserResponse:
    connection.execute(
        "UPDATE users SET name = ?, phone = ? WHERE id = ?",
        (profile.name, profile.phone, user["id"]),
    )
    connection.commit()
    return UserResponse(
        id=user["id"],
        name=profile.name,
        email=user["email"],
        phone=profile.phone,
        role=user["role"],
        active=bool(user["active"]),
    )
