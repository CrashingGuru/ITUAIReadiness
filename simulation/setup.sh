#!/bin/bash
# ==============================================================
# AI Readiness Simulation Game — First-time setup
# Pulls Ollama models and ingests seed documents into ChromaDB
# ==============================================================
set -e

echo "================================================"
echo "  AI Readiness Simulation Game — Setup"
echo "================================================"
echo ""

# Wait for Ollama to be ready
OLLAMA_URL="${AIREADY_OLLAMA_BASE_URL:-http://localhost:11434}"
echo "Waiting for Ollama at $OLLAMA_URL ..."
until curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; do
    sleep 2
    echo "  ...still waiting for Ollama"
done
echo "Ollama is ready!"
echo ""

# Pull required models
echo "Pulling LLM model (qwen2.5:14b) — this may take a few minutes on first run..."
curl -sf "$OLLAMA_URL/api/pull" -d '{"name":"qwen2.5:14b"}' | while IFS= read -r line; do
    status=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || true)
    [ -n "$status" ] && echo "  $status"
done
echo "LLM model ready."
echo ""

echo "Pulling embedding model (nomic-embed-text)..."
curl -sf "$OLLAMA_URL/api/pull" -d '{"name":"nomic-embed-text"}' | while IFS= read -r line; do
    status=$(echo "$line" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || true)
    [ -n "$status" ] && echo "  $status"
done
echo "Embedding model ready."
echo ""

# Ingest seed documents
echo "Ingesting seed documents into Knowledge Base..."
python3 -m server.knowledge.ingest --dir server/knowledge/InputDocs
echo ""

echo "================================================"
echo "  Setup complete! Start the server with:"
echo "    python3 run_server.py"
echo "================================================"
