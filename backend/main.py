# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import settings, check_api_keys
from backend.models import ChatRequest, ChatResponse, OnboardingRequest
from backend.llm import llm_service
from backend.rag import rag_pipeline
from backend.audio import audio_service, AUDIO_DIR
from typing import List, Dict
import uuid
from datetime import datetime

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="AI-powered Jain learning companion with RAG",
    version="1.0.0"
)

# Serve static files (frontend)
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage
sessions: Dict[str, Dict] = {}


@app.on_event("startup")
async def startup_event():
    """Run on app startup"""
    print(f"\n🚀 Starting {settings.app_name}...")
    check_api_keys()
    print("✅ All systems ready!\n")


# FIXED: Root endpoint serves the frontend
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the frontend"""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        with open(index_file, 'r') as f:
            return f.read()
    return HTMLResponse(content="<h1>Frontend not found. Access API docs at <a href='/docs'>/docs</a></h1>")


# Health check moved to /health
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "app": settings.app_name,
        "status": "running",
        "version": "1.0.0",
        "features": ["RAG", "Chat", "Onboarding"],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/stats")
async def stats():
    """Get system statistics"""
    from backend.vector_db import vector_db
    db_stats = vector_db.get_stats()
    
    return {
        "vector_db": db_stats,
        "active_sessions": len(sessions),
        "model": settings.llm_model
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with RAG
    
    Retrieves relevant Jain content and generates informed responses
    """
    
    # Create or get session
    session_id = request.session_id or str(uuid.uuid4())
    
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "knowledge_level": "beginner",
            "created_at": datetime.now()
        }
    
    session = sessions[session_id]
    
    # Generate response using RAG WITH LANGUAGE
    response = rag_pipeline.adaptive_response(
        query=request.message,
        knowledge_level=session.get("knowledge_level", "beginner"),
        chat_history=session["history"][-10:],
        language=request.language  # PASS LANGUAGE HERE!
    )
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail="Failed to generate response")
    
    # Update session history
    session["history"].append({
        "role": "user",
        "content": request.message
    })
    session["history"].append({
        "role": "assistant",
        "content": response["response"]
    })
    
    # Generate audio if requested
    audio_url = None
    if request.include_audio and audio_service and audio_service.available:
        audio_text = response["response"]
        audio_path = await audio_service.text_to_speech_async(
            audio_text,
            language=request.language  # Use the language from request
        )
        if audio_path:
            audio_filename = Path(audio_path).name
            audio_url = f"/audio/{audio_filename}"
    
    # Generate follow-up suggestions
    suggestions = generate_contextual_suggestions(request.message, response)
    
    return ChatResponse(
        message=response["response"],
        sources=response["sources"],
        audio_url=audio_url,
        session_id=session_id,
        suggestions=suggestions
    )


@app.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files"""
    audio_path = AUDIO_DIR / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=filename
    )


@app.post("/onboarding")
async def onboarding(request: OnboardingRequest):
    """Generate personalized onboarding message"""
    
    response = llm_service.generate_onboarding_response(
        knowledge_level=request.knowledge_level,
        interests=request.interests
    )
    
    if not response["success"]:
        raise HTTPException(status_code=500, detail="Failed to generate onboarding")
    
    # Create session with user preferences
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "history": [],
        "knowledge_level": request.knowledge_level,
        "preferred_language": request.preferred_language,
        "preferred_mode": request.preferred_mode,
        "interests": request.interests,
        "created_at": datetime.now()
    }
    
    return {
        "message": response["message"],
        "session_id": session_id
    }


@app.get("/test")
async def test_endpoint():
    """Test RAG endpoint"""
    response = rag_pipeline.generate_response("What is Jainism?")
    
    return {
        "test": "successful",
        "response": response["response"],
        "sources": len(response["sources"]),
        "context_used": response["context_used"]
    }


def generate_contextual_suggestions(query: str, response: Dict) -> List[str]:
    """Generate contextual follow-up suggestions based on response"""
    
    # Extract topics from sources
    topics = set()
    for source in response.get("sources", []):
        topic = source.get("topic", "")
        if topic:
            topics.add(topic)
    
    # Generic suggestions
    base_suggestions = [
        "How can I apply this in my daily life?",
        "Tell me more about this concept",
        "Is there a story that illustrates this?"
    ]
    
    # Topic-specific suggestions
    topic_suggestions = {
        "ahimsa": ["What are practical ways to practice ahimsa?", "How do Jains avoid harming microorganisms?"],
        "karma": ["How does karma affect rebirth?", "Can karma be eliminated?"],
        "tirthankaras": ["Who were the other Tirthankaras?", "What is a Tirthankara?"],
        "daily_life": ["What rituals should I do daily?", "How do I start a meditation practice?"]
    }
    
    # Add topic-specific suggestions
    for topic in topics:
        if topic in topic_suggestions:
            base_suggestions.extend(topic_suggestions[topic][:1])
    
    return base_suggestions[:3]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )