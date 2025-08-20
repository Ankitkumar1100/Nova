const stateEl = document.getElementById('state');
const micBtn = document.getElementById('micBtn');
const youSaid = document.getElementById('youSaid');
const assistantSays = document.getElementById('assistantSays');
const replyAudio = document.getElementById('replyAudio');
const visualizer = document.getElementById('visualizer');
const fileInput = document.getElementById('audioFile');
const continuousToggle = document.getElementById('continuousToggle');
const wakeToggle = document.getElementById('wakeToggle');
const wakeWordInput = document.getElementById('wakeWord');
const sttLangSel = document.getElementById('sttLang');
const ttsLangSel = document.getElementById('ttsLang');
const applyLangBtn = document.getElementById('applyLang');

let mediaStream = null;
let audioContext = null;
let analyser = null;
let sourceNode = null;
let processorNode = null;
let rafId = null;
let recordingBuffers = [];
let inputSampleRate = 44100;
let recordingActive = false;
let spokenSinceStart = false;
let silenceFrames = 0;

function setState(text) { stateEl.textContent = text; }
function setMicActive(active) { micBtn.classList.toggle('active', active); }

function drawVisualizer() {
	if (!analyser) return;
	const ctx = visualizer.getContext('2d');
	const bufferLength = analyser.frequencyBinCount;
	const dataArray = new Uint8Array(bufferLength);
	ctx.clearRect(0, 0, visualizer.width, visualizer.height);
	analyser.getByteFrequencyData(dataArray);
	ctx.fillStyle = 'rgba(96,165,250,0.25)';
	const barWidth = (visualizer.width / bufferLength) * 2.5;
	let x = 0;
	for (let i = 0; i < bufferLength; i++) {
		const barHeight = dataArray[i] / 255 * visualizer.height;
		ctx.fillRect(x, visualizer.height - barHeight, barWidth, barHeight);
		x += barWidth + 1;
	}
	rafId = requestAnimationFrame(drawVisualizer);
}

async function startRecording() {
	if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
		alert('getUserMedia not supported. Use the upload WAV option.');
		return;
	}
	setState('Listening…');
	setMicActive(true);
	recordingActive = true;
	recordingBuffers = [];
	spokenSinceStart = false;
	silenceFrames = 0;
	mediaStream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
	audioContext = new (window.AudioContext || window.webkitAudioContext)();
	inputSampleRate = audioContext.sampleRate;
	sourceNode = audioContext.createMediaStreamSource(mediaStream);
	analyser = audioContext.createAnalyser();
	analyser.fftSize = 256;
	sourceNode.connect(analyser);
	processorNode = audioContext.createScriptProcessor(4096, 1, 1);
	sourceNode.connect(processorNode);
	processorNode.connect(audioContext.destination);
	processorNode.onaudioprocess = (e) => {
		const channelData = e.inputBuffer.getChannelData(0);
		recordingBuffers.push(new Float32Array(channelData));
		// Simple RMS to detect speech
		let sum = 0;
		for (let i = 0; i < channelData.length; i++) sum += channelData[i] * channelData[i];
		const rms = Math.sqrt(sum / channelData.length);
		if (rms > 0.02) { spokenSinceStart = true; silenceFrames = 0; }
		else if (spokenSinceStart) { silenceFrames++; }
		// Auto-stop if continuous off and we observed ~500ms of silence
		if (!continuousToggle.checked && spokenSinceStart && silenceFrames > 4) {
			stopRecording();
		}
	};
	drawVisualizer();
}

async function stopRecording() {
	if (!recordingActive) return;
	recordingActive = false;
	setState('Processing…');
	setMicActive(false);
	try {
		if (processorNode) processorNode.disconnect();
		if (sourceNode) sourceNode.disconnect();
		if (analyser) analyser.disconnect();
		if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
		if (rafId) cancelAnimationFrame(rafId);
		if (audioContext) await audioContext.close();
	} finally {
		processorNode = null; sourceNode = null; analyser = null; audioContext = null; mediaStream = null; rafId = null;
	}
	const wavBlob = buildWavFromFloat32(recordingBuffers, inputSampleRate, 16000);
	await uploadWav(wavBlob);
	// Auto-restart if continuous listening on (and no wake word gating)
	if (continuousToggle.checked && !wakeToggle.checked) {
		startRecording();
	}
}

function mergeFloat32Arrays(buffers) {
	let total = 0;
	for (const b of buffers) total += b.length;
	const out = new Float32Array(total);
	let offset = 0;
	for (const b of buffers) { out.set(b, offset); offset += b.length; }
	return out;
}

function downsampleFloat32(buffer, inSampleRate, outSampleRate) {
	if (outSampleRate === inSampleRate) return buffer;
	const sampleRateRatio = inSampleRate / outSampleRate;
	const newLength = Math.round(buffer.length / sampleRateRatio);
	const result = new Float32Array(newLength);
	let offsetResult = 0;
	let offsetBuffer = 0;
	while (offsetResult < result.length) {
		const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
		let accum = 0, count = 0;
		for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
			accum += buffer[i];
			count++;
		}
		result[offsetResult] = accum / count;
		offsetResult++;
		offsetBuffer = nextOffsetBuffer;
	}
	return result;
}

function floatTo16BitPCM(float32Array) {
	const out = new Int16Array(float32Array.length);
	for (let i = 0; i < float32Array.length; i++) {
		let s = Math.max(-1, Math.min(1, float32Array[i]));
		out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
	}
	return out;
}

function encodeWAV(pcm16, sampleRate) {
	function writeString(dv, offset, str) { for (let i = 0; i < str.length; i++) dv.setUint8(offset + i, str.charCodeAt(i)); }
	const bytesPerSample = 2; const blockAlign = 1 * bytesPerSample; const byteRate = sampleRate * blockAlign; const dataSize = pcm16.byteLength;
	const buffer = new ArrayBuffer(44 + dataSize);
	const dv = new DataView(buffer);
	writeString(dv, 0, 'RIFF');
	dv.setUint32(4, 36 + dataSize, true);
	writeString(dv, 8, 'WAVE');
	writeString(dv, 12, 'fmt ');
	dv.setUint32(16, 16, true);
	dv.setUint16(20, 1, true);
	dv.setUint16(22, 1, true);
	dv.setUint32(24, sampleRate, true);
	dv.setUint32(28, byteRate, true);
	dv.setUint16(32, blockAlign, true);
	dv.setUint16(34, 16, true);
	writeString(dv, 36, 'data');
	dv.setUint32(40, dataSize, true);
	new Uint8Array(buffer, 44).set(new Uint8Array(pcm16.buffer));
	return buffer;
}

function buildWavFromFloat32(buffers, inSampleRate, outSampleRate) {
	const merged = mergeFloat32Arrays(buffers);
	const down = downsampleFloat32(merged, inSampleRate, outSampleRate);
	const pcm16 = floatTo16BitPCM(down);
	const wav = encodeWAV(pcm16, outSampleRate);
	return new Blob([new Uint8Array(wav)], { type: 'audio/wav' });
}

async function uploadWav(blob) {
	setState('Transcribing…');
	const form = new FormData();
	form.append('file', blob, 'command.wav');
	const res = await fetch('/api/upload-audio', { method: 'POST', body: form });
	const data = await res.json();
	if (!res.ok) { alert(data.error || 'Error'); setState('Ready'); return; }
	// Always show what was transcribed
	youSaid.textContent = data.transcription || '—';
	if (wakeToggle.checked) {
		// Gate by wake word: only forward when wake word is present
		const ww = (wakeWordInput.value || 'hey nova').toLowerCase();
		const said = (data.transcription || '').toLowerCase();
		if (!said.includes(ww)) { setState('Ready'); return; }
	}
	displayResult(data);
	if (continuousToggle.checked && wakeToggle.checked) {
		// After action, re-arm listening
		startRecording();
	}
}

micBtn.addEventListener('click', () => {
	if (recordingActive) stopRecording(); else startRecording();
});
micBtn.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') micBtn.click(); });

document.querySelectorAll('[data-cmd]').forEach(btn => {
	btn.addEventListener('click', async () => {
		const text = btn.getAttribute('data-cmd');
		youSaid.textContent = text;
		await sendText(text);
	});
});

applyLangBtn.addEventListener('click', async () => {
	await fetch('/api/language', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ stt_lang: sttLangSel.value, tts_lang: ttsLangSel.value }) });
});

async function sendText(text) {
	setState('Thinking…');
	assistantSays.textContent = '';
	const res = await fetch('/api/command', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
	const data = await res.json();
	if (!res.ok) { alert(data.error || 'Error'); setState('Ready'); return; }
	displayResult(data);
}

function displayResult(data) {
	youSaid.textContent = data.transcription || '—';
	assistantSays.textContent = data.response_text || '—';
	if (data.audio_data_url) replyAudio.src = data.audio_data_url;
	setState('Ready');
}

fileInput.addEventListener('change', async () => {
	const file = fileInput.files[0];
	if (!file) return;
	setState('Uploading…');
	const form = new FormData();
	form.append('file', file);
	const res = await fetch('/api/upload-audio', { method: 'POST', body: form });
	const data = await res.json();
	if (!res.ok) { alert(data.error || 'Error'); setState('Ready'); return; }
	displayResult(data);
}); 