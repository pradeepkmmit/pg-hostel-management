# PG Hostel Management

A learning project for managing paying-guest accommodation: public room discovery, resident accounts, bookings, rent records, maintenance requests, and admin operations.

## Project status

The local MVP includes public room listings and inquiries, resident accounts and booking requests, maintenance requests, rent records, notices, and an administrator portal for managing those workflows. It uses SQLite and a local static frontend. It does not process payments, send email/SMS, or provide a production deployment configuration.

## Product roles

- **Visitor:** browse the public home page and available rooms, then send an inquiry.
- **PG resident:** manage a profile, request a room, review rent records and notices, and submit maintenance requests.
- **Admin:** manage rooms and residents, review booking requests, record payments, resolve requests, and publish notices.

## MVP scope

- Visitors can browse available listings and submit an inquiry.
- Residents can create an account, sign in, update their profile, request a room, submit maintenance requests, and review rent records and notices.
- Admins can manage listings, approve or decline booking requests, review residents and inquiries, resolve maintenance requests, add or update rent records, and publish or remove notices.
- Rent entries are records only; payment-card and bank details are not collected or stored.

Online payment processing, email/SMS delivery, password resets, and multi-property support remain future enhancements.

## Technology choices

- **Backend:** Python 3.10+ and FastAPI
- **Frontend:** HTML, CSS, and JavaScript
- **Database:** SQLite for the initial local version; PostgreSQL can be introduced when needed
- **API documentation:** FastAPI's generated Swagger UI at `/docs`
- **Containers:** optional; Docker Desktop is not required for local development

## Repository layout

```text
pg-hostel-management/
|-- backend/
|   |-- app/
|   |   |-- api/routes/    # Public, auth, resident, and admin endpoints
|   |   |-- db/            # SQLite connection and schema initialization
|   |   |-- schemas/       # Request and response validation
|   |   |-- scripts/       # Safe initial administrator provisioning
|   |   |-- services/      # Password hashing and session authorization
|   |   `-- main.py        # FastAPI application entry point
|   |-- tests/
|   |-- requirements.txt
|   `-- requirements-dev.txt
|-- frontend/
|   |-- index.html         # Public home page and resident/admin portal
|   `-- assets/            # Styles, scripts, and images
|-- .gitignore
`-- README.md
```

## Run locally

From the repository root on macOS:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m uvicorn app.main:app --reload
```

On first startup, the API creates `backend/data/hostel.db` and inserts example room listings. To provision an administrator, run this from a second terminal:

```bash
cd backend
source ../.venv/bin/activate
python -m app.scripts.create_admin
```

The script prompts for an administrator name, email, and password; it does not ship with a default admin account. Resident accounts can be created from the homepage.

Then start the frontend preview from another terminal at the repository root:

```bash
python3 -m http.server 4173 --directory frontend
```

Open `http://127.0.0.1:4173` in Safari. Sign in to the Resident portal to request a room, update a profile, submit a maintenance request, and view rent records and notices. Admins sign in at the same portal after provisioning.

The API is also available directly:

- `GET http://127.0.0.1:8000/api/rooms` lists available rooms.
- `POST http://127.0.0.1:8000/api/inquiries` saves a validated visitor inquiry.
- `POST http://127.0.0.1:8000/api/auth/register` creates a resident account and signs in.
- `POST http://127.0.0.1:8000/api/auth/login` starts a session; `POST /api/auth/logout` ends it.
- `/api/resident/*` contains authenticated profile, booking, maintenance, payment, and notice endpoints.
- `/api/admin/*` contains administrator-only listing, resident, inquiry, booking, maintenance, payment, and notice management endpoints.
- `GET http://127.0.0.1:8000/api/health` checks the API.
- `http://127.0.0.1:8000/docs` provides interactive API documentation.

Run the backend tests from the `backend/` directory with `python -m unittest discover -s tests -v`.

## Preview the home page

Room listings are starter examples and prices should be confirmed before being used as live pricing. If the backend is stopped, the static page still loads, but API-backed listings and portal workflows require both local servers.

## Persisted data

- **User:** name, email, optional phone, salted password hash, role, and account status.
- **Room listing:** name, type, description, monthly rent, availability, and short tag.
- **Booking:** resident, requested listing, optional move-in date, message, and review status.
- **Payment record:** resident, amount, billing period, due date, status, and note.
- **Maintenance request:** resident, category, description, status, and creation time.
- **Notice:** title, message, author, and creation time.
- **Inquiry:** visitor name, email, message, and creation time.

Passwords are stored as salted scrypt hashes. Sessions use random tokens stored as hashes in SQLite and are delivered in HttpOnly, SameSite cookies. For HTTPS deployments, set `APP_ENV=production` (or `COOKIE_SECURE=true`) so session cookies require HTTPS. The configured browser origins are local development origins; update CORS deliberately before deploying elsewhere. This project is a learning MVP and needs further operational security review before public deployment. Do not store payment card or bank credentials in this app.

## Contribution workflow

1. Create a branch for one feature or fix.
2. Keep changes focused and add tests as backend behavior is introduced.
3. Run the relevant checks before opening a pull request.
