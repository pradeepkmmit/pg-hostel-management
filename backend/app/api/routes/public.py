import sqlite3

from fastapi import APIRouter, Depends, status

from app.db.database import get_database
from app.schemas.public import InquiryCreate, InquiryResponse, RoomResponse

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/rooms", response_model=list[RoomResponse])
def list_rooms(
    connection: sqlite3.Connection = Depends(get_database),
) -> list[RoomResponse]:
    rows = connection.execute(
        """
        SELECT id, name, room_type, description, monthly_rent, available, tag
        FROM rooms
        WHERE available = 1
        ORDER BY id
        """
    ).fetchall()
    return [
        RoomResponse(
            id=row["id"],
            name=row["name"],
            room_type=row["room_type"],
            description=row["description"],
            monthly_rent=row["monthly_rent"],
            available=bool(row["available"]),
            tag=row["tag"],
        )
        for row in rows
    ]


@router.post(
    "/inquiries",
    response_model=InquiryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inquiry(
    inquiry: InquiryCreate,
    connection: sqlite3.Connection = Depends(get_database),
) -> InquiryResponse:
    cursor = connection.execute(
        """
        INSERT INTO inquiries (name, email, message)
        VALUES (?, ?, ?)
        """,
        (inquiry.name, inquiry.email, inquiry.message),
    )
    connection.commit()
    return InquiryResponse(
        id=cursor.lastrowid,
        message="Your inquiry was saved. The team can follow up with you.",
    )
