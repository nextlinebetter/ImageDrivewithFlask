"""OCR service delegating to teammate's pipeline in `others/imagedrive--OCR-main/ocr_pipeline.py`.

We load the module from file location (folder name contains dashes, not importable as package)
and call `extract_text_from_image_path` directly to keep behavior consistent.
Falls back to None on any error.
"""
from __future__ import annotations
from time import perf_counter
from PIL import Image, ImageOps
from flask import current_app
import numpy as np


_PIPELINE: OCRPipeline | None = None


class OCRPipeline:

    def __init__(self, model_name="PP-OCRv4"):
        # lazy import
        try:
            import torch
            import paddle
            from paddleocr import PaddleOCR
        except ImportError as e:
            current_app.logger.exception("Failed to import dependencies for OCRPipeline: %s", e)

        self.model_name = model_name
        try:
            self.device = "cuda" if paddle.is_compiled_with_cuda() else \
                        "mps" if paddle.is_compiled_with_mps() else "cpu"
        except Exception:
            self.device = "cpu"
        current_app.logger.info("Loading OCR model: '%s' (using device: %s)...", model_name, self.device) 

        try:
            self.model = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                ocr_version=model_name
            )
            current_app.logger.info("Successfully loaded OCR model.")
        except Exception as e:
            current_app.logger.exception("Failed to load OCR model '%s': %s", model_name, e)
            try:
                self.model = PaddleOCR(
                    use_angle_cls=True,
                    lang='ch',
                )
                current_app.logger.info("Successfully loaded OCR model with no specific version.")
            except Exception as e:
                current_app.logger.exception("Failed to load OCR model again: %s", e)
                self.model = None

    def process_image_batch(self, paths: list[str], batch_size: int = 32) -> list[str | None]:
        all_texts = []
        total = len(paths)

        current_app.logger.info(f"Processing {total} images using PaddleOCR Mobile...")

        for idx, path in enumerate(paths):
            try:
                img = Image.open(path).convert('RGB')
                img = ImageOps.exif_transpose(img)
                img_np = np.array(img)
  
                result = self.model.predict(img_np)

                if result is None or len(result) == 0 or result[0] is None:
                    all_texts.append(None)
                    continue

                full_text = ""
                first_item = result[0]

                if isinstance(first_item, dict) and 'rec_texts' in first_item:
                    text_list = first_item['rec_texts']
                    valid_texts = [str(t) for t in text_list if t]
                    full_text = " ".join(valid_texts)

                elif isinstance(first_item, list):
                    lines = []
                    for item in first_item:
                        if isinstance(item, (list, tuple)) and len(item) >= 2:
                            content = item[1]
                            if isinstance(content, (list, tuple)) and len(content) >= 1:
                                lines.append(str(content[0]))
                            elif isinstance(content, str):
                                lines.append(content)
                    full_text = " ".join(lines)

                all_texts.append(full_text.strip())

            except Exception as e:
                current_app.logger.warning(f"Error processing {path}: {e}")
                all_texts.append(None)

            if (idx + 1) % 10 == 0:
                current_app.logger.info(f"  > Processed {idx + 1}/{total}...")

        return all_texts

    def process_image(self, path: str) -> str | None:
        res = self.process_image_batch([path], batch_size=1)
        return res[0] if res else None


def _initialize_pipeline() -> OCRPipeline:
    return OCRPipeline(
        model_name=current_app.config.get("OCR_PADDLE_MODEL_NAME", "PP-OCRv4"),
    )


def ocr_extract_from_image_path(image_path: str) -> str | None:
    global _PIPELINE
    if _PIPELINE is None:
       _PIPELINE = _initialize_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("OCR model is not loaded.")
        return None

    return _PIPELINE.process_image(image_path)


def ocr_extract_from_image_path_batch(image_paths: list[str], batch_size: int = 32) -> list[str | None]:
    global _PIPELINE

    total_images = len(image_paths)

    if _PIPELINE is None:
        _PIPELINE = _initialize_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("OCR model is not loaded.")
        return [None] * total_images

    return _PIPELINE.process_image_batch(image_paths, batch_size=batch_size)


def get_arch_name() -> str | None:
    global _PIPELINE
    if _PIPELINE is None:
        return None
    return f"{_PIPELINE.model_name}"
