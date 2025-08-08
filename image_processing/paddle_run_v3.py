import os
import json
import re
from pathlib import Path
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import concurrent.futures

# Use single-threading for reliability.
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

input_dir = Path.cwd().parent / 'corpus' / 'mlk_documents_imgs'
output_dir = Path.cwd().parent / 'corpus' / 'mlk_documents_json_paddle'
output_dir.mkdir(parents=True, exist_ok=True)

def process_image(img_path_str, output_dir_str):
    try:
        img_path = Path(img_path_str)
        output_dir = Path(output_dir_str)
        m = re.search(r'_page_(\d+)', img_path.name)
        page = int(m.group(1)) if m else 1

        ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False)
        res = ocr.ocr(str(img_path), cls=True)
        if not res or not isinstance(res[0], list):
            return f"SKIP {img_path.name}"

        lines = res[0]
        texts = [line[1][0] for line in lines]
        scores = [line[1][1] for line in lines]
        boxes = [line[0] for line in lines]
        num = len(texts)
        avg = sum(scores) / num if num else 0

        img = Image.open(img_path).convert('RGB')
        w, h = img.size

        data = {
            "metadata": {
                "page_number": page,
                "confidence": round(avg, 4),
                "dimensions": [w, h],
                "ocr_engine": "PaddleOCR",
                "text_blocks": num
            },
            "filename": img_path.name,
            "text": "\n".join(texts).strip()
        }

        json_out = output_dir / f"{img_path.stem}.json"
        with open(json_out, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        drawn = draw_ocr(img, boxes, texts, scores)
        out_img = Image.fromarray(drawn)
        out_img.save(output_dir / f"result_{img_path.name}")
        img.close()
        out_img.close()
        return f"OK {img_path.name}"
    except Exception as e:
        return f"ERROR {img_path_str}: {e}"



if __name__ == '__main__':
    os.environ['OMP_NUM_THREADS'] = '1'
    os.environ['MKL_NUM_THREADS'] = '1'
    input_dir = Path.cwd().parent / 'corpus' / 'mlk_documents_imgs'
    output_dir = Path.cwd().parent / 'corpus' / 'mlk_documents_json_paddle'
    output_dir.mkdir(parents=True, exist_ok=True)
    img_files = [str(f) for f in input_dir.glob('*.png')]

    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_image, img_path, str(output_dir)): img_path for img_path in img_files}
        for fut in concurrent.futures.as_completed(futures):
            print(fut.result())
