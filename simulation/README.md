# AI Readiness Simulation Game

An interactive simulation game based on the **ITU AI Readiness Framework 2025** (Report 2.0). Country delegates describe their AI readiness across 13 dimensions, and 6 AI agents analyze, score, and simulate "what-if" policy scenarios using a knowledge base of 27+ national AI strategy documents.

## Features

- **6 AI Agents** — dataset, open-source, sandbox, research, deployment, standards
- **13 Dimensions** — covering 6 factors with 100+ metrics from the ITU framework
- **Knowledge Base** — seeded with 27 international AI policy documents (ChromaDB)
- **What-If Analysis** — causal graph propagation across dimension interdependencies
- **Scoring** — 0-5 maturity scale with weighted composite indices and gap analysis
- **CLI + API** — Rich-based terminal client + FastAPI backend with 24 REST routes

## Requirements

- **Docker Desktop** (includes Docker Compose)
- **~16 GB RAM** minimum (for Ollama LLM inference with qwen2.5:14b)
- **~15 GB disk** (for LLM models on first run)

## Quick Start (Docker)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/ai-readiness-game.git
cd ai-readiness-game
```

### 2. Start the services

```bash
docker compose up -d
```

This starts two containers:
- **ollama** — local LLM server (port 11434)
- **ai-readiness-server** — game API server (port 8000)

### 3. First-time setup (pull models + ingest documents)

```bash
docker compose exec server bash setup.sh
```

This will:
- Pull `qwen2.5:14b` (~4.7 GB) and `nomic-embed-text` (~274 MB) models
- Ingest 27 seed documents into the Knowledge Base

**This takes 10-20 minutes on first run.** Subsequent starts skip this step.

### 4. Run the CLI client

**Option A — Inside the container:**
```bash
docker compose exec server python run_cli.py
```

**Option B — On your host (requires Python 3.9+):**
```bash
pip install httpx rich
python run_cli.py
```

### 5. Play the game

Once the CLI starts, you'll see a REPL prompt. Try these commands:

```
> help                              # list all commands
> register India delegate1          # register as a delegate
> assess India is developing its AI infrastructure with NITI Aayog leading...
> clarify What is dimension D7 about?
> whatif Increase open data availability by 2 points
> dashboard                         # view scores
> decide Accept open data policy    # record a decision
```

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `register <country> <name>` | Register as a delegate |
| `assess <description>` | Submit country assessment (free-form text) |
| `clarify <question>` | Ask about the ITU framework |
| `whatif <scenario>` | Simulate a policy change |
| `decide <decision>` | Record a policy decision |
| `dashboard` | View current scores |
| `impact` | View causal graph relationships |
| `agents` | List the 6 AI agents |
| `stats` | View KB and session statistics |
| `help` | Show all commands |
| `quit` | Exit |

## Architecture

```
docker compose up
       |
       v
+------------------+     +------------------+
|  ollama:11434    |<----|  server:8000     |
|  qwen2.5:14b     |     |  FastAPI + 6     |
|  nomic-embed-text|     |  AI Agents       |
+------------------+     |  ChromaDB (KB)   |
                          |  SQLite (sessions)|
                          |  NetworkX (causal)|
                          +------------------+
                                  ^
                                  |
                          +------------------+
                          |  CLI (Rich REPL) |
                          |  run_cli.py      |
                          +------------------+
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Configuration

Environment variables (prefix `AIREADY_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `AIREADY_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `AIREADY_LLM_MODEL` | `qwen2.5:14b` | LLM model for reasoning |
| `AIREADY_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `AIREADY_HOST` | `0.0.0.0` | Server bind address |
| `AIREADY_PORT` | `8000` | Server port |

## GPU Support (Optional)

For NVIDIA GPU acceleration, uncomment the GPU section in `docker-compose.yml` and install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

## Stopping

```bash
docker compose down          # stop containers (data preserved in volumes)
docker compose down -v       # stop and delete all data (models, KB, sessions)
```

## Without Docker (Manual Setup)

```bash
# 1. Install Ollama: https://ollama.com/download
# 2. Pull models
ollama pull qwen2.5:14b
ollama pull nomic-embed-text

# 3. Install Python deps
pip install -r requirements.txt

# 4. Ingest documents
python -m server.knowledge.ingest --dir server/knowledge/InputDocs

# 5. Start server (terminal 1)
python run_server.py

# 6. Start CLI (terminal 2)
python run_cli.py
```

## Project Structure

```
simulation/
  server/
    agents/          # 6 AI agents + router
    game/            # engine, scoring, causal graph, sessions
    knowledge/       # ChromaDB KB, cache, ingestion, InputDocs/
    routes/          # FastAPI route handlers
    config.py        # settings
    main.py          # FastAPI app
    models.py        # data models
  cli/
    app.py           # Rich REPL client
  data/
    framework/       # dimensions.json (13 dimensions, 100+ metrics)
    chromadb/        # vector database (generated)
  run_server.py      # server launcher
  run_cli.py         # CLI launcher
  setup.sh           # first-time setup script
  Dockerfile
  docker-compose.yml
  requirements.txt
```

## License

Open source. Built for the ITU AI/ML in 5G Challenge training program.
