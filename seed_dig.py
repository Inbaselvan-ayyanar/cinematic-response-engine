from app.db.mongodb import movie_dialogues_collection


dialogues = [
    {
        "movie_id": "leo_2023",
        "actor_id": "vijay",
        "character": "Leo",
        "dialogue": "YOUR ACTUAL LEO DIALOGUE HERE",
        "is_default": True
    },
    {
        "movie_id": "jailer_2023",
        "actor_id": "rajini",
        "character": "Muthuvel Pandian",
        "dialogue": "YOUR ACTUAL JAILER DIALOGUE HERE",
        "is_default": True
    }
]


result = movie_dialogues_collection.insert_many(dialogues)

print("Inserted documents:")
for inserted_id in result.inserted_ids:
    print(inserted_id)

print("\nTotal documents:",
      movie_dialogues_collection.count_documents({}))