from typing import Dict, List, Tuple

from app.config.genre_criteria import GENRE_CRITERIA
from app.config.vector_schema import VECTOR_DIMENSIONS


NUMBER_OF_BUCKETS = 5


def quantize(value: float) -> int:
    value = max(0.0, min(1.0, value))

    bucket = int(value * NUMBER_OF_BUCKETS)

    if bucket == NUMBER_OF_BUCKETS:
        bucket -= 1

    return bucket


def get_relevant_criteria(
    genres: List[str]
) -> Dict[str, float]:

    combined = {}

    for genre in genres:

        genre = genre.lower().strip()

        genre_criteria = GENRE_CRITERIA.get(
            genre,
            {}
        )

        for criterion, weight in genre_criteria.items():

            if criterion not in combined:
                combined[criterion] = weight

            else:
                combined[criterion] = max(
                    combined[criterion],
                    weight
                )

    return combined


def build_preference_vector(
    user_preferences: Dict[str, float],
    genres: List[str]
) -> Tuple[Dict[str, float], List[float], List[str]]:

    relevant = get_relevant_criteria(genres)

    criteria = {}
    vector = []

    # IMPORTANT:
    # Always use the same global dimension order.
    for name in VECTOR_DIMENSIONS:

        user_value = user_preferences.get(
            name,
            0.0
        )

        user_value = max(
            0.0,
            min(1.0, user_value)
        )

        genre_weight = relevant.get(
            name,
            0.0
        )

        effective_value = (
            user_value * genre_weight
        )

        criteria[name] = effective_value

        vector.append(effective_value)

    return criteria, vector, VECTOR_DIMENSIONS


def build_profile_key(
    movie_id: str,
    actor_id: str,
    genres: List[str],
    criteria: Dict[str, float]
) -> str:

    genre_part = ",".join(
        sorted(
            genre.lower().strip()
            for genre in genres
        )
    )

    bucket_values = []

    for name in VECTOR_DIMENSIONS:

        bucket = quantize(
            criteria.get(name, 0.0)
        )

        bucket_values.append(
            f"{name}:{bucket}"
        )

    criteria_part = "|".join(
        bucket_values
    )

    return (
        f"{movie_id}:"
        f"{actor_id}:"
        f"{genre_part}:"
        f"{criteria_part}"
    )