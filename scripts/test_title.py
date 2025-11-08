# scripts/check_titles.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_db import vector_db

# Get all documents
results = vector_db.collection.get()

print("\n" + "="*70)
print("DATABASE TITLE AUDIT")
print("="*70 + "\n")

untitled_count = 0
titled_count = 0

print("Documents in database:")
for i, (doc_id, metadata) in enumerate(zip(results['ids'], results['metadatas']), 1):
    title = metadata.get('title', 'NO TITLE KEY')
    
    if not title or title == 'Untitled' or title == 'NO TITLE KEY':
        untitled_count += 1
        print(f"❌ [{i}] ID: {doc_id[:20]}... | Title: {title}")
        print(f"    Category: {metadata.get('category', 'N/A')}")
        print(f"    URL: {metadata.get('source_url', 'N/A')[:60]}")
    else:
        titled_count += 1
        print(f"✅ [{i}] {title}")

print("\n" + "="*70)
print(f"Summary:")
print(f"  ✅ Titled: {titled_count}")
print(f"  ❌ Untitled: {untitled_count}")
print(f"  📊 Total: {titled_count + untitled_count}")
print("="*70 + "\n")