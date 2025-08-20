import re
from datetime import datetime, timedelta
from typing import Optional


def sanitize_filename(name: str) -> str:
	name = (name or "").strip()
	name = re.sub(r"[\\/:*?\"<>|]", "_", name)
	name = re.sub(r"\s+", "_", name)
	return name or "untitled"


def parse_reminder_time(in_minutes: Optional[str], at_time: Optional[str], am_pm: Optional[str]) -> Optional[int]:
	"""
	Return a UTC timestamp (int) when the reminder should trigger.
	Supports relative minutes or local time today/tomorrow if time has already passed.
	"""
	now = datetime.now()
	if in_minutes:
		try:
			mins = int(in_minutes)
			return int((now + timedelta(minutes=mins)).timestamp())
		except ValueError:
			return None
	if at_time:
		try:
			h, m = at_time.split(":")
			h = int(h)
			m = int(m)
			if am_pm:
				ap = am_pm.lower()
				if ap == "pm" and h < 12:
					h += 12
				if ap == "am" and h == 12:
					h = 0
			sched = now.replace(hour=h, minute=m, second=0, microsecond=0)
			if sched <= now:
				sched += timedelta(days=1)
			return int(sched.timestamp())
		except Exception:
			return None
	return None 