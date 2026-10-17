import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.db.database import get_database
from app.schemas.public import LoginRequest, UserCreate, UserResponse
from app.services.auth import (
    SESSION_COOKIE_NAME,
    create_session,
    create_user,
    delete_session,
    get_current_user,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])
SESSION_MAX_AGE = 7 * 24 * 60 * 60


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=request.app.state.cookie_secure,
        samesite="lax",
        path="/api",
    )


def user_response(user: sqlite3.Row) -> UserResponse:
    return UserResponse(
        id=user["id"],
        name=user["name"],
        email=user["email"],
        phone=user["phone"],
        role=user["role"],
        active=bool(user["active"]),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(
    account: UserCreate,
    request: Request,
    response: Response,
    connection: sqlite3.Connection = Depends(get_database),
) -> UserResponse:
    try:
        user = create_user(
            connection,
            name=account.name,
            email=account.email,
            phone=account.phone,
            password=account.password,
            role="resident",
        )
    except sqlite3.IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        ) from error
    token = create_session(connection, user["id"])
    set_session_cookie(response, request, token)
    return user_response(user)


@router.post("/login", response_model=UserResponse)
def login(
    credentials: LoginRequest,
    request: Request,
    response: Response,
    connection: sqlite3.Connection = Depends(get_database),
) -> UserResponse:
    user = connection.execute(
        "SELECT * FROM users WHERE email = ? COLLATE NOCASE",
        (credentials.email,),
    ).fetchone()
    if (
        user is None
        or not user["active"]
        or not verify_password(credentials.password, user["password_hash"])
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    token = create_session(connection, user["id"])
    set_session_cookie(response, request, token)
    return user_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    connection: sqlite3.Connection = Depends(get_database),
) -> Response:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        delete_session(connection, token)
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/api",
        httponly=True,
        secure=request.app.state.cookie_secure,
        samesite="lax",
    )
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: sqlite3.Row = Depends(get_current_user)) -> UserResponse:
    return user_response(user)
