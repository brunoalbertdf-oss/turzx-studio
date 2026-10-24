"""Skins prontas e telas prontas (paisagem 800x480).

Skin = cores + fontes + decoração de fundo. Trocar a skin muda o visual de todas as telas
que a usam, sem mexer no layout. As decorações são desenhadas em código (decor.py): nenhuma
arte, personagem ou logo de franquia é incluído.

Nas telas, use "$font_title" e "$font_num" como fonte para seguir a skin.
"""
import copy


def T(text, x, y, w, h, size=24, color="$text", font="segoeui.ttf", align="left", **kw):
    return {"type": "text", "text": text, "x": x, "y": y, "w": w, "h": h, "size": size, "color": color,
            "font": font, "align": align, **kw}


def P(x, y, w, h, **kw):
    return {"type": "panel", "x": x, "y": y, "w": w, "h": h, "fill": "$panel", "radius": 16, **kw}


def D(style, x, y, w, h, color, color2=None, **kw):
    return {"type": "deco", "style": style, "x": x, "y": y, "w": w, "h": h, "color": color,
            "color2": color2 or color, **kw}


BG = {"type": "gradient", "color1": "$bg1", "color2": "$bg2", "direction": "diagonal"}
TITLE, NUM = "$font_title", "$font_num"


# ---------------------------------------------------------------- telas prontas

def dashboard(name="Painel completo"):
    """Relógio, tempo, CPU e GPU com fabricante, FPS, RAM e HDs."""
    w = [
        T("{time}", 24, 8, 320, 70, 60, font=TITLE),
        T("{weekday}, {day} {month}", 28, 74, 330, 26, 18, "$muted"),
        {"type": "weather_icon", "x": 600, "y": 12, "w": 64, "h": 60, "color": "$text", "color2": "$accent"},
        T("{weather_temp}°", 664, 10, 116, 64, 44, font=NUM, align="right"),
        T("{weather_city} · {weather_desc}", 380, 74, 400, 26, 16, "$muted", align="right"),
        # CPU
        P(16, 106, 376, 192),
        {"type": "brand", "device": "cpu", "x": 30, "y": 116, "w": 350, "h": 30, "color": "$text"},
        {"type": "gauge", "value": "cpu_percent", "x": 26, "y": 154, "w": 136, "h": 136, "color": "$accent",
         "bg": "#ffffff1a", "label": "CPU", "warn_at": 90, "font": NUM},
        T("{cpu_temp}°C", 172, 158, 206, 40, 32, font=NUM),
        T("{cpu_freq} MHz · {cpu_cores}", 172, 198, 206, 24, 15, "$muted"),
        {"type": "graph", "value": "cpu_percent", "x": 172, "y": 230, "w": 206, "h": 56, "color": "$accent",
         "max": 100},
        # GPU
        P(408, 106, 376, 192),
        {"type": "brand", "device": "gpu", "x": 422, "y": 116, "w": 350, "h": 30, "color": "$text"},
        {"type": "gauge", "value": "gpu_percent", "x": 418, "y": 154, "w": 136, "h": 136, "color": "$accent2",
         "bg": "#ffffff1a", "label": "GPU", "warn_at": 90, "font": NUM},
        T("{gpu_temp:.0f}°C", 564, 158, 206, 40, 32, font=NUM),
        T("{gpu_power} W · VRAM {gpu_mem_used}/{gpu_mem_total} GB", 564, 198, 210, 24, 15, "$muted"),
        {"type": "graph", "value": "gpu_temp", "x": 564, "y": 230, "w": 206, "h": 56, "color": "$accent2",
         "min": 30, "max": 90},
        # FPS
        P(16, 310, 236, 156),
        T("{fps}", 16, 318, 236, 84, 72, "$accent", font=TITLE, align="center"),
        T("FPS", 16, 398, 236, 26, 18, "$muted", font=NUM, align="center"),
        T("{fps_app}", 24, 426, 220, 28, 15, "$muted", align="center"),
        # RAM e HDs
        P(264, 310, 520, 156),
        T("RAM  {ram_used} / {ram_total} GB", 280, 318, 300, 26, 17, font=NUM),
        T("{ram_percent:.0f}%", 600, 318, 168, 26, 17, "$muted", align="right"),
        {"type": "bar", "value": "ram_percent", "x": 280, "y": 348, "w": 488, "h": 10, "color": "$accent2",
         "warn_at": 90},
        {"type": "drives", "x": 280, "y": 368, "w": 488, "h": 92, "max": 3, "size": 15, "bar": "$accent",
         "muted": "$muted", "color": "$text"},
    ]
    return {"name": name, "duration": 20, "enabled": True, "background": dict(BG), "widgets": w}


def clock_screen(name="Relógio e tempo"):
    """Relógio grande, previsão do tempo e um espaço para o GIF do usuário."""
    w = [
        P(24, 24, 300, 300),
        {"type": "media", "file": "", "x": 32, "y": 32, "w": 284, "h": 284, "fit": "cover", "radius": 12,
         "placeholder": "Seu GIF aqui"},
        T("{time}", 340, 30, 440, 130, 120, font=TITLE, align="center"),
        T("{weekday}, {date}", 340, 160, 440, 34, 24, "$muted", align="center"),
        {"type": "weather_icon", "x": 380, "y": 206, "w": 110, "h": 100, "color": "$text", "color2": "$accent"},
        T("{weather_temp}°", 500, 206, 160, 100, 72, font=TITLE),
        T("{weather_desc}", 640, 224, 150, 30, 18, "$accent"),
        T("{weather_city}", 640, 256, 150, 30, 16, "$muted"),
        P(24, 340, 752, 124),
        {"type": "forecast", "x": 40, "y": 346, "w": 720, "h": 112, "days": 5, "size": 17, "color": "$text",
         "muted": "$muted", "icon_color": "$text", "icon_color2": "$accent"},
    ]
    return {"name": name, "duration": 12, "enabled": True, "background": dict(BG), "widgets": w}


LAYOUTS = {"dashboard": ("Painel completo", "Relógio, tempo, CPU/GPU com fabricante, FPS, RAM e HDs.", dashboard),
           "clock": ("Relógio e tempo", "Relógio grande, previsão de 5 dias e espaço para um GIF.", clock_screen)}


# ---------------------------------------------------------------- skins prontas

def _s(colors, title="segoeuib.ttf", num="segoeuib.ttf", decor=()):
    return {**colors, "font_title": title, "font_num": num, "decor": list(decor)}


SKIN_PACKS = [
    {"name": "Neon Noite", "inspired": "", "description": "Azul-noite e roxo com destaques ciano e rosa.",
     "skin": _s({"bg1": "#0e1430", "bg2": "#3a1250", "accent": "#00dcff", "accent2": "#ff4fa0", "text": "#f0f2ff",
                 "muted": "#9aa3cc", "panel": "#ffffff14", "warn": "#ff5050"})},
    {"name": "Saiyajin", "inspired": "Dragon Ball Z", "description": "Laranja e azul-escuro, explosão de energia e aura dourada.",
     "skin": _s({"bg1": "#2a0e00", "bg2": "#0a1a4a", "accent": "#ff8c00", "accent2": "#ffd400", "text": "#fff6e8",
                 "muted": "#ffcf9e", "panel": "#00000070", "warn": "#ff2b2b"}, "impact.ttf", "impact.ttf",
                [D("rays", 0, 0, 800, 480, "#ff8c001c", "#ffd4000c", count=32, cx=0.9, cy=0.05),
                 D("glow", 520, -120, 400, 300, "#ffd40066")])},
    {"name": "Super Saiyajin Blue", "inspired": "Dragon Ball Super", "description": "Azul elétrico, brilho de aura e estrelas.",
     "skin": _s({"bg1": "#00122e", "bg2": "#06306b", "accent": "#3fd0ff", "accent2": "#b0f4ff", "text": "#ffffff",
                 "muted": "#9fd8ff", "panel": "#00000060", "warn": "#ff4d6d"}, "seguibl.ttf", "seguibl.ttf",
                [D("glow", -100, 200, 500, 400, "#3fd0ff55"), D("glow", 500, -150, 450, 350, "#b0f4ff40"),
                 D("stars", 0, 0, 800, 480, "#b0f4ff70", "#3fd0ff90", count=50)])},
    {"name": "Esferas do Dragão", "inspired": "Dragon Ball", "description": "Noite verde, céu estrelado e esferas de cristal nos cantos.",
     "skin": _s({"bg1": "#06140c", "bg2": "#14361d", "accent": "#ffa21f", "accent2": "#ff5a1f", "text": "#fffbe6",
                 "muted": "#c9e6b8", "panel": "#00000080", "warn": "#ff3030"}, "arialbd.ttf", "arialbd.ttf",
                [D("stars", 0, 0, 800, 480, "#fffbe660", "#ffa21f80", count=45, seed=12),
                 D("orb", -30, 390, 110, 110, "#ffa21f", "#d4161b", count=4, opacity=0.45),
                 D("orb", 730, -35, 100, 100, "#ffa21f", "#d4161b", count=1, opacity=0.45)])},
    {"name": "Ninja da Folha", "inspired": "Naruto", "description": "Laranja e preto com um grande redemoinho.",
     "skin": _s({"bg1": "#140a03", "bg2": "#4a1d00", "accent": "#ff7a00", "accent2": "#2e7dff", "text": "#fff3e0",
                 "muted": "#ffbf80", "panel": "#00000070", "warn": "#ff2b2b"}, "impact.ttf", "impact.ttf",
                [D("spiral", 470, -60, 420, 420, "#ff7a0028", "#ff7a0040", count=4, thickness=14)])},
    {"name": "Tático", "inspired": "Counter-Strike 2", "description": "HUD tático escuro, laranja e azul de equipe, grade.",
     "skin": _s({"bg1": "#0b0e12", "bg2": "#1b232c", "accent": "#f5a623", "accent2": "#5aa9e6", "text": "#e8edf2",
                 "muted": "#8a97a6", "panel": "#ffffff0d", "warn": "#ff4040"}, "bahnschrift.ttf", "bahnschrift.ttf",
                [D("grid", 0, 0, 800, 480, "#ffffff08", "#f5a62318", step=20, count=5)])},
    {"name": "Operações", "inspired": "Call of Duty", "description": "Verde militar, camuflagem e linhas de varredura.",
     "skin": _s({"bg1": "#0a0c08", "bg2": "#2a2f1f", "accent": "#c9d36a", "accent2": "#d7c58a", "text": "#eeeadf",
                 "muted": "#a39f8a", "panel": "#00000070", "warn": "#e04040"}, "impact.ttf", "consola.ttf",
                [D("camo", 0, 0, 800, 480, "#3b4226a0", "#1b1f12a0", count=80),
                 D("scanlines", 0, 0, 800, 480, "#00000030", step=3)])},
    {"name": "Liberty", "inspired": "GTA IV", "description": "Cidade à noite em sépia, prédios com janelas acesas.",
     "skin": _s({"bg1": "#14140f", "bg2": "#3b3a2e", "accent": "#e8d8a0", "accent2": "#9bb7c9", "text": "#f2efe6",
                 "muted": "#a8a596", "panel": "#00000070", "warn": "#d9534f"}, "impact.ttf", "arialbd.ttf",
                [D("glow", 150, 200, 600, 400, "#e8d8a030"),
                 D("skyline", 0, 330, 800, 150, "#0c0c09c0", "#e8d8a060", seed=8)])},
    {"name": "Festival", "inspired": "Forza Horizon", "description": "Rosa e amarelo, faixas de corrida e quadriculado.",
     "skin": _s({"bg1": "#14002b", "bg2": "#5a0a5e", "accent": "#ff2e88", "accent2": "#ffb800", "text": "#ffffff",
                 "muted": "#ffc7e3", "panel": "#0000005c", "warn": "#ff3b3b"}, "seguibl.ttf", "bahnschrift.ttf",
                [D("stripes", 380, 0, 420, 110, "#ff2e8870", "#ffb80070", count=3, thickness=22, cx=0.3),
                 D("speedlines", 0, 0, 800, 480, "#ffffff10", "#ff2e8820", count=40, seed=6),
                 D("checker", 0, 0, 800, 6, "#ffffffcc", "#000000cc", step=6)])},
]


def builtin_skins():
    return {p["name"]: copy.deepcopy(p["skin"]) for p in SKIN_PACKS}


def catalog():
    return [{k: p[k] for k in ("name", "inspired", "description")} for p in SKIN_PACKS]


def pack(name):
    return next((p for p in SKIN_PACKS if p["name"] == name), None)
