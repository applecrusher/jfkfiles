import os
import json
import re
from pathlib import Path
from paddleocr import PaddleOCR, draw_ocr
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize PaddleOCR (downloads models automatically on first run)
try:
    ocr = PaddleOCR(use_angle_cls=True, lang='en')  # 'en' for English
except Exception as e:
    logging.error(f"Failed to initialize PaddleOCR: {e}")
    exit(1)

# Specify the directory containing PNG files
input_directory = (Path.cwd().parent / 'corpus' / 'mlk_documents_imgs').resolve()
output_directory = (Path.cwd().parent / 'corpus' / 'mlk_documents_json_paddle').resolve()

# Create output directory if it doesn't exist
os.makedirs(output_directory, exist_ok=True)

# Get all PNG files in the directory
png_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.png')]

for i, png_file in enumerate(png_files, 1):
    logging.info(f"Processing file {i}/{len(png_files)}: {png_file}")
    # Full path to the input image
    img_path = os.path.join(input_directory, png_file)
    
    # Extract page number from filename (e Dolan, 124-10226-10305_page_0134.png -> 134)
    page_match = re.search(r'_page_(\d+)', png_file)
    page_number = int(page_match.group(1)) if page_match else 1  # Default to 1 if no match
    
    # Run OCR on the image
    try:
        result = ocr.ocr(img_path, cls=True)
    except Exception as e:
        logging.error(f"OCR failed for {png_file}: {e}")
        continue
    
    # Assuming single-page image, take the first (and only) result
    if not result or not result[0]:
        logging.warning(f"No OCR results for {png_file}")
        continue
    res = result[0]
    
    # Extract data
    rec_texts = [line[1][0] for line in res]
    rec_scores = [line[1][1] for line in res]
    rec_boxes = [line[0] for line in res]
    
    # Prepare text and metadata
    all_text = "\n".join(rec_texts)
    num_blocks = len(rec_texts)
    avg_confidence = sum(rec_scores) / num_blocks if num_blocks > 0 else 0
    
    # Get image dimensions
    try:
        image = Image.open(img_path).convert('RGB')
        width, height = image.size
    except Exception as e:
        logging.error(f"Failed to open image {png_file}: {e}")
        continue
    
    # Create JSON structure
    json_data = {
        "metadata": {
            "page_number": page_number,
            "confidence": round(avg_confidence, 4),
            "dimensions": [width, height],
            "ocr_engine": "PaddleOCR",
            "text_blocks": num_blocks
        },
        "filename": png_file,
        "text": all_text.strip()
    }
    
    # Save JSON output
    try:
        json_output_path = os.path.join(output_directory, f"{os.path.splitext(png_file)[0]}.json")
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        logging.info(f"JSON output saved as {json_output_path}")
    except Exception as e:
        logging.error(f"Failed to save JSON for {png_file}: {e}")
        continue
    
    # Visualize results
    try:
        output_image_path = os.path.join(output_directory, f'result_{png_file}')
        im_show = draw_ocr(image, rec_boxes, rec_texts, rec_scores, font_path=None)
        im_show.save(output_image_path)
        logging.info(f"Visualized output saved as {output_image_path}")
    except Exception as e:
        logging.error(f"Failed to save visualized output for {png_file}: {e}")