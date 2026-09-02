import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("MONGO_URI")

print("URI loaded:", bool(uri))
print("Using Atlas:", uri.startswith("mongodb+srv://"))

from app.db.mongodb import db

print("Database:", db.name)
print("Collections:", db.list_collection_names())