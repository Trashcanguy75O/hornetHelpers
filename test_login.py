from DBMethods import UserRepository

repo = UserRepository("database.db")
repo.initialize()
repo.add_user("testuser", "testpw", "testuser", "test@gmail.com")
print("Success!")