import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.db.database import get_database
from app.schemas.public import (
    BookingResponse,
    BookingStatusUpdate,
    MaintenanceResponse,
    MaintenanceStatusUpdate,
    NoticeCreate,
    NoticeResponse,
    PaymentCreate,
    PaymentStatusUpdate,
    RoomResponse,
    UserResponse,
)
from app.services.auth import require_admin

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


class RoomCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    room_type: str = Field(pattern="^(private|shared|suite)$")
    description: str = Field(min_length=1, max_length=500)
    monthly_rent: int = Field(ge=0, le=100_000_000)
    tag: str = Field(min_length=1, max_length=80)
    available: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    monthly_rent: int | None = Field(default=None, ge=0, le=100_000_000)
    tag: str | None = Field(default=None, min_length=1, max_length=80)
    available: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)


def room_response(row: sqlite3.Row) -> RoomResponse:
    return RoomResponse(
        id=row["id"],
        name=row["name"],
        room_type=row["room_type"],
        description=row["description"],
        monthly_rent=row["monthly_rent"],
        available=bool(row["available"]),
        tag=row["tag"],
    )


@router.get("/rooms", response_model=list[RoomResponse])
def list_all_rooms(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[RoomResponse]:
    rows = connection.execute("SELECT * FROM rooms ORDER BY id").fetchall()
    return [room_response(row) for row in rows]


@router.post("/rooms", response_model=RoomResponse, status_code=201)
def create_room(
    room: RoomCreate,
    connection: sqlite3.Connection = Depends(get_database),
) -> RoomResponse:
    try:
        cursor = connection.execute(
            """
            INSERT INTO rooms (name, room_type, description, monthly_rent, available, tag)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                room.name,
                room.room_type,
                room.description,
                room.monthly_rent,
                int(room.available),
                room.tag,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A listing for that room type already exists.",
        ) from error
    row = connection.execute(
        "SELECT * FROM rooms WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return room_response(row)


@router.patch("/rooms/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    updates: RoomUpdate,
    connection: sqlite3.Connection = Depends(get_database),
) -> RoomResponse:
    values = updates.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide at least one room field to update.",
        )
    if any(value is None for value in values.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Room fields cannot be null.",
        )
    assignments = ", ".join(f"{field} = ?" for field in values)
    cursor = connection.execute(
        f"UPDATE rooms SET {assignments} WHERE id = ?",
        (*values.values(), room_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room listing not found.",
        )
    connection.commit()
    row = connection.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    return room_response(row)


@router.get("/residents", response_model=list[UserResponse])
def list_residents(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[UserResponse]:
    rows = connection.execute(
        """
        SELECT id, name, email, phone, role, active
        FROM users WHERE role = 'resident'
        ORDER BY id DESC
        """
    ).fetchall()
    return [
        UserResponse(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            role=row["role"],
            active=bool(row["active"]),
        )
        for row in rows
    ]


@router.get("/bookings", response_model=list[BookingResponse])
def list_bookings(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[BookingResponse]:
    rows = connection.execute(
        """
        SELECT bookings.*, rooms.name AS room_name,
            users.name AS resident_name, users.email AS resident_email
        FROM bookings
        JOIN rooms ON rooms.id = bookings.room_id
        JOIN users ON users.id = bookings.user_id
        ORDER BY bookings.id DESC
        """
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
            resident_name=row["resident_name"],
            resident_email=row["resident_email"],
        )
        for row in rows
    ]


@router.patch("/bookings/{booking_id}", response_model=BookingResponse)
def update_booking_status(
    booking_id: int,
    update: BookingStatusUpdate,
    connection: sqlite3.Connection = Depends(get_database),
) -> BookingResponse:
    booking = connection.execute(
        """
        SELECT bookings.*, rooms.name AS room_name,
            users.name AS resident_name, users.email AS resident_email
        FROM bookings
        JOIN rooms ON rooms.id = bookings.room_id
        JOIN users ON users.id = bookings.user_id
        WHERE bookings.id = ?
        """,
        (booking_id,),
    ).fetchone()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking request not found.")
    if booking["status"] != "pending":
        raise HTTPException(
            status_code=409,
            detail="This booking request has already been reviewed.",
        )
    if update.status == "approved" and not connection.execute(
        "SELECT available FROM rooms WHERE id = ?", (booking["room_id"],)
    ).fetchone()["available"]:
        raise HTTPException(
            status_code=409,
            detail="This room has been made unavailable.",
        )

    connection.execute(
        "UPDATE bookings SET status = ? WHERE id = ?",
        (update.status, booking_id),
    )
    if update.status == "approved":
        connection.execute(
            "UPDATE rooms SET available = 0 WHERE id = ?",
            (booking["room_id"],),
        )
    connection.commit()
    return BookingResponse(
        id=booking["id"],
        room_id=booking["room_id"],
        room_name=booking["room_name"],
        move_in_date=booking["move_in_date"],
        message=booking["message"],
        status=update.status,
        created_at=booking["created_at"],
        resident_name=booking["resident_name"],
        resident_email=booking["resident_email"],
    )


@router.get("/maintenance", response_model=list[MaintenanceResponse])
def list_maintenance(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[MaintenanceResponse]:
    rows = connection.execute(
        """
        SELECT maintenance_requests.*, users.name AS resident_name
        FROM maintenance_requests
        JOIN users ON users.id = maintenance_requests.user_id
        ORDER BY maintenance_requests.id DESC
        """
    ).fetchall()
    return [
        MaintenanceResponse(
            id=row["id"],
            user_id=row["user_id"],
            category=row["category"],
            description=row["description"],
            status=row["status"],
            created_at=row["created_at"],
            resident_name=row["resident_name"],
        )
        for row in rows
    ]


@router.patch("/maintenance/{request_id}", response_model=MaintenanceResponse)
def update_maintenance_status(
    request_id: int,
    update: MaintenanceStatusUpdate,
    connection: sqlite3.Connection = Depends(get_database),
) -> MaintenanceResponse:
    cursor = connection.execute(
        "UPDATE maintenance_requests SET status = ? WHERE id = ?",
        (update.status, request_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Maintenance request not found.")
    connection.commit()
    row = connection.execute(
        """
        SELECT maintenance_requests.*, users.name AS resident_name
        FROM maintenance_requests
        JOIN users ON users.id = maintenance_requests.user_id
        WHERE maintenance_requests.id = ?
        """,
        (request_id,),
    ).fetchone()
    return MaintenanceResponse(
        id=row["id"],
        user_id=row["user_id"],
        category=row["category"],
        description=row["description"],
        status=row["status"],
        created_at=row["created_at"],
        resident_name=row["resident_name"],
    )


@router.post("/payments", status_code=201)
def create_payment(
    payment: PaymentCreate,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    resident = connection.execute(
        "SELECT id FROM users WHERE id = ? AND role = 'resident' AND active = 1",
        (payment.user_id,),
    ).fetchone()
    if resident is None:
        raise HTTPException(status_code=404, detail="Active resident not found.")
    cursor = connection.execute(
        """
        INSERT INTO payments (user_id, amount, billing_period, due_date, status, note)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payment.user_id,
            payment.amount,
            payment.billing_period,
            payment.due_date.isoformat(),
            payment.status,
            payment.note,
        ),
    )
    connection.commit()
    return dict(
        connection.execute(
            """
            SELECT id, user_id, amount, billing_period, due_date, status, note, created_at
            FROM payments WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
    )


@router.get("/payments")
def list_payments(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT payments.id, payments.user_id, users.name AS resident_name,
            users.email AS resident_email, payments.amount, payments.billing_period,
            payments.due_date, payments.status, payments.note, payments.created_at
        FROM payments
        JOIN users ON users.id = payments.user_id
        ORDER BY payments.due_date DESC, payments.id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


@router.patch("/payments/{payment_id}")
def update_payment_status(
    payment_id: int,
    update: PaymentStatusUpdate,
    connection: sqlite3.Connection = Depends(get_database),
) -> dict[str, object]:
    cursor = connection.execute(
        "UPDATE payments SET status = ? WHERE id = ?",
        (update.status, payment_id),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Rent record not found.")
    connection.commit()
    return dict(
        connection.execute(
            """
            SELECT payments.id, payments.user_id, users.name AS resident_name,
                payments.amount, payments.billing_period, payments.due_date,
                payments.status, payments.note, payments.created_at
            FROM payments
            JOIN users ON users.id = payments.user_id
            WHERE payments.id = ?
            """,
            (payment_id,),
        ).fetchone()
    )


@router.post("/notices", response_model=NoticeResponse, status_code=201)
def create_notice(
    notice: NoticeCreate,
    admin: sqlite3.Row = Depends(require_admin),
    connection: sqlite3.Connection = Depends(get_database),
) -> NoticeResponse:
    cursor = connection.execute(
        "INSERT INTO notices (title, message, author_id) VALUES (?, ?, ?)",
        (notice.title, notice.message, admin["id"]),
    )
    connection.commit()
    return NoticeResponse(
        id=cursor.lastrowid,
        title=notice.title,
        message=notice.message,
        author_name=admin["name"],
        created_at=connection.execute(
            "SELECT created_at FROM notices WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()["created_at"],
    )


@router.get("/notices", response_model=list[NoticeResponse])
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


@router.delete("/notices/{notice_id}", status_code=204)
def delete_notice(
    notice_id: int,
    connection: sqlite3.Connection = Depends(get_database),
) -> None:
    cursor = connection.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Notice not found.")
    connection.commit()


@router.get("/inquiries")
def list_inquiries(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT id, name, email, message, created_at
        FROM inquiries
        ORDER BY id DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]
