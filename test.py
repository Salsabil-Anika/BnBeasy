from config import users_collection

try:
    print("Number of users:", users_collection.count_documents({}))
except Exception as e:
    print("Connection failed:", e)
