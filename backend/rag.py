# backend/rag.py - BIDIRECTIONAL FIX

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
    
    def _detect_language_in_history(self, chat_history: Optional[List[Dict]]) -> str:
        """
        Detect what language was used in recent chat history
        
        Args:
            chat_history: Previous messages
            
        Returns:
            Detected language code ('en', 'hi', 'mr', 'mixed', or 'unknown')
        """
        if not chat_history or len(chat_history) == 0:
            return 'unknown'
        
        # Check last assistant message
        for msg in reversed(chat_history):
            if msg.get('role') == 'assistant':
                content = msg.get('content', '')
                
                # Check for Devanagari script (Hindi/Marwadi)
                if any('\u0900' <= char <= '\u097F' for char in content):
                    return 'hi'  # or 'mr', both use Devanagari
                
                # Check for English (basic Latin characters)
                elif any('a' <= char.lower() <= 'z' for char in content):
                    return 'en'
        
        return 'unknown'
    
    def _get_language_instruction(self, language: str, history_language: str = 'unknown') -> str:
        """
        FIXED: Get language-specific instruction with BIDIRECTIONAL support
        
        Args:
            language: Target language code (en, hi, mr)
            history_language: Language detected in chat history
            
        Returns:
            Language instruction string
        """
        
        # If history is in different language, be MORE forceful
        is_switching = (history_language != 'unknown' and 
                       history_language != language and 
                       history_language != 'mixed')
        
        language_instructions = {
            "en": f"""
{"⚠️ LANGUAGE SWITCH DETECTED ⚠️" if is_switching else ""}
{"YOU ARE NOW SWITCHING TO ENGLISH - STOP USING HINDI/MARWADI!" if is_switching else ""}

LANGUAGE REQUIREMENT: RESPOND IN ENGLISH

MANDATORY RULES:
1. Use ONLY English language - NO Hindi, NO Marwadi, NO Devanagari script
2. {"Even though previous messages were in Hindi/Marwadi, respond in ENGLISH now" if is_switching else "Respond naturally in English"}
3. Translate any Hindi/Marwadi terms to English
4. Use Latin alphabet only (A-Z, a-z)
5. Keep the warm, teaching style in English

{"EXAMPLES:" if is_switching else ""}
{"❌ WRONG: 'अहिंसा का अर्थ है non-violence'" if is_switching else ""}
{"✅ CORRECT: 'Ahimsa means non-violence and is the cornerstone of Jainism'" if is_switching else ""}

{"IGNORE any Hindi/Marwadi in conversation history - respond ONLY in English." if is_switching else ""}
""",
            "hi": f"""
{"⚠️ LANGUAGE SWITCH DETECTED ⚠️" if is_switching else ""}
{"YOU ARE NOW SWITCHING TO HINDI - STOP USING ENGLISH!" if is_switching else ""}

⚠️ CRITICAL LANGUAGE REQUIREMENT - HIGHEST PRIORITY ⚠️
YOU MUST RESPOND 100% IN HINDI (हिंदी) - NO EXCEPTIONS!

MANDATORY RULES:
1. DO NOT use ANY English words - translate EVERYTHING to Hindi
2. Use ONLY Devanagari script (देवनागरी) - NO Latin alphabet
3. {"Even though ALL previous messages were in English, YOU MUST respond in Hindi now" if is_switching else "Respond entirely in Hindi"}
4. Translate ALL technical terms to Hindi:
   - "Ahimsa" → "अहिंसा"
   - "karma" → "कर्म"
   - "Jainism" → "जैन धर्म"
   - "non-violence" → "अहिंसा"
5. Keep the warm, teaching style but IN HINDI

EXAMPLES:
❌ WRONG: "Ahimsa means non-violence"
✅ CORRECT: "अहिंसा का अर्थ है अहिंसा और यह जैन धर्म का सबसे महत्वपूर्ण सिद्धांत है"

{"IGNORE any English in conversation history - respond ONLY in Hindi." if is_switching else ""}
""",
            "mr": f"""
{"⚠️ LANGUAGE SWITCH DETECTED ⚠️" if is_switching else ""}
{"YOU ARE NOW SWITCHING TO MARWADI - STOP USING ENGLISH!" if is_switching else ""}

⚠️ CRITICAL LANGUAGE REQUIREMENT - HIGHEST PRIORITY ⚠️
YOU MUST RESPOND 100% IN MARWADI-STYLE HINDI (मारवाड़ी हिंदी) - NO EXCEPTIONS!

MANDATORY RULES:
1. DO NOT use ANY English words - translate EVERYTHING to Marwadi/Hindi
2. Use ONLY Devanagari script (देवनागरी)
3. Use Rajasthani/Marwadi Hindi dialect when speaking
4. {"Even though ALL previous messages were in English, YOU MUST respond in Marwadi Hindi now" if is_switching else "Respond in Marwadi Hindi"}
5. Keep the warm, teaching style but IN MARWADI HINDI

NOTE: Marwadi is a Rajasthani dialect. Use Hindi with Rajasthani flavor.

{"IGNORE any English in conversation history - respond ONLY in Marwadi/Hindi." if is_switching else ""}
"""
        }
        
        return language_instructions.get(language, "")
    
    def generate_response(
        self,
        query: str,
        chat_history: Optional[List[Dict]] = None,
        user_profile: Optional[Dict] = None,
        include_sources: bool = True,
        language: str = "en"
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
        
        # Step 3: Detect language in history
        history_language = self._detect_language_in_history(chat_history)
        
        # Step 4: Get system prompt with BIDIRECTIONAL language instruction
        base_system_prompt = self.llm._get_jain_teacher_prompt()
        language_instruction = self._get_language_instruction(language, history_language)
        system_prompt = base_system_prompt + language_instruction
        
        # Step 5: Filter chat history ALWAYS when switching languages
        filtered_history = None
        if chat_history:
            # If language is switching, limit history to reduce contamination
            if history_language != 'unknown' and history_language != language:
                # Language switch detected - use minimal history
                filtered_history = chat_history[-1:] if len(chat_history) > 0 else None
                print(f"🔄 Language switch detected: {history_language} → {language}")
                print(f"   Using limited history: {len(filtered_history) if filtered_history else 0} messages")
            else:
                # Same language - use more history
                filtered_history = chat_history[-5:] if len(chat_history) > 5 else chat_history
        
        # Step 6: Handle very short queries like "Hi" by adding context
        enhanced_query = query
        if len(query.strip()) < 10 and not any(c.isalnum() for c in query if ord(c) > 127):
            # Short English-like query - add language hint
            lang_name = {"en": "English", "hi": "Hindi", "mr": "Marwadi"}
            enhanced_query = f"{query} (Please respond in {lang_name.get(language, 'English')})"
        
        # Step 7: Generate response with language-aware system prompt
        llm_response = self.llm.generate_response(
            user_message=enhanced_query,
            context=context if context else "",
            chat_history=filtered_history,
            system_prompt=system_prompt
        )
        
        # Step 8: Prepare sources for citation
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
        
        # Step 9: Return complete response
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
        language: str = "en"
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
            language=language
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