import re
from typing import Dict, Any

INTENTS = {
	"greet": re.compile(r"\b(hi|hello|hey)\b", re.I),
	"bye": re.compile(r"\b(bye|goodbye|see you)\b", re.I),
	"time": re.compile(r"\btime\b", re.I),
	"date": re.compile(r"\b(date|day|today)\b", re.I),
	"open_app": re.compile(r"\b(open|launch|start)\s+(?P<app>[\w .-]+)\b", re.I),
	"close_app": re.compile(r"\b(close|quit|exit)\s+(?P<app>[\w .-]+)\b", re.I),
	"open_path": re.compile(r"\b(open|launch|start)\s+(?P<target>(?:[a-zA-Z]:\\[\\\w .-]+|https?://[^\s]+|www\.[^\s]+|/[^\s]+))", re.I),
	"type_text": re.compile(r"\b(type|write|dictate)\s+(?P<text>.+)$", re.I),
	"save_as": re.compile(r"\bsave\s+(?:as\s+)?(?P<filename>[\w .-]+)\b", re.I),
	"save_text": re.compile(r"\bsave(?:\s+(?P<content>.+?))?(?:\s+as\s+(?P<filename>[\w .-]+))?\b", re.I),
	"reminder_create": re.compile(r"\bremind\s+me\s+(?P<what>.+?)\s+(?:in\s+(?P<in_minutes>\d+)\s+minutes|at\s+(?P<at_time>\d{1,2}:\d{2})(?:\s*(?P<am_pm>am|pm))?)\b", re.I),
	"weather_query": re.compile(r"\b(weather|forecast)(?:\s+in\s+(?P<city>[\w .-]+))?\b", re.I),
	"set_language": re.compile(r"\b(set|switch)\s+(?:language|lang)\s+to\s+(?P<lang>[a-z]{2}(?:-[A-Z]{2})?)\b", re.I),
}

APP_ALIASES = {
	"notepad": ["notepad", "note pad"],
	"calculator": ["calculator", "calc"],
	"browser": ["browser", "chrome", "edge", "firefox"],
	"vscode": ["vs code", "vscode", "code"],
	"whatsapp": ["whatsapp", "whats app"],
	"instagram": ["instagram"],
}


def normalize_app(name: str) -> str:
	name_l = name.strip().lower()
	for canonical, variants in APP_ALIASES.items():
		if name_l == canonical or any(name_l == v for v in variants):
			return canonical
	return name_l


def interpret(text: str) -> Dict[str, Any]:
	text = (text or "").strip()
	if not text:
		return {"intent": "none", "entities": {}}
	for intent, pattern in INTENTS.items():
		m = pattern.search(text)
		if m:
			entities = {k: v for k, v in (m.groupdict() or {}).items() if v}
			if "app" in entities:
				entities["app"] = normalize_app(entities["app"])
			if intent == "save_text" and "content" in entities:
				entities["content"] = entities["content"].strip()
			return {"intent": intent, "entities": entities}
	return {"intent": "none", "entities": {}} 