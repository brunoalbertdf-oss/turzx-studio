"""Configuração inicial: skins e três telas de exemplo (paisagem 800x480)."""
from themes import builtin_skins, dashboard

SKINS = {**builtin_skins(), **{
    "Verde Matrix": {"bg1": "#020a04", "bg2": "#0b2a12", "accent": "#39ff6a", "accent2": "#c6ff3a",
                     "text": "#e8ffe8", "muted": "#6fae7c", "panel": "#39ff6a14", "warn": "#ffcc00"},
    "Pôr do Sol": {"bg1": "#2b0f2e", "bg2": "#b8452a", "accent": "#ffb347", "accent2": "#ff5e78",
                   "text": "#fff4e6", "muted": "#e0b8a8", "panel": "#00000033", "warn": "#ffffff"},
    "Gelo": {"bg1": "#e8f0fa", "bg2": "#b9cbe6", "accent": "#1f6fd1", "accent2": "#7a4fd8",
             "text": "#132033", "muted": "#4a5c78", "panel": "#ffffff88", "warn": "#d12f2f"},
    "RTX Verde": {"bg1": "#0a0a0a", "bg2": "#1a1f12", "accent": "#76b900", "accent2": "#e0e0e0",
                  "text": "#ffffff", "muted": "#8c8c8c", "panel": "#ffffff10", "warn": "#ff3b3b"},
}}


def T(text, x, y, w, h, size=24, color="$text", font="segoeui.ttf", align="left", **kw):
    return {"type": "text", "text": text, "x": x, "y": y, "w": w, "h": h, "size": size, "color": color,
            "font": font, "align": align, **kw}


def P(x, y, w, h, **kw):
    return {"type": "panel", "x": x, "y": y, "w": w, "h": h, "fill": "$panel", "radius": 18, **kw}


BG = {"type": "gradient", "color1": "$bg1", "color2": "$bg2", "direction": "diagonal"}

SYSTEM = dashboard("Sistema")

WEATHER = {
    "name": "Tempo", "duration": 12, "enabled": True, "background": dict(BG),
    "widgets": [
        T("{weather_city}", 40, 24, 500, 50, 36, font="segoeuib.ttf"),
        T("{time}", 560, 24, 200, 50, 36, "$muted", align="right"),
        {"type": "weather_icon", "x": 40, "y": 90, "w": 200, "h": 180, "color": "$text", "color2": "$accent"},
        T("{weather_temp}°", 250, 90, 260, 130, 110, font="segoeuib.ttf"),
        T("{weather_desc}", 256, 220, 300, 40, 26, "$accent"),
        T("Sensação {weather_feels}°", 540, 110, 230, 34, 22, "$muted", align="right"),
        T("Umidade {weather_hum}%", 540, 150, 230, 34, 22, "$muted", align="right"),
        T("Vento {weather_wind} km/h", 540, 190, 230, 34, 22, "$muted", align="right"),
        T("Chuva {weather_rain}%", 540, 230, 230, 34, 22, "$muted", align="right"),
        P(24, 290, 752, 170),
        {"type": "forecast", "x": 40, "y": 300, "w": 720, "h": 150, "days": 5, "size": 20, "color": "$text",
         "muted": "$muted", "icon_color": "$text", "icon_color2": "$accent"},
    ],
}

MEDIA = {
    "name": "Mídia", "duration": 15, "enabled": True, "background": {"type": "color", "color1": "$bg1"},
    "widgets": [
        P(24, 24, 432, 432),
        {"type": "media", "file": "demo.gif", "x": 80, "y": 80, "w": 320, "h": 320, "fit": "cover", "fps": 10,
         "radius": 160},
        T("{time}", 500, 30, 280, 80, 64, font="segoeuib.ttf", align="center"),
        T("{weekday}", 500, 110, 280, 30, 22, "$muted", align="center"),
        T("CPU {cpu_percent:.0f}%", 510, 190, 260, 30, 22, "$accent"),
        {"type": "bar", "value": "cpu_percent", "x": 510, "y": 224, "w": 260, "h": 10, "color": "$accent"},
        T("GPU {gpu_percent:.0f}%", 510, 260, 260, 30, 22, "$accent2"),
        {"type": "bar", "value": "gpu_percent", "x": 510, "y": 294, "w": 260, "h": 10, "color": "$accent2"},
        T("RAM {ram_percent:.0f}%", 510, 330, 260, 30, 22, "$accent"),
        {"type": "bar", "value": "ram_percent", "x": 510, "y": 364, "w": 260, "h": 10, "color": "$accent"},
        T("{weather_temp}° · {weather_desc}", 500, 410, 280, 40, 22, "$muted", align="center"),
    ],
}

CONFIG = {
    "settings": {"city": "São Paulo", "brightness": 60, "orientation": "landscape", "carousel": True,
                 "max_fps": 10, "skin": "Neon Noite", "port": "", "ffmpeg": "", "transition": "fade",
                 "autostart": False,
                 "lhm_url": "http://127.0.0.1:8085/data.json"},
    "skins": SKINS,
    "screens": [SYSTEM, WEATHER, MEDIA],
}
