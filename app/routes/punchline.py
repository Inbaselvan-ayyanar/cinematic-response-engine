from fastapi import APIRouter, BackgroundTasks

from app.models.punchline import (
    PunchlineRequest,
    PunchlineResponse
)

from app.services.punchline_service import get_punchline


router = APIRouter(
    tags=["Punchlines"]
)


@router.post(
    "/punchlines",
    response_model=PunchlineResponse
)
def retrieve_punchline(
    request: PunchlineRequest,
    background_tasks: BackgroundTasks
):

    context = {
        "movie_title": request.movie_title,
        "actor_name": request.actor_name,
        "character": request.character
    }

    result = get_punchline(
        movie_id=request.movie_id,
        actor_id=request.actor_id,
        genres=request.genres,
        user_preferences=request.user_preferences,
        context=context,
        background_tasks=background_tasks
    )

    return result