import os
import hashlib
import json

from extractors.pdf_extractor import extract_text_from_pdf
from extractors.docx_extractor import extract_text_from_docx
from extractors.xlsx_extractor import extract_text_from_xlsx
from extractors.image_extractor import extract_info_from_image

from utils.text_utils import extract_keywords
from utils.solr_client import solr_add, solr_delete
from utils.graph_client import update_graph, delete_document_node
from utils.embeddings_client import embed_text
from utils.vectorstore import add_document, delete_document_vector

ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", "/app/archive")
STATE_FILE = os.path.join(ARCHIVE_DIR, ".index_state.json")

def file_hash(path):
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def extract_text_auto(filepath):
    ext = filepath.lower().split(".")[-1]
    with open(filepath, "rb") as f:
        content = f.read()
    if ext == "pdf":
        return extract_text_from_pdf(content)
    if ext == "docx":
        return extract_text_from_docx(content)
    if ext in ["xlsx", "xls"]:
        return extract_text_from_xlsx(content)
    if ext in ["jpg","jpeg","png","gif","bmp","tif","tiff"]:
        return extract_info_from_image(os.path.basename(filepath), filepath)
    try:
        return content.decode("utf-8", errors="ignore")
    except:
        return ""

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def reindex_folder():
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    old_state = load_state()
    new_state = {}

    print(f"Scanning {ARCHIVE_DIR} ...")

    for root, dirs, files in os.walk(ARCHIVE_DIR):
        for filename in files:
            if filename.startswith("."):
                continue
            path = os.path.join(root, filename)
            h = file_hash(path)
            new_state[path] = h
            doc_id = hashlib.md5(path.encode()).hexdigest()

            if path in old_state and old_state[path] == h:
                continue

            print(f"Indexing: {filename}")
            text = extract_text_auto(path)
            kws = extract_keywords(text)

            solr_doc = {
                "id": doc_id,
                "filename_s": filename,
                "doctype_s": filename.split(".")[-1].lower(),
                "keywords_ss": kws,
                "content_txt": text
            }
            solr_add(solr_doc)
            update_graph(doc_id, filename, kws)

            snippet = text[:1000] or filename
            try:
                emb = embed_text(snippet)
                add_document(doc_id, filename, snippet, emb)
            except Exception as e:
                print("Embedding error:", e)

    deleted_paths = [p for p in old_state if p not in new_state]
    for path in deleted_paths:
        doc_id = hashlib.md5(path.encode()).hexdigest()
        filename = os.path.basename(path)
        print(f"Removing: {filename}")
        try:
            solr_delete(doc_id)
        except Exception as e:
            print("Solr delete error:", e)
        try:
            delete_document_node(doc_id)
        except Exception as e:
            print("Neo4j delete error:", e)
        try:
            delete_document_vector(doc_id)
        except Exception as e:
            print("FAISS delete error:", e)

    save_state(new_state)
    print("Reindex done.")
