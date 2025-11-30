from __future__ import annotations
import os

from app import create_app
from app.services.ocr_pipeline_paddle import ocr_extract_from_image_path, ocr_extract_from_image_path_batch, get_arch_name

def main():
    app = create_app()
    with app.app_context():
        print("ocr arch(before)):", get_arch_name())

        try:
            text = ocr_extract_from_image_path(os.path.join("data/samples", "test_ocr_zh.jpg"))
            print("ocr result", text)
        except Exception as e:
            print("ocr exception:", e)

        print("ocr arch(after)):", get_arch_name())


if __name__ == "__main__":
    main()
