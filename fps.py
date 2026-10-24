"""FPS do jogo em primeiro plano.

Fontes, em ordem de preferência:
1. PresentMon (Intel, MIT): mede pelos eventos de quadros do próprio Windows (ETW), sem entrar no jogo,
   então funciona em qualquer jogo e placa (inclusive o CS2, que bloqueia o RivaTuner). O Windows só
   libera essa medição para programas executados como administrador (o app original da TURZX faz o mesmo).
2. RivaTuner Statistics Server (vem com o MSI Afterburner): memória compartilhada "RTSSSharedMemoryV2",
   conforme o RTSSSharedMemory.h do SDK do RTSS.
"""
import ctypes
import os
import struct
import subprocess
import tempfile
import threading
import time
from collections import deque
from ctypes import wintypes

from paths import RES_DIR

_u32 = ctypes.WinDLL("user32")
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)


def foreground_pid():
    pid = wintypes.DWORD()
    _u32.GetWindowThreadProcessId(_u32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


# ---------------------------------------------------------------- PresentMon

PRESENTMON = os.path.join(RES_DIR, "tools", "PresentMon.exe")
SESSION = "TURZXStudio"
WINDOW_SECONDS = 2


class PresentMonSource:
    """Mede o FPS em janelas curtas: o PresentMon captura ~1 s, fecha o arquivo e o app lê.

    Ler a saída enquanto ele grava não funciona: pelo pipe os dados ficam presos no buffer, e o
    arquivo fica trancado até ele terminar."""

    def __init__(self, exe=PRESENTMON):
        self.exe = exe
        self.error = "" if os.path.isfile(exe) else "PresentMon não encontrado"
        self.running = False
        self._latest = {}  # pid -> (instante, fps, ms, nome)
        self._lock = threading.Lock()
        self._proc = None
        self._stopped = False
        self.debug = {"ciclos": 0}
        if not self.error:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        path = os.path.join(tempfile.gettempdir(), f"turzx-studio-presentmon-{os.getpid()}.csv")
        cmd = [self.exe, "--output_file", path, "--no_console_stats", "--stop_existing_session",
               "--session_name", SESSION, "--v1_metrics", "--no_track_input", "--exclude", "dwm.exe",
               "--timed", str(WINDOW_SECONDS), "--terminate_after_timed"]
        while not self._stopped:
            try:
                os.remove(path)
            except OSError:
                pass
            try:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                              creationflags=0x08000000)
                _, err = self._proc.communicate(timeout=WINDOW_SECONDS + 15)
            except (OSError, subprocess.TimeoutExpired) as e:
                self.stop()
                self.error, self.running = str(e), False
                time.sleep(5)
                continue
            self.debug.update(ciclos=self.debug["ciclos"] + 1, arquivo=path, existe=os.path.isfile(path),
                              stderr=(err or "").strip()[-300:])
            if not os.path.isfile(path):
                self.running = False
                if "access denied" in (err or "").lower():
                    self.error = "precisa ser executado como administrador"
                    return  # sem permissão não adianta insistir; vale o RivaTuner
                self.error = (err or "").strip().splitlines()[-1] if (err or "").strip() else "PresentMon não iniciou"
                time.sleep(5)
                continue
            try:
                self._parse(path)
                self.error, self.running = "", True
            except OSError as e:
                self.error, self.running = str(e), False
                time.sleep(2)

    def _parse(self, path):
        frames, names = {}, {}
        with open(path, encoding="utf-8-sig", errors="replace") as f:  # o PresentMon grava com BOM
            header = [c.strip().lower() for c in f.readline().split(",")]  # ex.: "msBetweenPresents"
            try:
                i_app, i_pid, i_ms = (header.index(c) for c in ("application", "processid", "msbetweenpresents"))
            except ValueError:
                self.debug["cabecalho"] = header[:12]
                return
            for line in f:
                parts = line.split(",")
                try:
                    pid, ms = int(parts[i_pid]), float(parts[i_ms])
                except (ValueError, IndexError):
                    continue
                if ms > 0:
                    frames.setdefault(pid, []).append(ms)
                    names[pid] = parts[i_app]
        now = time.monotonic()
        self.debug["processos"] = sorted(((names[p], p, len(m)) for p, m in frames.items()), key=lambda x: -x[2])[:6]
        self.debug["primeiro_plano"] = foreground_pid()
        with self._lock:
            for pid, ms in frames.items():
                if len(ms) >= 2:
                    avg = sum(ms) / len(ms)
                    self._latest[pid] = (now, round(1000 / avg), round(avg, 1), names[pid])

    def stop(self):
        self._stopped = True
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        try:
            os.remove(os.path.join(tempfile.gettempdir(), f"turzx-studio-presentmon-{os.getpid()}.csv"))
        except OSError:
            pass

    def read(self):
        """FPS do processo em primeiro plano, da última janela de captura."""
        if not self.running:
            return {}
        with self._lock:
            hit = self._latest.get(foreground_pid())
        if not hit or time.monotonic() - hit[0] > 4:
            return {}
        _, fps, ms, name = hit
        return {"fps": fps, "frametime": ms, "fps_app": os.path.splitext(name)[0], "fps_source": "PresentMon"}


# ---------------------------------------------------------------- RivaTuner (RTSS)

FILE_MAP_READ = 0x0004
SIGNATURE = 0x52545353  # 'RTSS'
MAX_PATH = 260
HEADER = struct.Struct("<5I")  # assinatura, versão, tamanho da entrada, offset e quantidade das entradas
ENTRY = struct.Struct(f"<I{MAX_PATH}s5I")  # pid, nome, flags, time0, time1, frames, frametime (µs)

_k32.OpenFileMappingW.restype = wintypes.HANDLE
_k32.OpenFileMappingW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
_k32.MapViewOfFile.restype = ctypes.c_void_p
_k32.MapViewOfFile.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t)
_k32.UnmapViewOfFile.argtypes = (ctypes.c_void_p,)
_k32.CloseHandle.argtypes = (wintypes.HANDLE,)
_k32.GetTickCount.restype = wintypes.DWORD


def rtss_running():
    h = _k32.OpenFileMappingW(FILE_MAP_READ, False, "RTSSSharedMemoryV2")
    if h:
        _k32.CloseHandle(h)
    return bool(h)


def read_rtss():
    handle = _k32.OpenFileMappingW(FILE_MAP_READ, False, "RTSSSharedMemoryV2")
    if not handle:
        return {}
    view = _k32.MapViewOfFile(handle, FILE_MAP_READ, 0, 0, 0)
    try:
        if not view:
            return {}
        sig, ver, entry_size, arr_offset, arr_count = HEADER.unpack(ctypes.string_at(view, HEADER.size))
        if sig != SIGNATURE or entry_size < ENTRY.size or arr_count > 1024:
            return {}
        data = ctypes.string_at(view + arr_offset, entry_size * arr_count)
    finally:
        if view:
            _k32.UnmapViewOfFile(view)
        _k32.CloseHandle(handle)

    now_ms = _k32.GetTickCount()  # o RTSS usa o mesmo relógio nos campos time0/time1
    fg = foreground_pid()
    best = None
    for i in range(arr_count):
        pid, name, _flags, t0, t1, frames, frametime = ENTRY.unpack_from(data, i * entry_size)
        if not pid or t1 <= t0 or not frames or (now_ms - t1) & 0xFFFFFFFF > 3000:
            continue
        app = os.path.splitext(os.path.basename(name.split(b"\0", 1)[0].decode("latin1")))[0]
        cand = (pid == fg, t1, {"fps": round(1000.0 * frames / (t1 - t0)), "frametime": round(frametime / 1000, 1),
                                "fps_app": app, "fps_source": "RivaTuner"})
        if best is None or cand[:2] > best[:2]:
            best = cand
    return best[2] if best else {}


# ---------------------------------------------------------------- fonte combinada

class FpsReader:
    def __init__(self):
        self.presentmon = PresentMonSource()

    def read(self):
        return self.presentmon.read() or read_rtss()

    def status(self):
        pm = self.presentmon
        if pm.running:
            return "PresentMon"
        return pm.error or "iniciando"
