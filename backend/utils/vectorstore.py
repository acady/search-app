import os
import faiss
import numpy as np
import pickle
from typing import List

VECTORSTORE_PATH = os.getenv("VECTORSTORE_PATH", "/app/vectorstore/faiss.index")
META_PATH = VECTORSTORE_PATH + ".meta.pkl"

_index = None
_metadata = []

def _ensure_loaded(dim: int = 1536):
    global _index, _metadata
    if _index is not None:
        return
    os.makedirs(os.path.dirname(VECTORSTORE_PATH), exist_ok=True)
    if os.path.exists(VECTORSTORE_PATH) and os.path.exists(META_PATH):
        _index = faiss.read_index(VECTORSTORE_PATH)
        with open(META_PATH, "rb") as f:
            _metadata = pickle.load(f)
    else:
        _index = faiss.IndexFlatIP(dim)
        _metadata = []

def _save():
    global _index, _metadata
    faiss.write_index(_index, VECTORSTORE_PATH)
    with open(META_PATH, "wb") as f:
        pickle.dump(_metadata, f)

def add_document(doc_id: str, filename: str, text_snippet: str, embedding: List[float]):
    global _index, _metadata
    _ensure_loaded(dim=len(embedding))
    vec = np.array([embedding], dtype="float32")
    faiss.normalize_L2(vec)
    _index.add(vec)
    _metadata.append({
        "doc_id": doc_id,
        "filename": filename,
        "snippet": text_snippet[:500]
    })
    _save()

def search_similar(query_embedding: List[float], top_k: int = 5):
    global _index, _metadata
    _ensure_loaded(dim=len(query_embedding))
    if _index.ntotal == 0:
        return []
    q = np.array([query_embedding], dtype="float32")
    faiss.normalize_L2(q)
    scores, idxs = _index.search(q, top_k)
    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1 or idx >= len(_metadata):
            continue
        meta = _metadata[idx]
        results.append({
            "score": float(score),
            "doc_id": meta["doc_id"],
            "filename": meta["filename"],
            "snippet": meta["snippet"],
        })
    return results

def delete_document_vector(doc_id: str):
    global _index, _metadata
    _ensure_loaded()
    new_meta = [m for m in _metadata if m["doc_id"] != doc_id]
    if len(new_meta) == len(_metadata):
        return
    _metadata = new_meta
    dim = _index.d
    new_index = faiss.IndexFlatIP(dim)
    _index = new_index
    _save()
