from app.db.mongodb import db


movies_collection = db["movies"]


def get_movie(movie_id: str):

    return movies_collection.find_one(
        {
            "movie_id": movie_id
        },
        {
            "_id": 0
        }
    )


def get_actor(movie_id: str, actor_id: str):

    movie = movies_collection.find_one(
        {
            "movie_id": movie_id,
            "actors.actor_id": actor_id
        },
        {
            "_id": 0
        }
    )

    if not movie:
        return None

    for actor in movie["actors"]:
        if actor["actor_id"] == actor_id:
            return actor

    return None