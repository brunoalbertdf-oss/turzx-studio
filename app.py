"""TURZX Studio: servidor local do editor + motor da tela + ícone na bandeja.

Uso: python app.py [--background] [--no-browser] [--no-tray]
  --background  inicia sem abrir o editor (usado ao iniciar com o Windows)
"""
import io
import json
import mimetypes
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import autostart
import renderer
import themes
from engine import Engine
from paths import DEVICE_CACHE, LOG_PATH, MEDIA_DIR, WEB_DIR, ensure_data_dir
from sensors import CATALOG

HOST, PORT = "127.0.0.1", 8777
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".mp4", ".mkv", ".webm", ".mov", ".avi"}

engine = None  # criado em main()
STATE = {"admin": autostart.is_admin(), "admin_task": False}
RESTART_ELEVATED = None  # definido em main()


def media_list():
    return sorted(f for f in os.listdir(MEDIA_DIR) if os.path.splitext(f)[1].lower() in MEDIA_EXT)


def safe_name(name):
    name = os.path.basename(urllib.parse.unquote(name or ""))
    name = re.sub(r"[^\w.\- ()]", "_", name).strip()
    return name if os.path.splitext(name)[1].lower() in MEDIA_EXT else None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, body, ctype="application/json; charset=utf-8", code=200):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf8")
        elif isinstance(body, str):
            body = body.encode("utf8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _png(self, img):
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=1)
        self._send(buf.getvalue(), "image/png")

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def _status(self):
        values = engine.sensors.snapshot()
        values.update(engine.weather.values)
        return {"status": engine.status, "current": engine.current, "pinned": engine.pinned, "values": values,
                "video_errors": engine.video_errors, "fps_status": engine.sensors.fps.status(), **STATE}

    def _device_info(self):
        def query(lcd):
            total, used, free = lcd.storage()
            files = lcd.list_videos()
            return {"files": files, "sizes": {f: lcd.file_size(f) for f in files},
                    "total_kb": total, "used_kb": used, "free_kb": free}
        info = engine.device_call(query, timeout=30)
        ours = set(os.listdir(DEVICE_CACHE)) if os.path.isdir(DEVICE_CACHE) else set()
        info["ours"] = [f for f in info["files"] if f in ours]
        return info

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        path = url.path
        if path == "/":
            path = "/index.html"
        if path == "/api/state":
            return self._send({"config": engine.cfg, "catalog": CATALOG, "fonts": renderer.list_fonts(),
                               "media": media_list(), "ffmpeg": bool(engine.media.ffmpeg), **self._status()})
        if path == "/api/status":
            return self._send(self._status())
        if path == "/api/device":
            try:
                return self._send(self._device_info())
            except Exception as e:
                return self._send({"error": str(e)}, code=503)
        if path == "/api/skins":
            return self._send(themes.catalog())
        if path == "/api/layouts":
            return self._send([{"id": k, "name": v[0], "description": v[1]} for k, v in themes.LAYOUTS.items()])
        if path == "/api/skin_preview.png":  # uma tela do usuário desenhada com a skin pedida
            name = qs.get("name", [""])[0]
            skin = engine.cfg["skins"].get(name) or (themes.pack(name) or {}).get("skin")
            screens = [sc for sc in engine.cfg["screens"] if sc.get("kind") != "device_video"] or [themes.dashboard()]
            screen = screens[min(int(qs.get("screen", ["0"])[0] or 0), len(screens) - 1)]
            if not skin:
                return self._send({"error": "skin não encontrada"}, code=404)
            with engine.preview_lock:
                ctx = engine.context(screen, engine.preview_media)
                ctx.skin = skin
                img = renderer.render(screen, engine.logical_size(), ctx)
            img.thumbnail((400, 400))
            return self._png(img)
        m = re.fullmatch(r"/api/preview/(\d+)\.png", path)
        if m:
            return self._png(engine.render_preview(int(m.group(1))))
        if path == "/api/live.png":
            img = engine.last_frame or engine.render_preview(engine.current)
            return self._png(img)
        if path.startswith("/media/"):
            name = safe_name(path[7:])
            p = os.path.join(MEDIA_DIR, name or "")
            if name and os.path.isfile(p):
                with open(p, "rb") as f:
                    return self._send(f.read(), mimetypes.guess_type(p)[0] or "application/octet-stream")
        p = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if p.startswith(WEB_DIR) and os.path.isfile(p):
            with open(p, "rb") as f:
                return self._send(f.read(), (mimetypes.guess_type(p)[0] or "text/plain") + "; charset=utf-8")
        self._send({"error": "não encontrado"}, code=404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(url.query)
        try:
            if url.path == "/api/config":
                cfg = json.loads(self._body())
                engine.update_config(cfg)
                want = bool(cfg.get("settings", {}).get("autostart"))
                if not STATE["admin_task"] and want != autostart.is_enabled():
                    autostart.set_enabled(want)
                return self._send({"ok": True})
            if url.path == "/api/upload":
                name = safe_name(qs.get("name", [""])[0])
                if not name:
                    return self._send({"error": "tipo de arquivo não suportado"}, code=400)
                with open(os.path.join(MEDIA_DIR, name), "wb") as f:
                    f.write(self._body())
                return self._send({"ok": True, "name": name, "media": media_list()})
            if url.path == "/api/media/delete":
                name = safe_name(qs.get("name", [""])[0])
                if name and os.path.isfile(os.path.join(MEDIA_DIR, name)):
                    os.remove(os.path.join(MEDIA_DIR, name))
                return self._send({"ok": True, "media": media_list()})
            if url.path == "/api/device/delete":
                name = os.path.basename(qs.get("name", [""])[0])
                if not name.lower().endswith(".mp4"):
                    return self._send({"error": "nome inválido"}, code=400)
                engine.device_call(lambda lcd: lcd.delete_video(name), timeout=30)
                engine._video = None  # se era o vídeo tocando, a tela de vídeo envia de novo na próxima vez
                return self._send(self._device_info())
            if url.path == "/api/admin_mode":
                on = qs.get("on", ["1"])[0] == "1"
                code = autostart.run_elevated("--install-admin-task" if on else "--remove-admin-task")
                if code is None:
                    return self._send({"error": "permissão de administrador não concedida"}, code=403)
                if code != 0:
                    return self._send({"error": f"o Windows recusou (código {code})"}, code=500)
                STATE["admin_task"] = on
                if on:
                    threading.Timer(0.5, RESTART_ELEVATED).start()
                    return self._send({"ok": True, "restarting": True})
                if engine.cfg["settings"].get("autostart"):
                    autostart.set_enabled(True)
                return self._send({"ok": True})
            if url.path == "/api/skin/use":
                name = qs.get("name", [""])[0]
                cfg = json.loads(json.dumps(engine.cfg))
                if name not in cfg["skins"] and themes.pack(name):
                    cfg["skins"][name] = themes.pack(name)["skin"]
                if name not in cfg["skins"]:
                    return self._send({"error": "skin não encontrada"}, code=404)
                cfg["settings"]["skin"] = name
                engine.update_config(cfg)
                return self._send({"ok": True, "config": engine.cfg})
            if url.path == "/api/layout/add":
                lay = themes.LAYOUTS.get(qs.get("id", [""])[0])
                if not lay:
                    return self._send({"error": "tela pronta não encontrada"}, code=404)
                cfg = json.loads(json.dumps(engine.cfg))
                cfg["screens"].append(lay[2]())
                engine.update_config(cfg)
                return self._send({"ok": True, "config": engine.cfg, "index": len(cfg["screens"]) - 1})
            if url.path == "/api/control":
                cmd = json.loads(self._body())
                act = cmd.get("action")
                if act == "next":
                    engine.pinned = None
                    engine.step(1)
                elif act == "prev":
                    engine.pinned = None
                    engine.step(-1)
                elif act == "pin":
                    engine.pinned = int(cmd["index"])
                    engine.goto(engine.pinned)
                elif act == "unpin":
                    engine.pinned = None
                    engine.screen_started = time.time()
                return self._send(self._status())
        except Exception as e:
            return self._send({"error": str(e)}, code=500)
        self._send({"error": "não encontrado"}, code=404)


def already_running(url):
    try:
        urllib.request.urlopen(url + "api/status", timeout=1.5)
        return True
    except Exception:
        return False


def main():
    global engine, RESTART_ELEVATED
    args = set(sys.argv[1:])
    if "--install-admin-task" in args:  # chamado elevado pelo próprio app
        sys.exit(autostart.install_task())
    if "--remove-admin-task" in args:
        sys.exit(autostart.remove_task())
    ensure_data_dir()
    if getattr(sys, "frozen", False):  # sem console: mensagens vão para o log
        sys.stdout = sys.stderr = open(LOG_PATH, "a", encoding="utf8", buffering=1)
    url = f"http://{HOST}:{PORT}/"
    if already_running(url):  # segunda execução: só abre o editor da que já está rodando
        if "--background" not in args:
            webbrowser.open(url)
        return
    engine = Engine()
    STATE["admin_task"] = autostart.task_installed()
    engine.cfg["settings"]["autostart"] = STATE["admin_task"] or autostart.is_enabled()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    engine.start()
    print(f"{time.ctime()} TURZX Studio rodando em {url}")
    if not args & {"--background", "--no-browser"}:
        threading.Timer(1.0, webbrowser.open, [url]).start()

    def quit_app():
        engine.stop()
        engine.sensors.fps.presentmon.stop()
        server.shutdown()
        server.server_close()

    def restart_elevated():
        """Fecha esta instância (porta serial e servidor) e abre a versão elevada pela tarefa agendada."""
        quit_app()
        engine.thread.join(10)
        autostart.run_task()
        import tray
        tray.stop()

    RESTART_ELEVATED = restart_elevated

    try:
        if "--no-tray" in args:
            while True:
                time.sleep(3600)
        else:
            import tray
            tray.run(engine, url, quit_app)
    except KeyboardInterrupt:
        quit_app()


if __name__ == "__main__":
    main()
