from flask import Flask, render_template
from flask import url_for
#from acc_recovery import hello_world

app = Flask(__name__)

@app.route("/account_recovery")
def recovery():
    return render_template("acc_recovery.html")

if __name__ == "__main__":
    app.run(debug=True)