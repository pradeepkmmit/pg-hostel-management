from fastapi import FastAPI

app = FastAPI(
    title="PG Hostel Management API",
    description="API for managing PG hostel rooms, bookings, residents, and requests.",
    version="0.1.0",
)


@app.get("/api/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}