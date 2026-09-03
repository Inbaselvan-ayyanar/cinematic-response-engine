import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from google import genai


# ==========================================================
# CONFIGURATION
# ==========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

if not GEMINI_API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set"
    )

client = genai.Client(
    api_key=GEMINI_API_KEY
)

MODEL_NAME = "gemini-3.6-flash"


# ==========================================================
# HELPERS
# ==========================================================

def clean(
    value: Any,
    default: Any
) -> Any:

    if value is None:
        return default

    if isinstance(value, str):

        if not value.strip():
            return default

    return value


def get_genre_text(
    context: Dict[str, Any]
) -> str:

    genres = context.get(
        "genres",
        []
    )

    if isinstance(
        genres,
        list
    ) and genres:

        return " / ".join(
            str(g)
            for g in genres
            if g
        )

    if isinstance(
        genres,
        str
    ) and genres.strip():

        return genres

    return "Unknown genre"


def sort_preferences(
    criteria: Dict[str, Any]
) -> List:

    """
    Sort preferences from highest weight
    to lowest weight.

    Example:

    comedy       0.95
    mass         0.70
    serious      0.30
    aggressive   0.20
    intense      0.20
    intimidating 0.15
    mysterious   0.10
    """

    items = []

    for key, value in criteria.items():

        try:

            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError
        ):

            continue

        items.append(
            (
                key,
                numeric_value
            )
        )

    items.sort(
        key=lambda item: item[1],
        reverse=True
    )

    return items


def format_candidates(
    available_dialogues: List[
        Dict[str, Any]
    ]
) -> str:

    if not available_dialogues:

        return "NO CANDIDATE DIALOGUES AVAILABLE."

    lines = []

    for index, dialogue in enumerate(
        available_dialogues,
        start=1
    ):

        text = clean(
            dialogue.get(
                "dialogue"
            ),
            ""
        )

        if not text:
            continue

        preference = clean(
            dialogue.get(
                "preference"
            ),
            "unspecified"
        )

        candidate_criteria = dialogue.get(
            "criteria"
        )

        is_default = dialogue.get(
            "is_default",
            False
        )

        lines.append(
            f"""
CANDIDATE {index}
Dialogue: {text}
Preference tag: {preference}
Criteria: {candidate_criteria}
Default: {is_default}
""".strip()
        )

    if not lines:

        return "NO CANDIDATE DIALOGUES AVAILABLE."

    return "\n\n".join(lines)


# ==========================================================
# GEMINI CALL 1
#
# PURPOSE:
# Select ONE actual dialogue from the candidates
# stored in MongoDB.
#
# Preference priority:
#
# highest weight
#       ↓
# next highest
#       ↓
# ...
#       ↓
# default
# ==========================================================

def generate_movie_punchline(
    context: Dict[str, Any],
    criteria: Dict[str, Any],
    available_dialogues: Optional[
        List[Dict[str, Any]]
    ] = None,
    default_dialogue: Optional[
        Dict[str, Any]
    ] = None
) -> str:

    movie_title = clean(
        context.get(
            "movie_title"
        ),
        "Unknown movie"
    )

    actor_name = clean(
        context.get(
            "actor_name"
        ),
        "Unknown actor"
    )

    character = clean(
        context.get(
            "character"
        ),
        "Unknown character"
    )

    genre_text = get_genre_text(
        context
    )

    available_dialogues = (
        available_dialogues
        or []
    )

    sorted_preferences = (
        sort_preferences(
            criteria
        )
    )

    preference_order = "\n".join(
        f"{index}. {name}: {value}"
        for index, (
            name,
            value
        ) in enumerate(
            sorted_preferences,
            start=1
        )
    )

    candidates_text = (
        format_candidates(
            available_dialogues
        )
    )

    default_text = "NO DEFAULT DIALOGUE."

    if default_dialogue:

        default_text = (
            f"Default dialogue: "
            f"{default_dialogue.get('dialogue')}"
        )

    prompt = f"""
You are the dialogue selection engine for a
personalized movie response system.

Your job is ONLY to select one dialogue from the
candidate dialogues supplied below.

Movie:
{movie_title}

Actor:
{actor_name}

Character:
{character}

Genre:
{genre_text}

User preference criteria:
{criteria}

Preference priority from highest to lowest:

{preference_order}

AVAILABLE MOVIE DIALOGUES:

{candidates_text}

DEFAULT DIALOGUE:

{default_text}


SELECTION RULES:

1. Higher preference weight has higher priority.

2. Start with the highest-weight preference.

3. Look for a candidate dialogue that genuinely
   matches that preference.

4. If a suitable candidate exists for the highest
   preference, select it immediately.

5. If no suitable candidate exists, move to the
   next-highest preference.

6. Continue this process until a suitable candidate
   is found.

7. If none of the preference categories has a suitable
   candidate, use the DEFAULT DIALOGUE.

8. ONLY select a dialogue that appears in the supplied
   candidate list or is exactly the supplied default
   dialogue.

9. NEVER invent a dialogue.

10. NEVER paraphrase a dialogue.

11. NEVER translate a dialogue.

12. NEVER combine multiple dialogues.

13. NEVER modify the wording of a dialogue.

14. The selected dialogue must belong to the supplied
   movie/actor/character context.

15. Return ONLY the selected dialogue text.

16. Do not return explanations.

17. Do not return labels.

18. Do not return quotation marks around the answer.

19. If there are no candidates and no default dialogue,
    return exactly:

NOT_FOUND
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    result = clean(
        response.text,
        ""
    )

    if not result:

        raise ValueError(
            "Gemini Call 1 returned an empty response."
        )

    result = result.strip()

    if result == "NOT_FOUND":

        raise ValueError(
            "No suitable movie dialogue was available."
        )

    return result


# ==========================================================
# COMPATIBILITY FUNCTION
# ==========================================================

def generate_punchline(
    context: Dict[str, Any],
    criteria: Dict[str, Any]
) -> str:

    return generate_movie_punchline(
        context=context,
        criteria=criteria
    )


# ==========================================================
# GEMINI CALL 2
#
# PURPOSE:
#
# Generate:
#
# Personalized DIG
#       +
# Actual selected movie dialogue
# ==========================================================

def generate_contextual_response(
    context: Dict[str, Any],
    criteria: Dict[str, Any],
    movie_punchline: str
) -> str:

    movie_title = clean(
        context.get(
            "movie_title"
        ),
        "Unknown movie"
    )

    actor_name = clean(
        context.get(
            "actor_name"
        ),
        "Unknown actor"
    )

    character = clean(
        context.get(
            "character"
        ),
        "Unknown character"
    )

    genre_text = get_genre_text(
        context
    )

    movie_punchline = clean(
        movie_punchline,
        ""
    )

    if not movie_punchline:

        raise ValueError(
            "Movie punchline is required "
            "for Gemini Call 2."
        )

    prompt = f"""
You are generating the final personalized
cinematic response for a movie.

Movie:
{movie_title}

Actor:
{actor_name}

Character:
{character}

Genre:
{genre_text}

User preference criteria:
{criteria}

Selected actual movie dialogue:

{movie_punchline}


TASK:

Generate ONE concise cinematic response.

The response must contain:

1. A personalized DIG/context describing the
   actor/character.

2. A natural transition into the supplied dialogue.

3. The supplied dialogue exactly as given.


The DIG must be based on:

- Movie
- Actor
- Character
- Genre
- User preferences


PREFERENCE RULE:

Higher preference values must have greater influence
on the DIG.

If multiple preferences have high values, naturally
combine them.

If preferences conflict, naturally express the
contrast.


IMPORTANT:

1. The supplied dialogue is the actual movie dialogue
   selected by the system.

2. Preserve the supplied dialogue EXACTLY.

3. Do NOT modify the dialogue.

4. Do NOT paraphrase the dialogue.

5. Do NOT translate the dialogue.

6. Do NOT shorten the dialogue.

7. Do NOT add words inside the dialogue.

8. Do NOT remove words from the dialogue.

9. Do NOT invent another dialogue.

10. Do NOT create a replacement dialogue.

11. Do NOT claim the DIG itself is movie dialogue.

12. Do NOT add headings.

13. Do NOT add explanations.

14. Do NOT add recommendations.

15. Keep the response concise.

16. The DIG should naturally lead into the dialogue.

17. Return ONLY the final cinematic response.


DESIRED FORMAT:

[personalized DIG], [natural transition] "[supplied dialogue]"


Do not copy this wording literally.
Generate wording specific to the current movie,
actor, character, genre and preferences.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    result = clean(
        response.text,
        ""
    )

    if not result:

        raise ValueError(
            "Gemini Call 2 returned an empty response."
        )

    return result.strip()


# ==========================================================
# FINAL RESPONSE
#
# TWO GEMINI CALLS
# ==========================================================

def generate_final_response(
    context: Dict[str, Any],
    criteria: Dict[str, Any]
) -> str:

    # CALL 1

    movie_punchline = (
        generate_movie_punchline(
            context=context,
            criteria=criteria
        )
    )

    # CALL 2

    final_response = (
        generate_contextual_response(
            context=context,
            criteria=criteria,
            movie_punchline=movie_punchline
        )
    )

    return final_response