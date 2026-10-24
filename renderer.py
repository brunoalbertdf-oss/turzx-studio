"""Desenha uma tela (fundo + widgets) em uma imagem PIL.

Cores aceitam "#rrggbb", "#rrggbbaa" ou "$nome" (cor da skin ativa).
Textos aceitam variáveis entre chaves, ex.: "CPU {cpu_percent:.0f}%".
"""
import glob
import math
import os
import string
from functools import lru_cache

from PIL import Image, ImageColor, ImageDraw, ImageFont

import decor
from paths import DATA_DIR, find_turzx_dir

FONT_DIRS = [os.path.join(DATA_DIR, "fonts"),
             os.path.join(find_turzx_dir(), "fonts"),
             r"C:\Windows\Fonts",
             os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts")]


def list_fonts():
    names = set()
    for d in FONT_DIRS:
        for ext in ("ttf", "otf", "ttc"):
            names.update(os.path.basename(p) for p in glob.glob(os.path.join(d, f"*.{ext}")))
    return sorted(names, key=str.lower)


@lru_cache(maxsize=256)
def font(name, size):
    for d in FONT_DIRS:
        p = os.path.join(d, name or "")
        if name and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", size)


def color(value, skin, default="#ffffff"):
    value = value or default
    if isinstance(value, str) and value.startswith("$"):
        value = skin.get(value[1:], default)
    try:
        c = ImageColor.getcolor(value, "RGBA")
    except (ValueError, AttributeError):
        c = ImageColor.getcolor(default, "RGBA")
    return c


class _SafeFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        return kwargs.get(key, "—")

    def format_field(self, value, spec):
        try:
            return format(value, spec)
        except (ValueError, TypeError):
            return str(value)


_fmt = _SafeFormatter()


def fill_template(text, values):
    try:
        return _fmt.vformat(text or "", (), values)
    except (ValueError, IndexError):
        return text


def num(values, key):
    try:
        return float(values.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def gradient(size, c1, c2, direction):
    w, h = size
    if direction == "horizontal":
        line = Image.linear_gradient("L").rotate(90, expand=True).resize((w, h))
    elif direction == "diagonal":
        big = Image.linear_gradient("L").rotate(45, expand=True)
        line = big.crop((big.width // 4, big.height // 4, big.width * 3 // 4, big.height * 3 // 4)).resize((w, h))
    else:
        line = Image.linear_gradient("L").resize((w, h))
    return Image.composite(Image.new("RGBA", size, c2), Image.new("RGBA", size, c1), line)


# ---------------------------------------------------------------- ícones do tempo

def draw_weather_icon(d, box, kind, col, col2):
    x, y, w, h = box
    s = min(w, h)
    cx, cy = x + w / 2, y + h / 2

    def sun(cx, cy, r):
        for i in range(8):
            a = i * math.pi / 4
            d.line([(cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35),
                    (cx + math.cos(a) * r * 1.8, cy + math.sin(a) * r * 1.8)], fill=col2, width=max(2, int(r / 5)))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col2)

    def cloud(cx, cy, r):
        d.ellipse([cx - r * 1.6, cy - r * 0.2, cx - r * 0.2, cy + r * 1.0], fill=col)
        d.ellipse([cx - r * 0.9, cy - r * 0.9, cx + r * 0.7, cy + r * 0.7], fill=col)
        d.ellipse([cx + r * 0.1, cy - r * 0.4, cx + r * 1.6, cy + r * 1.0], fill=col)
        d.rectangle([cx - r * 1.0, cy + r * 0.2, cx + r * 1.0, cy + r * 1.0], fill=col)

    if kind == "sun":
        sun(cx, cy, s * 0.22)
    elif kind == "sun_cloud":
        sun(cx - s * 0.12, cy - s * 0.12, s * 0.17)
        cloud(cx + s * 0.05, cy + s * 0.05, s * 0.2)
    elif kind == "fog":
        for i in range(4):
            yy = cy - s * 0.25 + i * s * 0.16
            d.line([(cx - s * 0.35, yy), (cx + s * 0.35, yy)], fill=col, width=max(2, int(s / 18)))
    else:
        cloud(cx, cy - s * 0.1, s * 0.22)
        base = cy + s * 0.22
        if kind == "rain":
            for i in range(-1, 2):
                xx = cx + i * s * 0.18
                d.line([(xx, base), (xx - s * 0.06, base + s * 0.18)], fill=col2, width=max(2, int(s / 20)))
        elif kind == "snow":
            for i in range(-1, 2):
                xx = cx + i * s * 0.18
                d.ellipse([xx - s * 0.04, base + s * 0.05, xx + s * 0.04, base + s * 0.13], fill=col2)
        elif kind == "storm":
            d.polygon([(cx, base - s * 0.02), (cx - s * 0.1, base + s * 0.14), (cx, base + s * 0.12),
                       (cx - s * 0.06, base + s * 0.27), (cx + s * 0.1, base + s * 0.08), (cx, base + s * 0.1)],
                      fill=col2)


# ---------------------------------------------------------------- widgets

def _text_in_box(d, box, text, fnt, fill, align, valign="middle"):
    x, y, w, h = box
    l, t, r, b = d.textbbox((0, 0), text, font=fnt)
    tw, th = r - l, b - t
    tx = {"left": x, "center": x + (w - tw) / 2, "right": x + w - tw}.get(align, x) - l
    ty = {"top": y, "middle": y + (h - th) / 2, "bottom": y + h - th}.get(valign, y) - t
    d.text((tx, ty), text, font=fnt, fill=fill)


def w_text(layer, d, wd, box, ctx):
    text = fill_template(wd.get("text", ""), ctx.values)
    fnt = font(wd.get("font", "segoeui.ttf"), int(wd.get("size", 24)))
    fill = color(wd.get("color"), ctx.skin, "#ffffff")
    if wd.get("shadow"):
        sx, sy, sw, sh = box
        _text_in_box(d, (sx + 2, sy + 2, sw, sh), text, fnt, color(wd.get("shadow_color"), ctx.skin, "#00000099"),
                     wd.get("align", "left"), wd.get("valign", "middle"))
    _text_in_box(d, box, text, fnt, fill, wd.get("align", "left"), wd.get("valign", "middle"))


def w_panel(layer, d, wd, box, ctx):
    x, y, w, h = box
    d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=int(wd.get("radius", 16)),
                        fill=color(wd.get("fill"), ctx.skin, "#00000066"),
                        outline=color(wd.get("outline"), ctx.skin, "#00000000") if wd.get("outline") else None,
                        width=int(wd.get("outline_width", 2)))


def _frac(wd, ctx):
    lo, hi = float(wd.get("min", 0)), float(wd.get("max", 100))
    return max(0.0, min(1.0, (num(ctx.values, wd.get("value", "cpu_percent")) - lo) / ((hi - lo) or 1)))


def _value_color(wd, ctx, frac):
    """Muda para a cor de alerta acima do limite configurado."""
    warn = wd.get("warn_at")
    if warn not in (None, "") and frac * 100 >= float(warn):
        return color(wd.get("warn_color"), ctx.skin, "$warn" if "warn" in ctx.skin else "#ff4040")
    return color(wd.get("color"), ctx.skin, "#00d0ff")


def w_bar(layer, d, wd, box, ctx):
    x, y, w, h = box
    f = _frac(wd, ctx)
    r = int(wd.get("radius", min(w, h) // 2))
    d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=r, fill=color(wd.get("bg"), ctx.skin, "#ffffff22"))
    if f <= 0:
        return
    col = _value_color(wd, ctx, f)
    if wd.get("vertical"):
        fh = max(int(h * f), min(w, 2 * r))
        d.rounded_rectangle([x, y + h - fh, x + w - 1, y + h - 1], radius=r, fill=col)
    else:
        fw = max(int(w * f), min(h, 2 * r))
        d.rounded_rectangle([x, y, x + fw - 1, y + h - 1], radius=r, fill=col)


def w_gauge(layer, d, wd, box, ctx):
    x, y, w, h = box
    s = min(w, h)
    bx, by = x + (w - s) / 2, y + (h - s) / 2
    th = int(wd.get("thickness", max(6, s // 10)))
    start, sweep = 135, 270
    f = _frac(wd, ctx)
    rect = [bx + th / 2, by + th / 2, bx + s - th / 2, by + s - th / 2]
    d.arc(rect, start, start + sweep, fill=color(wd.get("bg"), ctx.skin, "#ffffff22"), width=th)
    if f > 0:
        d.arc(rect, start, start + sweep * f, fill=_value_color(wd, ctx, f), width=th)
    if wd.get("show_value", True):
        txt = fill_template(wd.get("text") or "{%s:.0f}%s" % (wd.get("value", "cpu_percent"), wd.get("unit", "%")),
                            ctx.values)
        fnt = font(wd.get("font", "segoeuib.ttf"), int(wd.get("size", s // 4)))
        _text_in_box(d, (bx, by, s, s), txt, fnt, color(wd.get("text_color"), ctx.skin, "#ffffff"), "center")
    if wd.get("label"):
        fnt = font(wd.get("font", "segoeuib.ttf"), max(10, int(wd.get("size", s // 4)) // 2))
        _text_in_box(d, (bx, by + s * 0.62, s, s * 0.3), fill_template(wd["label"], ctx.values), fnt,
                     color(wd.get("label_color"), ctx.skin, "#ffffffaa"), "center")


def w_graph(layer, d, wd, box, ctx):
    x, y, w, h = box
    data = list(ctx.history.get(wd.get("value", "cpu_percent"), []))
    if wd.get("bg"):
        d.rounded_rectangle([x, y, x + w - 1, y + h - 1], radius=int(wd.get("radius", 8)),
                            fill=color(wd.get("bg"), ctx.skin, "#ffffff11"))
    if len(data) < 2:
        return
    lo = float(wd.get("min", 0))
    hi = float(wd["max"]) if wd.get("max") not in (None, "", "auto") else max(max(data), lo + 1)
    pts = [(x + i * (w - 1) / (len(data) - 1), y + h - 1 - (max(lo, min(hi, v)) - lo) / ((hi - lo) or 1) * (h - 1))
           for i, v in enumerate(data)]
    col = color(wd.get("color"), ctx.skin, "#00d0ff")
    if wd.get("fill", True):
        fc = col[:3] + (int(col[3] * 0.3),)
        d.polygon(pts + [(x + w - 1, y + h - 1), (x, y + h - 1)], fill=fc)
    d.line(pts, fill=col, width=int(wd.get("thickness", 2)), joint="curve")


def w_media(layer, d, wd, box, ctx):
    x, y, w, h = box
    frame = ctx.media.get(wd.get("file"), (w, h), wd.get("fit", "cover"), int(wd.get("fps", 10)),
                          float(wd.get("speed", 1)))
    if frame is None:
        if ctx.preview:  # na tela física um espaço vazio fica invisível
            d.rectangle([x, y, x + w - 1, y + h - 1], outline="#ffffff55", width=2)
            _text_in_box(d, box, wd.get("placeholder") or "sem mídia", font("segoeui.ttf", 16), "#ffffff88",
                         "center")
        return
    r = int(wd.get("radius", 0))
    mask = frame.getchannel("A")
    if r:
        rm = Image.new("L", (w, h), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
        mask = Image.composite(mask, rm, rm)
    op = float(wd.get("opacity", 1))
    if op < 1:
        mask = mask.point(lambda v: int(v * op))
    layer.paste(frame, (x, y), mask)


def w_weather_icon(layer, d, wd, box, ctx):
    draw_weather_icon(d, box, ctx.values.get("weather_icon", "cloud"),
                      color(wd.get("color"), ctx.skin, "#e0e6ff"), color(wd.get("color2"), ctx.skin, "#ffcc33"))


def w_forecast(layer, d, wd, box, ctx):
    x, y, w, h = box
    days = ctx.forecast[: int(wd.get("days", 5))]
    if not days:
        return
    cw = w / len(days)
    fnt = font(wd.get("font", "segoeuib.ttf"), int(wd.get("size", 18)))
    tc = color(wd.get("color"), ctx.skin, "#ffffff")
    mc = color(wd.get("muted"), ctx.skin, "#ffffff99")
    for i, day in enumerate(days):
        cx = x + i * cw
        _text_in_box(d, (cx, y, cw, h * 0.2), day["day"], fnt, tc, "center")
        draw_weather_icon(d, (int(cx), int(y + h * 0.2), int(cw), int(h * 0.5)), day["icon"],
                          color(wd.get("icon_color"), ctx.skin, "#e0e6ff"),
                          color(wd.get("icon_color2"), ctx.skin, "#ffcc33"))
        _text_in_box(d, (cx, y + h * 0.72, cw, h * 0.28), f'{day["max"]}° / {day["min"]}°', fnt, mc, "center")


def w_deco(layer, d, wd, box, ctx):
    fn = decor.DECOS.get(wd.get("style", "rays"))
    if fn:
        x, y, w, h = box
        sub = Image.new("RGBA", (w, h), (0, 0, 0, 0))  # recorta o desenho na caixa do widget
        fn(sub, ImageDraw.Draw(sub), (0, 0, w, h), color(wd.get("color"), ctx.skin, "#ffffff33"),
           color(wd.get("color2"), ctx.skin, "#ffffff11"), wd)
        layer.alpha_composite(sub, (max(0, x), max(0, y)), (max(0, -x), max(0, -y)))


def w_brand(layer, d, wd, box, ctx):
    """Selo do fabricante (AMD/NVIDIA/Intel) e, opcionalmente, o nome da peça ao lado."""
    x, y, w, h = box
    dev = wd.get("device", "cpu")
    vendor = ctx.values.get(f"{dev}_vendor", "")
    if not wd.get("show_name", True):
        decor.draw_brand_badge(layer, d, box, vendor, font, wd.get("style", "badge"))
        return
    lw = int(min(w * 0.42, h * 2.6))
    decor.draw_brand_badge(layer, d, (x, y, lw, h), vendor, font, wd.get("style", "badge"))
    name = ctx.values.get(f"{dev}_name" if not wd.get("full_name") else f"{dev}_name_full", "")
    fnt = font(wd.get("font", "segoeuib.ttf"), int(wd.get("size", max(10, h * 0.55))))
    _text_in_box(d, (x + lw + int(h * 0.3), y, w - lw - int(h * 0.3), h), str(name), fnt,
                 color(wd.get("color"), ctx.skin, "#ffffff"), "left")


def w_drives(layer, d, wd, box, ctx):
    """Lista as unidades de disco com barra de uso."""
    x, y, w, h = box
    only = [s.strip().upper() for s in str(wd.get("letters", "")).split(",") if s.strip()]
    drives = [dr for dr in ctx.drives if not only or dr["letter"] in only][: int(wd.get("max", 6))]
    if not drives:
        return
    rh = h / len(drives)
    fnt = font(wd.get("font", "segoeuib.ttf"), int(wd.get("size", max(10, min(22, rh * 0.38)))))
    tc = color(wd.get("color"), ctx.skin, "#ffffff")
    mc = color(wd.get("muted"), ctx.skin, "#ffffffaa")
    warn = float(wd.get("warn_at", 90))
    for i, dr in enumerate(drives):
        ry = y + i * rh
        label = f'{dr["letter"]}:' + (f' {dr["label"]}' if dr["label"] and wd.get("show_label", True) else "")
        _text_in_box(d, (x, ry, w * 0.55, rh * 0.55), label, fnt, tc, "left")
        _text_in_box(d, (x + w * 0.45, ry, w * 0.55, rh * 0.55), f'{dr["free"]} GB livres de {dr["total"]}', fnt, mc,
                     "right")
        bh = max(4, int(rh * 0.18))
        by = int(ry + rh * 0.62)
        d.rounded_rectangle([x, by, x + w - 1, by + bh], radius=bh // 2, fill=color(wd.get("bg"), ctx.skin, "#ffffff22"))
        fw = int(w * dr["percent"] / 100)
        if fw > bh:
            col = color(wd.get("warn_color"), ctx.skin, "#ff4040") if dr["percent"] >= warn else \
                color(wd.get("bar"), ctx.skin, "#00d0ff")
            d.rounded_rectangle([x, by, x + fw, by + bh], radius=bh // 2, fill=col)


WIDGETS = {"text": w_text, "panel": w_panel, "bar": w_bar, "gauge": w_gauge, "graph": w_graph,
           "media": w_media, "weather_icon": w_weather_icon, "forecast": w_forecast,
           "deco": w_deco, "brand": w_brand, "drives": w_drives}


class Context:
    def __init__(self, values, history, forecast, skin, media, drives=(), preview=False):
        self.values, self.history, self.forecast, self.skin, self.media = values, history, forecast, skin, media
        self.drives, self.preview = list(drives), preview


def render(screen, size, ctx):
    bg = screen.get("background", {})
    kind = bg.get("type", "gradient")
    c1 = color(bg.get("color1"), ctx.skin, "#101830")
    if kind == "color":
        canvas = Image.new("RGBA", size, c1)
    elif kind == "media" and bg.get("file"):
        canvas = Image.new("RGBA", size, c1)
        frame = ctx.media.get(bg["file"], size, bg.get("fit", "cover"), int(bg.get("fps", 5)))
        if frame is not None:
            canvas.alpha_composite(frame)
    else:
        canvas = gradient(size, c1, color(bg.get("color2"), ctx.skin, "#3c1450"), bg.get("direction", "vertical"))

    for wd in screen.get("widgets", []):
        if wd.get("hidden"):
            continue
        fn = WIDGETS.get(wd.get("type"))
        if not fn:
            continue
        box = (int(wd.get("x", 0)), int(wd.get("y", 0)), max(1, int(wd.get("w", 100))), max(1, int(wd.get("h", 40))))
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        try:
            fn(layer, ImageDraw.Draw(layer), wd, box, ctx)
        except Exception as e:
            print("widget", wd.get("type"), e)
        canvas.alpha_composite(layer)
    return canvas.convert("RGB")
