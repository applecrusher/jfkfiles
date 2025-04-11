import json
from pathlib import Path
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Updated paths
CORPUS_DIR = Path("../corpus/jfk_combined_documents_json")
INDEX_DIR = "../corpus/faiss_index"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64
EMBED_MODEL = "all-MiniLM-L6-v2"  # Swap to another if desired

def load_texts():
    docs = []
    for file_path in CORPUS_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                doc_id = data.get("document_id", "unknown")
                pages = data.get("pages", [])

                for page in pages:
                    text = page.get("text", "").strip()
                    if not text:
                        continue

                    metadata = {
                        "document_id": doc_id,
                        "page_number": page.get("page_number", -1),
                        "source": file_path.name,
                        "ocr_engine": page.get("ocr_engine", ""),
                        "confidence": page.get("confidence", 0),
                        "dimensions": page.get("dimensions", []),
                    }

                    docs.append(Document(page_content=text, metadata=metadata))
        except Exception as e:
            print(f"❌ Error loading {file_path.name}: {e}")
    return docs

def split_docs(docs):
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunked_docs = []
    for doc in docs:
        chunks = splitter.split_text(doc.page_content)
        for chunk in chunks:
            chunked_docs.append(Document(page_content=chunk, metadata=doc.metadata))
    return chunked_docs

def build_index():
    print("📖 Loading documents...")
    docs = load_texts()
    print(f"✅ Loaded {len(docs)} pages")

    print("✂️ Chunking text...")
    chunks = split_docs(docs)
    print(f"✅ Created {len(chunks)} chunks")

    print("🧠 Embedding and saving index...")
    embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    db = FAISS.from_documents(chunks, embedder)
    db.save_local(INDEX_DIR)
    print(f"✅ FAISS index saved to {INDEX_DIR}")

if __name__ == "__main__":
    build_index()
