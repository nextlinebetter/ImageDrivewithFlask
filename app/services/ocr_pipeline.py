"""OCR service delegating to teammate's pipeline in `others/imagedrive--OCR-main/ocr_pipeline.py`.

We load the module from file location (folder name contains dashes, not importable as package)
and call `extract_text_from_image_path` directly to keep behavior consistent.
Falls back to None on any error.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from flask import current_app
import numpy as np


_PIPELINE: OCRPipeline | None = None


class OCRPipeline:
    
    def __init__(self, det_arch="db_mobilenet_v3_large", reco_arch="crnn_mobilenet_v3_large"):
        # lazy import
        try:
            import torch
            from doctr.models import ocr_predictor
        except ImportError as e:
            current_app.logger.exception("Failed to import dependencies for OCRPipeline: %s", e)
        
        self.det_arch = det_arch
        self.reco_arch = reco_arch
        try:
            self.device = "mps" if torch.backends.mps.is_available() else \
                        "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            self.device = "cpu"
        current_app.logger.info("Loading OCR model: '%s' + '%s' (using device: %s)...", det_arch, reco_arch, self.device) 

        try:
            self.model = ocr_predictor(det_arch, reco_arch, pretrained=True).to(self.device) 
            current_app.logger.info("Successfully loaded OCR model.")
        except Exception as e:
            current_app.logger.exception("Failed to load OCR model '%s' + '%s': %s", det_arch, reco_arch, e)
            self.model = None

    def _process_image_file(self, image_path: str) -> np.ndarray | None:
        try:
            image = Image.open(image_path).convert("RGB")
            image = np.array(image)
            return image
        except Exception as e:
            current_app.logger.exception("Failed to process image %s: %s", image_path, e)
            return None

    def _process_page_result(self, page, ocr_threshold=0.3) -> str | None:
        if page is None:
            return None
        try:
            text = " ".join(
                word.value
                for block in page.blocks
                for line in block.lines
                for word in line.words
                if word.confidence > ocr_threshold 
            )
        except Exception as e:
            current_app.logger.exception("Failed to process page result: %s", e)
            text = ""

        if not text or (not any(char.isalpha() for char in text) or len(text) < 3) \
        or all(len(word) == 1 for word in text.split() if word.isalpha()):
            return None
            
        return text.strip()

    def extract_from_image_path(self, image_path: str) -> str | None:
        image_np = self._process_image_file(image_path)
        if image_np is None:
            return None
        
        model_result = self.model([image_np])
        if model_result is None or not model_result.pages:
            return None
        
        text_result = self._process_page_result(model_result.pages[0], ocr_threshold=0.3)
        current_app.logger.info("Successfully extracted OCR text from '%s'.", image_path)
        
        return text_result

    def extract_from_image_path_batch(self, image_paths: list[str], batch_size: int = 32) -> list[str | None]:
        total_images = len(image_paths)
        all_texts = []
        total_batches = (total_images + batch_size - 1) // batch_size 

        current_app.logger.info("Start batch processing %d images (batch_size: %d) in %d batches...", total_images, batch_size, total_batches)

        for i in range(0, total_images, batch_size):
            batch_paths = image_paths[i : i + batch_size]
            current_batch_num = (i // batch_size) + 1

            current_app.logger.info("  Batch %d/%d: Pre-processing {len(batch_paths)} images (I/O)...", current_batch_num, total_batches)

            with ThreadPoolExecutor() as executor:
                images_np = list(executor.map(self._process_image_file, batch_paths))
            
            valid_images = [img for img in images_np if img is not None]
            if not valid_images:
                all_texts.extend([None] * len(batch_paths))
                current_app.logger.warning("  Batch %d/%d: All images failed to load. Skipping.", current_batch_num, total_batches)
                continue

            current_app.logger.info("  Batch %d/%d: Running model on %d images...",current_batch_num, total_batches, len(valid_images))
            results = self.model(valid_images)
            current_app.logger.info("  Batch %d/%d: Model inference complete.", current_batch_num, total_batches)

            current_app.logger.info("  Batch %d/%d: Post-processing results (CPU)...", current_batch_num, total_batches)
            with ThreadPoolExecutor() as executor:
                texts = list(executor.map(lambda page: self._process_page_result(page, ocr_threshold=0.3), results.pages))
            
            text_iter = iter(texts)
            batch_results = []
            for img in images_np:
                if img is None:
                    batch_results.append(None)
                else:
                    batch_results.append(next(text_iter, None))
            
            all_texts.extend(batch_results)
            
        current_app.logger.info("Batch processing complete.")
        return all_texts


def _initialize_pipeline() -> None:
    global _PIPELINE
    _PIPELINE = OCRPipeline(
        det_arch=current_app.config.get("OCR_DET_ARCH", "db_mobilenet_v3_large"),
        reco_arch=current_app.config.get("OCR_RECO_ARCH", "crnn_mobilenet_v3_large"),
    )


def ocr_extract_from_image_path(image_path: str) -> str | None:
    global _PIPELINE
    if _PIPELINE is None:
        _initialize_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("OCR model is not loaded.")
        return None
    
    return _PIPELINE.extract_from_image_path(image_path)


def ocr_extract_from_image_path_batch(image_paths: list[str], batch_size: int = 32) -> list[str | None]:
    global _PIPELINE
        
    total_images = len(image_paths)
    
    if _PIPELINE is None:
        _initialize_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("OCR model is not loaded.")
        return [None] * total_images
    
    return _PIPELINE.extract_from_image_path_batch(image_paths, batch_size=batch_size)