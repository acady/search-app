# search-app

## Voraussetzungen
- Docker & Docker Compose installiert
- Ports 8000, 8983, 7474, 7687 frei
- Einen OpenAI API Key (in docker-compose.yml bei OPENAI_API_KEY eintragen)

## Start (lokal)
```bash
docker-compose build
docker-compose up -d
```

Dann:
- Web-UI (Upload, Suche, Chat, Graph): http://localhost:8000
- Solr Admin: http://localhost:8983
- Neo4j Browser: http://localhost:7474 (neo4j / password)

## Solr Schema
Für den Core `files` folgende Felder anlegen (falls nicht vorhanden):

- id (string, uniqueKey)
- filename_s (string, stored, indexed)
- doctype_s (string, stored, indexed)
- keywords_ss (string, stored, indexed, multiValued)
- content_txt (text_general, stored, indexed)

Beispiel:
```bash
curl -X POST "http://localhost:8983/solr/files/schema" \
  -H "Content-type:application/json" \
  --data-binary '{
    "add-field": [
      {"name":"filename_s","type":"string","stored":true,"indexed":true},
      {"name":"doctype_s","type":"string","stored":true,"indexed":true},
      {"name":"keywords_ss","type":"string","stored":true,"indexed":true,"multiValued":true},
      {"name":"content_txt","type":"text_general","stored":true,"indexed":true}
    ]
  }'
```

## Archiv-Ordner
Lege deine Dateien in `./archive` ab. Dann:

```bash
curl -X POST http://localhost:8000/api/reindex
```

- Neue/geänderte Dateien werden indexiert.
- Gelöschte Dateien werden aus Solr, Neo4j und dem Vektorstore entfernt.

## Chat
Nutze im Web-UI den Chat-Bereich, um in natürlicher Sprache über deine Dokumente zu fragen.
Die Antworten basieren auf semantischer Suche mit Embeddings.
