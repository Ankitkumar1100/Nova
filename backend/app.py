import os
import logging
from flask import Flask, request, jsonify, send_from_directory, session

from backend import config
from backend.nlu.rule_based import interpret
from backend.executor import execute_intent
from backend.services.speech import transcribe_wav
from backend.services.tts import synthesize_speech, to_base64_audio_mp3
from backend.storage import list_reminders

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'frontend')

app = Flask(
	__name__,
	static_folder=os.path.join(FRONTEND_DIR, 'assets'),
	static_url_path='/assets'
)
app.secret_key = 'nova-dev'  # for session


def get_langs():
	stt_lang = session.get('stt_lang') or config.STT_LANGUAGE
	tts_lang = session.get('tts_lang') or config.TTS_LANGUAGE
	return stt_lang, tts_lang


def process_text_command(text: str):
	intent_res = interpret(text)
	intent = intent_res.get('intent')
	entities = intent_res.get('entities', {})
	response_text = execute_intent(intent, entities)
	_, tts_lang = get_langs()
	mp3 = synthesize_speech(response_text, lang=tts_lang)
	audio_url = to_base64_audio_mp3(mp3)
	return {
		"transcription": text,
		"intent": intent,
		"entities": entities,
		"response_text": response_text,
		"audio_data_url": audio_url,
	}


@app.route('/')
def index():
	return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def send_frontend(path):
	full_path = os.path.join(FRONTEND_DIR, path)
	if os.path.exists(full_path):
		return send_from_directory(FRONTEND_DIR, path)
	return send_from_directory(FRONTEND_DIR, 'index.html')


@app.post('/api/command')
def api_command():
	data = request.get_json(force=True, silent=True) or {}
	text = (data.get('text') or '').strip()
	if not text:
		return jsonify({"error": "text is required"}), 400
	lang_override = data.get('tts_lang')
	if lang_override:
		session['tts_lang'] = lang_override
	try:
		res = process_text_command(text)
		return jsonify(res)
	except Exception as exc:
		logger.exception("/api/command error")
		return jsonify({"error": str(exc)}), 500


@app.post('/api/upload-audio')
def upload_audio():
	if 'file' not in request.files:
		return jsonify({"error": "file is required (WAV)"}), 400
	file = request.files['file']
	if not file.filename:
		return jsonify({"error": "empty filename"}), 400
	# Save to tmp and transcribe
	tmp_path = os.path.join(config.TMP_DIR, file.filename)
	file.save(tmp_path)
	try:
		stt_lang, _ = get_langs()
		text = transcribe_wav(tmp_path, language=stt_lang)
		if not text:
			return jsonify({"error": "Could not transcribe audio", "transcription": ""}), 400
		res = process_text_command(text)
		return jsonify(res)
	except Exception as exc:
		logger.exception("/api/upload-audio error")
		return jsonify({"error": str(exc)}), 500
	finally:
		try:
			os.remove(tmp_path)
		except OSError:
			pass


@app.post('/api/language')
def set_language():
	data = request.get_json(force=True, silent=True) or {}
	stt_lang = data.get('stt_lang')
	tts_lang = data.get('tts_lang')
	if stt_lang:
		session['stt_lang'] = stt_lang
	if tts_lang:
		session['tts_lang'] = tts_lang
	return jsonify({"stt_lang": session.get('stt_lang'), "tts_lang": session.get('tts_lang')})


@app.get('/api/reminders')
def api_reminders():
	try:
		return jsonify({"reminders": list_reminders()})
	except Exception as exc:
		return jsonify({"error": str(exc)}), 500


@app.get('/api/health')
def health():
	return jsonify({"status": "ok"})


if __name__ == '__main__':
	app.run(host=config.HOST, port=config.PORT, debug=config.FLASK_DEBUG) 