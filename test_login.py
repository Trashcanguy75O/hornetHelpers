from DBMethods import UserRepository
from acc_recovery import generate_hashed_password

repo = UserRepository("hornethelpers.db")
repo.initialize()

hashed_password = generate_hashed_password("testpw")
result = repo.add_user("testuser", hashed_password, "testuser", "test@gmail.com")
print(result)