import requests
import os
import json

SOLR_URL = os.getenv("SOLR_URL")

def solr_add(doc: dict):
    r = requests.post(
        f"{SOLR_URL}/update/json/docs",
        headers={"Content-Type": "application/json"},
        data=json.dumps(doc)
    )
    r.raise_for_status()
    rc = requests.get(f"{SOLR_URL}/update?commit=true")
    rc.raise_for_status()

def solr_search(query: str, rows: int = 20):
    params = {
        "q": query if query else "*:*",
        "fl": "id,filename_s,doctype_s,keywords_ss,content_txt,score",
        "rows": rows,
        "wt": "json"
    }
    r = requests.get(f"{SOLR_URL}/select", params=params)
    r.raise_for_status()
    data = r.json()
    docs = data.get("response", {}).get("docs", [])
    return docs

def solr_delete(doc_id: str):
    r = requests.post(
        f"{SOLR_URL}/update",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"delete": {"id": doc_id}})
    )
    r.raise_for_status()
    requests.get(f"{SOLR_URL}/update?commit=true")
