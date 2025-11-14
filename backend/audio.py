# backend/audio.py - FIXED VERSION

import sys
from pathlib import Path
from typing import Optional
import hashlib

sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.config import settings

# Audio output directory
AUDIO_DIR = Path(__file__).parent.parent / "data" / "audio"
AUDIO_DIR.mkdir(exist_ok=True)


class AudioService:
    """
    Text-to-Speech service using FREE Edge TTS
    No API key required!
    """
    
    def __init__(self):
        """Initialize Edge TTS"""
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.available = True
            print("✅ Edge TTS initialized (FREE)")
        except ImportError:
            self.available = False
            print("⚠️  Edge TTS not installed. Run: pip install edge-tts")
    
    async def text_to_speech_async(
        self,
        text: str,
        language: str = "en",
        voice: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert text to speech using Edge TTS (ASYNC version for FastAPI)
        
        Args:
            text: Text to convert
            language: Language code (en, hi, mr)
            voice: Voice name (optional)
            
        Returns:
            Path to audio file or None if failed
        """
        if not self.available:
            print("⚠️  TTS not available")
            return None
        
        try:
            # Generate filename from text hash AND language
            text_hash = hashlib.md5(f"{text}_{language}".encode()).hexdigest()[:12]
            audio_file = AUDIO_DIR / f"tts_{language}_{text_hash}.mp3"
            
            # Check if already generated
            if audio_file.exists():
                print(f"♻️  Using cached audio: {audio_file.name}")
                return str(audio_file)
            
            # Select voice based on language
            if voice is None:
                voice = self._get_voice_for_language(language)
            
            print(f"🎤 Generating {language} audio with voice: {voice}")
            
            # Generate audio (await directly, don't use asyncio.run)
            await self._generate_audio(text, str(audio_file), voice)
            
            if audio_file.exists():
                print(f"🔊 Audio generated: {audio_file.name}")
                return str(audio_file)
            
        except Exception as e:
            print(f"❌ TTS error: {e}")
        
        return None
    
    def text_to_speech(
        self,
        text: str,
        language: str = "en",
        voice: Optional[str] = None
    ) -> Optional[str]:
        """
        Synchronous wrapper for text_to_speech (for testing only)
        Use text_to_speech_async in FastAPI!
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Can't use asyncio.run() here
                print("⚠️  Use text_to_speech_async() in async context")
                return None
            return asyncio.run(self.text_to_speech_async(text, language, voice))
        except RuntimeError:
            return asyncio.run(self.text_to_speech_async(text, language, voice))
    
    async def _generate_audio(self, text: str, output_path: str, voice: str):
        """Generate audio using Edge TTS"""
        communicate = self.edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
    
    def _get_voice_for_language(self, language: str) -> str:
        """
        FIXED: Get appropriate voice for language with better distinction
        
        Edge TTS voices available:
        - English: en-US-AriaNeural (female, clear), en-US-GuyNeural (male)
        - Hindi: hi-IN-SwaraNeural (female, natural), hi-IN-MadhurNeural (male)
        - Marathi: mr-IN-AarohiNeural (female), mr-IN-ManoharNeural (male)
        
        IMPORTANT: Use DIFFERENT voices for Hindi and Marwadi to avoid confusion!
        """
        voices = {
            "en": "en-US-AriaNeural",      # English - Clear female voice
            "hi": "hi-IN-SwaraNeural",     # Hindi - Natural female voice (NOT Marathi!)
            "mr": "mr-IN-AarohiNeural",    # Marwadi/Marathi - Distinct Marathi female voice
        }
        
        selected_voice = voices.get(language, "en-US-AriaNeural")
        print(f"🗣️  Selected voice for '{language}': {selected_voice}")
        
        return selected_voice


# Initialize singleton
audio_service = AudioService()


async def test_audio_async():
    """Test audio service (async version)"""
    print("\n" + "="*60)
    print("TESTING FREE EDGE TTS")
    print("="*60 + "\n")
    
    if not audio_service.available:
        print("⚠️  Edge TTS not installed.")
        print("   Install: pip install edge-tts")
        return
    
    test_cases = [
        {
            "language": "en",
            "text": "Ahimsa, meaning non-violence, is the cornerstone principle of Jainism."
        },
        {
            "language": "hi",
            "text": "अहिंसा जैन धर्म का मूल सिद्धांत है जो सभी जीवों के प्रति करुणा सिखाता है।"
        },
        {
            "language": "mr",
            "text": "अहिंसा हे जैन धर्माचे मूलभूत तत्त्व आहे."
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        lang = test_case["language"]
        text = test_case["text"]
        
        print(f"\n{'='*60}")
        print(f"Test {i}: {lang.upper()} voice")
        print(f"{'='*60}")
        print(f"Text: {text[:100]}...\n")
        
        audio_path = await audio_service.text_to_speech_async(text, language=lang)
        
        if audio_path:
            print(f"✅ {lang.upper()} audio generated!")
            print(f"📁 File: {audio_path}")
            print(f"📊 Size: {Path(audio_path).stat().st_size / 1024:.1f} KB")
        else:
            print(f"❌ Failed to generate {lang.upper()} audio")
    
    print("\n" + "="*60)
    print("✅ Audio tests complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_audio_async())