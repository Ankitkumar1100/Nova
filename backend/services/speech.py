import os
import contextlib
import wave
import speech_recognition as sr
from typing import Optional

from backend import config

_recognizer = sr.Recognizer()


def is_wav_file(file_path: str) -> bool:
	try:
		with contextlib.closing(wave.open(file_path, 'rb')) as wf:
			# Just attempting to open verifies WAV format
			return True
	except wave.Error:
		return False
	except FileNotFoundError:
		return False


def transcribe_wav(file_path: str, language: Optional[str] = None) -> str:
	"""
	Transcribe a WAV audio file using Google's free SpeechRecognition backend.
	Requires internet access and accepts only PCM WAV/AIFF/FLAC supported by SpeechRecognition.
	"""
	language = language or config.STT_LANGUAGE
	if not os.path.exists(file_path):
		raise FileNotFoundError(f"Audio file not found: {file_path}")
	if not is_wav_file(file_path):
		raise ValueError("Provided file is not a valid WAV file. Please upload 16-bit PCM WAV.")

	with sr.AudioFile(file_path) as source:
		audio = _recognizer.record(source)
	try:
		text = _recognizer.recognize_google(audio, language=language)
		return text
	except sr.UnknownValueError:
		return ""
	except sr.RequestError as exc:
		raise RuntimeError(f"Speech recognition service error: {exc}") 