from __future__ import annotations
from typing import List, Tuple
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models import Image, Embedding
from app.services.embedding_io import from_bytes
from app.services.vector_index import FaissVectorIndex
from app.services.index_store import search_topk
from app.services.clip_pipeline import embed_text
from app.utils.responses import ok, error

search_bp = Blueprint("search", __name__, url_prefix="/api/v1/search")


@search_bp.post("/vector")
@jwt_required()
def search_by_vector():
    """直接用提交的向量检索相似图片（便于无模型环境下联调）。

    Request JSON:
    - vector: list[float] (required)
    - k: int (optional, default 10)
    """
    data = request.get_json(silent=True) or {}
    vector = data.get("vector")
    if not isinstance(vector, list) or len(vector) == 0:
        return error("INVALID_VECTOR", "vector 必须为非空数组")
    try:
        k = int(data.get("k", 10))
    except Exception:
        return error("INVALID_K", "k 必须为整数")

    user_id = int(get_jwt_identity())
    rows = (
        db.session.query(Image.id, Embedding.vec, Embedding.dim)
        .join(Embedding, Embedding.image_id == Image.id)
        .filter(
            Image.owner_id == user_id,
            Image.status == "READY"
        )
        .order_by(Image.id.asc())
        .all()
    )
    if not rows:
        return ok({"results": [], "note": "no embeddings for current user"})

    image_ids: List[int] = []
    vectors: List[List[float]] = []
    for iid, vec_bytes, dim in rows:
        v = from_bytes(vec_bytes)
        if len(v) != int(dim):
            return error("EMBED_DIM_MISMATCH", f"image {iid} 向量维度不匹配: got {len(v)}, expect {dim}")
        image_ids.append(int(iid))
        vectors.append(v)

    # 优先使用持久化索引（per-user），其次使用临时内存索引，再退回纯 Python
    try:
        # Try persistent per-user index first
        pairs = search_topk(user_id, vector, k=k)
        if not pairs:
            # Build ephemeral index as fallback
            index = FaissVectorIndex(norm=True)
            index.build(vectors)
            inds, sims = index.search_topk_scores(vector, k=min(k, len(vectors)))
            pairs = [(int(image_ids[int(i)]), float(s)) for i, s in zip(inds, sims)]
        results = [{"image_id": iid, "similarity": sim, "rank": r + 1} for r, (iid, sim) in enumerate(pairs)]
        return ok({"results": results, "count": len(results)})
    except ValueError as e:
        # Common case: 查询向量维度与索引维度不一致
        return error("VECTOR_DIM_MISMATCH", str(e))
    except Exception as e:
        return error("", str(e))


@search_bp.post("/text")
@jwt_required()
def search_text():
    """文本检索：embed_text(query) → 在当前用户可见集上检索 top‑K。

    Request JSON:
    - query: str (required)
    - k: int (optional, default 10)
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return error("INVALID_QUERY", "query 不能为空")
    try:
        k = int(data.get("k", 10))
    except Exception:
        return error("INVALID_K", "k 必须为整数")

    vec = embed_text(query)
    if vec is None:
        return error(
            "EMBED_TEXT_FAILED",
            "文本嵌入失败或依赖缺失，请确认已安装 sentence-transformers/numpy/Pillow。",
        )

    user_id = int(get_jwt_identity())
    rows = (
        db.session.query(Image.id, Embedding.vec, Embedding.dim)
        .join(Embedding, Embedding.image_id == Image.id)
        .filter(
            Image.owner_id == user_id,
            Image.status == "READY"
        )
        .order_by(Image.id.asc())
        .all()
    )
    if not rows:
        return ok({"results": [], "note": "no embeddings for current user"})

    image_ids: List[int] = []
    vectors: List[List[float]] = []
    for iid, vec_bytes, dim in rows:
        v = from_bytes(vec_bytes)
        if len(v) != int(dim):
            return error("EMBED_DIM_MISMATCH", f"image {iid} 向量维度不匹配: got {len(v)}, expect {dim}")
        image_ids.append(int(iid))
        vectors.append(v)

    try:
        pairs = search_topk(user_id, vec, k=k)
        if not pairs:
            index = FaissVectorIndex(norm=True)
            index.build(vectors)
            inds, sims = index.search_topk_scores(vec, k=min(k, len(vectors)))
            pairs = [(int(image_ids[int(i)]), float(s)) for i, s in zip(inds, sims)]
        results = [{"image_id": iid, "similarity": sim, "rank": r + 1} for r, (iid, sim) in enumerate(pairs)]
        return ok({"results": results, "count": len(results)})
    except ValueError as e:
        return error("VECTOR_DIM_MISMATCH", str(e))
    except Exception as e:
        return error("", str(e))


@search_bp.get("/image/<int:image_id>/similar")
@jwt_required()
def similar_images(image_id: int):
    """基于库内向量做“以图找图”。只在当前用户可见集上检索。

    Query params:
    - k: 返回数量（默认 10）
    """
    try:
        k = int(request.args.get("k", 10))
    except Exception:
        return error("INVALID_K", "k 必须为整数")

    user_id = int(get_jwt_identity())

    # 只检索当前用户的 READY 图片且已有 embedding
    rows = (
        db.session.query(Image.id, Embedding.vec, Embedding.dim)
        .join(Embedding, Embedding.image_id == Image.id)
        .filter(
            Image.owner_id == user_id,
            Image.status == "READY"
        )
        .order_by(Image.id.asc())
        .all()
    )
    if not rows:
        return ok({"results": [], "note": "no embeddings for current user"})

    image_ids: List[int] = []
    vectors: List[List[float]] = []
    ref_idx: int | None = None
    for idx, (iid, vec_bytes, dim) in enumerate(rows):
        image_ids.append(int(iid))
        v = from_bytes(vec_bytes)
        if len(v) != int(dim):
            return error("EMBED_DIM_MISMATCH", f"image {iid} 向量维度不匹配: got {len(v)}, expect {dim}")
        vectors.append(v)
        if iid == image_id:
            ref_idx = idx

    if ref_idx is None:
        return error("TARGET_NO_EMBED", "目标图片不存在或尚未生成 embedding", http=404)

    # 若只有一条（自身），则无相似项
    if len(vectors) <= 1:
        return ok({"results": []})

    try:
        # Use persistent index if available
        ref_vec = vectors[ref_idx]
        pairs = search_topk(user_id, ref_vec, k=k + 1)
        # remove self
        pairs = [(iid, sim) for (iid, sim) in pairs if iid != image_id][:k]
        if not pairs:
            # Fallback: ephemeral index
            index = FaissVectorIndex(norm=True)
            index.build(vectors)
            kq = min(k + 1, len(vectors))
            inds, sims = index.search_topk_scores(ref_vec, k=kq)
            temp_pairs = [(int(image_ids[int(i)]), float(s)) for i, s in zip(inds, sims)]
            pairs = [(iid, sim) for (iid, sim) in temp_pairs if iid != image_id][:k]
        results = [{"image_id": iid, "similarity": sim, "rank": r + 1} for r, (iid, sim) in enumerate(pairs)]
        return ok({"results": results, "count": len(results)})
    except Exception as e:
        return error("", str(e))
