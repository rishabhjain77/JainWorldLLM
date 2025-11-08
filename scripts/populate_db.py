# scripts/populate_db.py - FIXED

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_db import vector_db
from backend.config import settings, SCRAPED_DIR
from scripts.scraper import scrape_jainworld  # FIXED: Use correct function name

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Split text into overlapping chunks
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            
            if break_point > chunk_size * 0.5:  # If we found a good break point
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        chunks.append(chunk.strip())
        start = end - overlap
    
    return chunks


def populate_database():
    """Populate vector database with Jain content"""
    print("\n" + "="*60)
    print("POPULATING VECTOR DATABASE")
    print("="*60 + "\n")
    
    # Check if we have scraped content
    scraped_file = SCRAPED_DIR / "learning_modules.json"
    
    if not scraped_file.exists():
        print("📥 No scraped content found. Running scraper...")
        documents = scrape_jainworld()  # FIXED: Use correct function name
    else:
        print(f"📂 Loading content from {scraped_file}")
        with open(scraped_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
    
    print(f"📚 Processing {len(documents)} documents...\n")
    
    # Process each document
    all_chunks = []
    all_metadatas = []
    
    for doc in documents:
        content = doc['content']
        metadata = doc['metadata']
        
        # Chunk the content
        chunks = chunk_text(
            content,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap
        )
        
        print(f"📄 {metadata['title']}")
        print(f"   Chunks: {len(chunks)}")
        
        # Add chunks with metadata
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_index'] = i
            chunk_metadata['total_chunks'] = len(chunks)
            all_metadatas.append(chunk_metadata)
    
    print(f"\n📊 Total chunks to index: {len(all_chunks)}")
    
    # Add to vector database
    print("\n🔄 Adding to vector database...")
    doc_ids = vector_db.add_documents(all_chunks, all_metadatas)
    
    # Get stats
    stats = vector_db.get_stats()
    
    print("\n" + "="*60)
    print("✅ DATABASE POPULATED SUCCESSFULLY!")
    print("="*60)
    print(f"📊 Total documents in DB: {stats['total_documents']}")
    print(f"📦 Collection: {stats['collection_name']}")
    print("="*60 + "\n")
    
    return len(doc_ids)


def test_search():
    """Test searching the populated database"""
    print("\n" + "="*60)
    print("TESTING SEARCH FUNCTIONALITY")
    print("="*60 + "\n")
    
    test_queries = [
        "What is ahimsa?",
        "Tell me about Mahavira",
        "How can I practice Jainism in daily life?",
        "Explain karma theory"
    ]
    
    for query in test_queries:
        print(f"🔍 Query: '{query}'")
        results = vector_db.search(query, top_k=2)
        
        if results['documents']:
            print(f"   Found {len(results['documents'])} results:\n")
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][:2],
                results['metadatas'][:2],
                results['distances'][:2]
            )):
                score = 1 - distance  # Convert distance to similarity
                print(f"   Result {i+1} (relevance: {score:.3f}):")
                print(f"   Title: {metadata.get('title', 'N/A')}")
                print(f"   Category: {metadata.get('category', 'N/A')}")
                print(f"   Preview: {doc[:150]}...\n")
        else:
            print("   No results found\n")
        
        print("-" * 60 + "\n")
    
    print("="*60)
    print("✅ Search tests complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Clear existing database (optional - comment out to keep existing data)
    # vector_db.clear_collection()
    
    # Populate database
    num_docs = populate_database()
    
    # Test search
    if num_docs > 0:
        test_search()