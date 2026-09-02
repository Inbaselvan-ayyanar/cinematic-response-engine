from fastapi import FastAPI

from app.routes.punchline import router as punchline_router
from app.routes.movie import router as movie_router


app = FastAPI(
    title="Personalized Movie Punchline API",
    version="1.0.0"
)


app.include_router(
    punchline_router,
    prefix="/api/v1"
)

app.include_router(
    movie_router,
    prefix="/api/v1"
)


@app.get("/health")
def health_check():

    return {
        "status": "OK"
    }