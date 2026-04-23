from flask import Flask, render_template, request, redirect, url_for 
from DBMethods import UserRepository

app = Flask(__name__)

repo = UserRepository("hornet_helpers.db")
repo.initialize()

# Temporary scaffold for testing until login/session is connected
if repo.find_user("testuser") is None:
    repo.add_user("testuser", "password123", "Test User", "testuser@csus.edu")

def get_current_username():
    return "testuser" # This should also be replaced

@app.route("/homepage")
def home():
    return render_template("homepage.html")


@app.route("/acc_login")
def login():
    return render_template("acc_login.html")


@app.route("/new_account")
def new_account():
    return render_template("new_account.html")


@app.route("/forgot_username")
def username():
    return render_template("forgot_username.html")


@app.route("/forgot_password")
def password():
    return render_template("forgot_password.html")


@app.route("/account")
def account():
    username = get_current_username()
    user = repo.find_user(username)
    return render_template("account.html", user=user)

@app.route("/account/edit")
def account_edit():
    username = get_current_username()
    user = repo.find_user(username)
    return render_template("account_edit.html", user=user)

@app.route("/account/update", methods=["POST"])
def update_account():
    username = get_current_username()
    full_name = request.form["full_name"].strip()
    email = request.form["email"].strip()

    success, message = repo.update_user(username, full_name, email)

    if success:
        return redirect(url_for("account"))

    user = repo.find_user(username)
    return render_template(
        "account_edit.html",
        user=user,
        message=message,
        success=success
    )


if __name__ == "__main__":
    app.run(debug=True)