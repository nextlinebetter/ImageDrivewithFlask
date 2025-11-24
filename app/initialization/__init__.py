import os
import uuid
import hashlib
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from app.models import Image, Embedding, OCRText, db
from app.services.clip_pipeline import embed_image_path_batch
from app.services.embedding_io import l2_normalize, to_bytes
from app.services.ocr_pipeline import ocr_extract_from_image_path_batch


def batch_upload_dataset():
    dataset_path = current_app.config.get("DATASET_PATH", "./data/tiny-imagenet-200/train")
    if not os.path.exists(dataset_path):
        current_app.logger.error("Dataset path does not exist: %s", dataset_path)
        return
    
    current_app.logger.info("Starting batch upload from dataset: %s", dataset_path)
    
    image_paths = []
    # TODO: read extensions from app.config
    valid_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.JPEG', '.JPG'}
    
    for class_dir in os.listdir(dataset_path):
        class_path = os.path.join(dataset_path, class_dir)
        if not os.path.isdir(class_path):
            continue

        images_dir = os.path.join(class_path, "images")
        if not os.path.exists(images_dir):
            current_app.logger.warning("No 'images' directory found in %s", class_path)
            continue
            
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            if os.path.isfile(file_path) and any(filename.lower().endswith(ext) for ext in valid_extensions):
                image_paths.append(file_path)
    
    current_app.logger.info("Found %d images in dataset", len(image_paths))
    
    if not image_paths:
        current_app.logger.warning("No images found in dataset")
        return
    
    _process_images_in_batches(image_paths)


def _process_images_in_batches(image_paths, batch_size=32):    
    total_images = len(image_paths)
    processed_count = 0
    success_count = 0
    
    owner_id = 1  # public user
    
    for i in range(0, total_images, batch_size):
        batch_paths = image_paths[i:i + batch_size]
        current_batch_num = (i // batch_size) + 1
        total_batches = (total_images + batch_size - 1) // batch_size
        
        current_app.logger.info(
            "Processing batch %d/%d (%d images)...", 
            current_batch_num, total_batches, len(batch_paths)
        )
        
        clip_embeddings = None
        try:
            clip_embeddings = embed_image_path_batch(batch_paths, batch_size=8)
        except Exception as e:
            current_app.logger.error("Failed to batch embed images: %s", e)
        
        ocr_texts = None
        try:
            ocr_texts = ocr_extract_from_image_path_batch(batch_paths, batch_size=8)
        except Exception as e:
            current_app.logger.error("Failed to batch OCR images: %s", e)
        
        batch_success = 0
        for j, image_path in enumerate(batch_paths):
            try:
                processed_count += 1

                checksum = _compute_file_checksum(image_path)
                existing_image = Image.query.filter_by(checksum=checksum).first()
                if existing_image:
                    current_app.logger.debug("Image already exists: %s", image_path)
                    continue
                
                original_filename = os.path.basename(image_path)
                ext = os.path.splitext(secure_filename(original_filename))[-1].lower()
                new_name = f"{uuid.uuid4().hex}{ext}"
                
                img = Image(
                    owner_id=owner_id,
                    original_filename=original_filename,
                    storage_uri=f"local://{new_name}",
                    mime_type="image/jpeg",  # 
                    checksum=checksum,
                    status="READY",
                    visibility="public" if owner_id == 1 else "private",
                )
                db.session.add(img)
                db.session.flush()  # get img.id, but not commit yet
                
                if clip_embeddings is not None and j < len(clip_embeddings):
                    vec = clip_embeddings[j]
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
                
                if ocr_texts is not None and j < len(ocr_texts):
                    text = ocr_texts[j]
                    if text is not None:
                        ocr_row = OCRText(image_id=img.id, text=text, avg_confidence=None)
                        db.session.add(ocr_row)
                
                batch_success += 1
                success_count += 1
                
                if processed_count % 100 == 0:
                    current_app.logger.info(
                        "Progress: %d/%d images processed (%d successful)", 
                        processed_count, total_images, success_count
                    )
                    
            except Exception as e:
                current_app.logger.error("Failed to process image %s: %s", image_path, e)
                db.session.rollback()
                continue
        
        # commit after each batch
        try:
            db.session.commit()
            current_app.logger.info(
                "Batch %d/%d completed: %d/%d images successfully processed", 
                current_batch_num, total_batches, batch_success, len(batch_paths)
            )
        except SQLAlchemyError as e:
            current_app.logger.error("Failed to commit batch %d: %s", current_batch_num, e)
            db.session.rollback()
    
    current_app.logger.info(
        "Batch upload completed: %d/%d images successfully processed", 
        success_count, total_images
    )


def _compute_file_checksum(file_path):
    """compute SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        current_app.logger.error("Failed to compute checksum for %s: %s", file_path, e)
        return None


def init_base_data(app):
    with app.app_context():
        if app.config.get("ENABLE_BATCH_UPLOAD", False):
            try:
                current_app.logger.info("Starting batch dataset upload...")
                batch_upload_dataset()
                current_app.logger.info("Batch dataset upload completed.")
            except Exception as e:
                current_app.logger.error("Batch dataset upload failed: %s", e)

