"""
OCR Pipeline - Mobile Speed Version
1. Model: Forces 'PP-OCRv4' (Mobile version, ~10x faster on CPU).
2. Robustness: Includes all previous crash fixes.
"""
import logging
import time
import numpy as np
from typing import List, Optional, Union, Any
from PIL import Image, ImageOps

try:
    import paddle
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OCR_ENGINE = None
DEFAULT_DEVICE = "unknown"

if PADDLE_AVAILABLE:
    try:
        if paddle.is_compiled_with_cuda():
            DEFAULT_DEVICE = "cuda"
        elif paddle.is_compiled_with_mps():
            DEFAULT_DEVICE = "mps"
        else:
            DEFAULT_DEVICE = "cpu"
    except:
        DEFAULT_DEVICE = "cpu"

def _init_model(device=None):
    global OCR_ENGINE
    if OCR_ENGINE is not None:
        return OCR_ENGINE
    
    if not PADDLE_AVAILABLE:
        logging.error("PaddleOCR not installed.")
        return None

    logging.info(f"OCR Pipeline: Initializing PaddleOCR (Device: {DEFAULT_DEVICE})...")
    
    try:
        # ⚡️ 核心提速：指定 ocr_version='PP-OCRv4'
        # 这会下载 Mobile 版模型，体积极小，CPU 运行极快
        OCR_ENGINE = PaddleOCR(
            use_angle_cls=True, 
            lang='ch', 
            ocr_version='PP-OCRv4' 
        )
        logging.info("PaddleOCR initialized successfully (Mobile Version).")
    except Exception as e:
        # 如果指定版本失败，尝试回退到默认
        logging.warning(f"Failed to load PP-OCRv4, falling back: {e}")
        try:
            OCR_ENGINE = PaddleOCR(use_angle_cls=True, lang='ch')
        except Exception as e2:
            logging.error(f"Fatal init error: {e2}", exc_info=True)
            OCR_ENGINE = None
        
    return OCR_ENGINE

def process_image_batch(paths: List[str], batch_size: int = 32, device: str = None) -> List[str]:
    if not paths: return []
    engine = _init_model(device)
    if engine is None: return [""] * len(paths)

    all_texts = []
    total = len(paths)
    
    logging.info(f"Processing {total} images using PaddleOCR Mobile...")

    for idx, path in enumerate(paths):
        try:
            # 1. 读取
            img = Image.open(path).convert('RGB')
            img = ImageOps.exif_transpose(img)
            img_np = np.array(img)
            
            # 2. 运行 OCR (不传 cls=True)
            result = engine.ocr(img_np)

            # 3. 结果解析 (兼容 PaddleX 字典 和 列表)
            if result is None or len(result) == 0 or result[0] is None:
                all_texts.append("")
                continue
            
            full_text = ""
            first_item = result[0]

            # 情况 A: PaddleX 字典
            if isinstance(first_item, dict) and 'rec_texts' in first_item:
                text_list = first_item['rec_texts']
                valid_texts = [str(t) for t in text_list if t]
                full_text = " ".join(valid_texts)

            # 情况 B: 标准列表
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
            logging.warning(f"Error processing {path}: {e}")
            all_texts.append("")
            
        if (idx + 1) % 10 == 0:
            logging.info(f"  > Processed {idx + 1}/{total}...")
            
    return all_texts

def process_image(path: str, lang: str = 'ch', device: str = None) -> str:
    res = process_image_batch([path], batch_size=1, device=device)
    return res[0] if res else ""