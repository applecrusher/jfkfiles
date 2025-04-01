import os
import json
from collections import defaultdict

# Configuration
INPUT_DIR = (Path.cwd().parent / 'corpus' / 'jfk_documents_json').resolve()
COMBINED_DIR = (Path.cwd().parent / 'corpus' / 'combined_documents').resolve()
os.makedirs(COMBINED_DIR, exist_ok=True)

def combine_documents():
    """Combine page JSONs into complete document JSONs"""
    # Create document grouping structure
    documents = defaultdict(list)
    
    # First pass: Group files and validate
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith('.json'):
            continue
        
        # Split filename into components
        try:
            base_name = os.path.splitext(filename)[0]
            doc_id, page_part = base_name.split('_page_')
            page_num = int(page_part)
        except (ValueError, IndexError):
            continue
        
        documents[doc_id].append({
            'page_num': page_num,
            'filename': filename
        })
    
    # Process each document
    for doc_id, pages in documents.items():
        # Sort pages numerically
        sorted_pages = sorted(pages, key=lambda x: x['page_num'])
        
        # Create document structure
        document = {
            "document_id": doc_id,
            "total_pages": len(sorted_pages),
            "pages": [],
            "metadata": {
                "source_files": [p['filename'] for p in sorted_pages]
            }
        }
        
        # Second pass: Load page data
        for page in sorted_pages:
            file_path = os.path.join(INPUT_DIR, page['filename'])
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    page_data = json.load(f)
                
                # Create enhanced page entry
                document['pages'].append({
                    "page_number": page['page_num'],
                    "text": page_data['text'],
                    "dimensions": page_data['metadata']['dimensions'],
                    "confidence": page_data['metadata']['confidence'],
                    "ocr_engine": page_data['metadata']['ocr_engine']
                })
            except Exception as e:
                print(f"Error loading {page['filename']}: {str(e)}")
                continue
        
        # Save combined document
        output_path = os.path.join(COMBINED_DIR, f"{doc_id}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(document, f, ensure_ascii=False, indent=2)
        
        print(f"Created combined document: {doc_id} ({len(sorted_pages)} pages)")

if __name__ == "__main__":
    combine_documents()