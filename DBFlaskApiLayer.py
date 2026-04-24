from flask import Flask, request, jsonify
from user_repository import UserRepository

app = Flask(__name__)
repo = UserRepository("users.db")

repo.initialize()


@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    result = repo.add_user(
        data["username"],
        data["password"],
        data["full_name"],
        data["email"]
    )
    return jsonify({"message": result})


@app.route("/users", methods=["GET"])
def get_users():
    users = repo.list_users()
    return jsonify([u.__dict__ for u in users])


@app.route("/users/<username>", methods=["GET"])
def get_user(username):
    user = repo.find_user(username)
    if user:
        return jsonify(user.__dict__)
    return jsonify({"error": "User not found"}), 404


@app.route("/users/<username>", methods=["DELETE"])
def delete_user(username):
    repo.delete_user(username)
    return jsonify({"message": "User deleted"})


@app.route("/users/<username>/password", methods=["PUT"])
def update_password(username):
    data = request.json
    success = repo.change_password(username, data["password"])
    return jsonify({"success": success})


if __name__ == "__main__":
    app.run(debug=True)