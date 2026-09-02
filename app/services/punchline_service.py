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


# ======================================================
# Background Task
#
# GEMINI CALL 1
#     ->
# Actual movie punchline
#
# GEMINI CALL 2
#     ->
# DIG + movie punchline
#
#     ->
# Store final response in MongoDB
# ======================================================

def generate_and_store_punchline(
    movie_id: str,
    actor_id: str,
    genres: list,
    user_preferences: dict,
    context: dict
):

    print(
        f"[BACKGROUND] Started: "
        f"{movie_id} / {actor_id}"
    )

    try:

        # --------------------------------------------------
        # 1. Build criteria and preference vector
        # --------------------------------------------------

        criteria, preference_vector, vector_dimensions = (
            build_preference_vector(
                user_preferences=user_preferences,
                genres=genres
            )
        )

        # --------------------------------------------------
        # 2. Build profile key
        # --------------------------------------------------

        profile_key = build_profile_key(
            movie_id=movie_id,
            actor_id=actor_id,
            genres=genres,
            criteria=criteria
        )

        # --------------------------------------------------
        # 3. Check duplicate
        # --------------------------------------------------

        existing = punchlines_collection.find_one(
            {
                "profile_key": profile_key
            }
        )

        if existing:

            print(
                f"[BACKGROUND] Skipped - "
                f"profile already exists: "
                f"{profile_key}"
            )

            return

        # ==================================================
        # GEMINI CALL 1
        #
        # Generate/select the movie punchline.
        #
        # This does NOT come from MongoDB.
        # Gemini receives:
        # - movie
        # - actor
        # - character
        # - genres
        # - user preferences
        # ==================================================

        print(
            "[BACKGROUND] Generating Gemini "
            "movie punchline..."
        )

        try:

            movie_punchline = generate_movie_punchline(
                context=context,
                criteria=criteria
            )

        except Exception as e:

            print(
                f"[BACKGROUND] Gemini Call 1 FAILED: "
                f"{movie_id} / {actor_id}"
            )

            print(
                f"[BACKGROUND] Error: {e}"
            )

            return

        if not movie_punchline:

            print(
                f"[BACKGROUND] Empty movie punchline: "
                f"{movie_id} / {actor_id}"
            )

            return

        print(
            "[BACKGROUND] Movie punchline generated."
        )

        # ==================================================
        # GEMINI CALL 2
        #
        # Generate:
        #
        # DIG + ACTUAL MOVIE PUNCHLINE
        #
        # Gemini Call 2 receives:
        # - movie
        # - actor
        # - character
        # - genres
        # - user preferences
        # - punchline from Gemini Call 1
        # ==================================================

        print(
            "[BACKGROUND] Generating Gemini "
            "contextual response..."
        )

        try:

            final_response = generate_contextual_response(
                context=context,
                criteria=criteria,
                movie_punchline=movie_punchline
            )

        except Exception as e:

            print(
                f"[BACKGROUND] Gemini Call 2 FAILED: "
                f"{movie_id} / {actor_id}"
            )

            print(
                f"[BACKGROUND] Error: {e}"
            )

            return

        # --------------------------------------------------
        # 6. Validate final response
        # --------------------------------------------------

        if not final_response:

            print(
                f"[BACKGROUND] Empty final response: "
                f"{movie_id} / {actor_id}"
            )

            return

        print(
            "[BACKGROUND] Final response generated."
        )

        # ==================================================
        # 7. Prepare MongoDB document
        # ==================================================

        document = {
            "movie_id": movie_id,
            "actor_id": actor_id,

            # IMPORTANT:
            # Save the character received in the request.
            "character": context.get("character"),

            "genres": genres,
            "criteria": criteria,

            "preference_vector": preference_vector,
            "vector_dimensions": vector_dimensions,
            "profile_key": profile_key,

            # Gemini 1 result.
            "movie_punchline": movie_punchline,

            # Gemini 2 result.
            # This is the final DIG + punchline.
            "response": final_response,

            "source": "gemini",
            "generation_status": "completed"
        }

        # ==================================================
        # 8. Store generated response
        # ==================================================

        try:

            punchlines_collection.insert_one(
                document
            )

            print(
                f"[BACKGROUND] Successfully stored: "
                f"{movie_id} / {actor_id}"
            )

        except DuplicateKeyError:

            print(
                f"[BACKGROUND] Duplicate prevented: "
                f"{profile_key}"
            )

            return

    except Exception as e:

        print(
            f"[BACKGROUND] FAILED: "
            f"{movie_id} / {actor_id}"
        )

        print(
            f"[BACKGROUND] Error: {e}"
        )


# ======================================================
# Main Punchline Service
# ======================================================

def get_punchline(
    movie_id: str,
    actor_id: str,
    genres: list,
    user_preferences: dict,
    context: dict,
    background_tasks: BackgroundTasks
):

    # --------------------------------------------------
    # 1. Check whether actor belongs to the movie
    # --------------------------------------------------

    actor_in_movie = movie_dialogues_collection.find_one(
        {
            "movie_id": movie_id,
            "actor_id": actor_id
        }
    )

    # --------------------------------------------------
    # 2. Actor NOT in movie
    # --------------------------------------------------

    if not actor_in_movie:

        default_dialogue = movie_dialogues_collection.find_one(
            {
                "movie_id": movie_id,
                "is_default": True
            }
        )

        if default_dialogue:

            return {
                "id": str(default_dialogue["_id"]),
                "movie_id": movie_id,
                "actor_id": default_dialogue["actor_id"],
                "character": default_dialogue["character"],
                "response": default_dialogue["dialogue"],
                "source": "default",
                "matched": False,
                "match_type": "actor_not_in_movie",
                "generation_queued": False,
                "similarity": None
            }

        return {
            "id": None,
            "movie_id": movie_id,
            "actor_id": actor_id,
            "character": context.get("character"),
            "response": (
                "No default dialogue found for this movie."
            ),
            "source": "default",
            "matched": False,
            "match_type": "default_unavailable",
            "generation_queued": False,
            "similarity": None
        }

    # --------------------------------------------------
    # 3. Build genre-aware criteria and vector
    # --------------------------------------------------

    criteria, preference_vector, vector_dimensions = (
        build_preference_vector(
            user_preferences=user_preferences,
            genres=genres
        )
    )

    # --------------------------------------------------
    # 4. Build canonical profile key
    # --------------------------------------------------

    profile_key = build_profile_key(
        movie_id=movie_id,
        actor_id=actor_id,
        genres=genres,
        criteria=criteria
    )

    # --------------------------------------------------
    # 5. Exact profile lookup
    # --------------------------------------------------

    existing = punchlines_collection.find_one(
        {
            "profile_key": profile_key
        }
    )

    # --------------------------------------------------
    # 6. Exact match found
    # --------------------------------------------------

    if existing:

        return format_result(
            document=existing,
            source=existing.get(
                "source",
                "database"
            ),
            matched=True
        )

    # --------------------------------------------------
    # 7. Search similar profiles
    # --------------------------------------------------

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

                # New field
                "response": 1,

                # Keep compatibility with old documents
                "punchline": 1,

                "source": 1,

                "score": {
                    "$meta": "vectorSearchScore"
                }
            }
        }
    ]

    # --------------------------------------------------
    # 8. Execute vector search
    # --------------------------------------------------

    similar_results = list(
        punchlines_collection.aggregate(
            vector_pipeline
        )
    )

    # --------------------------------------------------
    # 9. Check best vector match
    # --------------------------------------------------

    if similar_results:

        best_match = similar_results[0]

        similarity_score = best_match.get(
            "score",
            0.0
        )

        # --------------------------------------------------
        # 10. Similarity >= 75%
        #
        # Reuse existing response.
        # --------------------------------------------------

        if similarity_score >= SIMILARITY_THRESHOLD:

            # New documents use "response".
            # Old documents may still use "punchline".
            matched_response = best_match.get(
                "response"
            )

            if not matched_response:
                matched_response = best_match.get(
                    "punchline"
                )

            return {
                "id": str(best_match["_id"]),
                "movie_id": best_match["movie_id"],
                "actor_id": best_match["actor_id"],

                # Always use current request character
                # when available.
                "character": context.get(
                    "character",
                    best_match.get("character")
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

    # --------------------------------------------------
    # 11. No exact/suitable vector match
    #
    # We only use this to determine whether generation
    # should be queued.
    #
    # The actual generated dialogue comes from Gemini.
    # --------------------------------------------------

    default_dialogue = movie_dialogues_collection.find_one(
        {
            "movie_id": movie_id,
            "is_default": True
        }
    )

    # --------------------------------------------------
    # 12. Default dialogue found
    #
    # Queue Gemini generation.
    # --------------------------------------------------

    if default_dialogue:

        background_tasks.add_task(
            generate_and_store_punchline,
            movie_id,
            actor_id,
            genres,
            user_preferences,
            context
        )

        # --------------------------------------------------
        # Immediately return default dialogue
        #
        # This is the existing asynchronous behavior.
        # The newly generated DIG + punchline will be
        # available on a later request.
        # --------------------------------------------------

        return {
            "id": str(default_dialogue["_id"]),
            "movie_id": movie_id,

            "actor_id": actor_id,

            "character": context.get(
                "character",
                default_dialogue.get("character")
            ),

            "response": default_dialogue["dialogue"],

            "source": "default",

            "matched": False,

            "match_type": "default",

            "generation_queued": True,

            "similarity": None
        }

    # --------------------------------------------------
    # 13. No default dialogue found
    # --------------------------------------------------

    return {
        "id": None,
        "movie_id": movie_id,
        "actor_id": actor_id,
        "character": context.get("character"),
        "response": (
            "No default dialogue found for this movie."
        ),
        "source": "default",
        "matched": False,
        "match_type": "default_unavailable",
        "generation_queued": False,
        "similarity": None
    }


# ======================================================
# Helper Function
# ======================================================

def format_result(
    document: dict,
    source: str,
    matched: bool
):

    # New generated documents contain "response".
    # Old documents may contain "punchline".
    response = document.get("response")

    if not response:
        response = document.get("punchline")

    return {
        "id": str(document["_id"]),
        "movie_id": document["movie_id"],
        "actor_id": document["actor_id"],
        "character": document.get("character"),
        "response": response,
        "source": source,
        "matched": matched,
        "match_type": "exact",
        "generation_queued": False,
        "similarity": None
    }