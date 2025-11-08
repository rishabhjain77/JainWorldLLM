# backend/rag.py

from typing import List, Dict, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.vector_db import vector_db
from backend.llm import llm_service
from backend.config import settings


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline
    Combines vector search with LLM generation
    """
    
    def __init__(self):
        self.vector_db = vector_db
        self.llm = llm_service
        print("✅ RAG Pipeline initialized")
    
    def retrieve_context(
        self,
        query: str,
        top_k: int = None,
        filter_metadata: Optional[Dict] = None,
        min_relevance: float = 0.0
    ) -> Dict:
        """
        Retrieve relevant context from vector database
        
        Args:
            query: User's question
            top_k: Number of results to retrieve
            filter_metadata: Filter by metadata (e.g., difficulty level)
            min_relevance: Minimum relevance score (0-1)
            
        Returns:
            Dict with documents, metadatas, and relevance scores
        """
        if top_k is None:
            top_k = settings.top_k_results
        
        # Search vector database
        results = self.vector_db.search(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )
        
        # Filter by relevance
        filtered_results = {
            "documents": [],
            "metadatas": [],
            "scores": [],
            "ids": []
        }
        
        for doc, metadata, distance, doc_id in zip(
            results['documents'],
            results['metadatas'],
            results['distances'],
            results['ids']
        ):
            # Convert distance to similarity score (1 - distance)
            score = 1 - distance
            
            if score >= min_relevance:
                filtered_results['documents'].append(doc)
                filtered_results['metadatas'].append(metadata)
                filtered_results['scores'].append(score)
                filtered_results['ids'].append(doc_id)
        
        return filtered_results
    
    def format_context(self, retrieved_docs: Dict) -> str:
        """
        Format retrieved documents into context string for LLM
        
        Args:
            retrieved_docs: Retrieved documents from vector DB
            
        Returns:
            Formatted context string
        """
        if not retrieved_docs['documents']:
            return ""
        
        context_parts = []
        
        for i, (doc, metadata, score) in enumerate(zip(
            retrieved_docs['documents'],
            retrieved_docs['metadatas'],
            retrieved_docs['scores']
        ), 1):
            # Format each source
            title = metadata.get('title', 'Untitled')
            category = metadata.get('category', 'general')
            
            context_part = f"""
[Source {i}] {title} ({category})
Relevance: {score:.2f}
---
{doc}
---
"""
            context_parts.append(context_part)
        
        return "\n".join(context_parts)
    
    def _get_language_instruction(self, language: str) -> str:
        """
        Get language-specific instruction for the system prompt
        
        Args:
            language: Language code (en, hi, mr)
            
        Returns:
            Language instruction string
        """
        language_instructions = {
            "en": "",  # English is default, no special instruction needed
            "hi": """

CRITICAL LANGUAGE INSTRUCTION:
You MUST respond ENTIRELY in Hindi (हिंदी). 
- Translate all your responses to Hindi
- Use Devanagari script
- Keep the warm, teaching style but in Hindi
- All explanations, examples, and stories should be in Hindi
Example: Instead of "Ahimsa means non-violence", say "अहिंसा का अर्थ है अहिंसा"
""",
            "mr": """

CRITICAL LANGUAGE INSTRUCTION:
You MUST respond ENTIRELY in Hindi/Marwadi (हिंदी/मारवाड़ी).
- Translate all your responses to Hindi (as Marwadi uses similar script)
- Use Devanagari script
- Keep the warm, teaching style but in Hindi
- All explanations, examples, and stories should be in Hindi
"""
        }
        
        return language_instructions.get(language, "")
    
    def generate_response(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None,
        include_sources: bool = True,
        language: str = "en"  # NEW: Add language parameter
    ) -> Dict:
        """
        Generate response using RAG pipeline
        
        Args:
            query: User's question
            chat_history: Previous chat messages
            user_profile: User profile (knowledge level, interests, etc.)
            include_sources: Whether to include source citations
            language: Language for response (en, hi, mr)
            
        Returns:
            Dict with response, sources, and metadata
        """
        # Step 1: Retrieve relevant context
        filter_metadata = None
        if user_profile and user_profile.get('knowledge_level'):
            pass
        
        retrieved = self.retrieve_context(
            query=query,
            filter_metadata=filter_metadata,
            min_relevance=0.1
        )
        
        # Step 2: Format context
        context = self.format_context(retrieved)
        
        # Step 3: Get base system prompt and add language instruction
        base_system_prompt = self.llm._get_jain_teacher_prompt()
        language_instruction = self._get_language_instruction(language)
        system_prompt = base_system_prompt + language_instruction
        
        # Step 4: Generate response with context and language-aware system prompt
        llm_response = self.llm.generate_response(
            user_message=query,
            context=context if context else "",
            chat_history=chat_history,
            system_prompt=system_prompt  # Use language-specific prompt
        )
        
        # Step 5: Prepare sources for citation
        sources = []
        if include_sources and retrieved['documents']:
            for metadata, score in zip(retrieved['metadatas'], retrieved['scores']):
                source = {
                    "title": metadata.get('title', 'Untitled'),
                    "category": metadata.get('category', 'general'),
                    "topic": metadata.get('topic', ''),
                    "relevance": round(score, 3),
                    "source_url": metadata.get('source_url', '')
                }
                sources.append(source)
        
        # Step 6: Return complete response
        return {
            "success": llm_response.get("success", True),
            "response": llm_response.get("message", ""),
            "sources": sources,
            "context_used": bool(context),
            "num_sources": len(sources),
            "tokens_used": llm_response.get("tokens_used", {})
        }
    
    def adaptive_response(
        self,
        query: str,
        knowledge_level: str = "beginner",
        chat_history: Optional[List[Dict]] = None,
        language: str = "en"  # NEW: Add language parameter
    ) -> Dict:
        """
        Generate adaptive response based on user's knowledge level and language
        
        Args:
            query: User's question
            knowledge_level: User's knowledge level (beginner/intermediate/advanced)
            chat_history: Previous messages
            language: Language for response (en, hi, mr)
            
        Returns:
            Tailored response in requested language
        """
        # Get response with language
        response = self.generate_response(
            query=query,
            chat_history=chat_history,
            user_profile={"knowledge_level": knowledge_level},
            language=language  # Pass language through
        )
        
        return response


# Initialize singleton
rag_pipeline = RAGPipeline()


def test_rag():
    """Test the RAG pipeline"""
    print("\n" + "="*60)
    print("TESTING RAG PIPELINE")
    print("="*60 + "\n")
    
    test_queries = [
        {
            "query": "What is ahimsa and how can I practice it?",
            "level": "beginner",
            "language": "en"
        },
        {
            "query": "अहिंसा क्या है?",
            "level": "beginner",
            "language": "hi"
        },
        {
            "query": "Tell me an inspiring story from Jainism",
            "level": "beginner",
            "language": "en"
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {test['level'].upper()} level - Language: {test['language']}")
        print(f"{'='*60}\n")
        print(f"🧑 Query: {test['query']}\n")
        
        # Generate response
        response = rag_pipeline.adaptive_response(
            query=test['query'],
            knowledge_level=test['level'],
            language=test['language']
        )
        
        if response['success']:
            print(f"🤖 Response:\n{response['response']}\n")
            
            if response['sources']:
                print(f"📚 Sources used ({response['num_sources']}):")
                for source in response['sources']:
                    print(f"   • {source['title']} ({source['category']}) - Relevance: {source['relevance']}")
            
            print(f"\n📊 Context used: {response['context_used']}")
            print(f"📊 Tokens: {response['tokens_used'].get('total', 'N/A')}")
        else:
            print(f"❌ Error: {response.get('error', 'Unknown')}")
        
        print("\n" + "-"*60)
    
    print("\n" + "="*60)
    print("✅ RAG Pipeline tests complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_rag()