import os
import json
import cv2
import numpy as np
from PIL import Image
# Removed PIL ImageEnhance and ImageFilter as we'll use OpenCV
import pytesseract
import platform
from pathlib import Path
import math
import logging

# --- Configuration ---

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Tesseract Path (keep your existing logic)
try:
    if platform.system() == 'Windows':
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    elif platform.system() == 'Darwin':
        # Common paths on macOS, adjust if necessary
        possible_paths = ['/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract']
        tess_path = next((path for path in possible_paths if Path(path).exists()), None)
        if not tess_path:
            raise FileNotFoundError("Tesseract executable not found in common paths.")
        pytesseract.pytesseract.tesseract_cmd = tess_path
    elif platform.system() == 'Linux':
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract' # Common path on Linux
    # Verify Tesseract version or command
    tess_version_info = pytesseract.get_tesseract_version()
    logging.info(f"Using Tesseract version: {tess_version_info}")
except Exception as e:
    logging.error(f"Error setting or finding Tesseract path: {e}")
    logging.warning("Ensure Tesseract is installed and the path is correct.")
    # Exit or handle error appropriately if Tesseract is essential
    exit(1)


# Directories
BASE_DIR = Path.cwd().parent # Assuming script is in a 'scripts' folder maybe? Adjust if needed.
# BASE_DIR = Path(__file__).resolve().parent.parent # Alternative if running script directly

CORPUS_DIR = (BASE_DIR / 'corpus').resolve()
IMAGE_DIR = (CORPUS_DIR / 'jfk_documents_imgs').resolve()
OUTPUT_DIR = (CORPUS_DIR / 'jfk_documents_json_v2').resolve()
#PREPROCESSED_DIR = (CORPUS_DIR / 'jfk_documents_preprocessed').resolve() # Optional: Save preprocessed images for inspection
os.makedirs(OUTPUT_DIR, exist_ok=True)
# os.makedirs(PREPROCESSED_DIR, exist_ok=True) # Uncomment to save preprocessed images

# --- Image Preprocessing Functions ---

def deskew(image_cv):
    """Deskews an image using cv2."""
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY) if len(image_cv.shape) == 3 else image_cv
    gray = cv2.bitwise_not(gray) # Invert colors for contour finding
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if coords.size == 0:
        logging.warning("Deskew: No contours found, skipping deskew.")
        return image_cv # Return original if no contours

    angle = cv2.minAreaRect(coords)[-1] # Angle is [-90, 0)

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Don't rotate if angle is negligible
    if abs(angle) < 0.1:
         logging.debug("Deskew: Angle negligible, skipping rotation.")
         return image_cv

    logging.debug(f"Deskew: Detected angle: {angle:.2f} degrees")

    (h, w) = image_cv.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Use white border color for scanned documents
    rotated = cv2.warpAffine(image_cv, M, (w, h),
                             flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT,
                             borderValue=(255, 255, 255)) # White border for grayscale/color
    return rotated

# (Keep imports and other functions the same as the previous optimized version)
import cv2
import numpy as np
import logging
from pathlib import Path # Ensure pathlib is imported if not already

# ... (Keep deskew function as defined before) ...

def preprocess_image_for_ocr(image_path, save_intermediate=False, filename="",
                             # --- Enhancement Parameters ---
                             apply_contrast_brightness=True,
                             contrast_alpha=1.5, # Contrast control (1.0-3.0)
                             brightness_beta=5,  # Brightness control (0-100)
                             apply_sharpening=True,
                             # --- Other Preprocessing Parameters ---
                             apply_deskew=False, # Deskewing is optional, enable if needed
                             apply_noise_reduction=False, # Noise reduction is optional
                             noise_kernel_size=3,
                             # --- Binarization Parameters ---
                             adaptive_thresh_block_size=31, # Must be odd
                             adaptive_thresh_C=10
                            ):
    """Advanced image preprocessing for Tesseract using OpenCV with enhancement."""
    try:
        # Read with OpenCV
        img_cv = cv2.imread(str(image_path))
        if img_cv is None:
            logging.error(f"Could not read image: {image_path}")
            return None

        # 1. Convert to Grayscale
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        processed = gray # Start with grayscale image

        # 2. Optional: Deskewing
        if apply_deskew:
            logging.debug("Applying Deskew...")
            processed = deskew(processed)

        # 3. Optional: Noise Removal (Median Blur) - Apply early before enhancements amplify noise
        if apply_noise_reduction:
            logging.debug(f"Applying Median Blur with kernel size {noise_kernel_size}...")
            # Kernel size must be odd
            k_size = noise_kernel_size if noise_kernel_size % 2 != 0 else noise_kernel_size + 1
            processed = cv2.medianBlur(processed, k_size)

        # 4. Optional: Contrast and Brightness Adjustment
        if apply_contrast_brightness:
            logging.debug(f"Applying Contrast (Alpha={contrast_alpha}) and Brightness (Beta={brightness_beta})...")
            # Apply contrast/brightness: output = alpha * input + beta
            # cv2.convertScaleAbs handles potential clipping (values < 0 or > 255)
            processed = cv2.convertScaleAbs(processed, alpha=contrast_alpha, beta=brightness_beta)

        # 5. Optional: Sharpening
        if apply_sharpening:
            logging.debug("Applying Sharpening...")
            # Simple sharpening kernel
            kernel_sharpening = np.array([[-1,-1,-1],
                                          [-1, 9,-1],
                                          [-1,-1,-1]])
            # Applying the kernel to the input image
            processed = cv2.filter2D(processed, -1, kernel_sharpening)

        # 6. Binarization (Adaptive Thresholding) - Applied to the enhanced grayscale image
        logging.debug(f"Applying Adaptive Threshold (BlockSize={adaptive_thresh_block_size}, C={adaptive_thresh_C})...")
        binary = cv2.adaptiveThreshold(processed, 255,
                                       cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY,
                                       blockSize=adaptive_thresh_block_size,
                                       C=adaptive_thresh_C)

        # 7. Optional: Further Morphological Operations (on binary image)
        # kernel = np.ones((1, 1), np.uint8)
        # binary = cv2.dilate(binary, kernel, iterations=1)
        # binary = cv2.erode(binary, kernel, iterations=1)

        # Optional: Save final preprocessed image for inspection
        if save_intermediate and filename:
             intermediate_path = PREPROCESSED_DIR / f"preprocessed_{filename}" # Make sure PREPROCESSED_DIR is defined
             cv2.imwrite(str(intermediate_path), binary)
             logging.debug(f"Saved final preprocessed image to {intermediate_path}")

        return binary # Return the final binary image for OCR

    except Exception as e:
        logging.error(f"Error during preprocessing {image_path}: {str(e)}")
        # You might want to log the traceback for detailed debugging
        # import traceback
        # logging.error(traceback.format_exc())
        return None

# --- Important ---
# Make sure to define PREPROCESSED_DIR if you set save_intermediate=True
# PREPROCESSED_DIR = (CORPUS_DIR / 'jfk_documents_preprocessed').resolve()
# os.makedirs(PREPROCESSED_DIR, exist_ok=True) # Uncomment to save preprocessed images

# --- How to Use in process_image_with_ocr ---
# Inside the `process_image_with_ocr` function, call `preprocess_image_for_ocr` like this:
#
# def process_image_with_ocr(image_path, page_number):
#    try:
#        img_filename = os.path.basename(image_path)
#
#        # --- Call the updated preprocessing function ---
#        # Adjust parameters here based on experimentation!
#        img_processed = preprocess_image_for_ocr(
#            image_path,
#            save_intermediate=False, # Set to True to debug
#            filename=img_filename,
#            apply_contrast_brightness=True, # Enable/disable enhancement
#            contrast_alpha=1.5,           # Tune contrast
#            brightness_beta=5,            # Tune brightness
#            apply_sharpening=True,        # Enable/disable sharpening
#            apply_deskew=False,            # Enable if scans are skewed
#            apply_noise_reduction=False,   # Enable for noisy scans
#            noise_kernel_size=3,
#            adaptive_thresh_block_size=31,# Tune binarization block size
#            adaptive_thresh_C=10           # Tune binarization constant C
#        )
#
#        if img_processed is None:
#            logging.warning(f"Skipping OCR for {img_filename} due to preprocessing error.")
#            return None
#
#        # ... (rest of the OCR logic remains the same) ...
#
#    except Exception as e:
#        # ... (error handling) ...

# ... (Keep run_ocr and the main execution block as before) ...

# --- OCR Processing Function ---

def process_image_with_ocr(image_path, page_number):
    """Preprocesses image and runs Tesseract OCR."""
    try:
        img_filename = os.path.basename(image_path)
        # Preprocess the image
        # Set save_intermediate=True to debug preprocessing steps
        img_processed = preprocess_image_for_ocr(image_path, save_intermediate=False, filename=img_filename)

        if img_processed is None:
            logging.warning(f"Skipping OCR for {img_filename} due to preprocessing error.")
            return None

        # Get image dimensions (from processed image)
        height, width = img_processed.shape[:2]

        # --- Tesseract Configuration ---
        # --psm 3: Fully automatic page segmentation (usually best default)
        # --psm 4: Assume a single column of text of variable sizes.
        # --psm 6: Assume a single uniform block of text. (Your original, can be good for simple docs)
        # --psm 11: Sparse text. Find as much text as possible in no particular order.
        # --psm 12: Sparse text with OSD.
        # Choose the PSM that best fits your document types. Start with 3.
        # Specify language ('eng' for English). Install language packs if needed (e.g., 'sudo apt-get install tesseract-ocr-eng')
        # OEM 3 is the default LSTM engine, usually the best.
        custom_config = r'-l eng --oem 3 --psm 3' # Changed PSM to 3

        # Use image_to_string to preserve layout better
        extracted_text = pytesseract.image_to_string(img_processed, config=custom_config)

        # Alternative: Use image_to_data for word confidences, but requires careful reconstruction
        # data = pytesseract.image_to_data(
        #     img_processed,
        #     config=custom_config,
        #     output_type=pytesseract.Output.DICT
        # )
        #
        # # Filter and reconstruct text (more complex, only if word-level data is essential)
        # lines = {}
        # confidences = []
        # for i in range(len(data['text'])):
        #     conf = int(data['conf'][i])
        #     if conf > 60: # Your confidence threshold
        #         text = data['text'][i].strip()
        #         if text:
        #             line_num = data['line_num'][i]
        #             block_num = data['block_num'][i]
        #             par_num = data['par_num'][i]
        #             word_num = data['word_num'][i]
        #             # Unique key for each line within its block/paragraph
        #             line_key = (block_num, par_num, line_num)
        #
        #             if line_key not in lines:
        #                 lines[line_key] = []
        #             # Store word and its position to sort later
        #             lines[line_key].append((word_num, text))
        #             confidences.append(conf / 100.0)
        #
        # # Sort words within lines and join lines
        # reconstructed_text_list = []
        # for line_key in sorted(lines.keys()):
        #     words = [word[1] for word in sorted(lines[line_key])]
        #     reconstructed_text_list.append(" ".join(words))
        #
        # extracted_text = "\n".join(reconstructed_text_list)
        # avg_confidence = round(np.mean(confidences).item(), 4) if confidences else 0.0

        # --- Calculate Confidence (Using image_to_string doesn't directly give easy average) ---
        # Get confidence data separately if needed, AFTER getting text with image_to_string
        # This avoids re-running OCR but gives word-level confidence for reporting
        conf_data = pytesseract.image_to_data(
            img_processed,
            config=custom_config, # Use same config
            output_type=pytesseract.Output.DICT
        )
        valid_confidences = [int(c)/100.0 for c in conf_data['conf'] if int(c) > 0] # Consider only > 0 confidence
        avg_confidence = round(np.mean(valid_confidences).item(), 4) if valid_confidences else 0.0
        median_confidence = round(np.median(valid_confidences).item(), 4) if valid_confidences else 0.0


        return {
            "filename": img_filename,
            "text": extracted_text.strip(), # Remove leading/trailing whitespace from the whole text
            "metadata": {
                "page_number": page_number,
                "dimensions": [width, height],
                "avg_confidence": avg_confidence, # Report average confidence of detected words
                "median_confidence": median_confidence, # Median can be more robust to outliers
                "ocr_engine": f"Tesseract {pytesseract.get_tesseract_version()}",
                "tesseract_config": custom_config,
                # "text_blocks": len(all_text) # This needs recalculation based on how text is structured
            }
        }

    except pytesseract.TesseractNotFoundError:
         logging.error("Tesseract executable not found. Please ensure it's installed and the path is correct.")
         # Stop the script or handle as needed
         raise
    except Exception as e:
        logging.error(f"Error processing {image_path}: {str(e)}")
        return None


# --- Main Execution Logic ---

def run_ocr():
    """Finds images, processes them, and saves results as JSON."""
    try:
        image_files = sorted([
            f for f in IMAGE_DIR.iterdir() # Use pathlib for iteration
            if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.tif', '.tiff']
        ])
    except FileNotFoundError:
        logging.error(f"Image directory not found: {IMAGE_DIR}")
        return

    if not image_files:
        logging.warning(f"No image files found in {IMAGE_DIR}")
        return

    total_files = len(image_files)
    logging.info(f"Found {total_files} images to process.")

    for idx, image_path in enumerate(image_files, start=1):
        logging.info(f"Processing {idx}/{total_files}: {image_path.name}")

        data = process_image_with_ocr(image_path, idx)
        if not data:
            logging.warning(f"Skipped saving JSON for {image_path.name} due to processing error.")
            continue

        output_filename = f"{image_path.stem}.json" # Use stem for filename without extension
        output_path = OUTPUT_DIR / output_filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"Successfully saved JSON to {output_path}")
        except IOError as e:
            logging.error(f"Could not write JSON file {output_path}: {e}")
        except Exception as e:
             logging.error(f"An unexpected error occurred while saving JSON for {image_path.name}: {e}")


if __name__ == "__main__":
    # Optional: Check if input directory exists before running
    if not IMAGE_DIR.exists():
        print(f"ERROR: Image directory not found: {IMAGE_DIR}")
    elif not OUTPUT_DIR.exists():
         print(f"ERROR: Output directory not found: {OUTPUT_DIR}") # Should be created, but good check
    else:
        run_ocr()
        print("\nOCR processing finished.")