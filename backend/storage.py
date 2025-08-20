import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from backend import config
from backend.utils import sanitize_filename

REMINDERS_MEM: List[Dict[str, Any]] = []
FILES_DIR = os.path.join(config.DATA_DIR, "files")
os.makedirs(FILES_DIR, exist_ok=True)


def _ensure_db():
	if not config.USE_SQLITE:
		return
	dir_path = os.path.dirname(config.SQLITE_DB_PATH)
	os.makedirs(dir_path, exist_ok=True)
	conn = sqlite3.connect(config.SQLITE_DB_PATH)
	cur = conn.cursor()
	cur.execute(
		"""
		CREATE TABLE IF NOT EXISTS reminders (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			what TEXT NOT NULL,
			when_ts INTEGER NOT NULL,
			created_ts INTEGER NOT NULL
		)
		"""
	)
	conn.commit()
	conn.close()


_ensure_db()


def add_reminder(what: str, when_ts: int) -> Dict[str, Any]:
	created_ts = int(datetime.utcnow().timestamp())
	if config.USE_SQLITE:
		conn = sqlite3.connect(config.SQLITE_DB_PATH)
		cur = conn.cursor()
		cur.execute("INSERT INTO reminders (what, when_ts, created_ts) VALUES (?, ?, ?)", (what, when_ts, created_ts))
		conn.commit()
		rem_id = cur.lastrowid
		conn.close()
		return {"id": rem_id, "what": what, "when_ts": when_ts, "created_ts": created_ts}
	else:
		rem_id = (REMINDERS_MEM[-1]["id"] + 1) if REMINDERS_MEM else 1
		rem = {"id": rem_id, "what": what, "when_ts": when_ts, "created_ts": created_ts}
		REMINDERS_MEM.append(rem)
		return rem


def list_reminders() -> List[Dict[str, Any]]:
	if config.USE_SQLITE:
		conn = sqlite3.connect(config.SQLITE_DB_PATH)
		cur = conn.cursor()
		cur.execute("SELECT id, what, when_ts, created_ts FROM reminders ORDER BY when_ts ASC")
		rows = cur.fetchall()
		conn.close()
		return [
			{"id": r[0], "what": r[1], "when_ts": r[2], "created_ts": r[3]}
			for r in rows
		]
	else:
		return sorted(REMINDERS_MEM, key=lambda r: r["when_ts"]) 


def save_text_file(content: str, filename: Optional[str] = None) -> str:
	"""Save content to a sanitized .txt file and return the full path."""
	if not filename:
		stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
		filename = f"note_{stamp}.txt"
	filename = sanitize_filename(filename)
	if not filename.lower().endswith(".txt"):
		filename += ".txt"
	path = os.path.join(FILES_DIR, filename)
	with open(path, "w", encoding="utf-8") as f:
		f.write(content or "")
	return path 