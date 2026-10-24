"""FPS do jogo em primeiro plano, lido do RivaTuner Statistics Server (vem com o MSI Afterburner).

Memória compartilhada "RTSSSharedMemoryV2", conforme o RTSSSharedMemory.h do SDK do RTSS.
O RTSS precisa estar aberto antes do jogo. Jogos com proteção contra injeção (ex.: CS2 no
"Trusted Mode") não deixam o RTSS medir.
"""
import ctypes
import os
import struct
from ctypes import wintypes

_u32 = ctypes.WinDLL("user32")
_k32 = ctypes.WinDLL("kernel32", use_last_error=True)


def foreground_pid():
    pid = wintypes.DWORD()
    _u32.GetWindowThreadProcessId(_u32.GetForegroundWindow(), ctypes.byref(pid))
    return pid.value


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
