from flask import Flask, render_template
from flask import url_for
#from acc_recovery import hello_world

app = Flask(__name__)

@app.route("/account_recovery")
def recovery():
    return render_template("acc_recovery.html")

@app.route("/acc_login")
def login():
    return render_template("acc_login.html")

@app.route("/forgot_username")
def username():
    return render_template("forgot_username.html")

@app.route("/forgot_password")
def password():
    return render_template("forgot_password.html")

if __name__ == "__main__":
    app.run(debug=True)