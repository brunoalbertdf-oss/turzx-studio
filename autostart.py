"""Iniciar com o Windows.

Modo normal: entrada em HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run (só do usuário atual).
Modo administrador (necessário para o FPS nativo via PresentMon): tarefa no Agendador de Tarefas
que abre o programa elevado ao fazer login, sem pedir confirmação toda vez. Criar ou remover a
tarefa pede permissão de administrador (UAC) uma vez.
"""
import ctypes
import os
import subprocess
import sys
import tempfile
import winreg
from ctypes import wintypes

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE = TASK = "TURZX Studio"
NO_WINDOW = 0x08000000


def _program():
    """(executável, argumentos base) para abrir o TURZX Studio."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return pythonw, f'"{os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")}"'


def command():
    exe, base = _program()
    return f'"{exe}" {base} --background'.replace("  ", " ")


# ---------------------------------------------------------------- modo normal (registro)

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


# ---------------------------------------------------------------- modo administrador (tarefa agendada)

def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def task_installed():
    r = subprocess.run(["schtasks", "/Query", "/TN", TASK], capture_output=True, creationflags=NO_WINDOW)
    return r.returncode == 0


def _task_xml():
    exe, base = _program()
    user = f'{os.environ.get("USERDOMAIN", "")}\\{os.environ.get("USERNAME", "")}'
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Abre o TURZX Studio ao fazer login (como administrador, para medir FPS).</Description></RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{esc(user)}</UserId><Delay>PT10S</Delay></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{esc(user)}</UserId><LogonType>InteractiveToken</LogonType>
    <RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>6</Priority>
  </Settings>
  <Actions Context="Author"><Exec><Command>{esc(exe)}</Command><Arguments>{esc((base + " --background").strip())}</Arguments>
    <WorkingDirectory>{esc(os.path.dirname(exe))}</WorkingDirectory></Exec></Actions>
</Task>"""


def _log(msg):
    try:
        from paths import LOG_PATH
        with open(LOG_PATH, "a", encoding="utf8") as f:
            f.write(msg.strip() + "\n")
    except OSError:
        pass


def install_task():
    """Executar já elevado: cria a tarefa e desliga a entrada normal do registro."""
    path = os.path.join(tempfile.gettempdir(), "turzx-studio-task.xml")
    with open(path, "w", encoding="utf-16") as f:
        f.write(_task_xml())
    r = subprocess.run(["schtasks", "/Create", "/F", "/TN", TASK, "/XML", path], capture_output=True,
                       creationflags=NO_WINDOW)
    os.remove(path)
    _log(f"criar tarefa: código {r.returncode} {r.stdout.decode('cp850', 'replace')} {r.stderr.decode('cp850', 'replace')}")
    if r.returncode == 0:
        set_enabled(False)
    return r.returncode


def remove_task():
    """Executar já elevado."""
    return subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK], capture_output=True,
                          creationflags=NO_WINDOW).returncode


def run_task():
    """Inicia a tarefa (o programa abre elevado, sem pedir confirmação)."""
    return subprocess.run(["schtasks", "/Run", "/TN", TASK], capture_output=True, creationflags=NO_WINDOW).returncode


class _SHELLEXECUTEINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong), ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]


def run_elevated(flag):
    """Roda este programa com 'flag' como administrador (mostra o UAC) e espera. Retorna o código de saída,
    ou None se o usuário recusar.

    A janela de permissão fica vinculada à janela em primeiro plano (o navegador com o editor): sem uma
    janela dona, o Windows a mostra minimizada, piscando na barra de tarefas, e parece que nada aconteceu."""
    exe, base = _program()
    owner = ctypes.windll.user32.GetForegroundWindow()
    info = _SHELLEXECUTEINFO(cbSize=ctypes.sizeof(_SHELLEXECUTEINFO), fMask=0x40, hwnd=owner, lpVerb="runas",
                             lpFile=exe, lpParameters=f"{base} {flag}".strip(), nShow=0)
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)):
        return None
    ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, 300000)
    code = wintypes.DWORD()
    ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(info.hProcess)
    return code.value
