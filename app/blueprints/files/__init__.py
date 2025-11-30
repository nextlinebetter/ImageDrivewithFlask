from __future__ import annotations
import os
import uuid
import hashlib
from werkzeug.utils import secure_filename
from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Image, Embedding, OCRText
from app.services.clip_pipeline import embed_image_path
from app.services.ocr_pipeline import ocr_extract_from_image_path
from app.services.embedding_io import l2_normalize, to_bytes
from app.services.index_store import push_vector_id_pairs
from app.utils.responses import ok, error

files_bp = Blueprint("files", __name__, url_prefix="/api/v1/files")


def _ensure_upload_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _compute_sha256(stream) -> str:
    pos = stream.tell() if stream.seekable() else None
    h = hashlib.sha256()
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        if isinstance(chunk, str):
            chunk = chunk.encode("utf-8")
        h.update(chunk)
    if pos is not None:
        stream.seek(pos)
    return h.hexdigest()


@files_bp.post("/upload")
@jwt_required()
def upload_file():
    # Validate file presence
    if "file" not in request.files:
        return error("NO_FILE", "Attribute 'file' not found in form data.")
    file = request.files["file"]
    if not file or file.filename == "":
        return error("EMPTY_FILE", "Empty file in attribute 'file'.")

    # Validate size (Flask will also enforce MAX_CONTENT_LENGTH)
    # Validate mime
    allowed = current_app.config.get("UPLOAD_ALLOWED_MIME", [])
    mime = file.mimetype or ""
    if allowed and mime not in allowed:
        return error("INVALID_MIME", f"File mime not supported: {mime}")

    # Prepare paths
    upload_dir = current_app.config.get("UPLOAD_DIR", os.path.join(os.getcwd(), "uploads"))
    _ensure_upload_dir(upload_dir)

    # Filename handling
    original_name = file.filename
    ext = os.path.splitext(secure_filename(original_name))[-1].lower()
    new_name = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(upload_dir, new_name)

    # Compute checksum before saving (read stream, then save)
    checksum = _compute_sha256(file.stream)
    file.stream.seek(0)
    file.save(abs_path)

    # Persist image record
    owner_id = int(get_jwt_identity())
    img = Image(
        owner_id=owner_id,
        original_filename=original_name,
        storage_uri=f"local://{new_name}",
        mime_type=mime,
        checksum=checksum,
        status="READY",
        visibility="private",
    )
    db.session.add(img)
    db.session.commit()

    abs_public_path = abs_path  # currently local storage; could map from storage_uri later
    # Online embedding
    vec = embed_image_path(abs_public_path)
    if vec is not None:
        norm_vec = l2_normalize(vec)
        payload = to_bytes(norm_vec)
        emb = Embedding(
            image_id=img.id,
            vec=payload,
            dim=len(norm_vec),
            model_version=current_app.config.get("CLIP_MODEL_NAME", "clip-ViT-B-32")
        )
        db.session.add(emb)
        db.session.commit()

        # update vector index
        if not push_vector_id_pairs(owner_id, [norm_vec], [img.id]):
            current_app.logger.warning("Failed to add image (id: '%d') and its vector to existing index", img.id)

    # Online OCR
    text = ocr_extract_from_image_path(abs_public_path)
    row = OCRText.query.filter_by(image_id=img.id).first()
    if row is None:
        row = OCRText(
            image_id=img.id,
            text=text,
            avg_confidence=None
        )
        db.session.add(row)
        db.session.commit()
    else:
        row.text = text or row.text
        db.session.commit()

    # TODO: dispatch async tasks (generate thumbnails, OCR) ?

    return ok(
        {
            "image_id": img.id,
            "original_filename": img.original_filename,
            "storage_uri": img.storage_uri,
            "mime_type": img.mime_type,
            "checksum": img.checksum,
            "status": img.status,
            "visibility": img.visibility,
            "has_embedding": vec is not None,
            "has_ocr_text": text is not None,
        }
    )
