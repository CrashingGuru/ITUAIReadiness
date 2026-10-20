# AI Readiness Simulation Game — Participant Guide

Welcome! This guide walks you through running the AI Readiness Simulation Game on your own machine using Docker. Everything runs locally — no cloud account, no API keys.

---

## What you'll need

| Requirement | Notes |
|-------------|-------|
| **16 GB RAM minimum** | 24 GB recommended for the default `qwen2.5:14b` model |
| **~15 GB free disk** | Ollama image + LLM model + embeddings + knowledge base |
| **Git** | For cloning the repository |
| **Docker Desktop** | Mac, Windows, or Linux |
| **Python 3.9+** | For the CLI client only (the server runs in Docker) |
| **~30 min first-time setup** | Mostly download time for the LLM |

If your machine has less than 16 GB RAM, see the [troubleshooting section](#troubleshooting) for how to switch to the smaller `llama3.1:8b` model.

---

## Step 1 — Install Git

Git is used to download (clone) the project from GitHub.

### Mac

Git usually comes pre-installed. Check:
```bash
git --version
```
If you get a prompt to install the Xcode Command Line Tools, accept it — that includes Git. Alternatively:
```bash
brew install git            # if you have Homebrew
```

### Windows

Download and install **Git for Windows** from https://git-scm.com/download/win

Accept the defaults in the installer. This gives you:
- `git` on the command line
- **Git Bash** — a terminal where all the `bash`/`curl` commands in this guide work exactly as shown

**On Windows, use Git Bash (not Command Prompt or PowerShell) for the rest of this guide.**

### Linux

```bash
sudo apt-get install -y git            # Debian / Ubuntu
sudo dnf install -y git                # Fedora / RHEL
sudo pacman -S git                     # Arch
```

### Verify

```bash
git --version
```
Expected: `git version 2.x.x` or newer.

---

## Step 2 — Install Docker Desktop

- **Mac / Windows**: Download from https://www.docker.com/products/docker-desktop and launch the app.
- **Linux**: `curl -fsSL https://get.docker.com | sh` and then `sudo systemctl start docker`.

Verify both commands work:
```bash
docker --version
docker compose version
```

---

## Step 3 — Clone the repository

```bash
git clone https://github.com/CrashingGuru/ITUAIReadiness.git
cd ITUAIReadiness/simulation
```

---

## Step 4 — Start the Docker services

```bash
docker compose up -d
```

This starts two containers:
- **ollama** — the local LLM server (port 11434)
- **ai-readiness-server** — the FastAPI backend (port 8000)

First run takes 5–10 minutes to pull the Ollama image (~1 GB) and build the server image.

Verify they're running:
```bash
docker compose ps
```

You should see both services with status `running`.

---

## Step 5 — Pull the LLM + ingest documents (one-time)

```bash
bash setup.sh
```

This script will:
1. Wait for Ollama to be ready
2. Pull **qwen2.5:14b** (~9 GB — 10–20 min on a typical connection)
3. Pull **nomic-embed-text** (~275 MB)
4. Ingest all documents from `InputDocs/` into ChromaDB (~5 min)

> **Windows users without bash**: run the commands manually:
> ```bash
> docker exec ollama ollama pull qwen2.5:14b
> docker exec ollama ollama pull nomic-embed-text
> docker exec ai-readiness-server python -m server.knowledge.ingest --reset
> ```

---

## Step 6 — Verify the server is up

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status":"ok","websocket_connections":0}
```

---

## Step 7 — Install the CLI client (one-time)

The CLI runs on your host (not in Docker) so you get a nice interactive terminal:

```bash
pip install httpx rich
```

Or if `pip` isn't on your PATH:
```bash
python3 -m pip install httpx rich
```

---

## Step 8 — Run the game

```bash
python3 -m cli.app
```

You'll be prompted for:
- **Country name** (e.g., "Ethiopia")
- **Delegate name** (your name)

Then type `help` to see all available commands.

---

## Available commands

| Command | What it does |
|---------|--------------|
| **standardise** | Map your AI use case to the ITU-T Y.3172 ML pipeline nodes (SRC → C → PP → M → P → D → SINK) |
| **readiness** | Analyse your use case's impact on readiness dimensions |
| **assess** | Describe your country's AI readiness → get full 13-dimension scoring |
| **clarify** | Ask about any framework dimension, metric, or factor |
| **whatif** | Simulate a policy change and see cascading effects |
| **decide** | Record a policy decision — scores update, KB is written to |
| **dashboard** | View current dimension scores for your country |
| **impact** | Preview the causal effect of a single dimension change |
| **agents** | List the 7 AI agents and their coverage |
| **stats** | Show game statistics |
| **help** | Show the command reference |
| **quit** | Exit the CLI |

> First queries take 1–2 minutes while the LLM loads into memory. Subsequent queries are faster.
> Full `assess` / `whatif` / `readiness` runs can take 5–10 minutes because they invoke multiple agents sequentially.

---

## Example session

```
Country name: Ethiopia
Delegate name: alice

Ethiopia: standardise
Describe your AI use case.
> IoT-based livestock health monitoring for proactive disease prediction
> in rural animal husbandry operations.

[Agent analyses use case against Y.3172 pipeline — SRC, C, PP, M, P, D, SINK, MLFO, Sandbox]

Ethiopia: readiness
Describe your AI use case to analyse its readiness impact.
> Same use case as above.

[Routes to 5 agents — scores 13 dimensions — propagates causal effects]

Ethiopia: dashboard
[Shows current scores for all 13 dimensions]

Ethiopia: quit
```

---

## Stop / restart / clean up

```bash
docker compose stop        # stop containers, keep data
docker compose start       # restart later (no setup.sh needed)
docker compose down        # stop and remove containers (data persists)
docker compose down -v     # also delete volumes — fresh start, re-run setup.sh
```

Your knowledge base, scores, and sessions persist across restarts via Docker volumes (`ollama_data`, `chromadb_data`, `game_db`).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker: command not found` | Install Docker Desktop and make sure it's running |
| `qwen2.5:14b` download stalls | Cancel with Ctrl+C, re-run: `docker exec ollama ollama pull qwen2.5:14b` |
| Server returns 500 errors | View logs: `docker compose logs server` |
| LLM responses too slow or OOM | Switch to the smaller 8B model (see below) |
| Port 8000 or 11434 already in use | Edit `docker-compose.yml`, change the first port in `"8000:8000"` to e.g. `"8001:8000"`, then re-start |
| `curl: command not found` on Windows | Use `Invoke-WebRequest http://localhost:8000/health` in PowerShell, or skip the verify step |
| CLI shows "server not reachable" | Make sure containers are running: `docker compose ps` |
| Fresh start / reset everything | `docker compose down -v && docker compose up -d && bash setup.sh` |

### Switching to a smaller model (for machines with < 16 GB RAM)

1. Edit `simulation/server/config.py`:
   ```python
   llm_model: str = "llama3.1:8b"   # was "qwen2.5:14b"
   ```
2. Pull the smaller model:
   ```bash
   docker exec ollama ollama pull llama3.1:8b
   ```
3. Restart the server container:
   ```bash
   docker compose restart server
   ```

---

## What's actually running under the hood

- **Ollama** serves the LLM (`qwen2.5:14b` for reasoning, `nomic-embed-text` for embeddings)
- **FastAPI server** orchestrates **7 AI agents**:
  - Dataset, OpenSource, Research, Deployment, Standards, Sandbox, UseCase
- **ChromaDB** holds four knowledge collections:
  - `kb_main` — ingested ITU + national strategy documents
  - `kb_framework` — the 13 dimensions, 6 factors, metrics
  - `kb_usecase` — Y.3172 and AI4Good use-case documents
  - `kb_decisions` — delegate decisions recorded during play
- **NetworkX** causal graph — 13 nodes, 23 weighted edges — propagates score deltas across dimensions
- **SQLite** — session + decision history

Nothing leaves your laptop. No API keys. No cloud.

---

## Getting help

- **Issues or bugs**: open an issue at https://github.com/CrashingGuru/ITUAIReadiness/issues
- **Framework questions**: use the `clarify` command inside the CLI — the AI agents will answer from the ITU documents

Enjoy the game!
