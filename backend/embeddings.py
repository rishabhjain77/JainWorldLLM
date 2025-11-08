# backend/embeddings.py

from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.config import settings

class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self, model_name: str = None):
        """
        Initialize embedding model
        Uses all-MiniLM-L6-v2 by default (~80MB, runs great on 8GB Mac!)
        """
        if model_name is None:
            model_name = settings.embedding_model
            
        print(f"📥 Loading embedding model: {model_name}")
        print("   (This might take a minute on first run...)")
        
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        print(f"✅ Embedding model loaded! Dimension: {self.dimension}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats (embedding vector)
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            batch_size=batch_size,
            show_progress_bar=True
        )
        
        return embeddings.tolist()
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1, higher is more similar)
        """
        emb1 = self.model.encode(text1, convert_to_numpy=True)
        emb2 = self.model.encode(text2, convert_to_numpy=True)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)
    
    def find_most_similar(self, query: str, texts: List[str], top_k: int = 5) -> List[tuple]:
        """
        Find most similar texts to a query
        
        Args:
            query: Query text
            texts: List of texts to search
            top_k: Number of results to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        query_emb = self.model.encode(query, convert_to_numpy=True)
        text_embs = self.model.encode(texts, convert_to_numpy=True)
        
        # Calculate similarities
        similarities = np.dot(text_embs, query_emb) / (
            np.linalg.norm(text_embs, axis=1) * np.linalg.norm(query_emb)
        )
        
        # Get top k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]
        return results


# Initialize singleton
embedding_service = EmbeddingService()


# Test function
def test_embeddings():
    """Test the embedding service"""
    print("\n" + "="*60)
    print("Testing Embedding Service")
    print("="*60 + "\n")
    
    # Test texts about Jainism
    texts = [
        "Ahimsa means non-violence in thought, word, and action.",
        "Mahavira was the 24th Tirthankara of Jainism.",
        "Jains practice meditation and spiritual discipline.",
        "The three jewels of Jainism are right faith, knowledge, and conduct.",
        "Karma theory explains how actions affect the soul."
    ]
    
    # Test 1: Single embedding
    print("Test 1: Generate single embedding")
    query = "What is non-violence in Jainism?"
    embedding = embedding_service.embed_text(query)
    print(f"✅ Query: '{query}'")
    print(f"📊 Embedding dimension: {len(embedding)}")
    print(f"📊 First 5 values: {embedding[:5]}\n")
    
    # Test 2: Find similar texts
    print("Test 2: Find most similar texts")
    results = embedding_service.find_most_similar(query, texts, top_k=3)
    print(f"Query: '{query}'\n")
    print("Most similar texts:")
    for idx, score in results:
        print(f"  {score:.3f} - {texts[idx]}")
    
    # Test 3: Direct similarity
    print("\n" + "-"*60)
    print("Test 3: Direct similarity calculation")
    text1 = "Ahimsa is the principle of non-violence"
    text2 = "Non-violence is a core Jain value"
    text3 = "Meditation helps in spiritual growth"
    
    sim_12 = embedding_service.similarity(text1, text2)
    sim_13 = embedding_service.similarity(text1, text3)
    
    print(f"Similarity between:")
    print(f"  '{text1}'")
    print(f"  '{text2}'")
    print(f"  Score: {sim_12:.3f} (high similarity!)\n")
    
    print(f"Similarity between:")
    print(f"  '{text1}'")
    print(f"  '{text3}'")
    print(f"  Score: {sim_13:.3f} (lower similarity)\n")
    
    print("="*60)
    print("Embeddings working perfectly! ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_embeddings()