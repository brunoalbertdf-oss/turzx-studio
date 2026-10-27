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


def find_turzx_dir(configured=""):
    """Procura a instalação do app TURZX original (ele traz o ffmpeg e as fontes dos temas)."""
    return _find_turzx_dir(configured or "")


@lru_cache(maxsize=4)
def _find_turzx_dir(configured):
    if configured and os.path.isfile(os.path.join(configured, "UsbMonitorL.exe")):
        return configured
    memo = os.path.join(DATA_DIR, "turzx_dir.txt")  # a busca no disco leva ~1,5 s: guarda o resultado
    try:
        with open(memo, encoding="utf8") as f:
            found = f.read().strip()
        if not found or os.path.isfile(os.path.join(found, "UsbMonitorL.exe")):
            return found
    except OSError:
        pass
    found = _search_turzx_dir()
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(memo, "w", encoding="utf8") as f:
            f.write(found)
    except OSError:
        pass
    return found


def _search_turzx_dir():
    home = os.path.expanduser("~")
    roots = [os.path.join(home, d) for d in ("Documents", "Desktop", "Downloads")]
    roots += [os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", ""), "C:\\"]
    for root in filter(os.path.isdir, roots):
        for depth in ("*", "*/*", "*/*/*"):
            hits = glob.glob(os.path.join(root, depth, "UsbMonitorL.exe"))
            if hits:
                return os.path.dirname(hits[0])
    return ""
