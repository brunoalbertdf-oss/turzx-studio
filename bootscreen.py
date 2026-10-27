"""Tela de inicialização: roda antes do login (tarefa do Windows "ao iniciar o sistema", como SYSTEM).

Acende a tela com a skin do usuário, relógio, data e uso de CPU/RAM enquanto o Windows inicia.
Quando o TURZX Studio normal abre (depois do login), libera a tela e fecha: o app normal assume
sem a tela apagar no meio.
"""
import json
import os
import time
import urllib.request
from datetime import datetime

import psutil

import renderer
from engine import ROTATIONS, dirty_rects
from media import MediaCache
from paths import CONFIG_PATH, LOG_PATH, MEDIA_DIR
from sensors import DAYS, MONTHS
from turzx_screen import TurzxScreen

APP_URL = "http://127.0.0.1:8777/api/status"
MAX_HOURS = 12  # se ninguém fizer login, não fica rodando para sempre


def _log(msg):
    try:
        with open(LOG_PATH, "a", encoding="utf8") as f:
            f.write(f"{time.ctime()} tela de inicialização: {msg}\n")
    except OSError:
        pass


def _app_running():
    try:
        urllib.request.urlopen(APP_URL, timeout=0.5)
        return True
    except Exception:
        return False


def layout():
    T = lambda text, y, h, size, color, font: {"type": "text", "text": text, "x": 0, "y": y, "w": 800, "h": h,
                                                 "size": size, "color": color, "font": font, "align": "center"}
    return {"background": {"type": "gradient", "color1": "$bg1", "color2": "$bg2", "direction": "diagonal"},
            "widgets": [
                T("{time}", 70, 150, 150, "$text", "$font_title"),
                T("{weekday}, {day} {month}", 220, 40, 30, "$muted", "$font"),
                T("Iniciando o Windows…", 290, 34, 22, "$accent", "$font"),
                {"type": "bar", "value": "cpu_percent", "x": 200, "y": 350, "w": 400, "h": 8, "color": "$accent"},
                T("CPU {cpu_percent:.0f}%   ·   RAM {ram_percent:.0f}%", 364, 30, 18, "$muted", "$font"),
                T("TURZX Studio · by TorcZera", 438, 30, 16, "$muted", "$font"),
            ]}


def run():
    if _app_running():
        return
    try:
        with open(CONFIG_PATH, encoding="utf8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        cfg = {"settings": {}, "skins": {}}
    st = cfg.get("settings", {})
    skin = cfg.get("skins", {}).get(st.get("skin")) or {"bg1": "#0e1430", "bg2": "#3a1250", "accent": "#00dcff",
                                                          "text": "#f0f2ff", "muted": "#9aa3cc"}
    size, rot = ROTATIONS.get(st.get("orientation"), ROTATIONS["landscape"])
    screen = layout()
    media = MediaCache(MEDIA_DIR)
    psutil.cpu_percent()

    lcd, deadline = None, time.time() + 120
    while lcd is None:  # no início do boot a porta USB pode ainda não existir
        if _app_running() or time.time() > deadline:
            return
        try:
            lcd = TurzxScreen(st.get("port") or None)
            lcd.hello()
        except Exception:
            lcd = None
            time.sleep(1)
    _log("conectada, mostrando a tela de inicialização")
    old = None
    end = time.time() + MAX_HOURS * 3600
    try:
        lcd.stop_media()
        while time.time() < end and not _app_running():
            now = datetime.now()
            values = {"time": now.strftime("%H:%M"), "weekday": DAYS[now.weekday()], "day": now.day,
                      "month": MONTHS[now.month - 1], "cpu_percent": psutil.cpu_percent(),
                      "ram_percent": psutil.virtual_memory().percent}
            frame = renderer.render(screen, size, renderer.Context(values, {}, [], skin, media))
            native = frame.rotate(rot, expand=True) if rot else frame
            if old is None:
                lcd.show_full(native)
                lcd.set_brightness(int(st.get("brightness", 60)))  # acende já com a imagem
            else:
                for x, y, w, h in dirty_rects(old, native):
                    lcd.show_region(native.crop((x, y, x + w, y + h)), x, y)
            old = native
            time.sleep(1)
        _log("o app abriu: passando a tela para ele")
    except Exception as e:
        _log(f"erro: {e}")
    finally:
        lcd.close()
