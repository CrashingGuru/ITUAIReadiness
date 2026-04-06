"""Knowledge Base manager — persistent ChromaDB collections.

The KB stores validated, published information and is the authoritative
data source for agent reasoning.  Every mutation is audit-logged.

Collections
-----------
- kb_main       : ingested document chunks (the bulk of RAG data)
- kb_framework  : pre-loaded ITU dimension / metric definitions
- kb_decisions  : delegate decisions that modified the KB
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings

from server.config import settings

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Persistent Knowledge Base backed by ChromaDB."""

    def __init__(self, persist_dir: Optional[str] = None):
        persist_dir = persist_dir or str(settings.chromadb_dir)
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Lazily created on first access
        self._collections: dict[str, chromadb.Collection] = {}

    # ------------------------------------------------------------------
    # Collection helpers
    # ------------------------------------------------------------------

    def _col(self, name: str) -> chromadb.Collection:
        """Get or create a collection by name."""
        if name not in self._collections:
            self._collections[name] = self._client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    @property
    def main(self) -> chromadb.Collection:
        return self._col(settings.kb_main_collection)

    @property
    def framework(self) -> chromadb.Collection:
        return self._col(settings.kb_framework_collection)

    @property
    def decisions(self) -> chromadb.Collection:
        return self._col(settings.kb_decisions_collection)

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        collection_name: Optional[str] = None,
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        """Add document chunks with pre-computed embeddings.

        Returns the list of generated/supplied IDs.
        """
        col = self._col(collection_name) if collection_name else self.main
        if ids is None:
            ids = [str(uuid4()) for _ in texts]

        # ChromaDB add in batches of 5000 max
        batch_size = 5000
        for i in range(0, len(texts), batch_size):
            end = min(i + batch_size, len(texts))
            col.add(
                ids=ids[i:end],
                documents=texts[i:end],
                embeddings=embeddings[i:end],
                metadatas=metadatas[i:end],
            )

        logger.info("Added %d documents to collection '%s'", len(texts), col.name)
        return ids

    def add_decision(
        self,
        decision_text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> str:
        """Record a delegate decision in the decisions collection."""
        doc_id = str(uuid4())
        metadata.setdefault("timestamp", datetime.utcnow().isoformat())
        metadata.setdefault("entity_type", "decision")
        self.decisions.add(
            ids=[doc_id],
            documents=[decision_text],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        logger.info("Recorded decision %s", doc_id)
        return doc_id

    # ------------------------------------------------------------------
    # Read / search operations
    # ------------------------------------------------------------------

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        collection_name: Optional[str] = None,
        where: Optional[dict[str, Any]] = None,
        where_document: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Semantic search against a collection.

        Returns ChromaDB query result dict with keys:
        ids, documents, metadatas, distances, embeddings
        """
        col = self._col(collection_name) if collection_name else self.main
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, col.count() or 1),
            "include": ["documents", "metadatas", "distances", "embeddings"],
        }
        if where:
            kwargs["where"] = where
        if where_document:
            kwargs["where_document"] = where_document

        return col.query(**kwargs)

    def search_by_dimension(
        self,
        query_embedding: list[float],
        dimension_id: int,
        n_results: int = 5,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search filtered to a specific dimension."""
        return self.search(
            query_embedding=query_embedding,
            n_results=n_results,
            collection_name=collection_name,
            where={"dimension_id": dimension_id},
        )

    def search_by_factor(
        self,
        query_embedding: list[float],
        factor: str,
        n_results: int = 5,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search filtered to a specific factor."""
        return self.search(
            query_embedding=query_embedding,
            n_results=n_results,
            collection_name=collection_name,
            where={"factor": factor},
        )

    def search_by_country(
        self,
        query_embedding: list[float],
        country: str,
        n_results: int = 5,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search filtered to a specific country."""
        return self.search(
            query_embedding=query_embedding,
            n_results=n_results,
            collection_name=collection_name,
            where={"country": country},
        )

    def search_text(
        self,
        query_embedding: list[float],
        contains: str,
        n_results: int = 5,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search with a text-contains filter on document content."""
        return self.search(
            query_embedding=query_embedding,
            n_results=n_results,
            collection_name=collection_name,
            where_document={"$contains": contains},
        )

    def get_by_id(
        self,
        doc_id: str,
        collection_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Retrieve a single document by ID."""
        col = self._col(collection_name) if collection_name else self.main
        return col.get(ids=[doc_id], include=["documents", "metadatas", "embeddings"])

    def get_all(
        self,
        collection_name: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        """Retrieve all documents from a collection."""
        col = self._col(collection_name) if collection_name else self.main
        kwargs: dict[str, Any] = {"include": ["documents", "metadatas"]}
        if limit:
            kwargs["limit"] = limit
        return col.get(**kwargs)

    # ------------------------------------------------------------------
    # Stats / utility
    # ------------------------------------------------------------------

    def count(self, collection_name: Optional[str] = None) -> int:
        col = self._col(collection_name) if collection_name else self.main
        return col.count()

    def stats(self) -> dict[str, int]:
        """Return document counts per collection."""
        return {
            "kb_main": self.main.count(),
            "kb_framework": self.framework.count(),
            "kb_decisions": self.decisions.count(),
        }

    def delete_collection(self, collection_name: str) -> None:
        """Delete an entire collection (use with caution)."""
        self._client.delete_collection(collection_name)
        self._collections.pop(collection_name, None)
        logger.warning("Deleted collection '%s'", collection_name)

    def reset(self) -> None:
        """Delete all collections and start fresh (destructive!)."""
        for name in [
            settings.kb_main_collection,
            settings.kb_framework_collection,
            settings.kb_decisions_collection,
        ]:
            try:
                self._client.delete_collection(name)
            except Exception:
                pass
        self._collections.clear()
        logger.warning("Knowledge Base reset — all collections deleted")
