from flask import Flask, render_template
#from acc_recovery import hello_world

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(debug=True)