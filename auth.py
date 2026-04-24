from flask import Blueprint, render_template, request, flash, session, redirect, url_for
# from datetime import datetime, timedelta
import sqlite3

auth = Blueprint('auth', __name__)

def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

@auth.route("/acc_login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["user"]
        password = request.form["password"]

        ourConnection = get_db_connection()
        cursor = ourConnection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if not user:
            flash("Username not found.")
            return render_template("acc_login.html")

        # if user["lockout_until"]:
        #     lockout_time = datetime.fromisoformat(user["lockout_until"])
        #     if datetime.now() < lockout_time:
        #         flash("Account is locked. Please try again later.")
        #         ourConnection.close()
        #         return render_template("acc_login.html")

        if user["password"] == password:
            # cursor.execute("UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE id = ?", (user["id"],))
            # ourConnection.commit()
            ourConnection.close()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("home"))
        else:
            # failed_attempts = user["failed_attempts"] + 1
            # if failed_attempts >= 5:
            #     lockout_time = datetime.now() + timedelta(minutes=15)
            #     cursor.execute("UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE id = ?", (failed_attempts, lockout_time.isoformat(), user["id"]))
            #     ourConnection.commit()
            #     ourConnection.close()
            #     flash("Too many failed attempts. Account is locked for 15 minutes.")
            #     return render_template("acc_login.html")
            ourConnection.close()
            flash("Incorrect password. Please try again.")
            return render_template("acc_login.html")

    return render_template("acc_login.html")

@auth.route("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("username", None)
    return redirect(url_for("auth.login"))