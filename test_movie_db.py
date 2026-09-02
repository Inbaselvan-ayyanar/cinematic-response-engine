from app.db.mongodb import db

print("Collections:")
print(db.list_collection_names())

print("\n" + "=" * 60)

for collection_name in db.list_collection_names():

    print(f"\nCOLLECTION: {collection_name}")
    print("-" * 60)

    collection = db[collection_name]

    documents = list(collection.find().limit(5))

    if not documents:
        print("No documents found.")
        continue

    for i, document in enumerate(documents, 1):

        print(f"\nDocument {i}:")
        print(document)