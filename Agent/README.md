# CONSORT Deep Research Agent

A LangGraph-powered agent that performs multi-hop retrieval over a clinical trial document corpus stored in Qdrant, hydrates unfamiliar terms via You.com web search, and generates a CONSORT 2025-compliant report in LaTeX.

## Architecture

```
User Input
    |
    v
plan_research  -- GPT-5.2 decomposes CONSORT item into retrieval queries
    |
    v
retrieve       -- searches Qdrant (Akash-hosted) for relevant evidence
    |
    v
evaluate       -- judges if evidence is sufficient
    |            \
    |             need_more --> retrieve (up to 3 hops)
    |             need_web  --> web_search (You.com) --> evaluate
    v
synthesize     -- drafts prose from evidence + definitions
    |
    v  (loops back for remaining items)
generate_latex -- assembles full .tex document
    |
    v
report.tex
```

## Prerequisites

- Python 3.10+
- An OpenAI API key with access to `gpt-5.2` and `text-embedding-3-large`
- A Qdrant instance (hosted on Akash Network)
- A You.com Data API key ([api.you.com](https://api.you.com))

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Then edit .env and fill in your keys:
#   OPENAI_API_KEY, QDRANT_URL, QDRANT_API_KEY, YDC_API_KEY
```

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | -- | OpenAI API key |
| `QDRANT_URL` | Yes | -- | Qdrant REST endpoint (Akash) |
| `QDRANT_API_KEY` | No | -- | Qdrant auth key (if enabled) |
| `QDRANT_COLLECTION_NAME` | No | `clinical_trial_docs` | Collection name |
| `YDC_API_KEY` | Yes | -- | You.com Data API key |
| `EMBEDDING_MODEL` | No | `text-embedding-3-large` | OpenAI embedding model |
| `EMBEDDING_DIMENSIONS` | No | `3072` | Embedding vector size |
| `LLM_MODEL` | No | `gpt-5.2` | OpenAI chat model |
| `LLM_MAX_COMPLETION_TOKENS` | No | `16384` | Max output tokens per call |
| `LLM_REASONING_EFFORT` | No | `low` | `none`/`minimal`/`low`/`medium`/`high`/`xhigh` |

## Usage

### 1. Ingest documents into Qdrant

Place your clinical trial documents (PDF, DOCX, TXT) in a directory, then run:

```bash
python main.py ingest --input-dir ./docs/
```

This will:
- Load all supported files from the directory (recursively)
- Chunk them into ~1000-character segments with 200-character overlap
- Embed each chunk with `text-embedding-3-large`
- Upsert into your Qdrant collection

Optional flags:
- `--chunk-size 1000` (default)
- `--chunk-overlap 200` (default)

### 2. Generate a CONSORT report

```bash
python main.py generate --output report.tex
```

This will:
- Load all 42 CONSORT 2025 checklist items from `consort.json`
- For each item, decompose it into targeted search queries
- Retrieve evidence from Qdrant (multi-hop, up to 3 retrieval cycles)
- Hydrate unfamiliar clinical/statistical terms via You.com
- Synthesize each section into formal scientific prose
- Convert to LaTeX and assemble a complete `.tex` document with a CONSORT compliance checklist table

The output file can be compiled with any standard LaTeX toolchain (`pdflatex`, `latexmk`, etc.).

## Project structure

```
Agent/
  consort.json          CONSORT 2025 checklist (42 items)
  config.py             Pydantic Settings (loads from .env)
  main.py               CLI entry point: ingest | generate

  ingest/
    loader.py           Multi-format file loading (PDF, DOCX, TXT)
    chunker.py          Recursive text splitting with overlap
    uploader.py         Embed + batch upsert to Qdrant

  retrieval/
    client.py           QdrantRetriever: search + multi_query_search

  search/
    you_client.py       YouSearchClient: term hydration via You.com

  agent/
    state.py            AgentState TypedDict (LangGraph state)
    nodes.py            6 graph nodes (plan, retrieve, evaluate, web_search, synthesize, generate_latex)
    graph.py            StateGraph definition with conditional routing

  latex/
    templates.py        LaTeX preamble, section commands, CONSORT table template
    generator.py        Assemble section fragments into a complete .tex
```

## Partners

- **Akash Network** -- Hosts the Qdrant vector store for document embeddings and retrieval
- **You.com** -- Provides web search to supplement unfamiliar clinical/statistical terms
- **Render** -- Future deployment target for the backend + UI (the agent is designed to be stateless and wrappable in a FastAPI endpoint)
