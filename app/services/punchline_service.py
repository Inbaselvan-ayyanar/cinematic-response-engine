from typing import Any, Dict, List

from fastapi import BackgroundTasks
from pymongo.errors import DuplicateKeyError

from app.db.mongodb import (
    punchlines_collection,
    movie_dialogues_collection
)

from app.services.llm_service import (
    generate_movie_punchline,
    generate_contextual_response
)

from app.services.criteria_service import (
    build_preference_vector,
    build_profile_key
)


SIMILARITY_THRESHOLD = 0.75
VECTOR_SEARCH_LIMIT = 5


# ==========================================================
# HELPER
# ==========================================================

def serialize_dialogue(document: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert MongoDB dialogue document into a safe object
    that can be passed to Gemini.
    """

    return {
        "id": str(document.get("_id")),
        "movie_id": document.get("movie_id"),
        "actor_id": document.get("actor_id"),
        "character": document.get("character"),
        "dialogue": document.get("dialogue"),
        "preference": document.get("preference"),
        "criteria": document.get("criteria"),
        "is_default": document.get("is_default", False)
    }


# ==========================================================
# BACKGROUND GENERATION
#
# CALL 1
#   Mongo candidates + movie context + preferences
#       ->
#   Best movie dialogue
#
# CALL 2
#   Same context + preferences + selected dialogue
#       ->
#   Personalized DIG + dialogue
#
#       ->
#   Store in MongoDB
# ==========================================================

def generate_and_store_punchline(
    movie_id: str,
    actor_id: str,
    genres: List[str],
    user_preferences: Dict[str, Any],
    context: Dict[str, Any]
):

    print(
        f"[BACKGROUND] Started: "
        f"{movie_id} / {actor_id}"
    )

    try:

        # ==================================================
        # 1. Build criteria and preference vector
        # ==================================================

        criteria, preference_vector, vector_dimensions = (
            build_preference_vector(
                user_preferences=user_preferences,
                genres=genres
            )
        )

        print(
            f"[BACKGROUND] Criteria: {criteria}"
        )

        # ==================================================
        # 2. Build profile key
        # ==================================================

        profile_key = build_profile_key(
            movie_id=movie_id,
            actor_id=actor_id,
            genres=genres,
            criteria=criteria
        )

        print(
            f"[BACKGROUND] Profile key: {profile_key}"
        )

        # ==================================================
        # 3. Check duplicate generation
        # ==================================================

        existing = punchlines_collection.find_one(
            {
                "profile_key": profile_key
            }
        )

        if existing:

            print(
                "[BACKGROUND] Skipped - "
                f"profile already exists: {profile_key}"
            )

            return

        # ==================================================
        # 4. Get available movie dialogues
        #
        # IMPORTANT:
        # Gemini cannot know what exists in MongoDB.
        # We explicitly pass the available candidates.
        # ==================================================

        raw_dialogues = list(
            movie_dialogues_collection.find(
                {
                    "movie_id": movie_id,
                    "actor_id": actor_id
                }
            )
        )

        available_dialogues = [
            serialize_dialogue(d)
            for d in raw_dialogues
            if d.get("dialogue")
        ]

        print(
            "[BACKGROUND] Available dialogues: "
            f"{len(available_dialogues)}"
        )

        # ==================================================
        # 5. Get default dialogue
        # ==================================================

        default_dialogue_document = (
            movie_dialogues_collection.find_one(
                {
                    "movie_id": movie_id,
                    "is_default": True
                }
            )
        )

        default_dialogue = None

        if default_dialogue_document:

            default_dialogue = serialize_dialogue(
                default_dialogue_document
            )

            print(
                "[BACKGROUND] Default dialogue found."
            )

        else:

            print(
                "[BACKGROUND] No default dialogue found."
            )

        # ==================================================
        # GEMINI CALL 1
        #
        # Select the best available actual dialogue.
        #
        # Preference order:
        #
        # highest weight
        #       ↓
        # next highest
        #       ↓
        # ...
        #       ↓
        # default dialogue
        # ==================================================

        print(
            "[BACKGROUND] Starting Gemini Call 1..."
        )

        try:

            movie_punchline = generate_movie_punchline(
                context=context,
                criteria=criteria,
                available_dialogues=available_dialogues,
                default_dialogue=default_dialogue
            )

        except Exception as e:

            print(
                "[BACKGROUND] Gemini Call 1 FAILED: "
                f"{movie_id} / {actor_id}"
            )

            print(
                f"[BACKGROUND] Error: {e}"
            )

            return

        if not movie_punchline:

            print(
                "[BACKGROUND] Empty movie punchline: "
                f"{movie_id} / {actor_id}"
            )

            return

        print(
            "[BACKGROUND] Gemini Call 1 completed."
        )

        print(
            f"[BACKGROUND] Selected dialogue: "
            f"{movie_punchline}"
        )

        # ==================================================
        # GEMINI CALL 2
        #
        # Generate:
        #
        # Personalized DIG
        #       +
        # Selected actual movie dialogue
        # ==================================================

        print(
            "[BACKGROUND] Starting Gemini Call 2..."
        )

        try:

            final_response = generate_contextual_response(
                context=context,
                criteria=criteria,
                movie_punchline=movie_punchline
            )

        except Exception as e:

            print(
                "[BACKGROUND] Gemini Call 2 FAILED: "
                f"{movie_id} / {actor_id}"
            )

            print(
                f"[BACKGROUND] Error: {e}"
            )

            return

        if not final_response:

            print(
                "[BACKGROUND] Empty final response: "
                f"{movie_id} / {actor_id}"
            )

            return

        print(
            "[BACKGROUND] Gemini Call 2 completed."
        )

        # ==================================================
        # 6. Prepare MongoDB document
        # ==================================================

        document = {

            "movie_id": movie_id,

            "actor_id": actor_id,

            "character": context.get(
                "character"
            ),

            "genres": genres,

            "criteria": criteria,

            "preference_vector": preference_vector,

            "vector_dimensions": vector_dimensions,

            "profile_key": profile_key,

            # Selected actual movie dialogue
            "movie_punchline": movie_punchline,

            # Final DIG + dialogue
            "response": final_response,

            "source": "gemini",

            "generation_status": "completed"
        }

        # ==================================================
        # 7. Store generated response
        # ==================================================

        try:

            punchlines_collection.insert_one(
                document
            )

            print(
                "[BACKGROUND] Successfully stored: "
                f"{movie_id} / {actor_id}"
            )

        except DuplicateKeyError:

            print(
                "[BACKGROUND] Duplicate prevented: "
                f"{profile_key}"
            )

            return

    except Exception as e:

        print(
            "[BACKGROUND] FAILED: "
            f"{movie_id} / {actor_id}"
        )

        print(
            f"[BACKGROUND] Error: {e}"
        )


# ==========================================================
# MAIN PUNCHLINE SERVICE
# ==========================================================

def get_punchline(
    movie_id: str,
    actor_id: str,
    genres: List[str],
    user_preferences: Dict[str, Any],
    context: Dict[str, Any],
    background_tasks: BackgroundTasks
):

    print(
        f"[SERVICE] Request: "
        f"{movie_id} / {actor_id}"
    )

    # ==================================================
    # 1. Build criteria and vector
    # ==================================================

    criteria, preference_vector, vector_dimensions = (
        build_preference_vector(
            user_preferences=user_preferences,
            genres=genres
        )
    )

    print(
        f"[SERVICE] Criteria: {criteria}"
    )

    # ==================================================
    # 2. Build profile key
    # ==================================================

    profile_key = build_profile_key(
        movie_id=movie_id,
        actor_id=actor_id,
        genres=genres,
        criteria=criteria
    )

    print(
        f"[SERVICE] Profile key: {profile_key}"
    )

    # ==================================================
    # 3. Exact profile lookup
    # ==================================================

    existing = punchlines_collection.find_one(
        {
            "profile_key": profile_key
        }
    )

    if existing:

        print(
            "[SERVICE] Exact profile match found."
        )

        return format_result(
            document=existing,
            source=existing.get(
                "source",
                "database"
            ),
            matched=True
        )

    # ==================================================
    # 4. Vector search
    # ==================================================

    vector_pipeline = [

        {
            "$vectorSearch": {

                "index": "vector_index",

                "path": "preference_vector",

                "queryVector": preference_vector,

                "numCandidates": 50,

                "limit": VECTOR_SEARCH_LIMIT,

                "filter": {

                    "movie_id": {
                        "$eq": movie_id
                    },

                    "actor_id": {
                        "$eq": actor_id
                    },

                    "genres": {
                        "$in": genres
                    }
                }
            }
        },

        {
            "$project": {

                "_id": 1,

                "movie_id": 1,

                "actor_id": 1,

                "character": 1,

                "genres": 1,

                "criteria": 1,

                "preference_vector": 1,

                "vector_dimensions": 1,

                "profile_key": 1,

                "response": 1,

                "punchline": 1,

                "movie_punchline": 1,

                "source": 1,

                "score": {
                    "$meta": "vectorSearchScore"
                }
            }
        }
    ]

    try:

        similar_results = list(
            punchlines_collection.aggregate(
                vector_pipeline
            )
        )

    except Exception as e:

        print(
            f"[SERVICE] Vector search failed: {e}"
        )

        similar_results = []

    # ==================================================
    # 5. Check vector similarity
    # ==================================================

    if similar_results:

        best_match = similar_results[0]

        similarity_score = best_match.get(
            "score",
            0.0
        )

        print(
            "[SERVICE] Best similarity: "
            f"{similarity_score}"
        )

        # ==================================================
        # Similarity >= 75%
        # ==================================================

        if similarity_score >= SIMILARITY_THRESHOLD:

            matched_response = best_match.get(
                "response"
            )

            if not matched_response:

                matched_response = best_match.get(
                    "punchline"
                )

            return {

                "id": str(
                    best_match["_id"]
                ),

                "movie_id": best_match[
                    "movie_id"
                ],

                "actor_id": best_match[
                    "actor_id"
                ],

                "character": context.get(
                    "character",
                    best_match.get(
                        "character"
                    )
                ),

                "response": matched_response,

                "source": best_match.get(
                    "source",
                    "database"
                ),

                "matched": True,

                "match_type": "vector",

                "generation_queued": False,

                "similarity": similarity_score
            }

    # ==================================================
    # 6. No exact/vector match
    #
    # IMPORTANT:
    # We DO NOT check whether default exists before
    # queuing Gemini.
    #
    # Gemini must always get a chance to generate.
    # ==================================================

    print(
        "[SERVICE] No exact/vector match."
    )

    # ==================================================
    # 7. Get default dialogue
    #
    # Only used as immediate fallback while Gemini runs.
    # ==================================================

    default_dialogue = (
        movie_dialogues_collection.find_one(
            {
                "movie_id": movie_id,
                "is_default": True
            }
        )
    )

    # ==================================================
    # 8. ALWAYS queue Gemini
    # ==================================================

    print(
        "[SERVICE] Queueing Gemini generation..."
    )

    background_tasks.add_task(
        generate_and_store_punchline,

        movie_id,

        actor_id,

        genres,

        user_preferences,

        context
    )

    # ==================================================
    # 9. Return immediate response
    # ==================================================

    if default_dialogue:

        print(
            "[SERVICE] Returning default while "
            "Gemini generates."
        )

        return {

            "id": str(
                default_dialogue["_id"]
            ),

            "movie_id": movie_id,

            "actor_id": actor_id,

            "character": context.get(
                "character",
                default_dialogue.get(
                    "character"
                )
            ),

            "response": default_dialogue[
                "dialogue"
            ],

            "source": "default",

            "matched": False,

            "match_type": "default",

            "generation_queued": True,

            "similarity": None
        }

    # ==================================================
    # 10. No default dialogue
    #
    # Gemini is STILL running.
    # ==================================================

    print(
        "[SERVICE] No default dialogue."
    )

    return {

        "id": None,

        "movie_id": movie_id,

        "actor_id": actor_id,

        "character": context.get(
            "character"
        ),

        "response": (
            "Generating personalized response..."
        ),

        "source": "gemini",

        "matched": False,

        "match_type": "generation",

        "generation_queued": True,

        "similarity": None
    }


# ==========================================================
# FORMAT RESULT
# ==========================================================

def format_result(
    document: Dict[str, Any],
    source: str,
    matched: bool
):

    response = document.get(
        "response"
    )

    if not response:

        response = document.get(
            "punchline"
        )

    return {

        "id": str(
            document["_id"]
        ),

        "movie_id": document[
            "movie_id"
        ],

        "actor_id": document[
            "actor_id"
        ],

        "character": document.get(
            "character"
        ),

        "response": response,

        "source": source,

        "matched": matched,

        "match_type": "exact",

        "generation_queued": False,

        "similarity": None
    }