import json
import re
import spacy
from pathlib import Path
from datetime import datetime

SOURCE_DIR = (Path.cwd().parent / 'corpus' / 'jfk_combined_documents_json').resolve()
TARGET_DIR = (Path.cwd().parent / 'corpus' / 'jfk_combined_documents_json_nlp').resolve()
TARGET_DIR.mkdir(parents=True, exist_ok=True)

nlp = spacy.load("en_core_web_sm")

# Existing functions (ocr_corrections, clean_text, etc.)

ocr_corrections = {
    r"Osw[1i]ald": "Oswald",
    r"Harve[v|y]": "Harvey",
    r"Fidel Casto": "Fidel Castro",
    r"J\.F\.K\.?": "John F. Kennedy",
    r"K\.G\.B\.?": "KGB",
    r"C\.I\.A\.?": "CIA",
    r"F\.B\.I\.?": "FBI",
    r"U\.S\.S\.R\.?": "USSR",
    r"Mexic0": "Mexico",
    r"Dall as": "Dallas",
    r"Kenned[v|y]": "Kennedy"
}

def correct_ocr_errors(text: str) -> str:
    for pattern, replacement in ocr_corrections.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text

def extract_entities(text):
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
    return entities

def clean_text(text: str) -> str:
    text = text.replace('\n', ' ')
    text = ' '.join(text.split())
    text = correct_ocr_errors(text)
    return text

def process_document(doc_path: Path):
    try:
        with open(doc_path, "r", encoding="utf-8") as f:
            doc = json.load(f)

        total_pages = doc.get("total_pages", len(doc.get("pages", [])))
        modified_pages = []

        for idx, page in enumerate(doc.get("pages", [])):
            original_text = page.get("text", "")
            cleaned_text = clean_text(original_text)

            # Extract entities from cleaned text
            entities = extract_entities(cleaned_text)

            if idx == 0:
                prefix = "[START_DOC]\n"
            else:
                prefix = ""

            suffix = "[END_DOC]" if idx == total_pages - 1 else "[PAGE_BREAK]"

            annotated_text = f"{prefix}{cleaned_text}\n{suffix}"

            page["original_text"] = original_text
            page["text"] = annotated_text
            page["entities"] = entities  # Add extracted entities here
            modified_pages.append(page)

        doc["pages"] = modified_pages

        output_path = TARGET_DIR / doc_path.name
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(doc, out_f, ensure_ascii=False, indent=2)

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Skipping {doc_path.name}: {e}")

def preprocess_all_documents():
    for json_file in SOURCE_DIR.glob("*.json"):
        if json_file.name.startswith('.'):
            continue
        process_document(json_file)

if __name__ == "__main__":
    preprocess_all_documents()
    autocomplete = 