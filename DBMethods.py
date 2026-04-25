import sqlite3
import re
from typing import List, Optional


class User:
    def __init__(self, id: int, username: str, password: str, full_name: str, email: str, bio: str,
                 profile_photo: str = "", failed_attempts: int = 0, lockout_until: str = None,
                 reset_token: str = None, reset_token_expiry: str = None):
        self.id = id
        self.username = username
        self.password = password
        self.full_name = full_name
        self.email = email
        self.bio = bio
        self.profile_photo = profile_photo
        self.failed_attempts = failed_attempts
        self.lockout_until = lockout_until
        self.reset_token = reset_token
        self.reset_token_expiry = reset_token_expiry


class UserRepository:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _validate_user(self, username, password, full_name, email):
        patterns = {
            "username": r".+",
            "password": r".+",
            "full_name": r".+",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|gov|edu|net)$"
        }

        if not re.match(patterns["username"], username):
            return False, "Invalid username"
        if not re.match(patterns["password"], password):
            return False, "Invalid password"
        if not re.match(patterns["full_name"], full_name):
            return False, "Invalid full name"
        if not re.match(patterns["email"], email):
            return False, "Invalid email"

        return True, ""

    def initialize(self):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    fullName TEXT NOT NULL DEFAULT '',
                    bio TEXT NOT NULL DEFAULT '',
                    profile_photo TEXT NOT NULL DEFAULT '',
                    failed_attempts INTEGER DEFAULT 0,
                    lockout_until TEXT DEFAULT NULL,
                    reset_token TEXT DEFAULT NULL,
                    reset_token_expiry TEXT DEFAULT NULL
                )
            """)

            # Add columns if they don't exist (for existing databases)
            columns_to_add = [
                ("fullName", "TEXT NOT NULL DEFAULT ''"),
                ("bio", "TEXT NOT NULL DEFAULT ''"),
                ("profile_photo", "TEXT NOT NULL DEFAULT ''"),
                ("failed_attempts", "INTEGER DEFAULT 0"),
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise

            conn.commit()

    def add_user(self, username, password, full_name, email, bio="", profile_photo=""):
        valid, message = self._validate_user(username, password, full_name, email)
        if not valid:
            return message

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, email, password, fullName, bio, profile_photo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, email, password, full_name, bio, profile_photo))
                conn.commit()
            return "User Added."
        except Exception as e:
            return f"Error: {e}"

    def list_users(self) -> List[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password, fullName, email, bio, profile_photo
                FROM users
            """)
            rows = cursor.fetchall()
            return [User(*row) for row in rows]

    def find_user(self, username) -> Optional[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password, fullName, email, bio, profile_photo,
                    failed_attempts, lockout_until, reset_token, reset_token_expiry
                FROM users
                WHERE username = ?
            """, (username,))
            row = cursor.fetchone()
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    password=row[2],
                    full_name=row[3],
                    email=row[4],
                    bio=row[5],
                    profile_photo=row[6] or "",
                    failed_attempts=row[7] or 0,
                    lockout_until=row[8],
                    reset_token=row[9],
                    reset_token_expiry=row[10]
                )
            return None

    def find_by_email(self, email: str) -> Optional[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password, fullName, email, bio, profile_photo,
                    failed_attempts, lockout_until, reset_token, reset_token_expiry
                FROM users
                WHERE email = ?
            """, (email,))
            row = cursor.fetchone()
            if row:
                return User(
                    id=row[0],
                    username=row[1],
                    password=row[2],
                    full_name=row[3],
                    email=row[4],
                    bio=row[5],
                    profile_photo=row[6] or "",
                    failed_attempts=row[7] or 0,
                    lockout_until=row[8],
                    reset_token=row[9],
                    reset_token_expiry=row[10]
                )
            return None

    def change_password(self, username, new_password):
        if not re.match(r".+", new_password):
            return False

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET password = ?
                WHERE username = ?
            """, (new_password, username))
            conn.commit()
        return True

    def update_user(self, current_username, new_username, new_full_name, new_email, new_bio, new_profile_photo=None):
        if not re.match(r".+", new_username):
            return False, "Invalid username"

        if not re.match(r".+", new_full_name):
            return False, "Invalid full name"

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|gov|edu|net)$", new_email):
            return False, "Invalid email"

        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                if new_profile_photo is not None:
                    cursor.execute("""
                        UPDATE users
                        SET username = ?, fullName = ?, email = ?, bio = ?, profile_photo = ?
                        WHERE username = ?
                    """, (new_username, new_full_name, new_email, new_bio, new_profile_photo, current_username))
                else:
                    cursor.execute("""
                        UPDATE users
                        SET username = ?, fullName = ?, email = ?, bio = ?
                        WHERE username = ?
                    """, (new_username, new_full_name, new_email, new_bio, current_username))

                conn.commit()
            return True, "Account updated successfully."
        except Exception as e:
            return False, f"Error: {e}"

    def find_user_by_reset_token(self, token: str):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, password, fullName, email, bio, profile_photo,
                    failed_attempts, lockout_until, reset_token, reset_token_expiry
                FROM users
                WHERE reset_token = ?
            """, (token,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "password": row[2],
                    "fullName": row[3],
                    "email": row[4],
                    "bio": row[5],
                    "profile_photo": row[6],
                    "failed_attempts": row[7],
                    "lockout_until": row[8],
                    "reset_token": row[9],
                    "reset_token_expiry": row[10]
                }
            return None

    def update_failed_attempts(self, user_id: int, failed_attempts: int, lockout_until: str = None):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET failed_attempts = ?, lockout_until = ?
                WHERE id = ?
            """, (failed_attempts, lockout_until, user_id))
            conn.commit()

    def clear_failed_attempts(self, user_id: int):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET failed_attempts = 0, lockout_until = NULL
                WHERE id = ?
            """, (user_id,))
            conn.commit()

    def set_reset_token(self, user_id: int, token: str, expiry: str):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET reset_token = ?, reset_token_expiry = ?
                WHERE id = ?
            """, (token, expiry, user_id))
            conn.commit()

    def clear_reset_token(self, user_id: int):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users
                SET reset_token = NULL, reset_token_expiry = NULL,
                    failed_attempts = 0, lockout_until = NULL
                WHERE id = ?
            """, (user_id,))
            conn.commit()

    def delete_user(self, username):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
        return True
