# Web Image Drive — 一页版设计 V5

本页即权威交付说明；便于评审与实现对齐。后续若需细节可加“详细设计”文档，但本页即可完成开发。

## 目标与非目标
- 目标：本地可运行的图片网盘，支持上传/浏览/下载、语义搜索、以图搜图、OCR 文本搜、相似面板与基础分析。
- 约束：嵌入与 OCR 只在入库时计算一次并持久化；检索阶段不重算库内图片向量。
- 非目标：不在数据库做相似度/ANN；不实现复杂缓存与多索引合并（后续优化）。

## 技术栈（确定）
- 前端：Vue 3 + Vite + Element Plus
- 后端：Flask（REST，JWT access + httpOnly refresh/CSRF）
- 异步：Celery + Redis（embed / ocr / thumbs）
- 存储：MinIO/S3（原图/缩略图），Postgres（元数据/FTS/审计）
- 检索：FAISS IndexFlatL2（归一化 → 余弦）
- 模型：CLIP ViT-B/32（sentence-transformers），OCR: doctr

## 模块契约（最小）
- CLIP：
  - embed_image(path) -> np.float32[512]
  - embed_text(text) -> np.float32[512]
- 向量索引（与同学提供的 vector_index.py 对齐）：
  - build(vectors: np.float32[n,512])
  - search_topk(queries, k) -> indices
  - search_threshold(queries, r2) -> list[indices]；r2 为“平方 L2 半径”
- OCR：extract_text_from_image_path(path) -> Optional[str]
- 对象存储：上传→临时→校验/去重→持久区，返回 uri

## 数据模型（最小）
- images(id, owner_id, uri, filename, checksum, mime, w, h, size, upload_ts, status, visibility)
- embeddings(image_id PK, model_version, dim=512, normalized bool, vec BYTEA|double precision[512], created_at)
- ocr_texts(image_id, text, confidence NULL, created_at)
- categories(id, name unique); image_categories(image_id, category_id)
- audit_logs(id, user_id, action, target_id, details jsonb, ts)

索引要点：images.checksum 唯一去重；ocr_texts.text 建 FTS（pg_trgm）。

## 核心流程（简单版）
1) 入库：上传→去重→写 images(PENDING)→任务 embed/ocr/thumb。
   - embed：CLIP→np.float32→L2 归一化（epsilon 防护）→写 embeddings.vec，normalized=true。
   - ocr：doctr→返回文本→写 ocr_texts（无文本跳过）。
   - 完成后 images.status=READY。
2) 构建索引（按用户、按需）：
   - 选择可见集：READY 且 (owner=uid 或 visibility in (public, system))。
   - SELECT image_id, vec → 组装 np.float32[n,512] → build(vectors)。
   - 保存 positions[]：下标 i 对应 image_id。
3) 搜索：
   - 文本：embed_text(q)→top‑k→positions[I]。
   - 以图：embed_image(q)→top‑k→positions[I]。
   - OCR：PG FTS（pg_trgm）。
   - 相似面板：直接从 DB 取该 image_id 的 vec 作为查询，不 re‑embed。

附：余弦阈值 s_min 与平方 L2 半径换算 r²=2-2·s_min（向量已归一化）。

## API（最小）
- Auth：POST /auth/login|refresh|logout|register|me
- Upload：POST /upload
- Images：GET /images; GET /images/{id}; GET /images/{id}/download; GET /images/{id}/similar?k=
- Search：POST /search/text | /search/image | /search/ocr
- Categories：GET /categories; POST /images/{id}/categories
- Analytics：GET /analytics/summary; GET /analytics/export.csv

## 与同学模块的对接要点
- vector_index.py：IndexFlatL2 + norm=True；search_topk 返回行号，若需分数用 get_index().search() 拿 (D,I)，余弦=1-D/2。
- CLIP：返回 ndarray；入库前统一 np.float32 + 归一化后写 DB。
- OCR：返回聚合文本；confidence 可留空。

### CLIP 批处理（明确调用规范）
用途：服务器端导入初始数据集或一次性大量补图；减少单张调用开销。

接口来源：`EmbeddingProcessor.embed_batch(image_paths, batch_size=32)`。

调用规范：
1. 分块（chunk）而不是一次性传入巨大列表：
   - 将全量路径列表按 chunk_size（建议 256 或 512）切片。
   - 对每个 chunk 调用 embed_batch(image_paths_chunk, batch_size=32)。
   - batch_size 是模型内部处理的微批；chunk_size 是我们外层一次提交给模型的照片数。
2. 每块返回后立即：
   - 对结果矩阵逐行：`vec = vec.astype(np.float32); vec /= (np.linalg.norm(vec)+1e-8)`。
   - 批量写入 embeddings（image_id 对应、model_version、normalized=true、created_at）。
3. 错误处理：
   - embed_batch 返回 None 或长度不符 → 对该 chunk 中的图片降级为单张 embed_image 重试（最多 2 次）。
   - 单张仍失败 → 记录审计：`embedding_failed`，后续索引构建时跳过。
4. 内存注意：
   - PIL 图像全部展开在内存；chunk_size 控制峰值内存。若出现 OOM，减小 chunk_size 或 batch_size。
5. 日志/指标建议：
   - 记录 per-chunk 耗时(ms)、失败数、平均向量范数（用于检测异常，如全零向量）。
6. 不做的事：
   - 不在批处理里直接构建 FAISS 索引；索引只在检索前按用户可见集构建。

## 课程要求对照（精简）
- 一次性嵌入并持久化：是（DB 保存向量；检索仅 FAISS）。
- 语义/以图/OCR 搜索：是（CLIP+FAISS；PG FTS）。
- ≥10 类示例数据集：是（服务器端导入，支持自动打标）。
- 日志与导出：是（结构化日志；统计与 CSV/JSON 导出）。

## 后续优化（不影响当前交付）
- 索引缓存/复用（TTL+签名）、base_index + private_index 归并、删除/权限增量更新、GPU/IVF/HNSW 加速、诊断脚本。