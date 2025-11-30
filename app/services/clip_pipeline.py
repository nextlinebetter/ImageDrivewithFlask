from __future__ import annotations
from PIL import Image
from flask import current_app
import numpy as np


_PIPELINE: CLIPPipeline | None = None


class CLIPPipeline:

    def __init__(self, model_name='clip-ViT-B-32'):
        # lazy import
        try:
            import torch
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            current_app.logger.exception("Failed to import dependencies for CLIPPipeline: %s", e)

        self.model_name = model_name
        try:
            self.device = "mps" if torch.backends.mps.is_available() else \
                        "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            self.device = "cpu"
        current_app.logger.info("Loading CLIP model '%s' (using device: %s)...", model_name, self.device)

        try:
            self.model = SentenceTransformer(model_name, device=self.device)
            current_app.logger.info("Successfully loaded CLIP model.")
        except Exception as e:
            current_app.logger.exception("Failed to load CLIP model '%s': %s", model_name, e)
            self.model = None

        try:
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
        except Exception:
            # Compatibility for older versions or other model interfaces
            self.embedding_dim = None

    def embed_image_path(self, image_path: str) -> np.ndarray | None:
        try:
            pil_image = Image.open(image_path).convert("RGB")
            embedding = self.model.encode(pil_image, convert_to_numpy=True)
            return embedding
        except Exception as e:
            current_app.logger.exception("Failed to embed image '%s': %s", image_path, e)
            return None

    def embed_text(self, text_query: str) -> np.ndarray | None:
        try:
            embedding = self.model.encode(text_query, convert_to_numpy=True)
            return embedding
        except Exception as e:
            current_app.logger.exception("Failed to embed text '%s': %s", text_query, e)
            return None

    def embed_image_path_batch(self, image_paths: list[str], batch_size: int = 32) -> np.ndarray | None:
        current_app.logger.info("Start batch embedding %d images (batch_size: %d)...", len(image_paths), batch_size)
        try:
            pil_images = [Image.open(path).convert("RGB") for path in image_paths]
            all_embeddings = self.model.encode(
                pil_images, 
                batch_size=batch_size, 
                convert_to_numpy=True,
                show_progress_bar=True
            )
            return all_embeddings
        except Exception as e:
            current_app.logger.exception("Failed to batch embed images: %s", e)
            return None


def _initialze_pipeline() -> CLIPPipeline:
    return CLIPPipeline(
        model_name=current_app.config.get("CLIP_MODEL_NAME", "clip-ViT-B-32")
    )


def embed_image_path(path: str) -> np.ndarray | None:
    """Embed a single image file and return a np.ndarray. Returns None on failure.
    The caller is responsible for normalization and persistence.
    """
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = _initialze_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("CLIP model is not loaded.")
        return None

    return _PIPELINE.embed_image_path(path)


def embed_text(text: str) -> np.ndarray | None:
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = _initialze_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("CLIP model is not loaded.")
        return None

    return _PIPELINE.embed_text(text)


def embed_image_path_batch(image_paths: list[str], batch_size: int = 32) -> np.ndarray | None:
    """Embed a batch of image files and return a 2D np.ndarray. Returns None on failure.
    The caller is responsible for normalization and persistence.
    """
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = _initialze_pipeline()
    if _PIPELINE.model is None:
        current_app.logger.error("CLIP model is not loaded.")
        return None

    return _PIPELINE.embed_image_path_batch(image_paths, batch_size=batch_size)


def get_model_name() -> str | None:
    global _PIPELINE
    if _PIPELINE is None:
        return None
    return _PIPELINE.model_name


def get_embedding_dim() -> int | None:
    global _PIPELINE
    if _PIPELINE is None:
        return None
    return _PIPELINE.embedding_dim
