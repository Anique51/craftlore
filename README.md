# CraftLore

A Minecraft Java Edition lore and mechanics assistant built with RAG, LangChain, and LangGraph. It answers lore questions from the Minecraft Wiki with source citations, and answers crafting questions with an exact recipe lookup instead of guessing.

> **Status:** In development.

> **Disclaimer:** CraftLore is an unofficial fan project. Minecraft is a trademark of Mojang Studios.

> **Content license:** Wiki content comes from the Minecraft Wiki under CC BY-NC-SA. This project is non-commercial.

## How it works

1. **Ingestion:** wiki pages are fetched through the MediaWiki API, cleaned, and split into section-level chunks. Each chunk keeps its page title, section, and URL.
2. **Retrieval:** each question is searched two ways, by meaning (Chroma vector search with `all-MiniLM-L6-v2` embeddings) and by keywords (BM25). The two ranked lists are merged with Reciprocal Rank Fusion.
3. **Routing:** a LangGraph router sends each question to the lore branch (retrieval) or the mechanics branch (recipe lookup).
4. **Answering:** the LLM (Groq API) writes an answer that cites numbered sources.
5. **Verification:** a second LLM call checks each claim against the sources. Failed answers are rewritten once, and if they still fail, the answer is labeled as not fully verified.

## Setup

Requirements: Python 3.11, a Groq API key (free at console.groq.com).

```bash
git clone https://github.com/Anique51/craftlore.git
cd craftlore
python3.11 -m venv .venv
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
cp .env.example .env        # then add your GROQ_API_KEY and GROQ_MODEL
```

Download the recipe data (not stored in the repository because of its size):

```bash
mkdir -p data
curl -L -o data/recipes.json https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/pc/26.1/recipes.json
curl -L -o data/items.json https://raw.githubusercontent.com/PrismarineJS/minecraft-data/master/data/pc/26.1/items.json
```

Build the search index (fetches about 30 wiki pages, then builds the index):

```bash
python -m app.ingest.wiki
python -m app.ingest.build
```

Run the tests:

```bash
python -m pytest tests/ -v
```

## Evaluation

CraftLore was evaluated on 45 labeled questions: 30 wiki questions (lore, version-sensitive, and harder questions that don't name the page) and 15 recipe questions. The author wrote the labels and checked each one against the indexed text before scoring. The question set is in `eval/questions.jsonl`.

### Retrieval recall@5 (wiki questions, n = 30)

| Mode | Before tuning | Current |
|---|---|---|
| Vector only | 29/30 | 29/30 |
| Keyword only (BM25) | 27/30 | 28/30 |
| Hybrid (RRF) | 29/30 | 30/30 |

Changes made between the two columns:
- **Candidate pool 10 to 20:** lifted hybrid to 30/30 by letting a Wither chunk into the candidate list for the beacon question.
- **Per-page cap of 3 chunks:** needed so a Zombie drops chunk could reach the top five. Together with the drops chunks, this raised keyword recall to 28/30.
- **Plural-normalizing stemmer:** moved the Ghast drops chunk from rank 34 to rank 1 on keyword search. Keyword recall stayed at 28/30, because one question (Q54, "ender pearls") newly missed.

These changes were made after reviewing the questions that failed. The 30/30 hybrid score is therefore tuned to this test set, not a measure of general performance. A new held-out set of questions would be needed to measure the true effect.

### Routing accuracy

Before the router prompt change: 39/45. Current: 44/45. The prompt was tightened after six lore questions (drops, formation, and portal questions) were sent to the recipe branch. The one remaining miss is a label issue, not a routing error: the flying carpet item doesn't exist, so its label was moved to lore.

### Answer keyword match (full graph)

Before tuning: 34/45. Current: 41/45, measured after the cap and drops changes but before the stemmer. The stemmer can change answers, so this figure should be rerun to be current.

Keyword matching is strict. A correct answer that words a fact differently counts as a miss, so 41/45 is a lower bound.

### Known failures

- **Grounding error:** "What do zombies drop when they die?" was answered with iron ingots as the main drop, and Rotten Flesh was omitted. The verifier accepted the answer, so verification is weaker than it should be.
- **Incomplete answer:** "Where do piglins live?" returns a partial answer, because the indexed text covers only part of the relevant section.
- **Metric issue:** "What is sculk?" is answered correctly, but the keyword "Warden" is not in the answer, so it is scored as a miss.
- **Keyword regression:** "Which mob is a common source of ender pearls?" passed on keyword search before the stemmer and fails after it.
- **Version questions unscored:** 15 version-sensitive questions are in the set but not scored, because their first-version answers have not been checked against the wiki.
- **Recipe data is version 26.1 only:** the wiki pages and the recipe data may describe different game versions.
- **Limited scope:** only 30 wiki pages are indexed, so questions about other topics return "I don't know." Drop questions work only for indexed mobs.

## Licensing

Wiki content is licensed CC BY-NC-SA by the Minecraft Wiki. This project is for non-commercial portfolio use and attributes the source pages through the URL in each citation.
