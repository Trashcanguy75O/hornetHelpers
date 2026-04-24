from flask import Flask, render_template, request, flash, redirect, url_for, session    #Framework we used to build our website
import sqlite3  #Python built in for interacting with SQLite databases, we used this to store user data like usernames, emails, and hashed passwords
import bcrypt   #Python built in for hashing passwords, we used this for securely storing user passwords in the database
import secrets  #Python built in for generating secure tokens, we used this for password reset tokens
from datetime import datetime, timedelta    #Python built in for handling dates and times, we used this for lockout and reset token expiration
from dotenv import load_dotenv
import os
import re
from acc_recovery import send_recovery_email, send_username_email, generate_hashed_password   #Functions we created for sending recovery emails and generating a hashed password

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") #Setting the secret key for Flask sessions, we load this from our .env file for security

#Validation functions for email and password inputs
def is_valid_email(email):
    valid_email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|net|org|edu|gov)$"
    return bool(re.match(valid_email_pattern, email))

#Makes sure it's at least 8 chars long with at least one letter and number
def is_valid_password(password):
    pattern = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*?&]{8,}$"
    return bool(re.match(pattern, password))

#Database functions
def get_db_connection():
    db_connection = sqlite3.connect('hornethelpers.db')
    db_connection.row_factory = sqlite3.Row
    return db_connection

#Initializing our database and creating the users table if it doesn't exist
def init_db():
    connectionToDB = get_db_connection()
    cursor = connectionToDB.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            lockout_until TEXT DEFAULT NULL,
            reset_token TEXT DEFAULT NULL,
            reset_token_expiry TEXT DEFAULT NULL
        )
    ''')

    connectionToDB.commit()
    connectionToDB.close()

#Our ROUTES
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

        # Check if the account is locked out
        if user["lockout_until"]:
            lockout_time = datetime.fromisoformat(user["lockout_until"])
            if datetime.now() < lockout_time:
                connectionToDB.close()
                flash("Account is locked. Please try again later.")
                return redirect(url_for("acc_login"))

        #Checking the password using bcrypt. 
        #If the password is correct, we reset the failed attempts and lockout status
        if bcrypt.checkpw(password.encode('utf-8'), user["password"].encode('utf-8')):
            cursor.execute("UPDATE users SET failed_attempts = 0, lockout_until = NULL WHERE id = ?", (user["id"],))
            connectionToDB.commit()
            connectionToDB.close()

            #We then start a session, and redirect to the homepage.
            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect(url_for("homepage"))
        else:
            # If password is incorrect, we increment failed attempts
            failed_attempts = user["failed_attempts"] + 1

            # If failed attempts reach 5, we lock the account for 15 minutes
            if failed_attempts >= 5:
                lockout_time = datetime.now() + timedelta(minutes=15)
                cursor.execute("UPDATE users SET failed_attempts = ?, lockout_until = ? WHERE id = ?", (failed_attempts, lockout_time.isoformat(), user["id"]))
                flash("Too many failed attempts. Account is locked for 15 minutes.")
            else: #If the password is incorrect but failed attempts are less than 5, we just update the failed attempts count
                cursor.execute("UPDATE users SET failed_attempts = ? WHERE id = ?", (failed_attempts, user["id"]))
                flash("Incorrect username or password. Please try again.")
            
            connectionToDB.commit()
            connectionToDB.close()    
            return redirect(url_for("acc_login"))

@app.route("/new_account")
def new_account():
    return render_template("new_account.html")


@app.route("/forgot_username", methods=["GET", "POST"])
def forgot_username():
    if request.method == "POST":
        email = request.form["email"].strip().lower()

        #validating the email
        if not is_valid_email(email):
            flash("invalid email entered.")
            return redirect(url_for("forgot_username"))

        #If the email is valid, we check our database to see if it is associated with an account
        connectionToDB = get_db_connection()
        cursor = connectionToDB.cursor()
        cursor.execute("SELECT username FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        connectionToDB.close()
        
        #If the email is not associated with an account we flash an error message
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
            # Generating a secure reset token and making it expire in 1 hour
            reset_token = secrets.token_urlsafe(32)
            reset_token_expiry = datetime.now() + timedelta(hours=1)  

            # Storing the reset token and its expiry in the database
            cursor.execute("UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?", (reset_token, reset_token_expiry.isoformat(), user["id"]))
            connectionToDB.commit()
            
            # Sending the recovery email with the reset token
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
        
        # Update the user's password
        hashed_password = generate_hashed_password(new_password)
        
        connectionToDB = get_db_connection()
        cursor = connectionToDB.cursor()
        cursor.execute("UPDATE users SET password = ?, reset_token = NULL, reset_token_expiry = NULL, failed_attempts = 0, lockout_until = NULL WHERE id = ?", (hashed_password, user["id"],))
        connectionToDB.commit()
        connectionToDB.close()

        flash("Password reset successfully.")
        return redirect(url_for("acc_login"))

    return render_template("reset_password.html", token=token)

if __name__ == "__main__":
    init_db() #Initialize our database
    app.run(debug=True)