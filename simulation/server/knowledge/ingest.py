"""Document ingestion pipeline.

Reads files from InputDocs/ → parses (docling for PDF, plain read for
txt/md) → chunks (~512 tokens, 50 overlap) → embeds via Ollama
nomic-embed-text → stores in ChromaDB Knowledge Base with metadata.

Can be run standalone:
    python -m server.knowledge.ingest [--dir DIR] [--reset]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import ollama

from server.config import settings
from server.knowledge.kb import KnowledgeBase

logger = logging.getLogger(__name__)

# Source type inference from filename patterns
_SOURCE_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)ITU|Y\.3172|AI4G|sandbox", "standards_document"),
    (r"(?i)UNESCO|OECD|Oxford|UNCTAD|CCIA|Turing", "international_org_report"),
    (r"(?i)national.*(strategy|plan)|NAIS|SDAIA|EBIA|PBIA", "national_strategy"),
    (r"(?i)policy|regulation|act|governance", "policy_document"),
    (r"(?i)sample_national", "national_strategy"),
    (r"(?i)AI_Ready_Framework", "international_org_report"),
]

# Country inference from filename
_COUNTRY_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)ethiopia", "Ethiopia"),
    (r"(?i)saudi|SDAIA|NSDAI", "Saudi Arabia"),
    (r"(?i)egypt", "Egypt"),
    (r"(?i)kenya", "Kenya"),
    (r"(?i)zambia", "Zambia"),
    (r"(?i)brazil|PBIA|EBIA", "Brazil"),
    (r"(?i)india|NITI", "India"),
    (r"(?i)singapore|NAIS", "Singapore"),
    (r"(?i)japan", "Japan"),
    (r"(?i)china", "China"),
    (r"(?i)\bUS\b|USA|united.states", "United States"),
    (r"(?i)\bUK\b|united.kingdom", "United Kingdom"),
    (r"(?i)\bEU\b|european", "European Union"),
    (r"(?i)african.union", "African Union"),
]


# ------------------------------------------------------------------
# Parsing
# ------------------------------------------------------------------

def parse_file(filepath: Path) -> str:
    """Parse a file into plain text.

    Uses docling for PDFs (with fallback to PyMuPDF), plain read for
    text files.
    """
    suffix = filepath.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(filepath)
    elif suffix in (".txt", ".md", ".csv"):
        return filepath.read_text(encoding="utf-8", errors="replace")
    elif suffix == ".html":
        return _strip_html(filepath.read_text(encoding="utf-8", errors="replace"))
    else:
        logger.warning("Unknown file type '%s' for %s — reading as text", suffix, filepath.name)
        return filepath.read_text(encoding="utf-8", errors="replace")


def _parse_pdf(filepath: Path) -> str:
    """Parse PDF, trying docling first, then PyMuPDF fallback."""
    # Try docling
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        result = converter.convert(str(filepath))
        text = result.document.export_to_markdown()
        if text and len(text.strip()) > 100:
            logger.info("Parsed %s with docling (%d chars)", filepath.name, len(text))
            return text
    except ImportError:
        logger.debug("docling not installed, trying PyMuPDF")
    except Exception as e:
        logger.warning("docling failed for %s: %s — trying PyMuPDF", filepath.name, e)

    # Fallback: PyMuPDF
    try:
        import fitz
        doc = fitz.open(str(filepath))
        pages = []
        for page in doc:
            pages.append(page.get_text())
        text = "\n\n".join(pages)
        logger.info("Parsed %s with PyMuPDF (%d chars, %d pages)", filepath.name, len(text), len(pages))
        return text
    except ImportError:
        logger.error("Neither docling nor PyMuPDF installed — cannot parse PDF %s", filepath.name)
        return ""
    except Exception as e:
        logger.error("PyMuPDF failed for %s: %s", filepath.name, e)
        return ""


def _strip_html(html: str) -> str:
    """Crude HTML tag stripping."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ------------------------------------------------------------------
# Chunking
# ------------------------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = settings.chunk_size,
    overlap: int = settings.chunk_overlap,
    max_chars: int = 2000,
) -> list[str]:
    """Split text into overlapping chunks by word count.

    Uses paragraph boundaries when possible, falling back to word-level
    splitting.  Each chunk is also hard-capped at *max_chars* characters
    to stay within embedding model context limits (nomic-embed-text has
    an 8192 token context; 6000 chars ≈ ~1500 tokens, well within limit).
    """
    if not text or not text.strip():
        return []

    # Split into paragraphs first
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[str] = []
    current_words: list[str] = []

    for para in paragraphs:
        words = para.split()
        for word in words:
            current_words.append(word)
            if len(current_words) >= chunk_size:
                chunks.append(" ".join(current_words))
                # Keep overlap words for next chunk
                current_words = current_words[-overlap:] if overlap > 0 else []

    # Don't forget the last chunk
    if current_words:
        last_chunk = " ".join(current_words)
        # Only add if it has meaningful content (> 20 words)
        if len(current_words) > 20 or not chunks:
            chunks.append(last_chunk)
        elif chunks:
            # Append short trailing text to last chunk
            chunks[-1] = chunks[-1] + " " + last_chunk

    # Hard-cap: split any chunk that exceeds max_chars
    safe_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            safe_chunks.append(chunk)
        else:
            # Split oversized chunk into max_chars pieces by character
            for i in range(0, len(chunk), max_chars):
                piece = chunk[i : i + max_chars].strip()
                if piece:
                    safe_chunks.append(piece)

    return safe_chunks


# ------------------------------------------------------------------
# Embedding
# ------------------------------------------------------------------

def embed_texts(
    texts: list[str],
    model: str = settings.embed_model,
    base_url: str = settings.ollama_base_url,
) -> list[list[float]]:
    """Embed a list of texts using Ollama.

    Truncates any text over 7500 chars (~1800 tokens) to stay within
    nomic-embed-text's 8192 token context.  Falls back to one-at-a-time
    embedding if a batch call fails.
    """
    client = ollama.Client(host=base_url)
    max_text_chars = 2000  # conservative limit for nomic-embed-text (8192 token ctx)

    # Pre-truncate long texts
    safe_texts = [t[:max_text_chars] if len(t) > max_text_chars else t for t in texts]

    embeddings: list[list[float]] = []
    batch_size = 16

    for i in range(0, len(safe_texts), batch_size):
        batch = safe_texts[i : i + batch_size]
        try:
            response = client.embed(model=model, input=batch)
            embeddings.extend(response["embeddings"])
        except Exception:
            # Fallback: embed one at a time
            logger.warning("Batch embed failed at offset %d, falling back to one-at-a-time", i)
            for j, text in enumerate(batch):
                try:
                    resp = client.embed(model=model, input=[text])
                    embeddings.extend(resp["embeddings"])
                except Exception as e2:
                    # Last resort: truncate aggressively
                    logger.warning("Single embed failed for chunk %d (len=%d), truncating to 4000 chars", i + j, len(text))
                    resp = client.embed(model=model, input=[text[:4000]])
                    embeddings.extend(resp["embeddings"])

    return embeddings


# ------------------------------------------------------------------
# Metadata inference
# ------------------------------------------------------------------

def infer_source_type(filename: str) -> str:
    """Infer source type from filename patterns."""
    for pattern, source_type in _SOURCE_TYPE_PATTERNS:
        if re.search(pattern, filename):
            return source_type
    return "international_org_report"


def infer_country(filename: str) -> str:
    """Infer country from filename patterns. Returns 'global' if unknown."""
    for pattern, country in _COUNTRY_PATTERNS:
        if re.search(pattern, filename):
            return country
    return "global"


def build_metadata(
    filepath: Path,
    chunk_index: int,
    total_chunks: int,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """Build metadata dict for a document chunk."""
    meta: dict[str, str] = {
        "source_file": filepath.name,
        "source_type": infer_source_type(filepath.name),
        "country": infer_country(filepath.name),
        "chunk_index": str(chunk_index),
        "total_chunks": str(total_chunks),
        "ingested_at": datetime.utcnow().isoformat(),
    }
    if extra:
        for k, v in extra.items():
            meta[k] = str(v)
    return meta


# ------------------------------------------------------------------
# Main ingestion
# ------------------------------------------------------------------

def ingest_file(
    filepath: Path,
    kb: KnowledgeBase,
    collection_name: Optional[str] = None,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> int:
    """Ingest a single file into the Knowledge Base.

    Returns the number of chunks stored.
    """
    logger.info("Ingesting %s ...", filepath.name)

    # Parse
    text = parse_file(filepath)
    if not text.strip():
        logger.warning("No text extracted from %s — skipping", filepath.name)
        return 0

    # Chunk
    chunks = chunk_text(text)
    if not chunks:
        logger.warning("No chunks produced from %s — skipping", filepath.name)
        return 0

    logger.info("  %d chunks from %s", len(chunks), filepath.name)

    # Embed
    embeddings = embed_texts(chunks)

    # Build metadata per chunk
    metadatas = [
        build_metadata(filepath, i, len(chunks), extra_metadata)
        for i in range(len(chunks))
    ]

    # Store
    kb.add_documents(
        texts=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
        collection_name=collection_name,
    )

    logger.info("  Stored %d chunks from %s", len(chunks), filepath.name)
    return len(chunks)


def ingest_directory(
    directory: Path,
    kb: KnowledgeBase,
    collection_name: Optional[str] = None,
    skip_manifest: bool = True,
) -> dict[str, int]:
    """Ingest all supported files from a directory.

    Returns {filename: chunk_count} mapping.
    """
    supported = {".pdf", ".txt", ".md", ".csv", ".html"}
    results: dict[str, int] = {}

    files = sorted(directory.iterdir())
    for filepath in files:
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in supported:
            continue
        if skip_manifest and filepath.name.lower() == "inputs.md":
            continue

        try:
            count = ingest_file(filepath, kb, collection_name)
            results[filepath.name] = count
        except Exception as e:
            logger.error("Failed to ingest %s: %s", filepath.name, e)
            results[filepath.name] = 0

    return results


def ingest_framework_definitions(kb: KnowledgeBase) -> int:
    """Load dimensions.json into the kb_framework collection.

    Each dimension becomes one document with its full description
    and metric list embedded for retrieval.
    """
    dims_path = settings.framework_dir / "dimensions.json"
    if not dims_path.exists():
        logger.error("dimensions.json not found at %s", dims_path)
        return 0

    with open(dims_path) as f:
        data = json.load(f)

    texts: list[str] = []
    metadatas: list[dict[str, str]] = []

    # Add each dimension as a document
    for dim in data["dimensions"]:
        metrics_text = "\n".join(
            f"- {m['name']}: {m['description']}" for m in dim["metrics"]
        )
        doc_text = (
            f"Dimension {dim['id']}: {dim['name']}\n\n"
            f"{dim['description']}\n\n"
            f"Mapped Factors: {', '.join(dim['mapped_factors'])}\n\n"
            f"Metrics:\n{metrics_text}"
        )
        texts.append(doc_text)
        metadatas.append({
            "dimension_id": str(dim["id"]),
            "dimension_name": dim["name"],
            "short_name": dim["short_name"],
            "source_type": "framework_definition",
            "entity_type": "dimension",
            "factors": ",".join(dim["mapped_factors"]),
        })

    # Add each factor as a document
    for factor in data["factors"]:
        texts.append(
            f"Factor: {factor['name']}\n\n{factor['description']}"
        )
        metadatas.append({
            "factor_id": factor["id"],
            "factor_name": factor["name"],
            "source_type": "framework_definition",
            "entity_type": "factor",
        })

    embeddings = embed_texts(texts)

    kb.add_documents(
        texts=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        collection_name=settings.kb_framework_collection,
    )

    logger.info("Loaded %d framework definitions into kb_framework", len(texts))
    return len(texts)


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Ingest documents into the AI Readiness Knowledge Base"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=settings.input_docs_dir,
        help="Directory containing documents to ingest",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Ingest a single file",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the Knowledge Base before ingesting",
    )
    parser.add_argument(
        "--framework-only",
        action="store_true",
        help="Only load framework definitions (dimensions.json)",
    )
    args = parser.parse_args()

    # Ensure directories exist
    settings.chromadb_dir.mkdir(parents=True, exist_ok=True)

    kb = KnowledgeBase()

    if args.reset:
        logger.warning("Resetting Knowledge Base...")
        kb.reset()

    # Always load framework definitions
    logger.info("Loading framework definitions...")
    fw_count = ingest_framework_definitions(kb)
    print(f"Framework definitions: {fw_count} documents loaded")

    if args.framework_only:
        print("\nDone (framework only).")
        print(f"KB stats: {kb.stats()}")
        return

    if args.file:
        count = ingest_file(args.file, kb)
        print(f"\n{args.file.name}: {count} chunks ingested")
    else:
        doc_dir = args.dir
        if not doc_dir.exists():
            print(f"ERROR: Directory not found: {doc_dir}")
            sys.exit(1)

        print(f"\nIngesting all documents from: {doc_dir}")
        results = ingest_directory(doc_dir, kb)

        print("\n--- Ingestion Results ---")
        total = 0
        for filename, count in sorted(results.items()):
            status = f"{count} chunks" if count > 0 else "SKIPPED"
            print(f"  {filename:50s} {status}")
            total += count
        print(f"\nTotal: {total} chunks from {len(results)} files")

    print(f"\nKB stats: {kb.stats()}")


if __name__ == "__main__":
    main()
