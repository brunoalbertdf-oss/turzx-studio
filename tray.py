"""Ícone na bandeja do Windows."""
import webbrowser

import pystray
from PIL import Image, ImageDraw

import autostart


def make_icon(size=64):
    """Ícone desenhado: uma telinha com um gráfico."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size / 64
    d.rounded_rectangle([4 * s, 10 * s, 60 * s, 50 * s], radius=6 * s, fill=(20, 24, 48, 255),
                        outline=(0, 220, 255, 255), width=max(1, int(3 * s)))
    d.line([(12 * s, 40 * s), (22 * s, 28 * s), (32 * s, 34 * s), (44 * s, 20 * s), (52 * s, 26 * s)],
           fill=(255, 80, 160, 255), width=max(1, int(4 * s)), joint="curve")
    d.rectangle([26 * s, 50 * s, 38 * s, 56 * s], fill=(0, 220, 255, 255))
    return im


ICON = None


def stop():
    if ICON:
        ICON.stop()


def run(engine, url, on_quit):
    global ICON
    def toggle_autostart(icon, item):
        enabled = not autostart.is_enabled()
        autostart.set_enabled(enabled)
        engine.cfg["settings"]["autostart"] = enabled

    menu = pystray.Menu(
        pystray.MenuItem("Abrir editor", lambda: webbrowser.open(url), default=True),
        pystray.MenuItem("Próxima tela", lambda: (setattr(engine, "pinned", None), engine.step(1))),
        pystray.MenuItem("Iniciar com o Windows", toggle_autostart, checked=lambda item: autostart.is_enabled(),
                         visible=lambda item: not autostart.task_installed()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", lambda icon: (icon.stop(), on_quit())),
    )
    icon = ICON = pystray.Icon("turzx_studio", make_icon(), "TURZX Studio", menu)
    icon.run()  # bloqueia até "Sair"
