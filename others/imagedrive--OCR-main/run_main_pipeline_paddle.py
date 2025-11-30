from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor
import ocr_pipeline
import glob
import os
import time
import json

# --- 设置 ---
DATASET_ROOT = "./dataset/imagenet_images"
EXTENSIONS = ["**/*.jpg", "**/*.jpeg", "**/*.png"]
OUTPUT_FILE = "ocr_metadata.json"
NUM_WORKERS = 8  # ⚡️ 你的 Mac 核心数，设为 4 或 8

def process_one_image(path):
    """单个图片的处理任务，必须放在顶层"""
    try:
        # 调用单图接口
        text = ocr_pipeline.process_image(path)
        return path, text
    except Exception:
        return path, ""

def main():
    # 1. 找图
    image_paths = []
    for ext in EXTENSIONS:
        image_paths.extend(glob.glob(os.path.join(DATASET_ROOT, ext), recursive=True))
    
    # 截取 3800 张（如果需要测试全部，去掉切片）
    # image_paths = image_paths[:3800] 
    
    print(f"🚀 开始多进程处理 {len(image_paths)} 张图片 (Workers: {NUM_WORKERS})...")
    start_time = time.time()
    
    results = {}
    
    # 2. 多进程并行 (CPU 满载模式)
    with ProcessPoolExecutor(max_workers=NUM_WORKERS) as executor:
        # 使用 tqdm 显示进度条
        futures = list(tqdm(executor.map(process_one_image, image_paths), total=len(image_paths)))
        
        for path, text in futures:
            key = os.path.relpath(path, start=".")
            results[key] = text

    duration = time.time() - start_time
    print(f"✅ 完成！耗时: {duration:.2f}秒 | 平均: {duration/len(image_paths):.2f}s/张")
    
    # 3. 保存
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()