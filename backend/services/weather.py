import requests
from typing import Optional, Tuple

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


def geocode_city(city: str) -> Optional[Tuple[float, float, str]]:
	params = {"name": city, "count": 1}
	resp = requests.get(GEOCODE_URL, params=params, timeout=10)
	resp.raise_for_status()
	data = resp.json()
	if not data.get("results"):
		return None
	res = data["results"][0]
	return (res["latitude"], res["longitude"], res.get("name", city))


def get_current_weather_summary(city: str) -> str:
	geo = geocode_city(city)
	if not geo:
		return f"I couldn't find weather for {city}."
	lat, lon, canonical = geo
	params = {
		"latitude": lat,
		"longitude": lon,
		"current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature"],
	}
	resp = requests.get(WEATHER_URL, params=params, timeout=10)
	resp.raise_for_status()
	data = resp.json()
	current = data.get("current") or {}
	temp = current.get("temperature_2m")
	hum = current.get("relative_humidity_2m")
	apparent = current.get("apparent_temperature")
	if temp is None:
		return f"Weather data for {canonical} is currently unavailable."
	return f"In {canonical}, it's {temp}°C (feels like {apparent}°C) with humidity {hum}%." 