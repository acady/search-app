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

# mehrere Verzeichnisse möglich: "dir1;dir2"
ARCHIVE_DIRS = os.getenv("ARCHIVE_DIRS", "/app/archive").split(";")
STATE_FILE = "/app/.index_state.json"


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
    if ext in ["jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff"]:
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
    """
    Durchläuft alle ARCHIVE_DIRS, indexiert neue/geänderte Dateien
    und entfernt gelöschte. Fehler bei einzelnen Dateien werden geloggt,
    aber brechen den Lauf NICHT mehr ab.
    """
    old_state = load_state()
    new_state = {}
    errors = []

    print("Scanning archive dirs:")
    for base in ARCHIVE_DIRS:
        base = base.strip()
        if not base:
            continue
        print(f"  - {base}")
        if not os.path.exists(base):
            print(f"    (übersprungen, existiert nicht)")
            continue

        for root, dirs, files in os.walk(base):
            for filename in files:
                if filename.startswith("."):
                    continue
                path = os.path.join(root, filename)
                try:
                    h = file_hash(path)
                except Exception as e:
                    msg = f"Hash error for {path}: {e}"
                    print(msg)
                    errors.append(msg)
                    continue

                new_state[path] = h
                doc_id = hashlib.md5(path.encode()).hexdigest()

                # unverändert -> überspringen
                if path in old_state and old_state[path] == h:
                    continue

                print(f"Indexing: {path}")
                try:
                    text = extract_text_auto(path)
                    kws = extract_keywords(text)

                    solr_doc = {
                        "id": doc_id,
                        "filename_s": filename,
                        "doctype_s": filename.split(".")[-1].lower(),
                        "keywords_ss": kws,
                        "content_txt": text,
                        "path_s": path,
                    }

                    # Solr
                    try:
                        solr_add(solr_doc)
                    except Exception as e:
                        msg = f"Solr add error for {path}: {e}"
                        print(msg)
                        errors.append(msg)

                    # Neo4j
                    try:
                        update_graph(doc_id, filename, kws)
                    except Exception as e:
                        msg = f"Neo4j update error for {path}: {e}"
                        print(msg)
                        errors.append(msg)

                    # Embeddings / FAISS (optional, darf scheitern)
                    snippet = text[:1000] or filename
                    try:
                        emb = embed_text(snippet)
                        add_document(doc_id, filename, snippet, emb)
                    except Exception as e:
                        msg = f"Embedding/FAISS error for {path}: {e}"
                        print(msg)
                        errors.append(msg)

                except Exception as e:
                    msg = f"General index error for {path}: {e}"
                    print(msg)
                    errors.append(msg)

    # Gelöschte Dateien
    deleted_paths = [p for p in old_state if p not in new_state]
    for path in deleted_paths:
        doc_id = hashlib.md5(path.encode()).hexdigest()
        filename = os.path.basename(path)
        print(f"Removing: {path}")

        try:
            solr_delete(doc_id)
        except Exception as e:
            msg = f"Solr delete error for {path}: {e}"
            print(msg)
            errors.append(msg)

        try:
            delete_document_node(doc_id)
        except Exception as e:
            msg = f"Neo4j delete error for {path}: {e}"
            print(msg)
            errors.append(msg)

        try:
            delete_document_vector(doc_id)
        except Exception as e:
            msg = f"FAISS delete error for {path}: {e}"
            print(msg)
            errors.append(msg)

    save_state(new_state)
    print("Reindex done.")
    if errors:
        print("Reindex completed with errors:")
        for e in errors:
            print("  -", e)
    return errors
