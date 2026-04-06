"""Knowledge Cache manager — transient, ephemeral ChromaDB collections.

The Cache is used exclusively for what-if analysis.  Each what-if session
gets its own in-memory collection that is populated from relevant KB
entries, modified with hypothetical changes, queried by agents (with KB
as fallback base), and then discarded.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
logger = logging.getLogger(__name__)


class _NoOpEmbeddingFunction:
    """Dummy embedding function that does nothing.

    We always pass pre-computed embeddings, so this prevents ChromaDB
    from downloading/using a default model with the wrong dimensions.
    """

    def __call__(self, input: list[str]) -> list[list[float]]:
        raise RuntimeError("Cache requires pre-computed embeddings")

    def name(self) -> str:
        return "noop"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _NoOpEmbeddingFunction)

    def __hash__(self) -> int:
        return hash("noop")


class KnowledgeCache:
    """Transient, scenario-based Knowledge Cache backed by ephemeral ChromaDB."""

    def __init__(self):
        self._client = chromadb.EphemeralClient(
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Track active cache sessions: {cache_id: collection_name}
        self._active: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        delegate_id: str,
        scenario_id: Optional[str] = None,
    ) -> str:
        """Create a new cache session and return its cache_id."""
        scenario_id = scenario_id or str(uuid4())[:8]
        cache_id = f"cache_{delegate_id}_{scenario_id}"
        col_name = cache_id[:63]  # ChromaDB name limit

        self._client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=_NoOpEmbeddingFunction(),
        )
        self._active[cache_id] = col_name
        logger.info("Created cache session '%s'", cache_id)
        return cache_id

    def discard_session(self, cache_id: str) -> None:
        """Delete a cache session and free its resources."""
        col_name = self._active.pop(cache_id, None)
        if col_name:
            try:
                self._client.delete_collection(col_name)
            except Exception:
                pass
            logger.info("Discarded cache session '%s'", cache_id)
        else:
            logger.warning("Cache session '%s' not found — nothing to discard", cache_id)

    def discard_all(self) -> None:
        """Discard all active cache sessions."""
        for cache_id in list(self._active.keys()):
            self.discard_session(cache_id)

    # ------------------------------------------------------------------
    # Populate from KB
    # ------------------------------------------------------------------

    def populate_from_kb(
        self,
        cache_id: str,
        kb_results: dict[str, Any],
    ) -> int:
        """Copy KB query results into a cache session.

        Parameters
        ----------
        cache_id : str
            Active cache session ID.
        kb_results : dict
            ChromaDB query result dict (ids, documents, metadatas, embeddings)
            as returned by KnowledgeBase.search() or .get_all().

        Returns
        -------
        int
            Number of documents copied.
        """
        col = self._get_collection(cache_id)

        def _to_list(val):
            """Recursively convert numpy arrays to plain Python lists."""
            try:
                import numpy as np
                if isinstance(val, np.ndarray):
                    return val.tolist()
            except ImportError:
                pass
            if isinstance(val, list):
                return [_to_list(v) for v in val]
            return val

        def _unwrap(key: str) -> list:
            """Unwrap ChromaDB query result (nested [[...]]) into flat [...]."""
            val = kb_results.get(key)
            if val is None:
                return []
            val = _to_list(val)
            if not val:
                return []
            # ChromaDB query results are nested: [[item1, item2, ...]]
            # ChromaDB get results are flat: [item1, item2, ...]
            if val and isinstance(val[0], list) and key != "embeddings":
                return val[0]
            if val and isinstance(val[0], list) and key == "embeddings":
                # For embeddings: [[vec1, vec2, ...]] where each vec is [float, ...]
                inner = val[0]
                if inner and isinstance(inner[0], list):
                    return inner  # already [[float,...], [float,...]]
                return val  # flat list of vectors
            return val

        ids = _unwrap("ids")
        documents = _unwrap("documents")
        metadatas = _unwrap("metadatas")
        embeddings = _unwrap("embeddings")

        if not ids:
            return 0

        # Prefix IDs to avoid collision with KB IDs
        cache_ids = [f"c_{doc_id}" for doc_id in ids]

        add_kwargs = {
            "ids": cache_ids,
            "documents": documents,
            "metadatas": metadatas,
        }
        if embeddings and len(embeddings) == len(ids):
            add_kwargs["embeddings"] = embeddings
        col.add(**add_kwargs)
        logger.info("Populated cache '%s' with %d documents", cache_id, len(ids))
        return len(ids)

    # ------------------------------------------------------------------
    # Hypothetical modifications
    # ------------------------------------------------------------------

    def add_hypothetical(
        self,
        cache_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> str:
        """Add a hypothetical (what-if) document to the cache."""
        col = self._get_collection(cache_id)
        doc_id = f"hyp_{uuid4()!s:.8}"
        metadata["is_hypothetical"] = True
        col.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
        )
        return doc_id

    def modify_hypothetical(
        self,
        cache_id: str,
        doc_id: str,
        new_text: Optional[str] = None,
        new_embedding: Optional[list[float]] = None,
        new_metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update an existing document in the cache with hypothetical changes."""
        col = self._get_collection(cache_id)
        kwargs: dict[str, Any] = {"ids": [doc_id]}
        if new_text is not None:
            kwargs["documents"] = [new_text]
        if new_embedding is not None:
            kwargs["embeddings"] = [new_embedding]
        if new_metadata is not None:
            new_metadata["is_hypothetical"] = True
            kwargs["metadatas"] = [new_metadata]
        col.update(**kwargs)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        cache_id: str,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Semantic search within a cache session."""
        col = self._get_collection(cache_id)
        count = col.count()
        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(n_results, count),
        }
        if where:
            kwargs["where"] = where
        return col.query(**kwargs)

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def count(self, cache_id: str) -> int:
        return self._get_collection(cache_id).count()

    def list_sessions(self) -> list[str]:
        return list(self._active.keys())

    def is_active(self, cache_id: str) -> bool:
        return cache_id in self._active

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_collection(self, cache_id: str) -> chromadb.Collection:
        col_name = self._active.get(cache_id)
        if not col_name:
            raise ValueError(f"Cache session '{cache_id}' not found or already discarded")
        return self._client.get_collection(col_name, embedding_function=_NoOpEmbeddingFunction())
