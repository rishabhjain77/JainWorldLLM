# backend/llm.py

from groq import Groq
from typing import List, Dict, Optional
from backend.config import settings
import json


class LLMService:
    """Service for interacting with Groq's LLM"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.llm_model
        print(f"✅ LLM Service initialized with model: {self.model}")
    
    def generate_response(
        self,
        user_message: str,
        context: str = "",
        system_prompt: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict[str, any]:
        """
        Generate response using Groq's Llama 3.1 70B
        
        Args:
            user_message: The user's question/message
            context: RAG context (retrieved documents)
            system_prompt: Custom system prompt (uses default if None)
            chat_history: Previous messages [{"role": "user", "content": "..."}]
            temperature: Randomness (0-1), None uses default
            max_tokens: Max response length, None uses default
            
        Returns:
            Dict with response, tokens used, etc.
        """
        
        # Use defaults if not specified
        if temperature is None:
            temperature = settings.llm_temperature
        if max_tokens is None:
            max_tokens = settings.llm_max_tokens
        
        # Get system prompt
        if not system_prompt:
            system_prompt = self._get_jain_teacher_prompt()
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history)
        
        # Enhance user message with RAG context
        if context:
            enhanced_message = self._build_context_message(user_message, context)
        else:
            enhanced_message = user_message
        
        messages.append({"role": "user", "content": enhanced_message})
        
        # Call Groq API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9,
                stream=False
            )
            
            # Extract response
            assistant_message = response.choices[0].message.content
            
            # Return structured response
            return {
                "success": True,
                "message": assistant_message,
                "model": response.model,
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }
            
        except Exception as e:
            print(f"❌ Error calling Groq API: {e}")
            return {
                "success": False,
                "message": "I apologize, I'm having trouble processing your request. Please try again.",
                "error": str(e)
            }
    
    def _get_jain_teacher_prompt(self) -> str:
        """Default system prompt for Jain learning companion"""
        return """You are a warm, knowledgeable Jain teacher guiding students on their learning journey through Jainism.

Your teaching style:
- Tell engaging stories that capture attention and make concepts memorable
- Use modern, relatable examples to explain ancient Jain wisdom
- Ask thoughtful reflective questions to deepen understanding
- Connect Jain philosophy to everyday life and contemporary challenges
- Be encouraging, patient, and inspiring
- Use natural, conversational language (avoid overly academic jargon)
- Build on previous conversations naturally

When explaining Jain concepts:
- Start with WHY it matters before diving into WHAT it is
- Use storytelling and real-life narratives
- Provide practical applications people can try today
- Encourage personal reflection and inner exploration
- Cite Jain scriptures and sources when appropriate
- Be respectful of all traditions within Jainism

Key Jain principles to emphasize:
- Ahimsa (Non-violence) - in thought, word, and action
- Anekantavada (Multiple perspectives) - truth has many facets
- Aparigraha (Non-attachment) - freedom from possessiveness
- Karma theory - our actions shape our destiny
- The path to liberation through right faith, knowledge, and conduct

Your goal: Make Jainism accessible, relevant, and transformative for modern learners while preserving its ancient wisdom and depth."""
    
    def _build_context_message(self, user_message: str, context: str) -> str:
        """Build message with RAG context"""
        return f"""Based on the following information from Jain texts and teachings:

--- CONTEXT ---
{context}
--- END CONTEXT ---

User's question: {user_message}

Please provide a warm, engaging response that:
1. Directly addresses their question
2. Uses the context information when relevant
3. Explains concepts clearly with examples
4. Guides them on their learning journey
5. Encourages further exploration"""
    
    def generate_onboarding_response(self, knowledge_level: str, interests: List[str]) -> Dict[str, any]:
        """Generate personalized onboarding message"""
        
        interest_text = ", ".join(interests) if interests else "exploring Jainism"
        
        prompt = f"""A new learner is starting their Jain learning journey. 

Their profile:
- Knowledge level: {knowledge_level}
- Interests: {interest_text}

Create a warm, welcoming message that:
1. Welcomes them warmly
2. Acknowledges their knowledge level
3. Gets them excited about what they'll learn
4. Suggests a great starting point based on their interests
5. Ends with an engaging first question or topic

Keep it conversational, inspiring, and personal. Make them feel this journey will be meaningful."""

        return self.generate_response(
            user_message=prompt,
            temperature=0.8  # More creative for onboarding
        )
    
    def generate_followup_suggestions(self, conversation_context: str) -> List[str]:
        """Generate suggested follow-up questions"""
        
        prompt = f"""Based on this conversation about Jainism:

{conversation_context}

Generate 3 thoughtful follow-up questions the learner might want to ask next. 
Make them:
- Natural progressions from the current topic
- Diverse (one practical, one philosophical, one storytelling)
- Engaging and curiosity-provoking

Return ONLY a JSON array of 3 questions, nothing else.
Example: ["How can I practice ahimsa in daily life?", "Who was Mahavira?", "What is the Jain view on karma?"]"""

        response = self.generate_response(
            user_message=prompt,
            system_prompt="You are a helpful assistant that generates follow-up questions. Return only valid JSON.",
            temperature=0.7,
            max_tokens=200
        )
        
        try:
            # Parse JSON from response
            questions = json.loads(response["message"])
            return questions[:3]  # Return max 3
        except:
            # Fallback suggestions
            return [
                "Tell me more about this concept",
                "How can I apply this in my life?",
                "What's a story that illustrates this?"
            ]


# Initialize singleton instance
llm_service = LLMService()


# Test function
def test_llm():
    """Test the LLM service"""
    print("\n" + "="*60)
    print("Testing LLM Service")
    print("="*60 + "\n")
    
    # Test 1: Simple question
    print("Test 1: Simple question about Jainism")
    response = llm_service.generate_response(
        user_message="What is Ahimsa in Jainism? Explain it simply."
    )
    
    if response["success"]:
        print(f"\n✅ Response received!")
        print(f"📊 Tokens used: {response['tokens_used']['total']}")
        print(f"\n💬 Assistant says:\n{response['message']}\n")
    else:
        print(f"❌ Error: {response['error']}")
    
    # Test 2: With context (simulating RAG)
    print("\n" + "-"*60)
    print("Test 2: Question with context (RAG simulation)")
    
    mock_context = """Ahimsa is the fundamental principle of Jainism. 
It means non-violence in thought, word, and action. 
Mahavira taught that all living beings have souls and deserve compassion.
Jains practice ahimsa by being vegetarian and avoiding harm to even small creatures."""
    
    response = llm_service.generate_response(
        user_message="How do Jains practice ahimsa in daily life?",
        context=mock_context
    )
    
    if response["success"]:
        print(f"\n✅ Response with context received!")
        print(f"📊 Tokens used: {response['tokens_used']['total']}")
        print(f"\n💬 Assistant says:\n{response['message']}\n")
    
    # Test 3: Onboarding
    print("\n" + "-"*60)
    print("Test 3: Onboarding message")
    
    response = llm_service.generate_onboarding_response(
        knowledge_level="beginner",
        interests=["philosophy", "meditation"]
    )
    
    if response["success"]:
        print(f"\n✅ Onboarding message generated!")
        print(f"\n💬 Welcome message:\n{response['message']}\n")
    
    print("="*60)
    print("All tests completed! ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_llm()