from fastapi import APIRouter, HTTPException

from app.services.movie_service import (
    get_movie_details,
    get_movie_actor
)


router = APIRouter()


@router.get("/movies/{movie_id}")
def movie_details(movie_id: str):

    movie = get_movie_details(movie_id)

    if not movie:
        raise HTTPException(
            status_code=404,
            detail="Movie not found"
        )

    return movie


@router.get("/movies/{movie_id}/actors/{actor_id}")
def movie_actor(
    movie_id: str,
    actor_id: str
):

    actor = get_movie_actor(
        movie_id,
        actor_id
    )

    if not actor:
        raise HTTPException(
            status_code=404,
            detail="Actor not found in this movie"
        )

    return actor