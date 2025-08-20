import base64
from io import BytesIO
from typing import Optional
from gtts import gTTS

from backend import config


def synthesize_speech(text: str, lang: Optional[str] = None) -> bytes:
	"""Generate MP3 audio bytes for the provided text using gTTS."""
	if not text:
		text = "I'm here."
	language = lang or config.TTS_LANGUAGE
	tts = gTTS(text=text, lang=language)
	buf = BytesIO()
	tts.write_to_fp(buf)
	return buf.getvalue()


def to_base64_audio_mp3(mp3_bytes: bytes) -> str:
	"""Return a data URL (base64) for MP3 bytes suitable for HTML audio src."""
	b64 = base64.b64encode(mp3_bytes).decode('ascii')
	return f"data:audio/mp3;base64,{b64}" 