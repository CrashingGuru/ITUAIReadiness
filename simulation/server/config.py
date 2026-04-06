"""Configuration settings for the AI Readiness Simulation Game."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.1:8b"
    embed_model: str = "nomic-embed-text"

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = base_dir / "data"
    chromadb_dir: Path = data_dir / "chromadb"
    docs_dir: Path = data_dir / "docs"
    framework_dir: Path = data_dir / "framework"
    input_docs_dir: Path = base_dir / "server" / "knowledge" / "InputDocs"
    db_path: Path = data_dir / "game.db"

    # ChromaDB collections
    kb_main_collection: str = "kb_main"
    kb_decisions_collection: str = "kb_decisions"
    kb_framework_collection: str = "kb_framework"

    # Chunking
    chunk_size: int = 256
    chunk_overlap: int = 30

    # Scoring
    maturity_scale_min: float = 0.0
    maturity_scale_max: float = 5.0
    similarity_threshold: float = 0.7

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_prefix = "AIREADY_"


settings = Settings()
