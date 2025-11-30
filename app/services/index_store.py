"""Per-user FAISS index persistence and in-memory cache.

Stores FAISS index file and image_id mapping under `INDEX_DIR`/user_{id}/.

Usage:
- search_topk(user_id, query_vec, k): ensure index exists (load or build), then return top‑K with similarities.
"""
from __future__ import annotations
import json
import os

from flask import current_app
from app.extensions import db
from app.models import Image, Embedding
from app.services.embedding_io import from_bytes
from app.services.vector_index import FaissVectorIndex


CacheEntry = tuple[FaissVectorIndex, list[int]]
_STORE: IndexStore | None = None


class IndexStore:

    def __init__(self) -> None:
        self.base_dir = current_app.config.get("INDEX_DIR", os.path.join(os.getcwd(), "instance", "faiss"))
        self.cache: dict[int, CacheEntry] = {}

    def _user_index_paths(self, user_id: int) -> tuple[str, str]:
        user_dir = os.path.join(self.base_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        idx_path = os.path.join(user_dir, "index.faiss")
        ids_path = os.path.join(user_dir, "ids.json")
        return (idx_path, ids_path)

    def _load_files(self, user_id: int) -> CacheEntry | None:
        idx_path, ids_path = self._user_index_paths(user_id)
        if not (os.path.exists(idx_path) and os.path.exists(ids_path)):
            return None
        try:
            with open(ids_path, "r", encoding="utf-8") as f:
                ids = json.load(f)
                if not isinstance(ids, list):
                    return None
                ids = [int(x) for x in ids]
            idx = FaissVectorIndex.load_from_file(idx_path, norm=True)
            if idx.index is None:
                return None
            return (idx, ids)
        except Exception:
            return None

    def _save_files(self, user_id: int, index: FaissVectorIndex, image_ids: list[int]) -> None:
        idx_path, ids_path = self._user_index_paths(user_id)
        index.save(idx_path)
        with open(ids_path, "w", encoding="utf-8") as f:
            json.dump([int(i) for i in image_ids], f)

    def _build_from_db(self, user_id: int) -> CacheEntry | None:
        # Fetch user's READY images with embeddings ordered by image id (stable mapping)
        rows = (
            db.session.query(Image.id, Embedding.vec, Embedding.dim)
            .join(Embedding, Embedding.image_id == Image.id)
            .filter(Image.owner_id == user_id, Image.status == "READY")
            .order_by(Image.id.asc())
            .all()
        )
        if not rows:
            return None

        image_ids: list[int] = []
        vectors: list[list[float]] = []
        for iid, vec_bytes, dim in rows:
            v = from_bytes(vec_bytes)
            if len(v) != int(dim):
                # skip malformed
                continue
            image_ids.append(int(iid))
            vectors.append(v)

        if not vectors:
            return None

        idx = FaissVectorIndex(norm=True)
        idx.build(vectors)
        return (idx, image_ids)

    def ensure_index(self, user_id: int) -> CacheEntry | None:
        # Try cache
        entry = self.cache.get(user_id)
        if entry is not None:
            return entry
        # Try files
        entry = self._load_files(user_id)
        if entry is not None:
            self.cache[user_id] = entry
            return entry
        # Build and persist
        entry = self._build_from_db(user_id)
        if entry is None:
            return None
        self._save_files(user_id, entry[0], entry[1])
        self.cache[user_id] = entry
        return entry

    def push_vector_id_pairs(self, user_id: int, vectors: list, image_ids: list) -> bool:
        if len(vectors) != len(image_ids):
            return False

        entry = self.cache.get(user_id)
        if entry is None:
            entry = self._load_files(user_id)
            if entry is None:
                entry = self._build_from_db(user_id)
                if entry is None:
                    return False
                self._save_files(user_id, entry[0], entry[1])
            self.cache[user_id] = entry

        idx, existing_ids = entry
        idx.push(vectors)
        existing_ids.extend(image_ids)

        self._save_files(user_id, idx, existing_ids)
        self.cache[user_id] = (idx, existing_ids)
        return True

    def rebuild_index(self, user_id: int) -> bool:
        entry = self._build_from_db(user_id)
        if entry is None:
            return False
        self._save_files(user_id, entry[0], entry[1])
        self.cache[user_id] = entry
        return True

    def search_topk(self, user_id: int, query_vec: list[float], k: int = 10) -> list[tuple[int, float]]:
        entry = self.ensure_index(user_id)
        if entry is None:
            return []
        idx, image_ids = entry
        inds, sims = idx.search_topk_scores(query_vec, k=min(k, len(image_ids)))
        results: list[tuple[int, float]] = []
        for i, s in zip(list(inds), list(sims)):
            # Safety for out-of-range indices
            if 0 <= int(i) < len(image_ids):
                results.append((int(image_ids[int(i)]), float(s)))
        return results


def _initialze_store() -> IndexStore:
    return IndexStore()


def search_topk(user_id: int, query_vec: list[float], k: int = 10) -> list[tuple[int, float]]:
    global _STORE
    if _STORE is None:
        _STORE = _initialze_store()

    return _STORE.search_topk(user_id, query_vec, k=k)


def push_vector_id_pairs(user_id: int, vectors: list, image_ids: list) -> bool:
    global _STORE
    if _STORE is None:
        _STORE = _initialze_store()

    return _STORE.push_vector_id_pairs(user_id, vectors, image_ids)
