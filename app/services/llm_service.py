import os

from dotenv import load_dotenv
from google import genai


# ==========================================================
# CONFIGURATION
# ==========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

client = genai.Client(
    api_key=GEMINI_API_KEY
)

# Use the Gemini model available in your account.
MODEL_NAME = "gemini-3.6-flash"


# ==========================================================
# HELPER
# ==========================================================

def clean(value, default):
    if value is None:
        return default

    if isinstance(value, str) and not value.strip():
        return default

    return value


def get_genre_text(context: dict) -> str:

    genres = context.get("genres", [])

    if isinstance(genres, list) and genres:
        return " / ".join(
            str(g)
            for g in genres
            if g
        )

    if isinstance(genres, str) and genres.strip():
        return genres

    return "Unknown genre"


# ==========================================================
# GEMINI CALL 1
#
# PURPOSE:
# Find an ACTUAL movie dialogue/punchline.
#
# The dialogue is NOT taken from MongoDB.
# Gemini itself identifies the dialogue.
#
# The selection must be influenced by:
# - Movie
# - Actor
# - Character
# - Genre
# - User preferences
# ==========================================================

def generate_movie_punchline(
    context: dict,
    criteria: dict
) -> str:

    movie_title = clean(
        context.get("movie_title"),
        "Unknown movie"
    )

    actor_name = clean(
        context.get("actor_name"),
        "Unknown actor"
    )

    character = clean(
        context.get("character"),
        "Unknown character"
    )

    genre_text = get_genre_text(context)

    prompt = f"""
You are selecting an ACTUAL dialogue from a movie.

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


TASK:

Identify ONE actual dialogue spoken by the specified
character in the specified movie.

The selected dialogue must be the best match for the
user's preferences.

For example, if the user strongly prefers:

mass: high
aggressive: high
intimidating: high
serious: high

then prefer a real dialogue from the movie that reflects
mass, aggression, intimidation or seriousness.

If the user prefers comedy, romance, emotional moments,
calmness, intelligence, family-oriented characteristics,
etc., select an actual dialogue that best matches those
preferences instead.

The user's preference values are important.

Higher values should have greater influence when deciding
which dialogue is most appropriate.


IMPORTANT:

1. The dialogue MUST be an actual dialogue from the movie.

2. Do NOT invent a dialogue.

3. Do NOT create a dialogue that merely sounds like the
   character.

4. Do NOT write a new punchline.

5. Do NOT paraphrase a movie dialogue.

6. Do NOT translate a movie dialogue.

7. Do NOT combine multiple movie dialogues.

8. Do NOT modify the wording of the dialogue.

9. Do NOT add words before or after the dialogue.

10. Do NOT explain your choice.

11. Return ONLY the actual movie dialogue.

12. The dialogue should be spoken by the specified
    character whenever possible.

13. If you cannot confidently identify an actual dialogue
    from the movie, return exactly:

NOT_FOUND
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    result = response.text.strip()

    if not result:
        raise ValueError(
            "Gemini Call 1 returned an empty response."
        )

    if result == "NOT_FOUND":
        raise ValueError(
            f"Could not identify an actual dialogue for "
            f"{movie_title} / {character}"
        )

    return result


# ==========================================================
# EXISTING FUNCTION
#
# Kept for compatibility with existing code that imports:
#
# from app.services.llm_service import generate_punchline
#
# It now performs Gemini Call 1.
# ==========================================================

def generate_punchline(
    context: dict,
    criteria: dict
) -> str:

    return generate_movie_punchline(
        context=context,
        criteria=criteria
    )


# ==========================================================
# GEMINI CALL 2
#
# PURPOSE:
# Generate the FINAL response.
#
# Input:
# - Movie
# - Actor
# - Character
# - Genre
# - User preferences
# - Actual movie punchline from Gemini Call 1
#
# Output:
# DIG + ACTUAL MOVIE PUNCHLINE
# ==========================================================

def generate_contextual_response(
    context: dict,
    criteria: dict,
    movie_punchline: str
) -> str:

    movie_title = clean(
        context.get("movie_title"),
        "Unknown movie"
    )

    actor_name = clean(
        context.get("actor_name"),
        "Unknown actor"
    )

    character = clean(
        context.get("character"),
        "Unknown character"
    )

    genre_text = get_genre_text(context)

    movie_punchline = clean(
        movie_punchline,
        ""
    )

    if not movie_punchline:
        raise ValueError(
            "Movie punchline is required for Gemini Call 2."
        )

    prompt = f"""
You are generating the FINAL personalized cinematic
response for a movie.

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


ACTUAL MOVIE PUNCHLINE SELECTED BY GEMINI:

{movie_punchline}


TASK:

Generate ONE short, natural and powerful cinematic
response that combines:

1. A personalized DIG/contextual description.

2. The supplied actual movie punchline.


The DIG must be generated specifically from:

- Movie
- Actor
- Character
- Genre
- User preferences

The DIG should describe the actor/character's relevant
presence, personality, attitude, energy or contrasting
characteristics according to the user's preferences.


DESIRED STRUCTURE:

[PERSONALIZED DIG], [natural transition into the dialogue]
"[ACTUAL MOVIE PUNCHLINE]"


EXAMPLE OF THE DESIRED STYLE:

"Vijay brings the mass action and intimidating presence
of Leo, while Parthiban reveals his softer, family-oriented
side; but when that calm side is pushed too far,
"I buried Leo so my family could live. Touch them, and
I'll bury your entire bloodline.""


EXAMPLE CRITERIA FOR THAT EXAMPLE:

The example represents preferences such as:

mass: HIGH
aggressive: HIGH
intimidating: HIGH
serious: HIGH

with a softer/family-oriented characteristic being used
as a contrast.

Because those preferences are strong, the DIG emphasizes
mass, aggression and intimidation while contrasting them
with Parthiban's softer family-oriented side.


IMPORTANT RULES:

1. The example is ONLY an example of the desired structure.

2. Do NOT copy the example wording.

3. Do NOT use Vijay, Leo or Parthiban unless they belong
   to the current request.

4. Do NOT assume every movie should be mass or aggressive.

5. The ACTUAL user's preferences must determine the DIG.

6. Higher preference values must have greater influence.

7. Use ALL relevant information:
   movie, actor, character, genre and preferences.

8. If multiple preferences are high, naturally combine them.

9. If preferences contain contrasting characteristics,
   naturally express that contrast.

10. The system must work for ANY movie, language,
    country, film industry or genre.

11. The supplied movie punchline is an ACTUAL movie dialogue.

12. Preserve the supplied movie punchline EXACTLY.

13. Do NOT modify the movie punchline.

14. Do NOT paraphrase the movie punchline.

15. Do NOT translate the movie punchline.

16. Do NOT shorten the movie punchline.

17. Do NOT add words to the movie punchline.

18. Do NOT remove words from the movie punchline.

19. Do NOT invent another movie dialogue.

20. Do NOT generate a replacement dialogue.

21. Do NOT claim that the DIG itself is a movie dialogue.

22. Do NOT add headings such as:
    Context:
    Dialogue:
    Dig:

23. Do NOT add a separate watch recommendation.

24. Keep the response concise.

25. The final response must naturally flow from the
    personalized DIG into the actual movie punchline.

26. Return ONLY the final response.
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )

    result = response.text.strip()

    if not result:
        raise ValueError(
            "Gemini Call 2 returned an empty response."
        )

    return result


# ==========================================================
# FINAL RESPONSE
#
# TWO GEMINI CALLS:
#
# CALL 1:
#   Movie information + preferences
#   -> Actual movie punchline
#
# CALL 2:
#   Movie information + preferences + punchline
#   -> DIG + punchline
# ==========================================================

def generate_final_response(
    context: dict,
    criteria: dict
) -> str:

    # ------------------------------------------------------
    # GEMINI CALL 1
    # ------------------------------------------------------

    movie_punchline = generate_movie_punchline(
        context=context,
        criteria=criteria
    )

    # ------------------------------------------------------
    # GEMINI CALL 2
    # ------------------------------------------------------

    final_response = generate_contextual_response(
        context=context,
        criteria=criteria,
        movie_punchline=movie_punchline
    )

    return final_response