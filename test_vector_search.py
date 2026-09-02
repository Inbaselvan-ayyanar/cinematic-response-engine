from app.db.mongodb import punchlines_collection
from app.config.vector_schema import VECTOR_SIZE

from app.db.mongodb import client

info = client.server_info()

print("MongoDB version:", info.get("version"))
print("Server:", info.get("gitVersion"))

# Get one existing punchline
document = punchlines_collection.find_one(
    {
        "preference_vector": {
            "$exists": True
        }
    }
)

if not document:
    print("No punchline documents found.")
    exit()


query_vector = document["preference_vector"]


pipeline = [
    {
        "$vectorSearch": {
            "index": "punchline_vector_index",
            "path": "preference_vector",
            "queryVector": query_vector,
            "numCandidates": 10,
            "limit": 3
        }
    },
    {
        "$project": {
            "_id": 1,
            "movie_id": 1,
            "actor_id": 1,
            "genres": 1,
            "punchline": 1,
            "score": {
                "$meta": "vectorSearchScore"
            }
        }
    }
]


results = list(
    punchlines_collection.aggregate(pipeline)
)


print(f"Vector size: {VECTOR_SIZE}")
print(f"Query document: {document['_id']}")
print()
print("Search results:")
print()


for result in results:
    print(
        f"ID: {result['_id']}"
    )

    print(
        f"Movie: {result.get('movie_id')}"
    )

    print(
        f"Actor: {result.get('actor_id')}"
    )

    print(
        f"Genres: {result.get('genres')}"
    )

    print(
        f"Score: {result.get('score')}"
    )

    print(
        f"Punchline: {result.get('punchline')}"
    )

    print("-" * 60)