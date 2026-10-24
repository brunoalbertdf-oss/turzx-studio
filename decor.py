"""Desenhos procedurais usados pelos temas (raios, esferas, grades, horizontes…), o selo
de fabricante de CPU/GPU e a lista de unidades de disco.

Tudo é desenhado em código: nenhum logo ou arte de terceiros é incluído no programa.
"""
import math
import os
import random
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from paths import LOGO_DIR


# ---------------------------------------------------------------- formas básicas

def star_points(cx, cy, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _with_alpha(c, a):
    return c[:3] + (int(c[3] * a),)


# ---------------------------------------------------------------- estilos decorativos
# Cada função recebe (layer RGBA, draw, caixa, c1, c2, wd) e desenha dentro da caixa.

def deco_rays(layer, d, box, c1, c2, wd):
    """Explosão de energia: raios alternados a partir do centro."""
    x, y, w, h = box
    cx, cy = x + w * float(wd.get("cx", 0.5)), y + h * float(wd.get("cy", 0.5))
    n = int(wd.get("count", 24))
    r = math.hypot(w, h)
    for i in range(n):
        a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 0.5) / n
        d.polygon([(cx, cy), (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                   (cx + r * math.cos(a1), cy + r * math.sin(a1))], fill=c1 if i % 2 == 0 else c2)


def deco_glow(layer, d, box, c1, c2, wd):
    """Brilho radial suave (aura)."""
    x, y, w, h = box
    g = Image.radial_gradient("L").resize((w, h))
    g = g.point(lambda v: 255 - v)
    glow = Image.new("RGBA", (w, h), c1)
    glow.putalpha(g.point(lambda v: int(v * c1[3] / 255)))
    layer.alpha_composite(glow, (x, y))


def deco_orb(layer, d, box, c1, c2, wd):
    """Esfera de cristal com estrelas (o número vem de 'count')."""
    x, y, w, h = box
    s = min(w, h)
    ox, oy = x + (w - s) // 2, y + (h - s) // 2
    orb = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    grad = Image.radial_gradient("L").resize((s, s))
    base = Image.new("RGBA", (s, s), c1)
    dark = Image.new("RGBA", (s, s), tuple(int(v * 0.55) for v in c1[:3]) + (255,))
    body = Image.composite(dark, base, grad)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
    orb.paste(body, (0, 0), mask)
    od = ImageDraw.Draw(orb)
    n = max(1, min(7, int(wd.get("count", 4))))
    pos = [(0.5, 0.5)] if n == 1 else [(0.5 + 0.2 * math.cos(2 * math.pi * k / n - 1.2),
                                         0.52 + 0.2 * math.sin(2 * math.pi * k / n - 1.2)) for k in range(n)]
    for px, py in pos:
        od.polygon(star_points(px * s, py * s, s * 0.11, s * 0.045), fill=c2)
    od.ellipse([s * 0.22, s * 0.14, s * 0.42, s * 0.30], fill=(255, 255, 255, 140))  # reflexo
    layer.alpha_composite(orb, (ox, oy))


def deco_stars(layer, d, box, c1, c2, wd):
    x, y, w, h = box
    rnd = random.Random(int(wd.get("seed", 7)))
    for _ in range(int(wd.get("count", 40))):
        px, py, r = x + rnd.random() * w, y + rnd.random() * h, rnd.uniform(1, 3.5)
        d.polygon(star_points(px, py, r * 2, r * 0.8, 4), fill=c1 if rnd.random() > 0.3 else c2)


def deco_spiral(layer, d, box, c1, c2, wd):
    """Espiral (redemoinho) a partir do centro."""
    x, y, w, h = box
    cx, cy, s = x + w / 2, y + h / 2, min(w, h) / 2
    turns = float(wd.get("count", 3))
    pts = [(cx + s * t / (turns * 2 * math.pi) * math.cos(t), cy + s * t / (turns * 2 * math.pi) * math.sin(t))
           for t in [i * 0.05 for i in range(int(turns * 2 * math.pi / 0.05))]]
    d.line(pts, fill=c1, width=int(wd.get("thickness", 6)), joint="curve")
    d.ellipse([cx - s * 0.08, cy - s * 0.08, cx + s * 0.08, cy + s * 0.08], fill=c2)


def deco_grid(layer, d, box, c1, c2, wd):
    """Grade de HUD; a cada 'count' linhas, uma mais forte."""
    x, y, w, h = box
    step = int(wd.get("step", 24))
    major = int(wd.get("count", 4))
    for i, gx in enumerate(range(x, x + w, step)):
        d.line([(gx, y), (gx, y + h)], fill=c2 if i % major == 0 else c1, width=1)
    for i, gy in enumerate(range(y, y + h, step)):
        d.line([(x, gy), (x + w, gy)], fill=c2 if i % major == 0 else c1, width=1)


def deco_scanlines(layer, d, box, c1, c2, wd):
    x, y, w, h = box
    for gy in range(y, y + h, int(wd.get("step", 4))):
        d.line([(x, gy), (x + w, gy)], fill=c1)


def deco_hex(layer, d, box, c1, c2, wd):
    """Colmeia de hexágonos."""
    x, y, w, h = box
    r = int(wd.get("step", 22))
    hw, hh = r * math.sqrt(3), r * 1.5
    rnd = random.Random(int(wd.get("seed", 3)))
    row = 0
    yy = y - r
    while yy < y + h + r:
        xx = x - hw + (hw / 2 if row % 2 else 0)
        while xx < x + w + hw:
            pts = [(xx + r * math.cos(math.radians(60 * k - 30)), yy + r * math.sin(math.radians(60 * k - 30)))
                   for k in range(6)]
            d.polygon(pts, outline=c1, fill=c2 if rnd.random() < 0.08 else None)
            xx += hw
        yy += hh
        row += 1


def deco_crosshair(layer, d, box, c1, c2, wd):
    """Mira: círculos e marcas."""
    x, y, w, h = box
    cx, cy, s = x + w / 2, y + h / 2, min(w, h) / 2
    t = int(wd.get("thickness", 3))
    d.ellipse([cx - s + t, cy - s + t, cx + s - t, cy + s - t], outline=c1, width=t)
    d.ellipse([cx - s * 0.55, cy - s * 0.55, cx + s * 0.55, cy + s * 0.55], outline=c1, width=max(1, t - 1))
    for a in (0, 90, 180, 270):
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        d.line([(cx + dx * s * 0.25, cy + dy * s * 0.25), (cx + dx * s * 1.0, cy + dy * s * 1.0)], fill=c1, width=t)
    d.ellipse([cx - t * 1.5, cy - t * 1.5, cx + t * 1.5, cy + t * 1.5], fill=c2)


def deco_stripes(layer, d, box, c1, c2, wd):
    """Faixas diagonais (estilo pintura de carro de corrida)."""
    x, y, w, h = box
    n = int(wd.get("count", 3))
    width = float(wd.get("thickness", 26))
    gap = width * 0.45
    slant = h * float(wd.get("slant", 0.6))
    start = x + w * float(wd.get("cx", 0.55))
    for i in range(n):
        x0 = start + i * (width + gap)
        d.polygon([(x0, y + h), (x0 + width, y + h), (x0 + width + slant, y), (x0 + slant, y)],
                  fill=c1 if i % 2 == 0 else c2)


def deco_speedlines(layer, d, box, c1, c2, wd):
    x, y, w, h = box
    rnd = random.Random(int(wd.get("seed", 11)))
    for _ in range(int(wd.get("count", 30))):
        ly = y + rnd.random() * h
        lx = x + rnd.random() * w * 0.8
        ln = rnd.uniform(0.1, 0.45) * w
        d.line([(lx, ly), (min(x + w, lx + ln), ly)], fill=c1 if rnd.random() > 0.25 else c2,
               width=rnd.choice((1, 1, 2, 3)))


def deco_skyline(layer, d, box, c1, c2, wd):
    """Silhueta de cidade com janelas acesas."""
    x, y, w, h = box
    rnd = random.Random(int(wd.get("seed", 5)))
    bx = x
    while bx < x + w:
        bw = rnd.randint(int(w * 0.04), int(w * 0.11))
        bh = rnd.randint(int(h * 0.25), h)
        top = y + h - bh
        d.rectangle([bx, top, bx + bw, y + h], fill=c1)
        if rnd.random() < 0.25:  # antena
            d.line([(bx + bw / 2, top), (bx + bw / 2, top - h * 0.08)], fill=c1, width=2)
        for wy in range(top + 6, y + h - 4, 9):
            for wx in range(bx + 4, bx + bw - 3, 7):
                if rnd.random() < 0.28:
                    d.rectangle([wx, wy, wx + 2, wy + 3], fill=c2)
        bx += bw + rnd.randint(0, 3)


def deco_checker(layer, d, box, c1, c2, wd):
    """Bandeira quadriculada."""
    x, y, w, h = box
    s = int(wd.get("step", 16))
    for j, gy in enumerate(range(y, y + h, s)):
        for i, gx in enumerate(range(x, x + w, s)):
            d.rectangle([gx, gy, min(gx + s, x + w) - 1, min(gy + s, y + h) - 1], fill=c1 if (i + j) % 2 else c2)


def deco_camo(layer, d, box, c1, c2, wd):
    """Camuflagem: manchas sobrepostas e desfocadas."""
    x, y, w, h = box
    rnd = random.Random(int(wd.get("seed", 9)))
    tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tmp)
    for _ in range(int(wd.get("count", 60))):
        cx, cy, r = rnd.random() * w, rnd.random() * h, rnd.uniform(0.03, 0.12) * max(w, h)
        td.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=c1 if rnd.random() > 0.5 else c2)
    layer.alpha_composite(tmp.filter(ImageFilter.GaussianBlur(2)), (x, y))


def deco_chevrons(layer, d, box, c1, c2, wd):
    """Divisas militares."""
    x, y, w, h = box
    n = int(wd.get("count", 3))
    t = h / (n * 2)
    for i in range(n):
        top = y + i * t * 1.6
        d.polygon([(x, top), (x + w / 2, top + t * 1.2), (x + w, top), (x + w, top + t),
                   (x + w / 2, top + t * 2.2), (x, top + t)], fill=c1 if i % 2 == 0 else c2)


def deco_leaf(layer, d, box, c1, c2, wd):
    """Folha estilizada com nervura em espiral (emblema de vila ninja genérico)."""
    x, y, w, h = box
    s = min(w, h)
    cx, cy = x + w / 2, y + h / 2
    d.polygon([(cx, cy - s * 0.48), (cx + s * 0.4, cy + s * 0.05), (cx, cy + s * 0.45), (cx - s * 0.4, cy + s * 0.05)],
              fill=c1)
    pts = [(cx + s * 0.25 * (t / 12) * math.cos(t), cy + s * 0.25 * (t / 12) * math.sin(t)) for t in
           [i * 0.1 for i in range(120)]]
    d.line(pts, fill=c2, width=max(2, int(s / 30)))


DECOS = {"rays": deco_rays, "glow": deco_glow, "orb": deco_orb, "stars": deco_stars, "spiral": deco_spiral,
         "grid": deco_grid, "scanlines": deco_scanlines, "hex": deco_hex, "crosshair": deco_crosshair,
         "stripes": deco_stripes, "speedlines": deco_speedlines, "skyline": deco_skyline, "checker": deco_checker,
         "camo": deco_camo, "chevrons": deco_chevrons, "leaf": deco_leaf}


# ---------------------------------------------------------------- fabricante de CPU/GPU

BRANDS = {  # cores das marcas para o selo desenhado
    "AMD": {"bg": (0, 0, 0, 255), "fg": (255, 255, 255, 255), "accent": (237, 28, 36, 255), "word": "AMD"},
    "NVIDIA": {"bg": (118, 185, 0, 255), "fg": (0, 0, 0, 255), "accent": (255, 255, 255, 255), "word": "NVIDIA"},
    "Intel": {"bg": (0, 104, 181, 255), "fg": (255, 255, 255, 255), "accent": (0, 199, 253, 255), "word": "intel"},
}


@lru_cache(maxsize=16)
def _user_logo(vendor, mtime):
    path = os.path.join(LOGO_DIR, f"{vendor.lower()}.png")
    return Image.open(path).convert("RGBA")


def user_logo(vendor):
    """Logo oficial que o usuário colocou em %APPDATA%\\TURZX Studio\\logos\\<fabricante>.png."""
    path = os.path.join(LOGO_DIR, f"{vendor.lower()}.png")
    if vendor and os.path.isfile(path):
        return _user_logo(vendor, os.path.getmtime(path))
    return None


def draw_brand_badge(layer, d, box, vendor, font_fn, style="badge"):
    x, y, w, h = box
    logo = user_logo(vendor)
    if logo is not None:
        im = logo.copy()
        im.thumbnail((w, h), Image.LANCZOS)
        layer.alpha_composite(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
        return
    b = BRANDS.get(vendor, {"bg": (60, 60, 70, 255), "fg": (255, 255, 255, 255), "accent": (150, 150, 160, 255),
                            "word": vendor or "?"})
    fnt = font_fn("arialbd.ttf" if vendor != "Intel" else "segoeuib.ttf", max(8, int(h * 0.62)))
    if style == "badge":
        d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=max(2, h // 5), fill=b["bg"])
        d.rectangle([x + h * 0.25, y + h - max(2, h // 9) - h * 0.12, x + w - h * 0.25, y + h - h * 0.12],
                    fill=b["accent"])
        fg = b["fg"]
    else:  # só o nome, na cor da marca
        fg = b["bg"] if vendor != "AMD" else b["accent"]
    l, t, r, bt = d.textbbox((0, 0), b["word"], font=fnt)
    d.text((x + (w - (r - l)) / 2 - l, y + (h - (bt - t)) / 2 - t - h * 0.04), b["word"], font=fnt, fill=fg)
