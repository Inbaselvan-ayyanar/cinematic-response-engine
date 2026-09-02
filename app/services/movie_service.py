from app.db.movie_repository import get_movie, get_actor


def get_movie_details(movie_id: str):

    movie = get_movie(movie_id)

    if not movie:
        return None

    return movie


def get_movie_actor(movie_id: str, actor_id: str):

    actor = get_actor(
        movie_id,
        actor_id
    )

    return actor