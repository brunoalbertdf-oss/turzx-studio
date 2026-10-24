"""Sensores do MSI Afterburner (memória compartilhada "MAHMSharedMemory").

O Afterburner roda como administrador e mede o que o Windows não expõe a programas comuns:
temperatura e potência da CPU, além de todos os dados da GPU (NVIDIA, AMD ou Intel).
Layout conforme o MAHMSharedMemory.h do SDK do Afterburner.
"""
import ctypes
import struct
from ctypes import wintypes

SIGNATURE = 0x4D41484D  # 'MAHM'
HEADER = struct.Struct("<5Ii")  # assinatura, versão, tamanho do cabeçalho, nº de entradas, tamanho da entrada, hora
MAX_PATH = 260
DATA_OFFSET = 5 * MAX_PATH  # nome, unidade, nome traduzido, unidade traduzida, formato; depois o valor (float)
NO_DATA = 1e30  # o Afterburner usa FLT_MAX quando não há leitura (ex.: Framerate sem jogo aberto)

_k32 = ctypes.WinDLL("kernel32")
_k32.OpenFileMappingW.restype = wintypes.HANDLE
_k32.OpenFileMappingW.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR)
_k32.MapViewOfFile.restype = ctypes.c_void_p
_k32.MapViewOfFile.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t)
_k32.UnmapViewOfFile.argtypes = (ctypes.c_void_p,)
_k32.CloseHandle.argtypes = (wintypes.HANDLE,)

# Nome do sensor no Afterburner -> (valor do TURZX Studio, conversão)
MAP = {
    "CPU temperature": ("cpu_temp", round),
    "CPU power": ("cpu_power", round),
    "CPU clock": ("cpu_freq", round),
    "GPU temperature": ("gpu_temp", round),
    "GPU usage": ("gpu_percent", round),
    "Power": ("gpu_power", round),
    "Fan speed": ("gpu_fan", round),
    "Core clock": ("gpu_clock", round),
    "Memory usage": ("gpu_mem_used", lambda mb: round(mb / 1024, 1)),
    "Framerate": ("fps", round),
    "Frametime": ("frametime", lambda ms: round(ms, 1)),
}


def read_raw():
    """{nome do sensor: valor} de tudo que o Afterburner está monitorando, ou None se ele não estiver aberto."""
    handle = _k32.OpenFileMappingW(0x0004, False, "MAHMSharedMemory")
    if not handle:
        return None
    view = _k32.MapViewOfFile(handle, 0x0004, 0, 0, 0)
    try:
        if not view:
            return None
        sig, _ver, hsize, count, esize, _t = HEADER.unpack(ctypes.string_at(view, HEADER.size))
        if sig != SIGNATURE or esize < DATA_OFFSET + 4 or count > 4096:
            return None  # assinatura "DEAD" = Afterburner fechando
        blob = ctypes.string_at(view + hsize, esize * count)
    finally:
        if view:
            _k32.UnmapViewOfFile(view)
        _k32.CloseHandle(handle)
    out = {}
    for i in range(count):
        e = blob[i * esize:(i + 1) * esize]
        name = e[:MAX_PATH].split(b"\0", 1)[0].decode("latin1")
        value = struct.unpack_from("<f", e, DATA_OFFSET)[0]
        if name and name not in out and abs(value) < NO_DATA:  # 1ª ocorrência = 1ª GPU
            out[name] = value
    return out


def read():
    """Valores no formato do TURZX Studio. {} se o Afterburner não estiver aberto."""
    raw = read_raw()
    if raw is None:
        return {}
    v = {"afterburner": True}
    for name, (key, conv) in MAP.items():
        if name in raw:
            v[key] = conv(raw[name])
    if v.get("fps"):
        v["fps_source"] = "Afterburner"
    else:  # 0 = nenhum jogo sendo medido
        v.pop("fps", None)
        v.pop("frametime", None)
    return v
