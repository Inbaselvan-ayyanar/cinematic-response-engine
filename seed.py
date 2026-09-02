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

movie_dialogues_collection = db["movie_dialogues"]


# Add new movie
new_movie = {
    "movie_id": "vikram_2022",
    "actor_id": "kamal",
    "character": "Karnan",
    "dialogue": "YOUR ACTUAL VIKRAM DIALOGUE HERE",
    "is_default": True
}

result = movie_dialogues_collection.insert_one(new_movie)

print("New movie added:")
print(result.inserted_id)