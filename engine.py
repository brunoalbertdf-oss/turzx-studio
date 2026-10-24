"""Motor: carrossel de telas, renderização e envio incremental para a tela TURZX."""
import copy
import json
import os
import queue
import threading
import time

from PIL import Image, ImageChops

import renderer
from media import MediaCache, convert_for_device, device_video_name
from sensors import Sensors
import turzx_screen
from turzx_screen import TurzxScreen, WIDTH, HEIGHT
from weather import Weather
import defaults
import themes

from paths import CONFIG_PATH, DEVICE_CACHE, MEDIA_DIR, ensure_data_dir, find_turzx_dir

TILE = 16          # granularidade da detecção de mudanças (px)
MAX_RECTS = 8      # acima disso, envia um único retângulo englobando tudo
BAND = 160         # altura máxima de cada envio parcial (linhas)

ROTATIONS = {  # orientação lógica -> (tamanho lógico, rotação para o buffer nativo 800x480)
    "landscape": ((800, 480), 0), "landscape_flipped": ((800, 480), 180),
    "portrait": ((480, 800), 90), "portrait_flipped": ((480, 800), 270),
}


def load_config():
    ensure_data_dir()
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf8") as f:
            cfg = json.load(f)
        for k, v in defaults.CONFIG.items():
            cfg.setdefault(k, copy.deepcopy(v))
        for name, skin in themes.builtin_skins().items():  # skins prontas novas aparecem sozinhas
            cfg["skins"].setdefault(name, skin)
        return cfg
    cfg = copy.deepcopy(defaults.CONFIG)
    save_config(cfg)
    return cfg


def save_config(cfg):
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONFIG_PATH)


def dirty_rects(old, new):
    """Retângulos (x, y, w, h) que mudaram entre dois quadros nativos."""
    diff = ImageChops.difference(old, new).convert("L").point(lambda v: 255 if v > 2 else 0)
    if not diff.getbbox():
        return []
    tiles = diff.reduce(TILE)  # cada pixel = um bloco TILExTILE
    tw, th = tiles.size
    px = tiles.load()
    runs = []  # [x0, x1, y0, y1] em blocos
    open_runs = {}
    for ty in range(th):
        row_runs, tx = [], 0
        while tx < tw:
            if px[tx, ty]:
                start = tx
                while tx < tw and px[tx, ty]:
                    tx += 1
                row_runs.append((start, tx))
            tx += 1
        new_open = {}
        for span in row_runs:
            if span in open_runs:  # estende verticalmente o mesmo intervalo
                r = open_runs.pop(span)
                r[3] = ty + 1
            else:
                r = [span[0], span[1], ty, ty + 1]
                runs.append(r)
            new_open[span] = r
        open_runs = new_open
    rects = [(x0 * TILE, y0 * TILE, min((x1 - x0) * TILE, WIDTH - x0 * TILE), min((y1 - y0) * TILE, HEIGHT - y0 * TILE))
             for x0, x1, y0, y1 in runs]
    if len(rects) > MAX_RECTS:
        l, t, r, b = diff.getbbox()
        rects = [(l, t, r - l, b - t)]
    out = []
    for x, y, w, h in rects:
        for yy in range(y, y + h, BAND):
            out.append((x, yy, w, min(BAND, y + h - yy)))
    return out


class Engine:
    def __init__(self):
        self.cfg = load_config()
        self.sensors = Sensors(self.cfg["settings"].get("lhm_url", "http://127.0.0.1:8085/data.json"))
        self.weather = Weather(self.cfg["settings"]["city"])
        ff = self.cfg["settings"].get("ffmpeg", "") or find_turzx_dir(self.cfg["settings"].get("turzx_dir", ""))
        self.media = MediaCache(MEDIA_DIR, ff)
        self.preview_media = MediaCache(MEDIA_DIR, ff, static=True)
        self.preview_lock = threading.Lock()
        self.status = {"connected": False, "screen_id": "", "message": "Iniciando…", "fps": 0, "current": 0}
        self.current = 0
        self.screen_started = time.time()
        self.pinned = None          # índice fixado manualmente (pausa o carrossel)
        self.last_frame = None      # último quadro lógico enviado (para a prévia ao vivo)
        self._force_full = True
        self._brightness_sent = None
        self._stop = threading.Event()
        self._ops = queue.Queue()     # comandos do editor executados pela thread da tela
        self._video = None          # (índice da tela, nome do arquivo na tela) tocando agora
        self.video_errors = {}      # índice da tela -> mensagem
        self._video_failed = None
        self._shown = None          # última tela exibida (para detectar a troca e fazer o fade)
        self.thread = threading.Thread(target=self._run, daemon=True)

    # ------------------------------------------------------------- configuração

    def update_config(self, cfg):
        save_config(cfg)
        self.cfg = cfg
        self.weather.set_city(cfg["settings"]["city"])
        self._force_full = True
        self._brightness_sent = None
        self._video_failed = None
        self.video_errors = {}

    def skin_for(self, screen):
        skins = self.cfg["skins"]
        name = screen.get("skin") or self.cfg["settings"].get("skin")
        return skins.get(name) or next(iter(skins.values()))

    def logical_size(self):
        return ROTATIONS.get(self.cfg["settings"].get("orientation"), ROTATIONS["landscape"])[0]

    def context(self, screen, media):
        values = self.sensors.snapshot()
        values.update(self.weather.values)
        return renderer.Context(values, self.sensors.history, self.weather.forecast, self.skin_for(screen), media,
                                self.sensors.drives, preview=media is self.preview_media)

    def render_preview(self, index):
        screens = self.cfg["screens"]
        if not screens:
            return Image.new("RGB", self.logical_size(), "black")
        screen = screens[max(0, min(index, len(screens) - 1))]
        if screen.get("kind") == "device_video":  # a prévia mostra o primeiro quadro do vídeo
            screen = {"background": {"type": "media", "file": screen.get("file"), "fit": "cover",
                                     "color1": "#000000"}, "widgets": []}
        with self.preview_lock:
            img = renderer.render(screen, self.logical_size(), self.context(screen, self.preview_media))
            self.preview_media.sweep()
        return img

    # ------------------------------------------------------------- carrossel

    def active_screens(self):
        return [i for i, s in enumerate(self.cfg["screens"]) if s.get("enabled", True)]

    def goto(self, index):
        if 0 <= index < len(self.cfg["screens"]):
            self.current, self.screen_started = index, time.time()

    def step(self, delta):
        act = self.active_screens() or [0]
        pos = act.index(self.current) if self.current in act else 0
        self.goto(act[(pos + delta) % len(act)])

    def _pick_screen(self):
        n = len(self.cfg["screens"])
        if self.pinned is not None and self.pinned < n:
            self.current = self.pinned
        else:
            if self.current >= n or self.current not in self.active_screens():
                self.step(1)
            elif self.cfg["settings"].get("carousel", True):
                dur = float(self.cfg["screens"][self.current].get("duration", 15))
                if len(self.active_screens()) > 1 and time.time() - self.screen_started >= dur:
                    self.step(1)
        return self.cfg["screens"][self.current] if n else None

    # ------------------------------------------------------------- comandos para a tela

    def device_call(self, fn, timeout=180):
        """Executa fn(tela) na thread que controla a porta serial e devolve o resultado."""
        if not self.status.get("connected"):
            raise RuntimeError("tela desconectada")
        box, done = {}, threading.Event()
        self._ops.put((fn, box, done))
        if not done.wait(timeout):
            raise RuntimeError("a tela não respondeu a tempo")
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def _run_ops(self, lcd):
        while not self._ops.empty():
            fn, box, done = self._ops.get()
            try:
                box["result"] = fn(lcd)
            except Exception as e:
                box["error"] = e
            done.set()

    def _show_device_video(self, lcd, screen):
        """Garante o vídeo na memória da tela e manda tocar. Retorna False se não der."""
        key = (self.current, screen.get("file"), self.cfg["settings"].get("orientation"))
        if self._video == key:
            return True
        if self._video_failed == key:  # não insiste até a configuração mudar
            return False
        src = os.path.join(MEDIA_DIR, screen.get("file") or "")
        try:
            if not os.path.isfile(src):
                raise RuntimeError("arquivo de mídia não encontrado")
            ff = self.media.ffmpeg
            if not ff:
                raise RuntimeError("ffmpeg não encontrado")
            self.status["message"] = "Convertendo vídeo…"
            name, path = convert_for_device(src, self.cfg["settings"].get("orientation"), ff, DEVICE_CACHE)
            size = os.path.getsize(path)
            if name in lcd.list_videos() and lcd.file_size(name) != size:
                lcd.delete_video(name)  # sobra de um envio interrompido
            if name not in lcd.list_videos():
                free_kb = lcd.storage()[2]
                if size > (free_kb - 64) * 1024:
                    free_kb = self._free_old_videos(lcd, keep=name)
                if size > (free_kb - 64) * 1024:
                    raise RuntimeError(f"sem espaço na tela: precisa de {size // 1024} KB, livres {free_kb} KB")
                self.status["message"] = f"Enviando vídeo para a tela ({size // 1024} KB)…"
                lcd.upload_video(name, open(path, "rb").read())
            fade = self._fade_wanted()
            if fade:
                self._fade(lcd, out=True)
            lcd.play_video(name)
            if fade:
                time.sleep(0.25)  # a tela leva um instante para mostrar o 1º quadro
                self._fade(lcd, out=False)
            self._shown = self.current
            self._video = key
            self.video_errors.pop(self.current, None)
            self.status["message"] = "Conectada"
            return True
        except Exception as e:
            self._video_failed = key
            self.video_errors[self.current] = str(e)
            self.status["message"] = f"Vídeo: {e}"
            print("vídeo na tela:", e)
            return False

    def _free_old_videos(self, lcd, keep):
        """Apaga da tela vídeos que o próprio app enviou e que nenhuma tela usa mais."""
        orientation = self.cfg["settings"].get("orientation")
        wanted = {keep}
        for sc in self.cfg["screens"]:
            src = os.path.join(MEDIA_DIR, sc.get("file") or "")
            if sc.get("kind") == "device_video" and os.path.isfile(src):
                wanted.add(device_video_name(src, orientation))
        ours = set(os.listdir(DEVICE_CACHE)) if os.path.isdir(DEVICE_CACHE) else set()
        for f in lcd.list_videos():
            if f in ours and f not in wanted:
                lcd.delete_video(f)
                os.remove(os.path.join(DEVICE_CACHE, f))
        return lcd.storage()[2]

    # ------------------------------------------------------------- transição

    def _fade_wanted(self):
        return self.cfg["settings"].get("transition", "fade") == "fade" and self._shown is not None

    def _fade(self, lcd, out, duration=0.35, steps=10):
        """Apaga ou acende o brilho em degraus: esconde o desenho de cima para baixo da tela nova."""
        full = int(self.cfg["settings"].get("brightness", 60))
        for i in range(1, steps + 1):
            frac = i / steps
            lcd.set_brightness(round(full * (1 - frac if out else frac)))
            time.sleep(duration / steps)

    def _leave_device_video(self, lcd):
        if self._video:
            lcd.stop_media()  # 0x79 (parar vídeo) + 0x96: só o 0x96 não interrompe o vídeo da tela
            self._video = None
            self._force_full = True

    # ------------------------------------------------------------- laço principal

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.status.update(message="Procurando a tela…")
                lcd = TurzxScreen(self.cfg["settings"].get("port") or None)
                self.status.update(screen_id=lcd.hello(), connected=True, message="Conectada")
                lcd.stop_media()
                self._video = None
                self._shown = None
                self._force_full = True
                self._brightness_sent = None
                self._loop(lcd)
                lcd.close()  # parada pedida: libera a porta para outra instância
            except turzx_screen.ScreenDesync as e:
                self.status.update(connected=False, message="Reiniciando a tela (perdeu a sincronia)…")
                print(time.ctime(), "tela:", e, "- reiniciando")
                try:
                    lcd.restart()
                    lcd.close()
                except Exception:
                    pass
                time.sleep(12)
            except Exception as e:
                msg = str(e)
                if "PermissionError" in msg or "Acesso negado" in msg or "Access is denied" in msg:
                    msg = ("a porta da tela está em uso por outro programa. Feche o app TURZX original "
                           "(inclusive o ícone da bandeja) e tire-o da inicialização do Windows.")
                self.status.update(connected=False, message=f"Desconectada: {msg}")
                if msg != getattr(self, "_last_error", None):  # registra cada erro uma vez
                    print(time.ctime(), "tela:", msg)
                    self._last_error = msg
                try:
                    lcd.close()
                except Exception:
                    pass
                time.sleep(3)

    def _loop(self, lcd):
        native_old = None
        t_fps, frames = time.time(), 0
        while not self._stop.is_set():
            t0 = time.time()
            st = self.cfg["settings"]
            if self._brightness_sent != st.get("brightness"):
                lcd.set_brightness(int(st.get("brightness", 60)))
                self._brightness_sent = st.get("brightness")
            self._run_ops(lcd)
            screen = self._pick_screen()
            if screen is None:
                time.sleep(0.5)
                continue
            if screen.get("kind") == "device_video":
                if not self._show_device_video(lcd, screen):
                    if self.pinned is None:
                        self.step(1)  # pula a tela com problema
                    time.sleep(1)
                self.status["current"] = self.current
                time.sleep(0.1)
                continue
            switching = self._shown != self.current
            fade = switching and self._fade_wanted()
            if fade:
                self._fade(lcd, out=True)
            self._leave_device_video(lcd)
            size, rot = ROTATIONS.get(st.get("orientation"), ROTATIONS["landscape"])
            frame = renderer.render(screen, size, self.context(screen, self.media))
            if turzx_screen.TRACE["on"]:  # contador grande para cruzar com o registro
                from PIL import ImageDraw
                self._trace_n = getattr(self, "_trace_n", 0) + 1
                ImageDraw.Draw(frame).rectangle([0, 0, 170, 44], fill="black")
                ImageDraw.Draw(frame).text((6, 4), f"{self._trace_n} {time.strftime('%H:%M:%S')}",
                                           font=renderer.font("consola.ttf", 26), fill="yellow")
            self.media.sweep()
            self.last_frame = frame
            native = frame.rotate(rot, expand=True) if rot else frame
            if self._force_full or native_old is None:
                lcd.show_full(native)
                self._force_full = False
            else:
                for x, y, w, h in dirty_rects(native_old, native):
                    lcd.show_region(native.crop((x, y, x + w, y + h)), x, y)
            native_old = native
            if fade:
                self._fade(lcd, out=False)
            self._shown = self.current
            self.status["current"] = self.current
            frames += 1
            if time.time() - t_fps >= 2:
                self.status["fps"] = round(frames / (time.time() - t_fps), 1)
                t_fps, frames = time.time(), 0
            time.sleep(max(0.0, 1 / max(1, float(st.get("max_fps", 10))) - (time.time() - t0)))
