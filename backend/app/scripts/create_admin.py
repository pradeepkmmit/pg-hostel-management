import getpass
import sqlite3

from app.db.database import DEFAULT_DATABASE_PATH, connect, initialize_database
from app.schemas.public import UserCreate
from app.services.auth import create_user


def main() -> None:
    initialize_database(DEFAULT_DATABASE_PATH)
    name = input("Administrator name: ").strip()
    email = input("Administrator email: ").strip().lower()
    password = getpass.getpass("Administrator password (12+ characters): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    account = UserCreate(
        name=name,
        email=email,
        phone="",
        password=password,
    )
    connection = connect(DEFAULT_DATABASE_PATH)
    try:
        create_user(
            connection,
            name=account.name,
            email=account.email,
            phone="",
            password=account.password,
            role="admin",
        )
    except sqlite3.IntegrityError as error:
        raise SystemExit("An account with that email already exists.") from error
    finally:
        connection.close()
    print(f"Administrator account created for {account.email}.")


if __name__ == "__main__":
    main()
