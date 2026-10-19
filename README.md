# CraftLore

CraftLore is a question-answering assistant for Minecraft Java Edition. It answers lore and history questions from Minecraft Wiki pages, with links to the sources it used. It answers crafting questions with an exact recipe lookup, so recipes never come from the language model's memory. The page draws each recipe as a 3x3 crafting grid.

> **Status:** Working locally and in Docker. Not yet deployed to a public host.

> **Disclaimer:** CraftLore is an unofficial fan project. Minecraft is a trademark of Mojang Studios.

> **Content license:** Wiki content comes from the Minecraft Wiki under CC BY-NC-SA. This project is non-commercial.

## Features

- **Lore questions with citations.** Answers are built from retrieved wiki sections, and each source links to the section it came from.
- **Exact crafting recipes.** Recipe questions are answered from the game's recipe data, and the page draws the grid with the result.
- **Automatic routing.** A router sends each question to the lore branch or the recipe branch.
- **Answer verification.** A second model call checks each claim against the sources. Failed answers are rewritten once. If they still fail, they are labeled "not fully verified."
- **Honest "I don't know."** When the indexed sources don't contain the answer, the assistant says so instead of guessing.
- **Web interface and API.** A chat page sits on top of a FastAPI endpoint, with interactive API docs at `/docs`.
- **Tested and containerized.** Unit tests run without calling the LLM, and the app runs in Docker Compose.

## How it works

```
Browser (chat page)
     │  POST /ask
     ▼
FastAPI  ──►  LangGraph workflow
              │
              ├─ router (LLM: lore or mechanics?)
              │
              ├─ lore ──► rag: hybrid search over the wiki index
              │           (Chroma vector search + BM25 keyword search,
              │            merged with Reciprocal Rank Fusion)
              │
              ├─ mechanics ──► recipe tool: exact lookup in recipes.json
              │                (LLM only extracts the item name)
              │
              ├─ answer (LLM writes an answer citing [1], [2], ...)
              │
              └─ verify (LLM checks claims against sources)
                    │ fails and attempts left? ──► answer again (max 2 tries)
                    ▼
              JSON: answer, sources, route, verified, recipe layout
```

Offline pipeline (run once, or after changing the page list):

```
seed_titles.txt ──► fetch wiki pages (MediaWiki API) ──► data/raw/*.json
                 ──► clean markup, split by section ──► data/chunks.json
                 ──► embed chunks (sentence-transformers) ──► data/chroma/
```

## Tech stack

| Area | Tools | Why |
|---|---|---|
| Language | Python 3.11 | Best support for the AI libraries used |
| LLM | Groq API (model set in `.env`) | Free tier, fast, no local GPU needed |
| Orchestration | LangChain, LangGraph | Building blocks plus an explicit graph with a retry loop |
| Vector search | Chroma | Local, persistent, no separate server |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` | Small, runs on CPU, no per-call cost |
| Keyword search | rank-bm25 with stopwords and plural normalization | Finds exact item names that vector search can miss |
| Fusion | Reciprocal Rank Fusion | Merges two ranked lists without comparing their scores |
| Recipe data | PrismarineJS `minecraft-data` (Minecraft 26.1) | Machine-readable, MIT-licensed recipe data |
| API | FastAPI, Pydantic, Uvicorn | Typed request and response models, automatic docs |
| Frontend | HTML, CSS, JavaScript | No build step, easy to read |
| Tests | pytest | Fast unit tests with a fake LLM |
| Containers | Docker, Docker Compose | Same runtime on any machine |
| CI | GitHub Actions | Runs the tests on every push |

## Project structure

```
craftlore/
├── app/
│   ├── config.py            # settings loaded from .env
│   ├── llm.py               # Groq chat model
│   ├── main.py              # FastAPI app: /ask, /health, static page
│   ├── ingest/
│   │   ├── wiki.py          # fetch pages from the MediaWiki API
│   │   ├── chunk.py         # clean markup, split by section, cap length
│   │   ├── drops.py         # one "Drops" chunk per mob from DropLine templates
│   │   └── build.py         # build chunks.json and the Chroma index
│   ├── retrieval/
│   │   ├── store.py         # Chroma connection and embeddings
│   │   ├── bm25.py          # keyword index with stopwords and plural stemming
│   │   └── hybrid.py        # vector, keyword, and hybrid search with RRF
│   ├── tools/
│   │   └── recipes.py       # exact recipe lookup and grid layout
│   └── graph/
│       ├── state.py         # shared state for the workflow
│       ├── nodes.py         # router, rag, mechanics, answer, verify
│       └── build.py         # workflow wiring
├── static/
│   ├── index.html           # chat page
│   ├── recipe.css           # crafting grid styles
│   └── recipe.js            # crafting grid rendering
├── eval/
│   ├── questions.jsonl      # labeled evaluation questions
│   ├── check_questions.py   # checks labels against the indexed text
│   ├── run_eval.py          # retrieval, routing, and answer scoring
│   ├── results.md           # latest evaluation results
│   └── results_baseline.md  # results before tuning
├── tests/
│   ├── test_recipes.py
│   └── test_graph.py
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

`data/` holds the generated files: raw pages, `chunks.json`, the Chroma index, and the recipe data. It is excluded from Git because it is large and can be rebuilt.

## Getting started

### Prerequisites

- Python 3.11
- Git
- A free Groq API key from console.groq.com
- Docker (optional, for the container run)

### 1. Clone and install

```bash
git clone https://github.com/Anique51/craftlore.git
cd craftlore
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

The CPU-only PyTorch build is much smaller than the default one, and the embedding model doesn't need a GPU.

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-20b
EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHROMA_DIR=data/chroma
```

Model names change over time. If the app reports `model_not_found`, copy a current model ID from the Models page at console.groq.com.

### 3. Download the recipe data

```bash
mkdir -p data
curl -L -o data/recipes.json https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/pc/26.1/recipes.json
curl -L -o data/items.json https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/pc/26.1/items.json
```

### 4. Build the knowledge base

`data/seed_titles.txt` lists the wiki pages to index, one per line. Then run:

```bash
python -m app.ingest.wiki      # fetch the pages (about one second per page)
python -m app.ingest.build     # clean, chunk, and index them
```

The build prints the page and chunk counts. Re-running it rebuilds the index from scratch.

### 5. Run locally

```bash
uvicorn app.main:app --port 8000
```

Open `http://127.0.0.1:8000` for the chat page, or `http://127.0.0.1:8000/docs` for the API docs.

### 6. Run with Docker

Build the index first (step 4), because the image copies the built index and recipe data:

```bash
docker compose up --build
```

Check it with:

```bash
curl http://localhost:8000/health
```

The container reads `GROQ_API_KEY` from your `.env` file. The file is excluded from the image by `.dockerignore`.

## API

### `POST /ask`

Request:

```json
{ "question": "What do I need to craft a beacon?" }
```

Response:

```json
{
  "answer": "To craft a beacon you need: ... [1]",
  "sources": ["https://github.com/PrismarineJS/minecraft-data"],
  "route": "mechanics",
  "verified": true,
  "recipe": {
    "result": "Beacon",
    "count": 1,
    "type": "shaped",
    "grid": [["Glass", "Glass", "Glass"], ["Glass", "Nether Star", "Glass"], ["Obsidian", "Obsidian", "Obsidian"]],
    "ingredients": null
  }
}
```

Errors:
- **422:** the question is empty or longer than 500 characters.
- **503:** the LLM provider is rate-limiting requests. Wait a minute and retry.

### `GET /health`

Returns `{"status": "ok"}`.

## Testing

```bash
python -m pytest tests/ -v
```

The tests check recipe lookups, input normalization, the router's fallback, the verifier's logic, and the retry limit. They use a fake LLM, so they cost nothing. Recipe tests are skipped when `data/recipes.json` is missing, which is the case on CI.

## Evaluation

CraftLore was evaluated on 45 labeled questions: 30 wiki questions (lore, version-sensitive, and harder questions that don't name the page) and 15 recipe questions. The author wrote the labels and checked each one against the indexed text before scoring. The question set is in `eval/questions.jsonl`.

To reproduce:

```bash
python -m eval.check_questions          # validate labels against the index
python -m eval.run_eval                 # retrieval and routing
python -m eval.run_eval --full          # adds answer grading (uses Groq quota)
```

### Retrieval recall@5 (wiki questions, n = 30)

| Mode | Before tuning | Current |
|---|---|---|
| Vector only | 29/30 | 29/30 |
| Keyword only (BM25) | 27/30 | 28/30 |
| Hybrid (RRF) | 29/30 | 30/30 |

Changes between the two columns:
- **Candidate pool from 10 to 20:** lets a Wither chunk into the candidate list for a beacon question.
- **Per-page cap of 3 chunks:** keeps one page from filling all five slots, so a Zombie drops chunk can reach the top five.
- **Plural-normalizing stemmer:** moves the Ghast drops chunk from rank 34 to rank 1 on keyword search. Keyword recall stayed at 28/30 because one question (Q54, "ender pearls") newly missed.

These changes were made after reviewing the questions that failed, so the 30/30 hybrid score is tuned to this test set. It is not a measure of general performance. A new held-out set of questions is needed to measure the true effect.

### Routing accuracy

- Before the router prompt change: 39/45
- Current: 44/45

The prompt was tightened after six lore questions about drops, formation, and portals were sent to the recipe branch. The one remaining miss is a label issue: "How do I make a flying carpet?" asks about an item that doesn't exist, so its label was moved to the lore route.

### Answer keyword match (full graph)

- Before tuning: 34/45
- Current: 41/45, measured after the cap and drops changes but before the stemmer

Keyword matching is strict. A correct answer that words a fact differently counts as a miss, so 41/45 is a lower bound.

### Known failures

- **Grounding error:** "What do zombies drop when they die?" was answered with iron ingots as the main drop, and Rotten Flesh was omitted. The verifier accepted the answer, so verification is weaker than it should be.
- **Retrieval sensitivity:** the ghast drops question failed in an earlier run because its keywords didn't match. It now passes, but it should be rechecked after any index change.
- **Incomplete answer:** "Where do piglins live?" returns a partial answer, because the indexed text covers only part of the relevant section.
- **Metric issue:** "What is sculk?" is answered correctly, but the keyword "Warden" is not in the answer, so it is scored as a miss.
- **Keyword regression:** "Which mob is a common source of ender pearls?" passed on keyword search before the stemmer and fails after it.
- **Version questions unscored:** 15 version-sensitive questions are in the set but not scored, because their first-version answers have not been checked against the wiki.

## Design decisions

- **Recipes come from data, not the model.** The LLM only extracts the item name. The recipe text and grid come from `recipes.json`, so a recipe answer can't invent ingredients.
- **Hybrid retrieval.** Vector search matches meaning, and BM25 matches exact words. Each misses different questions. RRF merges the two lists by rank, because their scores aren't comparable.
- **Section-level chunks.** Wiki pages are split at their own headings, so each chunk covers one topic. Sections longer than 1,000 characters are split again with 100 characters of overlap.
- **Titles on every chunk.** Each chunk starts with its page and section name, so the embedding carries that context.
- **Bounded retries.** The verify-and-rewrite loop stops after two attempts, which caps the number of model calls.
- **Tests that don't spend quota.** The unit tests replace the LLM with a fake, and evaluation results are saved, so reruns don't repeat paid calls.

## Known limitations

- **Coverage:** only indexed wiki pages can be answered. Other questions return "I don't know."
- **Version:** the recipe data is Minecraft 26.1, and the wiki pages may describe other versions.
- **Drops:** drop questions work only for mobs whose pages are indexed.
- **Free-tier limits:** the Groq free tier has per-minute token limits, so the evaluation pauses between calls.
- **Tuning:** the hybrid score is tuned to the test set, as described above.
- **Not deployed:** the project runs locally and in Docker. There is no public URL yet.

## Roadmap

- Deploy the container to a public host.
- Expand the index with more pages, and add version-aware filtering.
- Add a held-out evaluation set and RAGAS faithfulness scoring.
- Replace the fixed stopword list with stemming or a larger list.
- Add item icons, after checking their license.

## Licensing and attribution

- **Wiki content:** from the Minecraft Wiki, licensed CC BY-NC-SA. Each answer links to the page it used.
- **Recipe data:** from PrismarineJS `minecraft-data`, MIT licensed.
- **Project:** non-commercial, for portfolio use.
- **Trademark:** Minecraft is a trademark of Mojang Studios. CraftLore is not affiliated with or endorsed by Mojang Studios or Microsoft.
