from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from groq import RateLimitError
from pydantic import BaseModel, Field

from app.graph.build import build_graph

MAX_QUESTION_CHARS = 500
STATIC_DIR = Path("static")
graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Build the graph once at startup, not on every request.
    global graph
    graph = build_graph()
    yield


app = FastAPI(title="CraftLore", lifespan=lifespan)

# Only the chat page's origin may call the API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    route: str
    verified: bool
    recipe: dict | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question cannot be blank.")
    try:
        result = graph.invoke({"question": question, "attempts": 0})
    except RateLimitError:
        raise HTTPException(
            status_code=503,
            detail="The AI service is busy right now. Please try again in a minute.",
        )
    return AskResponse(
        answer=result["answer"],
        sources=list(dict.fromkeys(c["url"] for c in result.get("context", []))),
        route=result.get("route", "lore"),
        verified=bool(result.get("verified")),
        recipe=result.get("recipe"),
    )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
