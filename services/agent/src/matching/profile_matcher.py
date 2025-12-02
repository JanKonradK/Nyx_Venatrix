"""
Profile Matching Service
Embedding-based job description vs profile matching using OpenAI embeddings
"""

import os
import logging
from typing import Optional, List
import numpy as np
from openai import OpenAI

logger = logging.getLogger(__name__)


class ProfileMatcher:
    """
    Computes match scores between job descriptions and user profiles
    using OpenAI text-embedding-3-small
    """

    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.embedding_model = embedding_model
        self.profile_embedding: Optional[np.ndarray] = None
        self.profile_text: Optional[str] = None

        logger.info(f"ProfileMatcher initialized with model: {embedding_model}")

    def load_profile(self, profile_text: str):
        """
        Load and embed the user profile once at startup.
        This is cached in memory for the lifetime of the service.

        Args:
            profile_text: Full CV/profile text combining skills, experience, education
        """
        self.profile_text = profile_text
        self.profile_embedding = self._embed_text(profile_text)
        logger.info(f"Profile embedded ({len(profile_text)} chars, {self.profile_embedding.shape[0]} dimensions)")

    def compute_match_score(self, job_description: str) -> float:
        """
        Compute match score between job description and cached profile.

        Args:
            job_description: Cleaned job description text

        Returns:
            Match score between 0.0 and 1.0 (cosine similarity)
        """
        if self.profile_embedding is None:
            raise RuntimeError("Profile not loaded. Call load_profile() first.")

        # Embed job description
        jd_embedding = self._embed_text(job_description)

        # Compute cosine similarity
        match_score = self._cosine_similarity(self.profile_embedding, jd_embedding)

        logger.info(f"Match score computed: {match_score:.3f}")
        return float(match_score)

    def _embed_text(self, text: str) -> np.ndarray:
        """
        Embed text using OpenAI API.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )

            embedding = np.array(response.data[0].embedding)
            return embedding

        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            raise

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0 to 1, where 1 is identical)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Normalize to 0-1 range (cosine can be -1 to 1)
        normalized = (similarity + 1) / 2

        return float(normalized)

    def embed_and_store(self, text: str, store_id: str) -> np.ndarray:
        """
        Embed text and return vector for storage in Qdrant.

        Args:
            text: Text to embed
            store_id: Identifier for storage

        Returns:
            Embedding vector
        """
        embedding = self._embed_text(text)
        logger.info(f"Embedded text for storage: {store_id}")
        return embedding


def load_profile_from_resume(resume_version_text: str, profile_summary: Optional[str] = None) -> str:
    """
    Combine resume and profile data into a single text for embedding.

    Args:
        resume_version_text: Full text from resume
        profile_summary: Optional profile summary

    Returns:
        Combined profile text
    """
    parts = []

    if profile_summary:
        parts.append("PROFILE SUMMARY:")
        parts.append(profile_summary)
        parts.append("")

    parts.append("RESUME:")
    parts.append(resume_version_text)

    return "\n".join(parts)
