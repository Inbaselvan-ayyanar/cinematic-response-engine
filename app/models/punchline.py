from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class PunchlineRequest(BaseModel):
    movie_id: str
    actor_id: str
    movie_title: str
    actor_name: str
    character: str
    genres: List[str]

    user_preferences: Dict[str, float] = Field(
        default_factory=dict
    )


class PunchlineResponse(BaseModel):
    id: Optional[str] = None

    movie_id: str
    actor_id: str

    character: Optional[str] = None

    response: str

    source: str
    matched: bool
    match_type: str

    generation_queued: bool = False

    similarity: Optional[float] = None