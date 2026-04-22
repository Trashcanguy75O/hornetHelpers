import sqlite3
import re
from typing import List, Optional


class User:
    def __init__(self, id: int, username: str, password: str, full_name: str, email: str):
        self.id = id
        self.username = username
        self.password = password
        self.full_name = full_name
        self.email = email


class UserRepository:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def _connect(self):
        return sqlite3.connect(self.database_path)

    #(REGEX HOOKS)
    def _validate_user(self, username, password, full_name, email):
        # For now: accept any non-empty string
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
                CREATE TABLE IF NOT EXISTS Users (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Username TEXT NOT NULL UNIQUE,
                    Email TEXT NOT NULL UNIQUE,
                    Password TEXT NOT NULL,
                    FullName TEXT NOT NULL
                );
            """)
            conn.commit()

    def add_user(self, username, password, full_name, email):
        valid, message = self._validate_user(username, password, full_name, email)
        if not valid:
            return message

        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Users (Username, Email, Password, FullName)
                    VALUES (?, ?, ?, ?)
                """, (username, email, password, full_name))
                conn.commit()
            return "User Added."
        except Exception as e:
            return f"Error: {e}"

    def list_users(self) -> List[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Id, Username, Email, Password, FullName FROM Users")
            rows = cursor.fetchall()
            return [User(*row) for row in rows]

    def find_user(self, username) -> Optional[User]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Id, Username, Email, Password, FullName
                FROM Users WHERE Username = ?
            """, (username,))
            row = cursor.fetchone()
            return User(*row) if row else None
            
    def find_by_email(self, email: str) -> Optional[User]:
    with self._connect() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Id, Username, Email, Password, FullName
            FROM Users WHERE Email = ?
        """, (email,))
        row = cursor.fetchone()
        return User(*row) if row else None

    def change_password(self, username, new_password):
        if not re.match(r".+", new_password):
            return False

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE Users SET Password = ?
                WHERE Username = ?
            """, (new_password, username))
            conn.commit()
        return True

    def delete_user(self, username):
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM Users WHERE Username = ?", (username,))
            conn.commit()
        return True
