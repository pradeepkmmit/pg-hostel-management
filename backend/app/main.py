from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.public import router as public_router
from app.api.routes.resident import router as resident_router
from app.db.database import DEFAULT_DATABASE_PATH, initialize_database


def create_app(database_path: Path = DEFAULT_DATABASE_PATH) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_application: FastAPI):
        initialize_database(_application.state.database_path)
        yield

    application = FastAPI(
        title="PG Hostel Management API",
        description="Visitor listings, resident services, and administrator workflows.",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database_path = database_path
    application.state.cookie_secure = (
        os.environ.get("COOKIE_SECURE", "").lower() == "true"
        or os.environ.get("APP_ENV", "").lower() == "production"
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:4173",
            "http://localhost:4173",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    application.include_router(public_router)
    application.include_router(auth_router)
    application.include_router(resident_router)
    application.include_router(admin_router)

    @application.get("/api/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()