"""Avisos do Windows de desligamento, logoff e suspensão.

Muitas placas-mãe mantêm a USB alimentada com o PC desligado: sem este aviso, a tela ficaria acesa
mostrando o último quadro. Uma janela oculta (não exibida) recebe as mensagens do sistema.
"""
import ctypes
import threading
from ctypes import wintypes

WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMESUSPEND = 0x0007
PBT_APMRESUMEAUTOMATIC = 0x0012

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

_u32 = ctypes.WinDLL("user32", use_last_error=True)
_u32.DefWindowProcW.restype = LRESULT
_u32.DefWindowProcW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
_u32.CreateWindowExW.restype = wintypes.HWND
_u32.CreateWindowExW.argtypes = (wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int,
                                 ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU,
                                 wintypes.HINSTANCE, wintypes.LPVOID)
_u32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT)


class _WNDCLASS(ctypes.Structure):
    _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH), ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR)]


def watch(on_off, on_resume):
    """on_off(): PC desligando, reiniciando, fazendo logoff ou suspendendo. on_resume(): voltou da suspensão."""

    def proc(hwnd, msg, wparam, lparam):
        if msg == WM_ENDSESSION and wparam:  # desligamento/logoff confirmado: ~5 s para terminar
            on_off()
            return 0
        if msg == WM_QUERYENDSESSION:
            return 1  # não impede o desligamento
        if msg == WM_POWERBROADCAST:
            if wparam == PBT_APMSUSPEND:
                on_off()
            elif wparam in (PBT_APMRESUMESUSPEND, PBT_APMRESUMEAUTOMATIC):
                on_resume()
            return 1
        return _u32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def loop():
        callback = WNDPROC(proc)  # referência mantida enquanto a thread vive
        hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
        wc = _WNDCLASS(lpfnWndProc=callback, hInstance=hinst, lpszClassName="TURZXStudioPower")
        _u32.RegisterClassW(ctypes.byref(wc))
        # janela de nível superior (não exibida): janelas "message-only" não recebem esses avisos
        _u32.CreateWindowExW(0, "TURZXStudioPower", "TURZX Studio", 0, 0, 0, 0, 0, None, None, hinst, None)
        msg = wintypes.MSG()
        while _u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            _u32.TranslateMessage(ctypes.byref(msg))
            _u32.DispatchMessageW(ctypes.byref(msg))

    threading.Thread(target=loop, daemon=True, name="avisos-do-windows").start()
