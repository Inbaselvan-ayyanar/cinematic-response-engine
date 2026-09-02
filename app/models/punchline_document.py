from typing import Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field


class PunchlineDocument(BaseModel):

    movie_id: str
    actor_id: str

    genres: List[str]

    criteria: Dict[str, float]

    preference_vector: List[float]

    punchline: str

    source: str = "gemini"

    created_at: datetime = Field(
        default_factory=datetime.utcnow
    )

    version: int = 1