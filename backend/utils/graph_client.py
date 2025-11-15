import os
from neo4j import GraphDatabase

NEO4J_URL = os.getenv("NEO4J_URL")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URL, auth=(NEO4J_USER, NEO4J_PASSWORD))

def add_document_node(tx, doc_id, filename, keywords):
    tx.run(
        '''
        MERGE (d:Document {id:$id})
        SET d.filename = $filename,
            d.keywords = $keywords
        ''',
        id=doc_id, filename=filename, keywords=keywords
    )

def add_keyword_nodes_and_rels(tx, doc_id, keywords):
    for kw in keywords:
        tx.run(
            '''
            MERGE (k:Keyword {name:$kw})
            MERGE (d:Document {id:$doc_id})
            MERGE (d)-[:HAS_KEYWORD]->(k)
            ''',
            kw=kw, doc_id=doc_id
        )

def update_graph(doc_id: str, filename: str, keywords: list[str]):
    with driver.session() as session:
        session.execute_write(add_document_node, doc_id, filename, keywords)
        session.execute_write(add_keyword_nodes_and_rels, doc_id, keywords)

def query_related_docs(keyword: str):
    with driver.session() as session:
        result = session.run(
            '''
            MATCH (k:Keyword {name:$kw})<-[:HAS_KEYWORD]-(d:Document)
            RETURN d.id as id, d.filename as filename, d.keywords as keywords
            ''',
            kw=keyword
        )
        return [r.data() for r in result]

def delete_document_node(doc_id: str):
    with driver.session() as session:
        session.run("MATCH (d:Document {id:$id}) DETACH DELETE d", id=doc_id)
