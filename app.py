from flask import Flask, render_template, request, flash, redirect, url_for, session
from DBMethods import UserRepository
import bcrypt
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import re
from pathlib import Path
from werkzeug.utils import secure_filename
from acc_recovery import send_recovery_email, send_username_email, generate_hashed_password

load_dotenv()

app = Flask(__name__)
#app.secret_key = os.getenv("SECRET_KEY")
app.secret_key = os.getenv("SECRET_KEY", "temp_secret_key_for_development")

repo = UserRepository("hornethelpers.db")
UPLOAD_FOLDER = Path("static/uploads/profile_photos")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

def get_current_username():
    return session.get("username")


def is_valid_email(email):
    valid_email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|net|org|edu|gov)$"
    return bool(re.match(valid_email_pattern, email))


def is_valid_password(password):
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(pattern, password))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/homepage")
def homepage():
    return render_template("homepage.html")


@app.route("/acc_login", methods=["GET", "POST"])
def acc_login():
    if request.method == "POST":
        username = request.form["user"].strip()
        password = request.form["password"].strip()

        user = repo.find_user(username)

        if not user:
            flash("Invalid username or password.")
            return redirect(url_for("acc_login"))

        if user.lockout_until:
            lockout_time = datetime.fromisoformat(user.lockout_until)
            if datetime.now() < lockout_time:
                flash("Account is locked. Please try again later.")
                return redirect(url_for("acc_login"))

        if bcrypt.checkpw(password.encode("utf-8"), user.password.encode("utf-8")):
            repo.clear_failed_attempts(user.id)

            session["user_id"] = user.id
            session["username"] = user.username

            return redirect(url_for("homepage"))
        else:
            failed_attempts = user.failed_attempts + 1

            if failed_attempts >= 5:
                lockout_time = datetime.now() + timedelta(minutes=15)
                repo.update_failed_attempts(user.id, failed_attempts, lockout_time.isoformat())
                flash("Too many failed attempts. Account is locked for 15 minutes.")
            else:
                repo.update_failed_attempts(user.id, failed_attempts)
                flash("Incorrect username or password. Please try again.")

            return redirect(url_for("acc_login"))

    return render_template("acc_login.html")

@app.route("/new_account", methods=["GET", "POST"])
def new_account():
    if request.method == "POST":
        # 1. Get data from the form (including full_name)
        full_name = request.form["full_name"].strip()
        username = request.form["user"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        confirm_password = request.form["confirm_password"].strip()

        # 2. Validation
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("new_account"))

        if not is_valid_email(email):
            flash("Invalid email address.")
            return redirect(url_for("new_account"))

        if not is_valid_password(password):
            flash("Password must be 8+ characters with a letter and a number.")
            return redirect(url_for("new_account"))

        if repo.find_user(username) or repo.find_by_email(email):
            flash("Username or Email already exists.")
            return redirect(url_for("new_account"))

        # 3. Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # 4. Call repo.add_user with matching arguments:
        # Your method: add_user(self, username, password, full_name, email, bio, photo)
        result_message = repo.add_user(username, hashed_password, full_name, email)

        if result_message == "User Added.":
            flash("Account created successfully! Please log in.")
            return redirect(url_for("acc_login"))
        else:
            flash(f"Error: {result_message}")
            return redirect(url_for("new_account"))

    return render_template("new_account.html")



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

        user = repo.find_by_email(email)

        if user:
            send_username_email(email, user.username)

        flash("If this email is associated with an account, you should receive an email shortly!")
    return render_template("forgot_username.html")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        if not is_valid_email(email):
            flash("invalid email entered.")
            return redirect(url_for("forgot_password"))

        user = repo.find_by_email(email)

        if user:
            reset_token = secrets.token_urlsafe(32)
            reset_token_expiry = datetime.now() + timedelta(hours=1)

            repo.set_reset_token(user.id, reset_token, reset_token_expiry.isoformat())

            send_recovery_email(email, reset_token)

        flash("If an account exists, you should receive a password reset link!")
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    user = repo.find_user_by_reset_token(token)

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

        repo.change_password(user["username"], hashed_password)
        repo.clear_reset_token(user["id"])

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

    current_user = repo.find_user(current_username)
    if not current_user:
        return redirect(url_for("acc_login"))

    new_username = request.form["username"].strip()
    full_name = request.form["full_name"].strip()
    email = request.form["email"].strip()
    bio = request.form["bio"].strip()

    photo = request.files.get("profile_photo")
    profile_photo_path = None

    if photo and photo.filename:
        if not allowed_file(photo.filename):
            user = repo.find_user(current_username)
            return render_template(
                "account_edit.html",
                user=user,
                message="Invalid file type. Please upload a PNG, JPG, or JPEG image.",
                success=False
            )

        extension = photo.filename.rsplit(".", 1)[1].lower()
        filename = secure_filename(f"user_{current_user.id}.{extension}")
        save_path = UPLOAD_FOLDER / filename
        photo.save(save_path)
        profile_photo_path = f"uploads/profile_photos/{filename}"

    success, message = repo.update_user(
        current_username,
        new_username,
        full_name,
        email,
        bio,
        profile_photo_path
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
    repo.initialize()
    app.run(debug=True)