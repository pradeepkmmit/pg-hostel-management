import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.db.database import connect, initialize_database
from app.main import create_app
from app.services.auth import create_user


class PublicApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "hostel.db"
        self.client_context = TestClient(create_app(self.database_path))
        self.client = self.client_context.__enter__()
        connection = connect(self.database_path)
        create_user(
            connection,
            name="Site Admin",
            email="admin@example.com",
            phone="",
            password="admin-password-secure",
            role="admin",
        )
        connection.close()
        self.admin_client_context = TestClient(create_app(self.database_path))
        self.admin_client = self.admin_client_context.__enter__()
        self.admin_client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "admin-password-secure"},
        )

    def tearDown(self) -> None:
        self.admin_client_context.__exit__(None, None, None)
        self.client_context.__exit__(None, None, None)
        self.temporary_directory.cleanup()

    def register_resident(self, email: str = "pradeep@example.com") -> dict[str, object]:
        response = self.client.post(
            "/api/auth/register",
            json={
                "name": "  Pradeep  ",
                "email": email,
                "phone": "1234567890",
                "password": "resident-password-secure",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_lists_available_rooms_from_database(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                "UPDATE rooms SET available = 0 WHERE room_type = ?",
                ("shared",),
            )
            connection.commit()

        response = self.client.get("/api/rooms")

        self.assertEqual(response.status_code, 200)
        rooms = response.json()
        self.assertEqual([room["room_type"] for room in rooms], ["private", "suite"])
        self.assertTrue(all(room["available"] for room in rooms))

    def test_migrates_legacy_room_types_and_preserves_existing_listings(self) -> None:
        legacy_database = self.database_path.parent / "legacy.db"
        with closing(sqlite3.connect(legacy_database)) as connection:
            connection.execute(
                """
                CREATE TABLE rooms (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    room_type TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    monthly_rent INTEGER NOT NULL,
                    available INTEGER NOT NULL DEFAULT 1,
                    tag TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO rooms (name, room_type, description, monthly_rent, tag)
                VALUES ('Existing private room', 'private', 'Kept listing', 10000, 'EXISTING')
                """
            )
            connection.commit()

        initialize_database(legacy_database)
        with closing(connect(legacy_database)) as connection:
            connection.execute(
                """
                INSERT INTO rooms (name, room_type, description, monthly_rent, tag)
                VALUES ('Second private room', 'private', 'Another listing', 12000, 'NEW')
                """
            )
            connection.commit()
            rows = connection.execute(
                "SELECT name FROM rooms ORDER BY id"
            ).fetchall()
        initialize_database(legacy_database)

        self.assertEqual(
            [row["name"] for row in rows],
            ["Existing private room", "Second private room"],
        )
        with closing(connect(legacy_database)) as connection:
            self.assertEqual(
                connection.execute("SELECT COUNT(*) FROM rooms").fetchone()[0],
                2,
            )

    def test_saves_normalized_inquiry(self) -> None:
        response = self.client.post(
            "/api/inquiries",
            json={
                "name": "  Pradeep  ",
                "email": "  PRADEEP@example.com ",
                "message": "  I am looking for a private room. ",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["id"], 1)
        with closing(sqlite3.connect(self.database_path)) as connection:
            inquiry = connection.execute(
                "SELECT name, email, message FROM inquiries WHERE id = 1"
            ).fetchone()
        self.assertEqual(
            inquiry,
            ("Pradeep", "pradeep@example.com", "I am looking for a private room."),
        )

    def test_rejects_invalid_email_without_saving(self) -> None:
        response = self.client.post(
            "/api/inquiries",
            json={"name": "Pradeep", "email": "not-an-email"},
        )

        self.assertEqual(response.status_code, 422)
        with closing(sqlite3.connect(self.database_path)) as connection:
            inquiry_count = connection.execute(
                "SELECT COUNT(*) FROM inquiries"
            ).fetchone()[0]
        self.assertEqual(inquiry_count, 0)

    def test_rejects_blank_name_without_saving(self) -> None:
        response = self.client.post(
            "/api/inquiries",
            json={"name": "   ", "email": "pradeep@example.com"},
        )

        self.assertEqual(response.status_code, 422)
        with closing(sqlite3.connect(self.database_path)) as connection:
            inquiry_count = connection.execute(
                "SELECT COUNT(*) FROM inquiries"
            ).fetchone()[0]
        self.assertEqual(inquiry_count, 0)

    def test_resident_registration_login_and_session(self) -> None:
        resident = self.register_resident()

        self.assertEqual(resident["role"], "resident")
        self.assertEqual(resident["name"], "Pradeep")
        self.assertTrue(self.client.cookies.get("staynest_session"))
        self.assertEqual(self.client.get("/api/auth/me").json()["email"], "pradeep@example.com")

        self.client.post("/api/auth/logout")
        login = self.client.post(
            "/api/auth/login",
            json={"email": "PRADEEP@example.com", "password": "resident-password-secure"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["role"], "resident")

    def test_rejects_duplicate_email_and_invalid_credentials(self) -> None:
        self.register_resident()
        duplicate = self.client.post(
            "/api/auth/register",
            json={
                "name": "Another Resident",
                "email": "PRADEEP@example.com",
                "password": "another-password-secure",
            },
        )
        bad_password = self.client.post(
            "/api/auth/login",
            json={"email": "pradeep@example.com", "password": "incorrect-password"},
        )

        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(bad_password.status_code, 401)

    def test_resident_can_create_booking_and_maintenance_request(self) -> None:
        self.register_resident()
        booking = self.client.post(
            "/api/resident/bookings",
            json={
                "room_id": 1,
                "move_in_date": (date.today() + timedelta(days=30)).isoformat(),
                "message": "Please contact me in the afternoon.",
            },
        )
        maintenance = self.client.post(
            "/api/resident/maintenance",
            json={"category": " Plumbing ", "description": " Leaking tap "},
        )

        self.assertEqual(booking.status_code, 201)
        self.assertEqual(booking.json()["status"], "pending")
        self.assertEqual(booking.json()["room_name"], "Private room")
        self.assertEqual(maintenance.status_code, 201)
        self.assertEqual(maintenance.json()["category"], "Plumbing")

    def test_admin_reviews_bookings_and_updates_room_availability(self) -> None:
        self.register_resident()
        booking_id = self.client.post(
            "/api/resident/bookings",
            json={"room_id": 1},
        ).json()["id"]

        response = self.admin_client.patch(
            f"/api/admin/bookings/{booking_id}",
            json={"status": "approved"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "approved")
        public_rooms = self.client.get("/api/rooms").json()
        self.assertNotIn(1, [room["id"] for room in public_rooms])
        repeated_review = self.admin_client.patch(
            f"/api/admin/bookings/{booking_id}",
            json={"status": "rejected"},
        )
        self.assertEqual(repeated_review.status_code, 409)

    def test_resident_is_forbidden_from_admin_data(self) -> None:
        self.register_resident()
        response = self.client.get("/api/admin/bookings")
        self.assertEqual(response.status_code, 403)

    def test_resident_can_update_profile(self) -> None:
        self.register_resident()
        response = self.client.patch(
            "/api/resident/profile",
            json={"name": "  Pradeep K  ", "phone": "  9876543210  "},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Pradeep K")
        self.assertEqual(response.json()["phone"], "9876543210")

    def test_admin_manages_rooms_payments_notices_and_maintenance(self) -> None:
        resident = self.register_resident()
        maintenance_id = self.client.post(
            "/api/resident/maintenance",
            json={"category": "Furniture", "description": "Desk needs repair."},
        ).json()["id"]

        new_room = self.admin_client.post(
            "/api/admin/rooms",
            json={
                "name": "Garden private room",
                "room_type": "private",
                "description": "A quiet room facing the garden.",
                "monthly_rent": 14000,
                "tag": "GARDEN VIEW",
            },
        )
        payment = self.admin_client.post(
            "/api/admin/payments",
            json={
                "user_id": resident["id"],
                "amount": 12000,
                "billing_period": "October 2026",
                "due_date": "2026-10-31",
            },
        )
        notice = self.admin_client.post(
            "/api/admin/notices",
            json={"title": "Welcome", "message": "The common room is open."},
        )
        maintenance_update = self.admin_client.patch(
            f"/api/admin/maintenance/{maintenance_id}",
            json={"status": "resolved"},
        )

        self.assertEqual(new_room.status_code, 201)
        self.assertEqual(payment.status_code, 201)
        self.assertEqual(notice.status_code, 201)
        self.assertEqual(maintenance_update.json()["status"], "resolved")
        payment_status = self.admin_client.patch(
            f"/api/admin/payments/{payment.json()['id']}",
            json={"status": "paid"},
        )
        self.assertEqual(payment_status.status_code, 200)
        self.assertEqual(payment_status.json()["status"], "paid")
        self.assertEqual(len(self.client.get("/api/resident/payments").json()), 1)
        self.assertEqual(self.client.get("/api/resident/notices").json()[0]["title"], "Welcome")

    def test_sessions_are_revoked_on_logout(self) -> None:
        self.register_resident()
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/resident/bookings").status_code, 401)


if __name__ == "__main__":
    unittest.main()
