import chromadb
from chromadb.utils import embedding_functions

CHROMA_PATH = "./chroma_db"
CHROMA_COLLECTION = "landlord_guide"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
N_RESULTS = 5

_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=EMBEDDING_MODEL
)
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_collection = _client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


def get_collection():
    """Return the ChromaDB collection. Used during ingestion."""
    return _collection


def embed_and_store(chunks):
    """
    Embed and store chunks from ingest.py in the vector database.

    Expects chunks with keys: text, source, chunk_id.
    chunk_id is an int per document, so IDs are namespaced as
    "<source>_<chunk_id>" to avoid collisions across files.
    """
    _collection.add(
        documents=[c["text"] for c in chunks],
        metadatas=[{"source": c["source"]} for c in chunks],
        ids=[f"{c['source']}_{c['chunk_id']}" for c in chunks],
    )
    print(f"Stored {_collection.count()} total chunks in the vector database.")


def retrieve(query, n_results=N_RESULTS):
    """
    Find the most relevant chunks for a user's question.

    Returns a list of dicts with:
      - "text"     : chunk text
      - "source"   : source filename
      - "distance" : cosine distance (lower = more similar)
    """
    if _collection.count() == 0:
        return []

    results = _collection.query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    return [
        {
            "text": results["documents"][0][i],
            "source": results["metadatas"][0][i]["source"],
            "distance": results["distances"][0][i],
        }
        for i in range(len(results["documents"][0]))
    ]
