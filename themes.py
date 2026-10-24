"""Temas prontos: paleta (skin) + telas (paisagem 800x480).

Os temas são homenagens de fã feitas só com formas desenhadas em código, cores e fontes do
Windows. Nenhuma arte, personagem ou logo das franquias é incluído; cada tema tem um espaço
"Seu GIF aqui" para o usuário colocar a própria mídia.
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


def dashboard(name, title_font="segoeuib.ttf", num_font="segoeuib.ttf", back=(), front=(), radius=16,
              outline=None):
    """Painel completo: relógio, tempo, CPU e GPU com fabricante, FPS, RAM e HDs."""
    pk = {"radius": radius, **({"outline": outline, "outline_width": 2} if outline else {})}
    w = list(back) + [
        T("{time}", 24, 8, 320, 70, 60, font=title_font),
        T("{weekday}, {day} {month}", 28, 74, 330, 26, 18, "$muted"),
        {"type": "weather_icon", "x": 600, "y": 12, "w": 64, "h": 60, "color": "$text", "color2": "$accent"},
        T("{weather_temp}°", 664, 10, 116, 64, 44, font=num_font, align="right"),
        T("{weather_city} · {weather_desc}", 380, 74, 400, 26, 16, "$muted", align="right"),
        # CPU
        P(16, 106, 376, 192, **pk),
        {"type": "brand", "device": "cpu", "x": 30, "y": 116, "w": 350, "h": 30, "size": 18, "color": "$text"},
        {"type": "gauge", "value": "cpu_percent", "x": 26, "y": 154, "w": 136, "h": 136, "color": "$accent",
         "bg": "#ffffff1a", "label": "CPU", "warn_at": 90, "font": num_font},
        T("{cpu_temp}°C", 172, 158, 206, 40, 32, font=num_font),
        T("{cpu_freq} MHz · {cpu_cores}", 172, 198, 206, 24, 15, "$muted"),
        {"type": "graph", "value": "cpu_percent", "x": 172, "y": 230, "w": 206, "h": 56, "color": "$accent",
         "max": 100},
        # GPU
        P(408, 106, 376, 192, **pk),
        {"type": "brand", "device": "gpu", "x": 422, "y": 116, "w": 350, "h": 30, "size": 18, "color": "$text"},
        {"type": "gauge", "value": "gpu_percent", "x": 418, "y": 154, "w": 136, "h": 136, "color": "$accent2",
         "bg": "#ffffff1a", "label": "GPU", "warn_at": 90, "font": num_font},
        T("{gpu_temp:.0f}°C", 564, 158, 206, 40, 32, font=num_font),
        T("{gpu_power} W · VRAM {gpu_mem_used}/{gpu_mem_total} GB", 564, 198, 210, 24, 15, "$muted"),
        {"type": "graph", "value": "gpu_temp", "x": 564, "y": 230, "w": 206, "h": 56, "color": "$accent2",
         "min": 30, "max": 90},
        # FPS
        P(16, 310, 236, 156, **pk),
        T("{fps}", 16, 318, 236, 84, 72, "$accent", font=title_font, align="center"),
        T("FPS", 16, 398, 236, 26, 18, "$muted", font=num_font, align="center"),
        T("{fps_app}", 24, 426, 220, 28, 15, "$muted", align="center"),
        # RAM e HDs
        P(264, 310, 520, 156, **pk),
        T("RAM  {ram_used} / {ram_total} GB", 280, 318, 300, 26, 17, font=num_font),
        T("{ram_percent:.0f}%", 600, 318, 168, 26, 17, "$muted", align="right"),
        {"type": "bar", "value": "ram_percent", "x": 280, "y": 348, "w": 488, "h": 10, "color": "$accent2",
         "warn_at": 90},
        {"type": "drives", "x": 280, "y": 368, "w": 488, "h": 92, "max": 3, "size": 15, "bar": "$accent",
         "muted": "$muted", "color": "$text"},
    ] + list(front)
    return {"name": name, "duration": 20, "enabled": True, "background": dict(BG), "widgets": w}


def clock_screen(name, title_font="segoeuib.ttf", back=(), emblem=None, gif_label="Seu GIF aqui"):
    """Relógio grande, previsão do tempo e um espaço para o GIF do usuário."""
    w = list(back) + [
        P(24, 24, 300, 300),
        {"type": "media", "file": "", "x": 32, "y": 32, "w": 284, "h": 284, "fit": "cover", "radius": 12,
         "placeholder": gif_label},
        T("{time}", 340, 30, 440, 130, 120, font=title_font, align="center"),
        T("{weekday}, {date}", 340, 160, 440, 34, 24, "$muted", align="center"),
        {"type": "weather_icon", "x": 380, "y": 206, "w": 110, "h": 100, "color": "$text", "color2": "$accent"},
        T("{weather_temp}°", 500, 206, 160, 100, 72, font=title_font),
        T("{weather_desc}", 640, 224, 150, 30, 18, "$accent"),
        T("{weather_city}", 640, 256, 150, 30, 16, "$muted"),
        P(24, 340, 752, 124),
        {"type": "forecast", "x": 40, "y": 346, "w": 720, "h": 112, "days": 5, "size": 17, "color": "$text",
         "muted": "$muted", "icon_color": "$text", "icon_color2": "$accent"},
    ]
    if emblem:
        w.append(emblem)
    return {"name": name, "duration": 12, "enabled": True, "background": dict(BG), "widgets": w}


THEMES = [
    {
        "id": "saiyajin", "name": "Saiyajin", "inspired": "Dragon Ball Z",
        "description": "Laranja e azul-escuro, explosão de energia e aura dourada.",
        "skin": {"bg1": "#2a0e00", "bg2": "#0a1a4a", "accent": "#ff8c00", "accent2": "#ffd400", "text": "#fff6e8",
                 "muted": "#ffcf9e", "panel": "#00000070", "warn": "#ff2b2b"},
        "screens": lambda: [
            dashboard("Saiyajin · Sistema", "impact.ttf", "impact.ttf",
                      back=[D("rays", 0, 0, 800, 480, "#ff8c001c", "#ffd4000c", count=32, cx=0.9, cy=0.05),
                            D("glow", 520, -120, 400, 300, "#ffd40066")]),
            clock_screen("Saiyajin · Relógio", "impact.ttf",
                         back=[D("rays", 0, 0, 800, 480, "#ff8c0020", "#00000000", count=28, cx=0.2, cy=0.35),
                               D("speedlines", 330, 0, 470, 330, "#ffd40030", "#ffffff18", count=26)]),
        ],
    },
    {
        "id": "super_blue", "name": "Super Saiyajin Blue", "inspired": "Dragon Ball Super",
        "description": "Azul elétrico, brilho de aura e estrelas.",
        "skin": {"bg1": "#00122e", "bg2": "#06306b", "accent": "#3fd0ff", "accent2": "#b0f4ff", "text": "#ffffff",
                 "muted": "#9fd8ff", "panel": "#00000060", "warn": "#ff4d6d"},
        "screens": lambda: [
            dashboard("Super Blue · Sistema", "seguibl.ttf", "seguibl.ttf", outline="#3fd0ff55",
                      back=[D("glow", -100, 200, 500, 400, "#3fd0ff55"), D("glow", 500, -150, 450, 350, "#b0f4ff40"),
                            D("stars", 0, 0, 800, 480, "#b0f4ff70", "#3fd0ff90", count=50)]),
            clock_screen("Super Blue · Relógio", "seguibl.ttf",
                         back=[D("glow", 0, 0, 800, 480, "#3fd0ff45"),
                               D("stars", 0, 0, 800, 480, "#ffffff80", "#3fd0ffa0", count=60, seed=4)]),
        ],
    },
    {
        "id": "esferas", "name": "Esferas do Dragão", "inspired": "Dragon Ball",
        "description": "Noite verde, esferas de cristal com estrelas e céu estrelado.",
        "skin": {"bg1": "#06140c", "bg2": "#14361d", "accent": "#ffa21f", "accent2": "#ff5a1f", "text": "#fffbe6",
                 "muted": "#c9e6b8", "panel": "#00000066", "warn": "#ff3030"},
        "screens": lambda: [
            dashboard("Esferas · Sistema", "arialbd.ttf", "arialbd.ttf",
                      back=[D("stars", 0, 0, 800, 480, "#fffbe660", "#ffa21f80", count=45, seed=12)],
                      front=[D("orb", 352, 6, 44, 44, "#ffa21f", "#d4161b", count=1),
                             D("orb", 404, 6, 44, 44, "#ffa21f", "#d4161b", count=4)]),
            clock_screen("Esferas · Relógio", "arialbd.ttf",
                         back=[D("stars", 0, 0, 800, 480, "#fffbe670", "#ffa21f90", count=60, seed=21)],
                         emblem=None),
        ],
    },
    {
        "id": "ninja", "name": "Ninja da Folha", "inspired": "Naruto",
        "description": "Laranja e preto, redemoinho e emblema de folha.",
        "skin": {"bg1": "#140a03", "bg2": "#4a1d00", "accent": "#ff7a00", "accent2": "#2e7dff", "text": "#fff3e0",
                 "muted": "#ffbf80", "panel": "#00000070", "warn": "#ff2b2b"},
        "screens": lambda: [
            dashboard("Ninja · Sistema", "impact.ttf", "impact.ttf",
                      back=[D("spiral", 470, -60, 420, 420, "#ff7a0028", "#ff7a0040", count=4, thickness=14)],
                      front=[D("leaf", 352, 8, 48, 48, "#ff7a00", "#140a03")]),
            clock_screen("Ninja · Relógio", "impact.ttf",
                         back=[D("spiral", 320, 0, 480, 480, "#ff7a0024", "#ff7a0040", count=5, thickness=16)]),
        ],
    },
    {
        "id": "tatico", "name": "Tático", "inspired": "Counter-Strike 2",
        "description": "HUD tático escuro, laranja e azul de equipe, grade e mira.",
        "skin": {"bg1": "#0b0e12", "bg2": "#1b232c", "accent": "#f5a623", "accent2": "#5aa9e6", "text": "#e8edf2",
                 "muted": "#8a97a6", "panel": "#ffffff0d", "warn": "#ff4040"},
        "screens": lambda: [
            dashboard("Tático · Sistema", "bahnschrift.ttf", "bahnschrift.ttf", radius=4, outline="#f5a62340",
                      back=[D("grid", 0, 0, 800, 480, "#ffffff08", "#f5a62318", step=20, count=5)],
                      front=[D("crosshair", 196, 316, 48, 48, "#f5a62390", "#f5a623", thickness=2)]),
            clock_screen("Tático · Relógio", "bahnschrift.ttf",
                         back=[D("hex", 0, 0, 800, 480, "#ffffff0a", "#f5a62312", step=26),
                               D("crosshair", 600, 20, 160, 160, "#5aa9e630", "#f5a62360", thickness=2)],
                         gif_label="Seu clipe aqui"),
        ],
    },
    {
        "id": "operacoes", "name": "Operações", "inspired": "Call of Duty",
        "description": "Verde militar, camuflagem, divisas e linhas de varredura.",
        "skin": {"bg1": "#0a0c08", "bg2": "#2a2f1f", "accent": "#c9d36a", "accent2": "#d7c58a", "text": "#eeeadf",
                 "muted": "#a39f8a", "panel": "#00000070", "warn": "#e04040"},
        "screens": lambda: [
            dashboard("Operações · Sistema", "impact.ttf", "consola.ttf", radius=6,
                      back=[D("camo", 0, 0, 800, 480, "#3b4226a0", "#1b1f12a0", count=80),
                            D("scanlines", 0, 0, 800, 480, "#00000030", step=3)],
                      front=[D("chevrons", 360, 14, 36, 50, "#c9d36a", "#d7c58a", count=3)]),
            clock_screen("Operações · Relógio", "impact.ttf",
                         back=[D("camo", 0, 0, 800, 480, "#3b4226a0", "#1b1f12a0", count=90, seed=2),
                               D("scanlines", 0, 0, 800, 480, "#00000030", step=3)],
                         gif_label="Seu clipe aqui"),
        ],
    },
    {
        "id": "liberty", "name": "Liberty", "inspired": "GTA IV",
        "description": "Cidade à noite em tons sépia, silhueta de prédios com janelas acesas.",
        "skin": {"bg1": "#14140f", "bg2": "#3b3a2e", "accent": "#e8d8a0", "accent2": "#9bb7c9", "text": "#f2efe6",
                 "muted": "#a8a596", "panel": "#00000070", "warn": "#d9534f"},
        "screens": lambda: [
            dashboard("Liberty · Sistema", "impact.ttf", "arialbd.ttf", radius=4,
                      back=[D("glow", 150, 200, 600, 400, "#e8d8a030"),
                            D("skyline", 0, 300, 800, 180, "#0c0c09d0", "#e8d8a070", seed=8)]),
            clock_screen("Liberty · Relógio", "impact.ttf",
                         back=[D("glow", 200, 150, 600, 400, "#e8d8a035"),
                               D("skyline", 0, 250, 800, 230, "#0c0c09e0", "#e8d8a080", seed=3)],
                         gif_label="Seu clipe aqui"),
        ],
    },
    {
        "id": "festival", "name": "Festival", "inspired": "Forza Horizon",
        "description": "Rosa e amarelo vibrantes, faixas de corrida, quadriculado e velocidade.",
        "skin": {"bg1": "#14002b", "bg2": "#5a0a5e", "accent": "#ff2e88", "accent2": "#ffb800", "text": "#ffffff",
                 "muted": "#ffc7e3", "panel": "#0000005c", "warn": "#ff3b3b"},
        "screens": lambda: [
            dashboard("Festival · Sistema", "seguibl.ttf", "bahnschrift.ttf", radius=10,
                      back=[D("stripes", 380, 0, 420, 110, "#ff2e8870", "#ffb80070", count=3, thickness=22, cx=0.3),
                            D("speedlines", 0, 0, 800, 480, "#ffffff10", "#ff2e8820", count=40, seed=6)],
                      front=[D("checker", 0, 0, 800, 6, "#ffffffcc", "#000000cc", step=6)]),
            clock_screen("Festival · Relógio", "seguibl.ttf",
                         back=[D("stripes", 0, 0, 800, 480, "#ff2e8838", "#ffb80038", count=4, thickness=40, cx=0.45),
                               D("checker", 0, 470, 800, 10, "#ffffffcc", "#000000cc", step=10)],
                         gif_label="Seu clipe aqui"),
        ],
    },
]


def get(theme_id):
    return next((t for t in THEMES if t["id"] == theme_id), None)


def skin_name(t):
    return f"{t['name']}"


def build(theme_id):
    """Retorna (nome da skin, cores, telas) prontos para entrar na configuração."""
    t = get(theme_id)
    screens = copy.deepcopy(t["screens"]())
    for s in screens:
        s["skin"] = skin_name(t)
    return skin_name(t), dict(t["skin"]), screens


def catalog():
    return [{k: t[k] for k in ("id", "name", "inspired", "description")} for t in THEMES]
