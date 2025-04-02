import os
import json
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import platform
from pathlib import Path

# Only set path manually if needed (e.g., not in PATH)
if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
elif platform.system() == 'Darwin':  # macOS
    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'  # or /usr/local/bin
elif platform.system() == 'Linux':
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


# Directories
IMAGE_DIR = (Path.cwd().parent / 'corpus' / 'jfk_documents_imgs').resolve()
OUTPUT_DIR = (Path.cwd().parent / 'corpus' / 'jfk_documents_json').resolve()
os.makedirs(OUTPUT_DIR, exist_ok=True)

def enhance_image(image_path):
    """Advanced image preprocessing for Tesseract"""
    img = Image.open(image_path).convert('L')  # Convert to grayscale
    
    # Enhance image
    img = img.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(1.2)
    
    # Resize if needed
    width, height = img.size
    if max(width, height) > 2000:
        img = img.resize((width//2, height//2), Image.LANCZOS)
    
    return img

def process_image(image_path, page_number):
    """Process image with Tesseract OCR"""
    try:
        img = enhance_image(image_path)
        width, height = img.size
        
        # Use Tesseract with optimized parameters
        custom_config = '--oem 3 --psm 6'
        data = pytesseract.image_to_data(
            img,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )
        
        # Process results
        all_text = []
        confidences = []
        
        for i, text in enumerate(data['text']):
            if int(data['conf'][i]) > 60:  # Filter low-confidence detections
                clean_text = text.strip()
                if clean_text:
                    all_text.append(clean_text)
                    confidences.append(int(data['conf'][i])/100)
        
        avg_confidence = round(np.mean(confidences).item(), 4) if confidences else 0.0
        
        return {
            "filename": os.path.basename(image_path),
            "text": "\n".join(all_text),
            "metadata": {
                "page_number": page_number,
                "dimensions": [width, height],
                "confidence": avg_confidence,
                "ocr_engine": "Tesseract v5.3.1",
                "text_blocks": len(all_text)
            }
        }
    
    except Exception as e:
        print(f"Error processing {image_path}: {str(e)}")
        return None


def run_ocr():
    count =0
    image_files = sorted([
        f for f in os.listdir(IMAGE_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    for idx, filename in enumerate(image_files, start=1):
        image_path = os.path.join(IMAGE_DIR, filename)
        print(f"Processing {idx}/{len(image_files)}: {filename}")
        
        data = process_image(image_path, idx)
        if not data:
            continue

        output_filename = f"{os.path.splitext(filename)[0]}.json"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        

if __name__ == "__main__":
    
    run_ocr()




    