from flask import Flask, render_template, request, flash, redirect, url_for, session
from DBMethods import UserRepository
import sqlite3
import bcrypt
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import re
from acc_recovery import send_recovery_email, send_username_email, generate_hashed_password

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

repo = UserRepository("hornethelpers.db")


def get_current_username():
    return session.get("username")


def is_valid_email(email):
    valid_email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|net|org|edu|gov)$"
    return bool(re.match(valid_email_pattern, email))


def is_valid_password(password):
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(pattern, password))


def get_db_connection():
    db_connection = sqlite3.connect("hornethelpers.db")
    db_connection.row_factory = sqlite3.Row
    return db_connection


def init_db():
    connectionToDB = get_db_connection()
    cursor = connectionToDB.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            fullName TEXT NOT NULL DEFAULT '',
            bio TEXT NOT NULL DEFAULT '',
            failed_attempts INTEGER DEFAULT 0,
            lockout_until TEXT DEFAULT NULL,
            reset_token TEXT DEFAULT NULL,
            reset_token_expiry TEXT DEFAULT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1].lower() for row in cursor.fetchall()]

    if "fullname" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN fullName TEXT NOT NULL DEFAULT ''")
    if "bio" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''")
    if "failed_attempts" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0")
    if "lockout_until" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN lockout_until TEXT DEFAULT NULL")
    if "reset_token" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token TEXT DEFAULT NULL")
    if "reset_token_expiry" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN reset_token_expiry TEXT DEFAULT NULL")

    connectionToDB.commit()
    connectionToDB.close()


@app.route("/homepage")
def homepage():
    return render_template("homepage.html")


@app.route("/acc_login", methods=["GET", "POST"])
def acc_login():
    if request.method == "POST":
        username = request.form["user"].strip()
        password = request.form["password"].strip()

        connectionToDB = get_db_connection()
        cursor = connectionToDB.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            connectionToDB.close()
            flash("Invalid username or password.")
            return redirect(url_for("acc_login"))

        if user["lockout_until"]:
            lockout_time = datetime.fromisoformat(user["lockout_until"])
            if datetime.now() < lockout_time:
                connectionToDB.close()
                flash("Account is locked. Please try again later.")
                return redirect(url_for("acc_login"))

        if bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            cursor.execute(
                "UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE id = ?",
                (user["id"],)
            )
            connectionToDB.commit()
            connectionToDB.close()

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("homepage"))
        else:
            failed_attempts = user["failed_attempts"] + 1

            if failed_attempts >= 5:
                lockout_time = datetime.now() + timedelta(minutes=15)
                cursor.execute(
                    "UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE id = ?",
                    (failed_attempts, lockout_time.isoformat(), user["id"])
                )
                flash("Too many failed attempts. Account is locked for 15 minutes.")
            else:
                cursor.execute(
                    "UPDATE users SET failed_attempts = ? WHERE id = ?",
                    (failed_attempts, user["id"])
                )
                flash("Incorrect username or password. Please try again.")

            connectionToDB.commit()
            connectionToDB.close()
            return redirect(url_for("acc_login"))

    return render_template("acc_login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("acc_login"))


@app.route("/new_account")
def new_account():
    return render_template("new_account.html")


@app.route("/forgot_username", methods=["GET", "POST"])
def forgot_username():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if not is_valid_email(email):
            flash("invalid email entered.")
            return redirect(url_for("forgot_username"))

        connectionToDB = get_db_connection()
        cursor = connectionToDB.cursor()
        cursor.execute("SELECT username FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        connectionToDB.close()

        if user:
            send_username_email(email, user["username"])

        flash("If this email is associated with an account, you should receive an email shortly!")
    return render_template("forgot_username.html")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if not is_valid_email(email):
            flash("invalid email entered.")
            return redirect(url_for("forgot_password"))

        connectionToDB = get_db_connection()
        cursor = connectionToDB.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            reset_token = secrets.token_urlsafe(32)
            reset_token_expiry = datetime.now() + timedelta(hours=1)

            cursor.execute(
                "UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?",
                (reset_token, reset_token_expiry.isoformat(), user["id"])
            )
            connectionToDB.commit()

            send_recovery_email(email, reset_token)

        connectionToDB.close()

        flash("If an account exists, you should receive a password reset link!")
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    connectionToDB = get_db_connection()
    cursor = connectionToDB.cursor()
    cursor.execute("SELECT * FROM users WHERE reset_token = ?", (token,))
    user = cursor.fetchone()
    connectionToDB.close()

    if (
        not user
        or not user["reset_token_expiry"]
        or datetime.fromisoformat(user["reset_token_expiry"]) < datetime.now()
    ):
        flash("Invalid or expired reset link.")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if new_password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("reset_password", token=token))

        if not is_valid_password(new_password):
            flash("Password must be at least 8 characters long and must contain at least 1 letter and number.")
            return redirect(url_for("reset_password", token=token))

        hashed_password = generate_hashed_password(new_password)

        connectionToDB = get_db_connection()
        cursor = connectionToDB.cursor()
        cursor.execute(
            "UPDATE users SET password = ?, reset_token = NULL, reset_token_expiry = NULL, failed_attempts = 0, lockout_until = NULL WHERE id = ?",
            (hashed_password, user["id"])
        )
        connectionToDB.commit()
        connectionToDB.close()

        flash("Password reset successfully.")
        return redirect(url_for("acc_login"))

    return render_template("reset_password.html", token=token)


@app.route("/account")
def account():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))

    user = repo.find_user(username)
    return render_template("account.html", user=user)


@app.route("/account/edit")
def account_edit():
    username = get_current_username()
    if not username:
        return redirect(url_for("acc_login"))

    user = repo.find_user(username)
    return render_template("account_edit.html", user=user)


@app.route("/account/update", methods=["POST"])
def update_account():
    current_username = get_current_username()
    if not current_username:
        return redirect(url_for("acc_login"))

    new_username = request.form["username"].strip()
    full_name = request.form["full_name"].strip()
    email = request.form["email"].strip()
    bio = request.form["bio"].strip()

    success, message = repo.update_user(
        current_username,
        new_username,
        full_name,
        email,
        bio
    )

    if success:
        session["username"] = new_username
        return redirect(url_for("account"))

    user = repo.find_user(current_username)
    return render_template(
        "account_edit.html",
        user=user,
        message=message,
        success=success
    )


if __name__ == "__main__":
    init_db()
    repo.initialize()
    app.run(debug=True)