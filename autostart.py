"""Iniciar com o Windows: entrada em HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run (só do usuário atual)."""
import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = "TURZX Studio"


def command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    app = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")
    return f'"{pythonw}" "{app}" --background'


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, VALUE)[0] == command()
    except OSError:
        return False


def set_enabled(enabled):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, VALUE, 0, winreg.REG_SZ, command())
        else:
            try:
                winreg.DeleteValue(k, VALUE)
            except FileNotFoundError:
                pass
