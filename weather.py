"""Tempo via Open-Meteo (gratuito, sem chave). Atualiza a cada 15 minutos."""
import json
import threading
import time
import urllib.parse
import urllib.request

CODES = {0: ("Céu limpo", "sun"), 1: ("Poucas nuvens", "sun_cloud"), 2: ("Parcialmente nublado", "sun_cloud"),
         3: ("Nublado", "cloud"), 45: ("Neblina", "fog"), 48: ("Neblina", "fog"),
         51: ("Garoa", "rain"), 53: ("Garoa", "rain"), 55: ("Garoa forte", "rain"),
         61: ("Chuva fraca", "rain"), 63: ("Chuva", "rain"), 65: ("Chuva forte", "rain"),
         71: ("Neve", "snow"), 73: ("Neve", "snow"), 75: ("Neve forte", "snow"),
         80: ("Pancadas", "rain"), 81: ("Pancadas", "rain"), 82: ("Pancadas fortes", "rain"),
         95: ("Trovoadas", "storm"), 96: ("Trovoadas", "storm"), 99: ("Trovoadas", "storm")}
REFRESH = 15 * 60


def _get(url, params):
    return json.load(urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=10))


class Weather:
    def __init__(self, city):
        self.city = city
        self.values = {}
        self.forecast = []  # [{day, max, min, icon}]
        self._wake = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    def set_city(self, city):
        if city != self.city:
            self.city = city
            self._wake.set()

    def _loop(self):
        while True:
            try:
                self._fetch()
                wait = REFRESH
            except Exception as e:
                print("tempo:", e)
                wait = 60
            self._wake.wait(wait)
            self._wake.clear()

    def _fetch(self):
        place = _get("https://geocoding-api.open-meteo.com/v1/search",
                     {"name": self.city, "count": 1, "language": "pt"})["results"][0]
        d = _get("https://api.open-meteo.com/v1/forecast", {
            "latitude": place["latitude"], "longitude": place["longitude"], "timezone": "auto",
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "forecast_days": 5})
        cur, day = d["current"], d["daily"]
        desc, icon = CODES.get(cur["weather_code"], ("—", "cloud"))
        self.values = {
            "weather_city": place["name"], "weather_temp": round(cur["temperature_2m"]),
            "weather_feels": round(cur["apparent_temperature"]), "weather_hum": cur["relative_humidity_2m"],
            "weather_wind": round(cur["wind_speed_10m"]), "weather_desc": desc, "weather_icon": icon,
            "weather_max": round(day["temperature_2m_max"][0]), "weather_min": round(day["temperature_2m_min"][0]),
            "weather_rain": day["precipitation_probability_max"][0] or 0,
        }
        from sensors import DAYS
        self.forecast = []
        for i, date in enumerate(day["time"]):
            wd = time.strptime(date, "%Y-%m-%d").tm_wday
            self.forecast.append({"day": "Hoje" if i == 0 else DAYS[wd][:3],
                                  "max": round(day["temperature_2m_max"][i]),
                                  "min": round(day["temperature_2m_min"][i]),
                                  "icon": CODES.get(day["weather_code"][i], ("", "cloud"))[1]})
