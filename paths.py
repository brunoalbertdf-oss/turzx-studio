"""Onde ficam os recursos do programa e os dados do usuário."""
import glob
import os
import shutil
import sys
from functools import lru_cache

APP_NAME = "TURZX Studio"

# Recursos somente leitura (editor web, mídia de exemplo). No executável ficam em sys._MEIPASS.
RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(RES_DIR, "web")
ASSETS_DIR = os.path.join(RES_DIR, "assets")

# Dados do usuário: configuração, mídias, logos e vídeos convertidos.
DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
MEDIA_DIR = os.path.join(DATA_DIR, "media")
DEVICE_CACHE = os.path.join(MEDIA_DIR, ".tela")
LOGO_DIR = os.path.join(DATA_DIR, "logos")
LOG_PATH = os.path.join(DATA_DIR, "turzx-studio.log")


def ensure_data_dir():
    for d in (DATA_DIR, MEDIA_DIR, LOGO_DIR):
        os.makedirs(d, exist_ok=True)
    sample = os.path.join(ASSETS_DIR, "media")
    if os.path.isdir(sample):
        for f in os.listdir(sample):
            dst = os.path.join(MEDIA_DIR, f)
            if not os.path.exists(dst):
                shutil.copy2(os.path.join(sample, f), dst)


@lru_cache(maxsize=1)
def find_turzx_dir(configured=""):
    """Procura a instalação do app TURZX original (ele traz o ffmpeg e as fontes dos temas)."""
    if configured and os.path.isfile(os.path.join(configured, "UsbMonitorL.exe")):
        return configured
    home = os.path.expanduser("~")
    roots = [os.path.join(home, d) for d in ("Documents", "Desktop", "Downloads")]
    roots += [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), "C:\\"]
    for root in filter(os.path.isdir, roots):
        for depth in ("*", "*/*", "*/*/*"):
            hits = glob.glob(os.path.join(root, depth, "UsbMonitorL.exe"))
            if hits:
                return os.path.dirname(hits[0])
    return ""
