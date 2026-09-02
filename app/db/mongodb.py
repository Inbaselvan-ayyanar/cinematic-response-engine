from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsAllowInvalidCertificates=True
)

db = client["punchline_db"]

punchlines_collection = db["punchlines"]
movie_dialogues_collection = db["movie_dialogues"]


# --------------------------------------------------
# Indexes
# --------------------------------------------------

# Used for movie/actor/genre filtering
punchlines_collection.create_index(
    [
        ("movie_id", 1),
        ("actor_id", 1),
        ("genres", 1)
    ]
)


# Prevent duplicate punchline profiles
punchlines_collection.create_index(
    "profile_key",
    unique=True
)


print("MongoDB connected")