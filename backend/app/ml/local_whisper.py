"""
Local Speech-to-Text: Whisper via Ollama (Privacy-Preserving).

NO cloud APIs. Audio processing happens on-device only.
Supports: MP3, WAV, M4A, OGG via ffmpeg conversion.

Pipeline:
1. Convert audio to WAV (if needed)
2. Send to Ollama Whisper (local inference)
3. Extract text + timestamps
4. Return transcription with metadata
"""

import os
import io
import subprocess
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import json
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class TranscriptionSegment(BaseModel):
    """Individual segment with timestamps."""
    start_time: float = Field(ge=0.0)  # seconds
    end_time: float = Field(ge=0.0)
    text: str
    confidence: Optional[float] = None  # If Whisper provides


class TranscriptionResult(BaseModel):
    """Complete transcription with metadata."""
    session_id: str
    audio_file_path: str
    transcript: str  # Full text
    segments: List[TranscriptionSegment] = []  # Per-segment timestamps
    language: str = "en"  # ISO 639-1 code
    duration_seconds: float = 0.0  # Audio duration
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model: str = "whisper"  # Model name
    inference_time_seconds: float = 0.0  # How long inference took


# ============================================================================
# LOCAL WHISPER SERVICE
# ============================================================================

class LocalWhisperService:
    """
    Speech-to-text using Whisper locally via Ollama.
    
    Privacy guarantee: NO network calls to cloud providers.
    All processing on local hardware (CPU/GPU).
    
    Requirements:
    - Ollama running locally (ollama pull whisper or whisper-tiny)
    - ffmpeg installed (for audio conversion)
    """
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.model_name = "whisper"  # or whisper-tiny, whisper-base, etc.
        
        # Verify Ollama is reachable
        self._verify_ollama_connection()
    
    def _verify_ollama_connection(self):
        """Check if Ollama is running locally."""
        try:
            import requests
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Ollama local service reachable")
            else:
                logger.warning(f"⚠ Ollama returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠ Ollama connection check failed: {e}")
            logger.info("  Make sure Ollama is running: ollama serve")
    
    # ========================================================================
    # AUDIO CONVERSION
    # ========================================================================
    
    @staticmethod
    def _get_audio_duration(audio_path: str) -> float:
        """Get audio duration in seconds using ffprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
                    audio_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            return 0.0
    
    @staticmethod
    def _convert_to_wav(audio_path: str) -> str:
        """
        Convert audio file to WAV format.
        
        Args:
            audio_path: Path to audio file (MP3, M4A, OGG, etc.)
        
        Returns:
            Path to converted WAV file (in temp directory)
        """
        path = Path(audio_path)
        
        # If already WAV, return as-is
        if path.suffix.lower() == ".wav":
            return audio_path
        
        # Convert to WAV
        wav_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", audio_path,
                    "-acodec", "pcm_s16le",
                    "-ar", "16000",  # 16 kHz sample rate (Whisper standard)
                    wav_path,
                    "-y",  # Overwrite without asking
                ],
                capture_output=True,
                timeout=300,  # 5 min timeout for long audio
            )
            logger.info(f"Converted {path.name} to WAV: {wav_path}")
            return wav_path
        except subprocess.TimeoutExpired:
            logger.error("Audio conversion timed out")
            raise
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise
    
    # ========================================================================
    # TRANSCRIPTION
    # ========================================================================
    
    async def transcribe_audio(
        self,
        session_id: str,
        audio_file_path: Optional[str] = None,
        audio_buffer: Optional[io.BytesIO] = None,
        language: str = "en",
    ) -> TranscriptionResult:
        """
        Transcribe audio using local Whisper model.
        
        Args:
            session_id: Curriculum session ID
            audio_file_path: Optional path to audio file
            audio_buffer: Optional BytesIO buffer containing audio data
            language: ISO 639-1 language code (default: "en")
        
        Returns:
            TranscriptionResult with full transcript + segments
        """
        temp_file = None
        
        try:
            # If buffer provided, write to temp file first
            if audio_buffer:
                temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                audio_buffer.seek(0)
                temp_file.write(audio_buffer.read())
                temp_file.close()
                audio_file_path = temp_file.name
                logger.info(f"Using temp file for audio buffer: {audio_file_path}")

            if not audio_file_path or not os.path.exists(audio_file_path):
                raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
            
            # Get audio duration
            duration = self._get_audio_duration(audio_file_path)
            
            # Convert to WAV (if needed)
            wav_path = self._convert_to_wav(audio_file_path)
            
            try:
                # Read WAV file as binary
                with open(wav_path, "rb") as f:
                    audio_bytes = f.read()
                
                # Call Ollama Whisper API
                import requests
                start_time = datetime.now(timezone.utc)
                
                response = requests.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": "",
                        "images": [self._encode_audio_base64(audio_bytes)],
                        "stream": False,
                    },
                    timeout=600,
                )
                
                inference_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama error: {response.text}")
                
                # Parse response
                result = response.json()
                transcript_text = result.get("response", "").strip()
                
                # Extract segments
                segments = self._parse_segments(transcript_text)
                
                return TranscriptionResult(
                    session_id=session_id,
                    audio_file_path=audio_file_path,
                    transcript=transcript_text,
                    segments=segments,
                    language=language,
                    duration_seconds=duration,
                    model=self.model_name,
                    inference_time_seconds=inference_time,
                )
            finally:
                # Clean up temp WAV if we created one during conversion
                if wav_path != audio_file_path and os.path.exists(wav_path):
                    try: os.remove(wav_path)
                    except: pass
        finally:
            # Clean up temp file if we created one from buffer
            if temp_file and os.path.exists(temp_file.name):
                try: os.remove(temp_file.name)
                except: pass
        
    
    @staticmethod
    def _encode_audio_base64(audio_bytes: bytes) -> str:
        """Encode audio bytes to base64 for Ollama API."""
        import base64
        return base64.b64encode(audio_bytes).decode()
    
    @staticmethod
    def _parse_segments(transcript: str) -> List[TranscriptionSegment]:
        """
        Parse transcript into segments with estimated timestamps.
        
        If Whisper returns JSON with timing info, parse it.
        Otherwise, approximate segment boundaries.
        """
        segments = []
        
        try:
            # Try to parse as JSON (Whisper verbose output)
            data = json.loads(transcript)
            if "segments" in data:
                for seg in data["segments"]:
                    segments.append(TranscriptionSegment(
                        start_time=seg.get("start", 0.0),
                        end_time=seg.get("end", 0.0),
                        text=seg.get("text", ""),
                        confidence=seg.get("confidence"),
                    ))
                return segments
        except (json.JSONDecodeError, TypeError):
            # Not JSON, fall back to splitting
            pass
        
        # Fallback: split by sentences
        sentences = transcript.split(". ")
        time_per_sentence = 5.0  # Rough estimate: 5s per sentence
        
        for i, sentence in enumerate(sentences):
            segments.append(TranscriptionSegment(
                start_time=i * time_per_sentence,
                end_time=(i + 1) * time_per_sentence,
                text=sentence.strip(),
            ))
        
        return segments
    
    # ========================================================================
    # BATCH TRANSCRIPTION (FOR MULTIPLE AUDIOS)
    # ========================================================================
    
    async def transcribe_batch(
        self,
        audio_files: Dict[str, str],  # {session_id: audio_path}
        language: str = "en",
    ) -> Dict[str, TranscriptionResult]:
        """
        Transcribe multiple audio files sequentially.
        
        Args:
            audio_files: Dict of {session_id: audio_path}
            language: Language code
        
        Returns:
            Dict of {session_id: TranscriptionResult}
        """
        results = {}
        
        for session_id, audio_path in audio_files.items():
            try:
                result = await self.transcribe_audio(audio_path, session_id, language)
                results[session_id] = result
            except Exception as e:
                logger.error(f"Transcription failed for {session_id}: {e}")
                results[session_id] = None
        
        return results
