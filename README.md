# PG Hostel Management

A learning project for managing paying-guest accommodation: public room discovery, resident accounts, bookings, rent records, maintenance requests, and admin operations.

## Project status

This repository contains the initial project scaffold. The API currently exposes a health check; booking, account, and management features are planned and are not implemented yet.

## Product roles

- **Visitor:** browse the public home page and available rooms, then send an inquiry.
- **PG resident:** manage a profile, request a room, review rent records and notices, and submit maintenance requests.
- **Admin:** manage rooms and residents, review booking requests, record payments, resolve requests, and publish notices.

## Initial scope

Build the project in small steps:

1. Start the FastAPI service and establish the project structure.
2. Add room and public listing features.
3. Add resident accounts and booking requests.
4. Add admin workflows, rent records, notices, and maintenance requests.
5. Add validation, tests, and deployment configuration.

Online payment processing, SMS, and multi-property support are later enhancements. The first version should track payment records, not handle card or bank details.

## Technology choices

- **Backend:** Python 3.10+ and FastAPI
- **Frontend:** HTML, CSS, and JavaScript (planned)
- **Database:** SQLite for the initial local version; PostgreSQL can be introduced when needed
- **API documentation:** FastAPI's generated Swagger UI at `/docs`
- **Containers:** optional; Docker Desktop is not required for local development

## Repository layout

```text
pg-hostel-management/
|-- backend/
|   |-- app/
|   |   |-- api/routes/    # HTTP endpoints
|   |   |-- core/          # Settings and shared configuration
|   |   |-- db/            # Database connection and session setup
|   |   |-- models/        # Database entities
|   |   |-- schemas/       # Request and response validation
|   |   |-- services/      # Business rules
|   |   `-- main.py        # FastAPI application entry point
|   `-- requirements.txt
|-- frontend/
|   |-- pages/             # Public, admin, and resident screens
|   `-- assets/
|       |-- css/
|       |-- js/
|       `-- images/
|-- .gitignore
`-- README.md
```

## Run locally

From the repository root on macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/api/health` to check the API, or `http://127.0.0.1:8000/docs` to explore it.

## Planned data entities

- **User:** name, email, phone, password hash, role, and account status.
- **Room:** room number, type, rent, capacity, amenities, and availability.
- **Booking:** resident, requested room, dates, and review status.
- **Payment:** resident, amount, billing period, due date, and payment status.
- **MaintenanceRequest:** resident, category, description, status, and timestamps.
- **Notice:** title, message, author, and publication date.

Passwords must be stored as hashes. Role checks and authorization must be enforced by the backend, not only hidden in the UI. Do not store payment card or bank credentials in this app.

## Contribution workflow

1. Create a branch for one feature or fix.
2. Keep changes focused and add tests as backend behavior is introduced.
3. Run the relevant checks before opening a pull request.
