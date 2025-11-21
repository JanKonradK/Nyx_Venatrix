from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import os
import uuid

class KnowledgeBase:
    def __init__(self):
        # Skills: Hugging Face Transformers, PyTorch
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = QdrantClient(url=os.getenv("QDRANT_URI"))
        self.collection_name = "obsidian_vault"

        # Ensure collection exists
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )

    def embed_text(self, text: str):
        # Returns list of floats (vector)
        return self.model.encode(text).tolist()

    def search_relevant_info(self, query: str, limit: int = 3):
        vector = self.embed_text(query)
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit
        )
        return [hit.payload['text'] for hit in results]

    def ingest_vault(self, vault_path="/app/vault"):
        # Skills: Python File I/O, Data Processing
        points = []
        for root, _, files in os.walk(vault_path):
            for file in files:
                if file.endswith(".md"):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Chunking logic could go here (RecursiveCharacterTextSplitter)
                        points.append(PointStruct(
                            id=str(uuid.uuid4()),
                            vector=self.embed_text(content),
                            payload={"text": content, "filename": file}
                        ))

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Ingested {len(points)} documents from Obsidian.")
