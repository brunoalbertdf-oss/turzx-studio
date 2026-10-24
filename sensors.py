"""Coleta de dados do PC.

Fontes:
- psutil: CPU, RAM, disco, rede, uptime.
- Windows (WMI): nome e fabricante da CPU e da GPU.
- nvidia-smi: GPU NVIDIA (uso, temperatura, memória, potência, ventoinha).
- LibreHardwareMonitor (opcional): temperatura/potência da CPU e dados de GPUs AMD/Intel, via o
  "Remote Web Server" dele (Options > Remote Web Server > Run, porta 8085).
"""
import ctypes
import json
import platform
import re
import subprocess
import threading
import time
import urllib.request
from collections import deque
from datetime import datetime

import psutil

from fps import read_fps

DAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
HISTORY_LEN = 120

# Descrição dos valores disponíveis (mostrada no editor).
CATALOG = {
    "cpu_percent": "Uso da CPU (%)", "cpu_freq": "Frequência da CPU (MHz)", "cpu_temp": "Temperatura da CPU (°C) *LHM",
    "cpu_power": "Potência da CPU (W) *LHM", "cpu_name": "Modelo da CPU (curto)", "cpu_name_full": "Modelo da CPU (completo)",
    "cpu_vendor": "Fabricante da CPU", "cpu_cores": "Núcleos / threads",
    "ram_percent": "Uso da RAM (%)", "ram_used": "RAM usada (GB)", "ram_total": "RAM total (GB)",
    "gpu_percent": "Uso da GPU (%)", "gpu_temp": "Temperatura da GPU (°C)", "gpu_mem_percent": "VRAM usada (%)",
    "gpu_mem_used": "VRAM usada (GB)", "gpu_power": "Potência da GPU (W)", "gpu_fan": "Ventoinha da GPU (%)",
    "gpu_clock": "Clock da GPU (MHz)", "gpu_name": "Modelo da GPU (curto)", "gpu_name_full": "Modelo da GPU (completo)",
    "gpu_vendor": "Fabricante da GPU", "gpu_mem_total": "VRAM total (GB)",
    "fps": "FPS do jogo *RivaTuner", "frametime": "Tempo de quadro (ms) *RivaTuner", "fps_app": "Jogo medido",
    "disk_percent": "Uso do disco C: (%)", "net_down": "Download (KB/s)", "net_up": "Upload (KB/s)",
    "uptime": "Tempo ligado", "time": "Hora (HH:MM)", "time_s": "Hora (HH:MM:SS)", "date": "Data (dd/mm/aaaa)",
    "weekday": "Dia da semana", "day": "Dia", "month": "Mês abreviado", "hostname": "Nome do PC",
    "weather_city": "Cidade", "weather_temp": "Temperatura (°C)", "weather_feels": "Sensação (°C)",
    "weather_desc": "Condição do tempo", "weather_hum": "Umidade (%)", "weather_wind": "Vento (km/h)",
    "weather_max": "Máxima de hoje (°C)", "weather_min": "Mínima de hoje (°C)", "weather_rain": "Chance de chuva (%)",
}


def vendor_of(name):
    n = (name or "").lower()
    if "nvidia" in n or "geforce" in n or "quadro" in n or re.search(r"\b(rtx|gtx)\b", n):
        return "NVIDIA"
    if "amd" in n or "radeon" in n or "ryzen" in n or "athlon" in n or "threadripper" in n:
        return "AMD"
    if "intel" in n or "core(tm)" in n or "arc" in n.split():
        return "Intel"
    return ""


def short_cpu(name):
    n = re.sub(r"\((R|TM)\)", "", name or "", flags=re.I)
    n = re.sub(r"\b(AMD|Intel|Processor|CPU|with Radeon Graphics)\b", "", n, flags=re.I)
    n = re.sub(r"\d+-Core|@.*$", "", n)
    return re.sub(r"\s+", " ", n).strip()


def short_gpu(name):
    n = re.sub(r"\((R|TM)\)", "", name or "", flags=re.I)
    n = re.sub(r"\b(NVIDIA|GeForce|AMD|Intel|Graphics|Laptop GPU)\b", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip() or name


def _volume_label(root):
    buf = ctypes.create_unicode_buffer(261)
    try:
        ok = ctypes.windll.kernel32.GetVolumeInformationW(root, buf, 261, None, None, None, None, 0)
        return buf.value if ok else ""
    except Exception:
        return ""


def read_drives():
    """Unidades fixas (HD/SSD) com uso em GB."""
    drives = []
    for p in psutil.disk_partitions(all=False):
        if "fixed" not in p.opts.lower() and p.fstype == "":
            continue
        if "cdrom" in p.opts.lower() or "removable" in p.opts.lower():
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        letter = p.device[:1].upper()
        drives.append({"letter": letter, "label": _volume_label(p.mountpoint), "percent": u.percent,
                       "used": round(u.used / 2**30), "total": round(u.total / 2**30), "free": round(u.free / 2**30)})
    return drives


def drive_values(drives):
    v = {}
    for d in drives:
        k = d["letter"].lower()
        v.update({f"disk_{k}_percent": d["percent"], f"disk_{k}_used": d["used"], f"disk_{k}_total": d["total"],
                  f"disk_{k}_free": d["free"], f"disk_{k}_label": d["label"] or f"Disco {d['letter']}:"})
    return v


def _hardware():
    """Nomes da CPU e da GPU principal pelo Windows (funciona com NVIDIA, AMD e Intel)."""
    ps = ("$c=Get-CimInstance Win32_Processor | Select-Object -First 1;"
          "$g=Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM;"
          "@{cpu=$c.Name;cores=$c.NumberOfCores;threads=$c.NumberOfLogicalProcessors;gpus=@($g)} | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True,
                             timeout=15, creationflags=0x08000000).stdout
        d = json.loads(out)
    except Exception:
        d = {"cpu": platform.processor(), "gpus": []}
    gpus = [g for g in d.get("gpus") or [] if g and g.get("Name") and "basic" not in g["Name"].lower()
            and "virtual" not in g["Name"].lower()]
    # prefere a placa dedicada: NVIDIA/AMD antes da Intel integrada
    gpus.sort(key=lambda g: {"NVIDIA": 0, "AMD": 1, "Intel": 2}.get(vendor_of(g["Name"]), 3))
    cpu = (d.get("cpu") or "").strip()
    gpu = gpus[0]["Name"].strip() if gpus else ""
    return {"cpu_name_full": cpu, "cpu_name": short_cpu(cpu), "cpu_vendor": vendor_of(cpu),
            "cpu_cores": f"{d.get('cores', '?')}C / {d.get('threads', '?')}T",
            "gpu_name_full": gpu, "gpu_name": short_gpu(gpu), "gpu_vendor": vendor_of(gpu)}


class Sensors:
    def __init__(self, lhm_url="http://127.0.0.1:8085/data.json"):
        self.lhm_url = lhm_url
        self.values = {k: 0 for k in CATALOG}
        self.values.update(_hardware(), hostname=platform.node(), cpu_temp="—", cpu_power="—")
        self.drives = read_drives()
        self._drives_t = time.time()
        self.values.update(drive_values(self.drives))
        for d in self.drives:  # aparecem na lista de valores do editor
            k, name = d["letter"].lower(), f"{d['letter']}:"
            CATALOG.update({f"disk_{k}_percent": f"Uso do disco {name} (%)", f"disk_{k}_free": f"Livre em {name} (GB)",
                            f"disk_{k}_used": f"Usado em {name} (GB)", f"disk_{k}_total": f"Tamanho de {name} (GB)",
                            f"disk_{k}_label": f"Nome do volume {name}"})
        self.history = {k: deque([0] * HISTORY_LEN, maxlen=HISTORY_LEN)
                        for k in ("cpu_percent", "ram_percent", "gpu_percent", "gpu_temp", "cpu_temp", "fps",
                                  "net_down", "net_up")}
        self._net = psutil.net_io_counters()
        self._net_t = time.time()
        self._lock = threading.Lock()
        psutil.cpu_percent()
        threading.Thread(target=self._loop, daemon=True).start()

    def snapshot(self):
        with self._lock:
            v = dict(self.values)
        now = datetime.now()
        v.update(time=now.strftime("%H:%M"), time_s=now.strftime("%H:%M:%S"), date=now.strftime("%d/%m/%Y"),
                 weekday=DAYS[now.weekday()], day=now.day, month=MONTHS[now.month - 1])
        return v

    def _loop(self):
        while True:
            try:
                self._poll()
            except Exception as e:  # sensor com problema não pode derrubar o app
                print("sensores:", e)
            time.sleep(1)

    def _poll(self):
        v = {}
        v["cpu_percent"] = psutil.cpu_percent()
        f = psutil.cpu_freq()
        v["cpu_freq"] = round(f.current) if f else 0
        m = psutil.virtual_memory()
        v["ram_percent"] = m.percent
        v["ram_used"] = round(m.used / 2**30, 1)
        v["ram_total"] = round(m.total / 2**30, 1)
        if time.time() - self._drives_t > 30:
            self.drives = read_drives()
            self._drives_t = time.time()
        v.update(drive_values(self.drives))
        v["disk_percent"] = v.get("disk_c_percent", 0)
        n, t = psutil.net_io_counters(), time.time()
        dt = max(t - self._net_t, 0.001)
        v["net_down"] = round((n.bytes_recv - self._net.bytes_recv) / 1024 / dt)
        v["net_up"] = round((n.bytes_sent - self._net.bytes_sent) / 1024 / dt)
        self._net, self._net_t = n, t
        up = int(time.time() - psutil.boot_time())
        v["uptime"] = f"{up // 86400}d {up % 86400 // 3600:02d}h{up % 3600 // 60:02d}"
        try:
            v.update(read_fps() or {"fps": "—", "frametime": "—", "fps_app": ""})
        except Exception:
            v.update(fps="—", frametime="—", fps_app="")
        v.update(self._nvidia())
        v.update(self._lhm())
        with self._lock:
            self.values.update(v)
            for k, h in self.history.items():
                val = self.values.get(k, 0)
                h.append(val if isinstance(val, (int, float)) else 0)

    def _nvidia(self):
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total,"
                 "power.draw,fan.speed,clocks.gr", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, creationflags=0x08000000).stdout
            name, util, temp, mu, mt, pw, fan, clk = [x.strip() for x in out.splitlines()[0].split(",")]
            num = lambda s: float(s) if s.replace(".", "", 1).isdigit() else 0
            return {"gpu_percent": num(util), "gpu_temp": num(temp), "gpu_mem_total": round(num(mt) / 1024, 1),
                    "gpu_mem_used": round(num(mu) / 1024, 1),
                    "gpu_mem_percent": round(num(mu) / max(num(mt), 1) * 100), "gpu_power": round(num(pw)),
                    "gpu_fan": num(fan), "gpu_clock": num(clk)}
        except Exception:
            return {}

    def _lhm(self):
        """Lê temperatura e potência da CPU do LibreHardwareMonitor, se estiver rodando."""
        try:
            data = json.load(urllib.request.urlopen(self.lhm_url, timeout=0.5))
        except Exception:
            return {}
        found = {}

        def walk(node, path):
            text = node.get("Text", "")
            if node.get("Value") and not node.get("Children"):
                p = " / ".join(path + [text]).lower()
                val = node["Value"].split()[0].replace(",", ".")
                try:
                    val = float(val)
                except ValueError:
                    return
                if "temperatures" in p and ("tctl" in p or "package" in p or "cpu" in text.lower()) \
                        and ("ryzen" in p or "intel" in p or "cpu" in p) and "cpu_temp" not in found:
                    found["cpu_temp"] = round(val)
                if "powers" in p and "package" in p and "cpu_power" not in found:
                    found["cpu_power"] = round(val)
            for c in node.get("Children", []):
                walk(c, path + [text])

        walk(data, [])
        return found
