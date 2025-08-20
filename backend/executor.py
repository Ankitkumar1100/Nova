import os
import sys
import platform
import subprocess
import webbrowser
from datetime import datetime
from typing import Dict, Any, Optional
import psutil

from backend.storage import save_text_file, add_reminder
from backend.services.weather import get_current_weather_summary
from backend.utils import parse_reminder_time

OS_NAME = platform.system().lower()

APP_COMMANDS = {
	"windows": {
		"notepad": ["cmd", "/c", "start", "", "notepad"],
		"calculator": ["cmd", "/c", "start", "", "calc"],
		"browser": ["cmd", "/c", "start", "", ""],
		"vscode": ["cmd", "/c", "code"],
		"whatsapp": ["cmd", "/c", "start", "", "https://web.whatsapp.com"],
		"instagram": ["cmd", "/c", "start", "", "https://instagram.com"],
	},
	"darwin": {
		"notepad": ["open", "-a", "TextEdit"],
		"calculator": ["open", "-a", "Calculator"],
		"browser": ["open", "-a", "Safari"],
		"vscode": ["open", "-a", "Visual Studio Code"],
		"whatsapp": ["open", "https://web.whatsapp.com"],
		"instagram": ["open", "https://instagram.com"],
	},
	"linux": {
		"notepad": ["gedit"],
		"calculator": ["gnome-calculator"],
		"browser": ["xdg-open", "https://www.google.com"],
		"vscode": ["code"],
		"whatsapp": ["xdg-open", "https://web.whatsapp.com"],
		"instagram": ["xdg-open", "https://instagram.com"],
	},
}

PROCESS_NAMES = {
	"notepad": ["notepad.exe", "TextEdit"],
	"calculator": ["Calculator.exe", "Calculator", "gnome-calculator"],
	"browser": ["chrome.exe", "msedge.exe", "firefox.exe", "Safari", "chrome", "firefox"],
	"vscode": ["Code.exe", "code"],
}


def _platform_key() -> str:
	if OS_NAME.startswith("win"):
		return "windows"
	if OS_NAME == "darwin":
		return "darwin"
	return "linux"


def open_application(app: str) -> str:
	key = _platform_key()
	cmd = APP_COMMANDS.get(key, {}).get(app)
	if not cmd:
		return f"I don't know how to open {app} on this OS."
	try:
		if key == "windows" and app == "browser":
			subprocess.Popen(["cmd", "/c", "start", "", "about:blank"], shell=False)
		else:
			subprocess.Popen(cmd, shell=False)
		return f"Opening {app}."
	except Exception as exc:
		return f"Failed to open {app}: {exc}"


def open_path_or_url(target: str) -> str:
	try:
		if target.startswith("http://") or target.startswith("https://") or target.startswith("www."):
			if target.startswith("www."):
				target = "https://" + target
			webbrowser.open(target)
			return f"Opening {target}."
		if os.path.exists(target):
			if OS_NAME.startswith("win"):
				subprocess.Popen(["cmd", "/c", "start", "", target])
			elif OS_NAME == "darwin":
				subprocess.Popen(["open", target])
			else:
				subprocess.Popen(["xdg-open", target])
			return f"Opening {target}."
		return f"Path not found: {target}"
	except Exception as exc:
		return f"Failed to open {target}: {exc}"


def _type_text_windows(text: str) -> str:
	try:
		from pywinauto import Application
		import pyautogui, pyperclip, time
		# Connect to the active window and send clipboard paste (more reliable for Unicode)
		pyperclip.copy(text)
		# Try Notepad edit control; otherwise send Ctrl+V to active window
		try:
			app = Application(backend="uia").connect(active_only=True, timeout=3)
			win = app.top_window()
			win.set_focus()
			try:
				edit = win.child_window(control_type="Edit")
				if edit.exists():
					edit.set_focus()
					edit.type_keys("^v", with_spaces=True, pause=0.01)
					return "Typed text into the active editor."
			except Exception:
				pass
		except Exception:
			pass
		pyautogui.hotkey('ctrl', 'v')
		return "Typed text in the active window."
	except Exception as exc:
		return f"Could not type text: {exc}"


def _save_as_windows(filename: str) -> str:
	try:
		from pywinauto import Application
		import pyautogui, time
		# Send Ctrl+S then type filename and Enter
		pyautogui.hotkey('ctrl', 's')
		time.sleep(0.5)
		pyautogui.typewrite(filename, interval=0.02)
		pyautogui.press('enter')
		return f"Saved as {filename}."
	except Exception as exc:
		return f"Could not save: {exc}"


def type_text(text: str) -> str:
	if OS_NAME.startswith("win"):
		return _type_text_windows(text)
	return "Typing into apps is not yet supported on this OS in the demo."


def save_as(filename: str) -> str:
	if OS_NAME.startswith("win"):
		return _save_as_windows(filename)
	return "Save-as automation is not yet supported on this OS in the demo."


def close_application(app: str) -> str:
	targets = PROCESS_NAMES.get(app, [])
	closed_any = False
	for proc in psutil.process_iter(attrs=["name"]):
		try:
			pname = proc.info.get("name") or ""
			if any(t.lower() in pname.lower() for t in targets):
				proc.terminate()
				closed_any = True
		except (psutil.NoSuchProcess, psutil.AccessDenied):
			continue
	return f"Closed {app}." if closed_any else f"Could not find running {app}."


def get_time_response() -> str:
	return f"It's {datetime.now().strftime('%I:%M %p').lstrip('0')}"


def get_date_response() -> str:
	return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"


def save_text(content: str, filename: Optional[str]) -> str:
	path = save_text_file(content or "", filename)
	return f"Saved your text to {os.path.basename(path)}."


def create_reminder(what: str, in_minutes: Optional[str], at_time: Optional[str], am_pm: Optional[str]) -> str:
	when_ts = parse_reminder_time(in_minutes, at_time, am_pm)
	if not when_ts:
		return "I couldn't understand the reminder time. Please say 'in 10 minutes' or 'at 5:30 pm'."
	add_reminder(what, when_ts)
	return "Reminder saved. I'll remember that."


def weather_summary(city: Optional[str]) -> str:
	city = city or "New York"
	return get_current_weather_summary(city)


def execute_intent(intent: str, entities: Dict[str, Any]) -> str:
	if intent == "greet":
		return "Hello! How can I help?"
	if intent == "bye":
		return "Goodbye!"
	if intent == "time":
		return get_time_response()
	if intent == "date":
		return get_date_response()
	if intent == "open_app":
		return open_application(entities.get("app", ""))
	if intent == "open_path":
		return open_path_or_url(entities.get("target", ""))
	if intent == "type_text":
		return type_text(entities.get("text", ""))
	if intent == "save_as":
		return save_as(entities.get("filename", ""))
	if intent == "close_app":
		return close_application(entities.get("app", ""))
	if intent == "save_text":
		return save_text(entities.get("content", ""), entities.get("filename"))
	if intent == "reminder_create":
		return create_reminder(entities.get("what", ""), entities.get("in_minutes"), entities.get("at_time"), entities.get("am_pm"))
	if intent == "weather_query":
		return weather_summary(entities.get("city"))
	if intent == "set_language":
		lang = entities.get("lang")
		return f"Language set to {lang}."
	return "I didn't understand that. Please try again." 