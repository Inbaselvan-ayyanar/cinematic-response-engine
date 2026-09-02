from app.db.mongodb import punchlines_collection

result = punchlines_collection.delete_many({})

print(f"Deleted {result.deleted_count} documents")