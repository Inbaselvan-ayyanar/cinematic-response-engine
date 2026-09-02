from pydantic import BaseModel
from typing import List


class Actor(BaseModel):
    actor_id: str
    actor_name: str
    character: str


class Movie(BaseModel):
    movie_id: str
    title: str
    language: str
    actors: List[Actor]
    genres: List[str]