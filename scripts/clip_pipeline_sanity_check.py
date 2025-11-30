from __future__ import annotations
import os

from app import create_app
from app.services.clip_pipeline import embed_image_path, embed_text, embed_image_path_batch, get_embedding_dim, get_model_name


def main():
    app = create_app()
    with app.app_context():
        print("embedding model(before)):", get_model_name())
        print("embedding dim(before):", get_embedding_dim())

        try:
            tv = embed_text("hello world")
            print("embed text length:", None if tv is None else len(tv))
        except Exception as e:
            print("embed text exception:", e)

        try:
            iv = embed_image_path(os.path.join("data/samples", "test_clip.jpg"))
            print("embed image length:", None if iv is None else len(iv))
        except Exception as e:
            print("embed image exception:", e)

        print("embedding model(after):", get_model_name())
        print("embedding dim(after):", get_embedding_dim())


if __name__ == "__main__":
    main()
