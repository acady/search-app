import os
import uuid
from fastapi import FastAPI, UploadFile, File


from extractors.pdf_extractor import extract_text_from_pdf
from extractors.docx_extractor import extract_text_from_docx
from extractors.xlsx_extractor import extract_text_from_xlsx
from extractors.image_extractor import extract_info_from_image

from utils.text_utils import extract_keywords
from utils.solr_client import solr_add, solr_search
from utils.graph_client import update_graph, query_related_docs
from utils.embeddings_client import embed_text
from utils.vectorstore import add_document, search_similar
from index_folder import reindex_folder

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")

app = FastAPI()

def guess_doctype(filename: str) -> str:
    return filename.split(".")[-1].lower()


def extract_text_by_type(filename: str, content: bytes) -> str:
    ext = filename.split(".")[-1].lower()
    if ext == "pdf":
        return extract_text_from_pdf(content)
    if ext == "docx":
        return extract_text_from_docx(content)
    if ext in ["xlsx", "xls"]:
        return extract_text_from_xlsx(content)
    if ext in ["png", "jpg", "jpeg", "gif", "tif", "tiff", "bmp", "webp"]:
        return extract_info_from_image(filename, UPLOAD_DIR)
    try:
        return content.decode("utf-8", errors="ignore")
    except:
        return ""


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_bytes = await file.read()
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    doc_id = str(uuid.uuid4())
    stored_path = os.path.join(UPLOAD_DIR, doc_id + "_" + file.filename)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    text_content = extract_text_by_type(file.filename, file_bytes)
    kws = extract_keywords(text_content)

    solr_doc = {
        "id": doc_id,
        "filename_s": file.filename,
        "doctype_s": guess_doctype(file.filename),
        "keywords_ss": kws,
        "content_txt": text_content,
    }
    solr_add(solr_doc)
    update_graph(doc_id, file.filename, kws)

    snippet = text_content[:1000]
    try:
        emb = embed_text(snippet if snippet.strip() else file.filename)
        add_document(
            doc_id=doc_id,
            filename=file.filename,
            text_snippet=snippet if snippet else "(kein Text extrahiert)",
            embedding=emb,
        )
    except Exception as e:
        print("Embedding fehlgeschlagen:", e)

    return {
        "status": "ok",
        "id": doc_id,
        "filename": file.filename,
        "keywords": kws,
    }


@app.get("/api/search")
def api_search(q: str = ""):
    solr_q = f"content_txt:{q}" if q else "*:*"
    docs = solr_search(solr_q)
    results = []
    for d in docs:
        fulltext = d.get("content_txt", "")
        snippet = fulltext[:300] + ("..." if len(fulltext) > 300 else "")
        results.append(
            {
                "id": d.get("id"),
                "filename": d.get("filename_s"),
                "doctype": d.get("doctype_s"),
                "keywords": d.get("keywords_ss", []),
                "snippet": snippet,
                "score": d.get("score"),
            }
        )
    return {"results": results}


@app.get("/api/related")
def api_related(keyword: str):
    rel = query_related_docs(keyword)
    return {"keyword": keyword, "documents": rel}


@app.get("/api/chat")
def api_chat(q: str):
    query_emb = embed_text(q)
    vector_hits = search_similar(query_emb, top_k=5)

    if not vector_hits:
        answer = (
            "Ich habe leider keine passenden Dokumente gefunden. "
            "Vielleicht kannst du den Begriff etwas anders formulieren?"
        )
        return {"answer": answer, "results": []}

    answer_lines = [
        f"Ich habe {len(vector_hits)} relevante Dokumente zu deiner Frage gefunden."
    ]
    for hit in vector_hits:
        answer_lines.append(
            f"- {hit['filename']} (Relevanz {round(hit['score'], 2)})"
        )
    answer = "\n".join(answer_lines)

    return {"answer": answer, "results": vector_hits}


# WICHTIG: Reindex-Route, GET UND POST
@app.api_route("/api/reindex", methods=["GET", "POST"])
def api_reindex():
    """
    Reindiziert alle konfigurierten Archiv-Verzeichnisse.
    Liefert eine Liste von Fehlern (falls welche auftraten).
    """
    try:
        errors = reindex_folder()
        return {
            "status": "ok" if not errors else "partial",
            "message": "Reindexierung abgeschlossen",
            "errors": errors,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}



from fastapi.staticfiles import StaticFiles

# Frontend statisch servieren
app.mount("/", StaticFiles(directory="static", html=True), name="static")

