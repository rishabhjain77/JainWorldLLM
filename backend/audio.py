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
            # Generate filename from text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()[:12]
            audio_file = AUDIO_DIR / f"tts_{text_hash}.mp3"
            
            # Check if already generated
            if audio_file.exists():
                print(f"♻️  Using cached audio: {audio_file.name}")
                return str(audio_file)
            
            # Select voice based on language
            if voice is None:
                voice = self._get_voice_for_language(language)
            
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
        Get appropriate voice for language
        
        Available voices:
        - English: en-US-AriaNeural (female), en-US-GuyNeural (male)
        - Hindi: hi-IN-SwaraNeural (female), hi-IN-MadhurNeural (male)
        - For Marwadi: Use Hindi voices
        """
        voices = {
            "en": "en-US-AriaNeural",  # Clear, warm female voice
            "hi": "hi-IN-SwaraNeural",  # Hindi female voice
            "mr": "hi-IN-SwaraNeural",  # Use Hindi for Marwadi
        }
        return voices.get(language, "en-US-AriaNeural")


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
    
    test_text = """Ahimsa, meaning non-violence, is the cornerstone principle of Jainism. 
    It extends beyond physical violence to include harm through thoughts, words, and actions."""
    
    print("🎤 Generating audio...")
    print(f"Text: {test_text[:100]}...\n")
    
    # Test English
    print("Testing English voice...")
    audio_path = await audio_service.text_to_speech_async(test_text, language="en")
    
    if audio_path:
        print(f"✅ English audio generated!")
        print(f"📁 File: {audio_path}")
        print(f"📊 Size: {Path(audio_path).stat().st_size / 1024:.1f} KB\n")
    
    # Test Hindi
    hindi_text = "जैन धर्म में अहिंसा सबसे महत्वपूर्ण सिद्धांत है।"
    print("Testing Hindi voice...")
    audio_path_hi = await audio_service.text_to_speech_async(hindi_text, language="hi")
    
    if audio_path_hi:
        print(f"✅ Hindi audio generated!")
        print(f"📁 File: {audio_path_hi}")
    
    print("\n" + "="*60)
    print("✅ Audio tests complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_audio_async())