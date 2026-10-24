"""FPS do jogo em primeiro plano.

Fontes, em ordem de preferência:
1. PresentMon (Intel, MIT): mede pelo próprio Windows (ETW), com qualquer placa de vídeo.
   O Windows só permite isso a programas executados como administrador.
2. RivaTuner Statistics Server (vem com o MSI Afterburner): memória compartilhada
   "RTSSSharedMemoryV2", conforme o RTSSSharedMemory.h do SDK do RTSS.
"""
import ctypes
import os
import struct
import subprocess
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


class PresentMonSource:
    """Mantém o PresentMon rodando e guarda o tempo entre quadros de cada processo."""

    def __init__(self, exe=PRESENTMON):
        self.exe = exe
        self.error = "" if os.path.isfile(exe) else "PresentMon não encontrado"
        self.running = False
        self._frames = {}  # pid -> deque[(instante, ms entre quadros)]
        self._names = {}
        self._lock = threading.Lock()
        self._proc = None
        if not self.error:
            threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while True:
            self._run_once()
            if "administrador" in self.error:
                return  # sem permissão não adianta insistir; vale o RivaTuner
            time.sleep(10)

    def _run_once(self):
        cmd = [self.exe, "--output_stdout", "--no_console_stats", "--stop_existing_session",
               "--session_name", SESSION, "--v1_metrics", "--no_track_input", "--exclude", "dwm.exe"]
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                          creationflags=0x08000000)
        except OSError as e:
            self.error = str(e)
            return
        header = self._proc.stdout.readline().strip().split(",")
        try:
            i_app, i_pid, i_ms = (header.index(c) for c in ("Application", "ProcessID", "MsBetweenPresents"))
        except ValueError:
            err = self._proc.stderr.read()
            self.error = ("precisa ser executado como administrador" if "access denied" in err.lower()
                          else err.strip().splitlines()[-1] if err.strip() else "PresentMon não iniciou")
            self._proc.wait()
            return
        self.error, self.running = "", True
        for line in self._proc.stdout:
            parts = line.split(",")
            try:
                pid, ms = int(parts[i_pid]), float(parts[i_ms])
            except (ValueError, IndexError):
                continue
            with self._lock:
                q = self._frames.setdefault(pid, deque(maxlen=2000))
                q.append((time.monotonic(), ms))
                self._names[pid] = parts[i_app]
        self.running = False

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()

    def read(self):
        """FPS do processo em primeiro plano, medido no último segundo."""
        if not self.running:
            return {}
        pid = foreground_pid()
        now = time.monotonic()
        with self._lock:
            q = self._frames.get(pid)
            recent = [ms for t, ms in q if now - t <= 1.0] if q else []
            name = self._names.get(pid, "")
        if len(recent) < 2:
            return {}
        avg = sum(recent) / len(recent)
        return {"fps": round(1000 / avg) if avg > 0 else 0, "frametime": round(avg, 1),
                "fps_app": os.path.splitext(name)[0], "fps_source": "PresentMon"}


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
            return "PresentMon (nativo do Windows)"
        return f"RivaTuner (PresentMon: {pm.error or 'iniciando'})"
