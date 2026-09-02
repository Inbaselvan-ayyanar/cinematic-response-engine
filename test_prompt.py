import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_contextual_response(payload: dict) -> str:
    def clean(value, default):
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return value

    # Extract from your exact JSON structure
    movie_title = clean(payload.get("movie_title"), "Unknown movie")
    actor_name = clean(payload.get("actor_name"), "Unknown actor")
    character = clean(payload.get("character"), None)
    
    genres_list = payload.get("genres", [])
    genre = " / ".join(g for g in genres_list if g) if genres_list else "their favorite genre"
    
    preferences = payload.get("user_preferences", {})
    character_line = character if character else "(no specific character provided)"

    prompt = f"""
You are generating a short, personalized cinematic pitch for a movie.

Movie: {movie_title}
Genre: {genre}
Actor: {actor_name}
Character: {character_line}
User preference criteria: {preferences}

TASK:
Generate a single, flowing paragraph (2-3 sentences max) that follows EXACTLY this structure in order:

1. THE CONTEXT: A third-person description of the character's presence based on the user's criteria. Give greater weight to criteria with higher values (e.g., if mass and aggressive are high, focus on those traits).
2. THE MOVIE DIG (PUNCHLINE): Immediately after the context, provide a hard-hitting dialogue or punchline spoken by the character, enclosed in "quotation marks". If an authentic quote is unavailable, generate a highly accurate personalized punchline that fits the character's persona and the user criteria.
3. THE WATCH HOOK: A closing sentence that makes the user want to watch the movie specifically because it features {actor_name} delivering this exact energy in the {genre} genre.

EXAMPLE OF THE EXACT FLOW AND TONE REQUIRED:
"Vijay brings the mass action and intimidating presence of Leo, while Parthiban reveals his softer, family-oriented side. "I buried Leo so my family could live. Touch them, and I'll bury your entire bloodline." This is exactly the kind of raw, mass-action spectacle that makes Vijay a must-watch in action thrillers."

IMPORTANT RULES:
- Do NOT use labels (e.g., "Context:", "Hook:"). 
- The paragraph must flow naturally from description to quote to hook.
- Return ONLY the final combined text paragraph.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return response.text.strip()
payload = {
  "movie_id": "leo_2023",
  "movie_title": "Leo",
  "actor_id": "vijay",
  "actor_name": "Vijay",
  "character": "Parthiban",
  "genres": ["action", "thriller"],
  "user_preferences": {
    "mass": 0.95,
    "aggressive": 0.85,
    "intimidating": 0.80,
    "serious": 0.70,
    "comedy": 0.10
  }
}

print(generate_contextual_response(payload))