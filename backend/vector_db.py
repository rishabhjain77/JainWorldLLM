# backend/vector_db.py

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.config import settings
from backend.embeddings import embedding_service

class VectorDB:
    """Vector database for storing and retrieving Jain knowledge"""
    
    def __init__(self):
        """Initialize ChromaDB"""
        print("🔧 Initializing Vector Database...")
        
        # Create ChromaDB client
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"description": "Jain knowledge base from Jainworld.com"}
        )
        
        print(f"✅ Vector DB ready! Collection: {settings.collection_name}")
        print(f"📊 Current documents: {self.collection.count()}")
    
    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector database
        
        Args:
            documents: List of text documents
            metadatas: Optional metadata for each document
            ids: Optional IDs (auto-generated if not provided)
            
        Returns:
            List of document IDs
        """
        if not documents:
            return []
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Generate embeddings
        print(f"📊 Generating embeddings for {len(documents)} documents...")
        embeddings = embedding_service.embed_batch(documents)
        
        # Add to collection
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Added {len(documents)} documents to vector DB")
        return ids
    
    def search(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            top_k: Number of results (uses config default if None)
            filter_metadata: Filter by metadata (e.g., {"category": "philosophy"})
            
        Returns:
            Dict with documents, metadatas, distances, ids
        """
        if top_k is None:
            top_k = settings.top_k_results
        
        # Generate query embedding
        query_embedding = embedding_service.embed_text(query)
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )
        
        return {
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
            "ids": results["ids"][0] if results["ids"] else []
        }
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get a specific document by ID"""
        try:
            result = self.collection.get(ids=[doc_id])
            if result["documents"]:
                return {
                    "document": result["documents"][0],
                    "metadata": result["metadatas"][0] if result["metadatas"] else {},
                    "id": doc_id
                }
        except:
            pass
        return None
    
    def delete_documents(self, ids: List[str]):
        """Delete documents by IDs"""
        self.collection.delete(ids=ids)
        print(f"🗑️  Deleted {len(ids)} documents")
    
    def clear_collection(self):
        """Clear all documents from collection"""
        self.client.delete_collection(settings.collection_name)
        self.collection = self.client.create_collection(
            name=settings.collection_name,
            metadata={"description": "Jain knowledge base from Jainworld.com"}
        )
        print("🗑️  Collection cleared")
    
    def get_stats(self) -> Dict:
        """Get collection statistics"""
        return {
            "total_documents": self.collection.count(),
            "collection_name": settings.collection_name
        }


# Initialize singleton
vector_db = VectorDB()


# Test function
def test_vector_db():
    """Test the vector database"""
    print("\n" + "="*60)
    print("Testing Vector Database")
    print("="*60 + "\n")
    
    # Sample Jain knowledge
    documents = [
        "Ahimsa (non-violence) is the fundamental principle of Jainism. It applies to thoughts, words, and actions.",
        "Mahavira was the 24th and last Tirthankara. He lived in the 6th century BCE and reformed Jain teachings.",
        "The three jewels of Jainism are Samyak Darshan (right faith), Samyak Gyan (right knowledge), and Samyak Charitra (right conduct).",
        "Anekantavada is the Jain doctrine of multiple perspectives. It teaches that truth has many aspects.",
        "Jains practice meditation and spiritual discipline to purify the soul and achieve liberation (moksha).",
        "The Jain calendar includes festivals like Paryushana, Mahavir Jayanti, and Diwali.",
        "Jain dietary practices are based on ahimsa. Jains are vegetarian and avoid root vegetables.",
        "There are 24 Tirthankaras in each time cycle. The first was Rishabhanatha and the last was Mahavira."
    ]
    
    metadatas = [
        {"category": "philosophy", "topic": "ahimsa", "difficulty": "beginner"},
        {"category": "history", "topic": "tirthankaras", "difficulty": "beginner"},
        {"category": "philosophy", "topic": "three_jewels", "difficulty": "intermediate"},
        {"category": "philosophy", "topic": "anekantavada", "difficulty": "intermediate"},
        {"category": "practices", "topic": "meditation", "difficulty": "beginner"},
        {"category": "practices", "topic": "festivals", "difficulty": "beginner"},
        {"category": "practices", "topic": "diet", "difficulty": "beginner"},
        {"category": "history", "topic": "tirthankaras", "difficulty": "beginner"}
    ]
    
    # Add documents
    print("Test 1: Adding documents to vector DB")
    doc_ids = vector_db.add_documents(documents, metadatas)
    print(f"✅ Added {len(doc_ids)} documents\n")
    
    # Search test
    print("Test 2: Searching for relevant documents")
    queries = [
        "What is non-violence in Jainism?",
        "Tell me about Jain festivals",
        "Who was the last Tirthankara?"
    ]
    
    for query in queries:
        print(f"\n🔍 Query: '{query}'")
        results = vector_db.search(query, top_k=2)
        
        print(f"Top {len(results['documents'])} results:")
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'],
            results['metadatas'],
            results['distances']
        )):
            print(f"\n  Result {i+1} (score: {1-distance:.3f}):")
            print(f"    {doc[:100]}...")
            print(f"    Category: {metadata.get('category', 'N/A')}")
    
    # Filter by metadata
    print("\n" + "-"*60)
    print("Test 3: Filtering by category")
    results = vector_db.search(
        "Jain teachings",
        top_k=3,
        filter_metadata={"category": "philosophy"}
    )
    print(f"Found {len(results['documents'])} philosophy documents")
    
    # Stats
    print("\n" + "-"*60)
    print("Test 4: Database statistics")
    stats = vector_db.get_stats()
    print(f"📊 Total documents: {stats['total_documents']}")
    print(f"📊 Collection: {stats['collection_name']}")
    
    print("\n" + "="*60)
    print("Vector DB working perfectly! ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_vector_db()