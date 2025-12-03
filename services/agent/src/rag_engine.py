from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue
import os
import uuid

class KnowledgeBase:
    def __init__(self):
        # Use OpenAI embeddings (text-embedding-3-small)
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.client = QdrantClient(url=os.getenv("QDRANT_URI", "http://localhost:6333"))
        self.collection_name = "profile_data"

        # Ensure collection exists (OpenAI text-embedding-3-small has 1536 dimensions)
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

    def embed_text(self, text: str):
        # Returns list of floats (vector)
        response = self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding

    def search_relevant_info(self, query: str, limit: int = 5):
        vector = self.embed_text(query)
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit * 2  # Fetch more to filter/sort
        )

        # Prioritization Logic: CVs > Professional_Info > Academic_Info > Personal_Info > Other_Info
        priority_map = {
            "CVs": 5,
            "Professional_Info": 4,
            "Academic_Info": 3,
            "Personal_Info": 2,
            "Other_Info": 1
        }

        processed_results = []
        for hit in results:
            category = hit.payload.get('category', 'Other_Info')
            score = hit.score
            # Boost score based on category priority (simple additive boost for sorting)
            priority_boost = priority_map.get(category, 0) * 0.05
            final_score = score + priority_boost

            processed_results.append({
                "text": hit.payload['text'],
                "source": hit.payload['filename'],
                "category": category,
                "score": final_score
            })

        # Sort by boosted score
        processed_results.sort(key=lambda x: x['score'], reverse=True)

        # Return top N
        return [res['text'] for res in processed_results[:limit]]

    def ingest_profile_data(self, profile_path="/app/profile_data"):
        points = []
        categories = ["CVs", "Personal_Info", "Academic_Info", "Professional_Info", "Other_Info"]

        for category in categories:
            cat_path = os.path.join(profile_path, category)
            if not os.path.exists(cat_path):
                continue

            for root, _, files in os.walk(cat_path):
                for file in files:
                    if file.endswith(".md") or file.endswith(".txt"):
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Chunking logic could go here
                            points.append(PointStruct(
                                id=str(uuid.uuid4()),
                                vector=self.embed_text(content),
                                payload={
                                    "text": content,
                                    "filename": file,
                                    "category": category
                                }
                            ))

        if points:
            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Ingested {len(points)} documents from Profile Data.")
