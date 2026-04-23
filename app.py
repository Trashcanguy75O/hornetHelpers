from flask import Flask, render_template, request
from DBMethods import UserRepository
from auth import auth

app = Flask(__name__)
app.secret_key = 'dev'
app.register_blueprint(auth)

repo = UserRepository("database.db")
repo.initialize()

@app.route("/homepage")
def home():
    return render_template("homepage.html")

@app.route("/new_account")
def new_account():
    return render_template("new_account.html")

@app.route("/forgot_username", methods=["GET", "POST"])
def username():
    if request.method == "POST":
        user_input = request.form["user"]
        user = repo.find_by_email(user_input)
        if user:
            # send username email here
            return render_template("forgot_username.html", found=True)
    return render_template("forgot_username.html", found=False)

@app.route("/forgot_password", methods=["GET", "POST"])
def password():
    if request.method == "POST":
        user_input = request.form["user"]
        user = repo.find_user(user_input) or repo.find_by_email(user_input)
        if user:
            # send password reset email here
            return render_template("forgot_password.html", found=True, name=user.full_name)
    return render_template("forgot_password.html", found=False)

if __name__ == "__main__":
    app.run(debug=True)