"""Driver para a tela TURZX / Turing Smart Screen 5" (Rev C, 480x800).

Protocolo serial (115200 baud). Os comandos são enviados em blocos de 250 bytes.
O buffer nativo da tela é em paisagem: 800 x 480.
"""
import math
import os
import time

import serial
from serial.tools import list_ports
from PIL import Image

WIDTH, HEIGHT = 800, 480  # paisagem nativa

HELLO = bytes((0x01, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0xC5, 0xD3))
SET_BRIGHTNESS = bytes((0x7B, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00))
TURN_OFF = bytes((0x83, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01))
STOP_VIDEO = bytes((0x79, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01))
STOP_MEDIA = bytes((0x96, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01))
QUERY_STATUS = bytes((0xCF, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01))
PRE_UPDATE_BITMAP = bytes((0x86, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01))
START_DISPLAY_BITMAP = bytes((0x2C,))
DISPLAY_BITMAP_5INCH = bytes((0xC8, 0xEF, 0x69, 0x00, 0x17, 0x70))
UPDATE_BITMAP = bytes((0xCC, 0xEF, 0x69, 0x00))
RESTART = bytes((0x84, 0xEF, 0x69, 0x00, 0x00, 0x00, 0x01))


class ScreenDesync(RuntimeError):
    """A tela perdeu a sincronia e só volta reiniciando."""

TRACE = {"on": False}
TRACE_PATH = os.path.join(os.environ.get("TEMP", "."), "turzx-trace.log")


def _trace(msg, t):
    with open(TRACE_PATH, "a", encoding="utf8") as f:
        f.write(f"{time.strftime('%H:%M:%S', time.localtime(t))}.{int(t * 1000) % 1000:03d} {msg}" + chr(10))


AWAKE_IDS = {(0x1D6B, 0x0121), (0x1D6B, 0x0106), (0x0525, 0xA4A7)}


def find_port():
    for p in list_ports.comports():
        if (p.vid, p.pid) in AWAKE_IDS or p.serial_number == "20080411":
            return p.device
    raise RuntimeError("Tela TURZX não encontrada. Ela está conectada e o TURZX fechado?")


def _pad(data: bytes, fill: int = 0x00) -> bytes:
    size = 250 * math.ceil(len(data) / 250)
    return data + bytes((fill,)) * (size - len(data))


def _chunk_join(data: bytes, size: int = 249) -> bytes:
    return b"\x00".join(data[i:i + size] for i in range(0, len(data), size))


class TurzxScreen:
    def __init__(self, port=None):
        self.port = port or find_port()
        self.ser = serial.Serial(self.port, 115200, timeout=1, write_timeout=10, rtscts=True)
        w, r = self.ser.write, self.ser.read  # diagnóstico: registra o tráfego USB quando TRACE estiver ligado

        def tw(data):
            t = time.time()
            n = w(data)
            if TRACE["on"]:
                _trace(f"W {len(data):7d} cmd={data[0]:02x} {1000 * (time.time() - t):6.0f}ms", t)
            return n

        def tr(size=1):
            t = time.time()
            b = r(size)
            if TRACE["on"]:
                txt = "".join(c for c in b[:40].decode("latin1") if c.isprintable())
                _trace(f"R {len(b):7d} {1000 * (time.time() - t):6.0f}ms {txt}", t)
            return b

        self.ser.write, self.ser.read = tw, tr
        self.rom_version = 87
        self.update_count = 0
        self.screen_id = ""

    def close(self):
        self.ser.close()

    def _send(self, data: bytes, fill: int = 0x00, read: int = 0):
        self.ser.write(_pad(data, fill))
        if read:
            return self.ser.read(read)
        return b""

    def hello(self) -> str:
        for _ in range(5):
            self.ser.reset_input_buffer()
            raw = self._send(HELLO, read=23)
            self.screen_id = "".join(c for c in raw.decode(errors="ignore") if c.isprintable())
            if self.screen_id.startswith("chs_"):
                try:
                    v = int(self.screen_id.split(".")[2])
                    self.rom_version = v if 80 <= v <= 100 else 87
                except (IndexError, ValueError):
                    pass
                return self.screen_id
            time.sleep(1)
        raise RuntimeError(f"Resposta inesperada da tela: {self.screen_id!r}")

    def set_brightness(self, percent: int):
        percent = max(0, min(100, percent))
        self._send(SET_BRIGHTNESS + bytes((int(percent / 100 * 255),)))

    def stop_media(self):
        self._send(STOP_VIDEO)
        self._send(STOP_MEDIA, read=1024)

    def turn_off(self):
        self._send(TURN_OFF)

    # ------------------------------------------------------------ memória da tela
    # Comandos descobertos com o REA no UsbMonitorL.exe (ver PROTOCOLO.md).

    VIDEO_DIR = "/root/video/"

    def _command(self, cmd: int, data: bytes = b"", length=None, wait=3.0) -> str:
        """Envia um comando no formato [cmd EF 69 tamanho(4) flag .. dados@10] e lê a resposta em texto."""
        buf = bytearray(250)
        buf[0], buf[1], buf[2] = cmd, 0xEF, 0x69
        buf[3:7] = (len(data) if length is None else length).to_bytes(4, "big")
        buf[10:10 + len(data)] = data
        self.ser.reset_input_buffer()
        self.ser.write(bytes(buf))
        return self._read_reply(wait)

    def _read_reply(self, wait=3.0, quiet=0.3) -> str:
        end, got, last = time.time() + wait, b"", time.time()
        while time.time() < end:
            n = self.ser.in_waiting
            if n:
                got += self.ser.read(n)
                last = time.time()
            elif got and time.time() - last > quiet:
                break
            else:
                time.sleep(0.02)
        return "".join(c for c in got.decode("latin1") if c.isprintable())

    def stop_all_media(self):
        return self._command(0x96, length=1)

    def storage(self):
        """Retorna (total_kb, usado_kb, livre_kb) da memória interna."""
        parts = self._command(0x64, length=1, wait=4).split("-")
        try:
            return tuple(int(x) for x in parts[:3])
        except ValueError:
            return (0, 0, 0)

    def list_videos(self):
        r = self._command(0x65, self.VIDEO_DIR.encode("ascii"))
        if "file:" not in r:
            return []
        return [f for f in r.split("file:", 1)[1].split("/") if f]

    def file_size(self, name: str) -> int:
        r = self._command(0x6E, (self.VIDEO_DIR + name).encode("ascii"))
        return int(r) if r.isdigit() else 0

    def delete_video(self, name: str):
        self._command(0x66, (self.VIDEO_DIR + name).encode("ascii"), wait=1)

    def upload_video(self, name: str, data: bytes):
        """Grava um MP4 na memória da tela. Envio contínuo: pausas fazem a tela abandonar o arquivo."""
        self.stop_all_media()
        self.list_videos()  # o TURZX lista a pasta antes de criar o arquivo
        path = (self.VIDEO_DIR + name).encode("ascii")
        r = self._command(0x6F, path + len(data).to_bytes(4, "little"), length=len(path))
        if "create_success" not in r:
            # nunca enviar os dados aqui: a tela para de ler e a porta trava
            raise RuntimeError(f"a tela recusou o arquivo ({r or 'sem resposta'})")
        self.ser.write(_pad(_chunk_join(data)))
        r = self._read_reply(60, 1.0)
        if "file_rev_done" not in r:
            raise RuntimeError(f"a tela não confirmou a gravação ({r[:40] or 'sem resposta'})")
        # arquivos grandes demoram a terminar de gravar: espera o tamanho bater
        for _ in range(15):
            if self.file_size(name) == len(data):
                return
            time.sleep(1)
        raise RuntimeError("arquivo incompleto na tela (memória cheia?)")

    def play_video(self, name: str):
        r = self._command(0x78, (self.VIDEO_DIR + name).encode("ascii"), wait=6)
        if "play_video_success" not in r:
            raise RuntimeError(f"a tela não tocou o vídeo ({r or 'sem resposta'})")

    def show_full(self, image: Image.Image):
        """Envia a tela inteira (800x480, paisagem). Mais lento: ~1,5 MB por quadro."""
        image = image.convert("RGB").resize((WIDTH, HEIGHT)) if image.size != (WIDTH, HEIGHT) else image.convert("RGB")
        bgra = image.convert("RGBA").tobytes("raw", "BGRA")
        self._send(PRE_UPDATE_BITMAP)
        self._send(START_DISPLAY_BITMAP, fill=0x2C)
        self._send(DISPLAY_BITMAP_5INCH + int(480 * 480 / 64).to_bytes(2, "big"))
        self._send(_chunk_join(bgra), read=1024)
        self._send(QUERY_STATUS, read=1024)

    def show_region(self, image: Image.Image, x: int, y: int):
        """Atualiza só um retângulo (coordenadas em paisagem 800x480). Bem mais rápido."""
        image = image.convert("RGB")
        w, h = image.size
        if self.rom_version > 88:
            pixels, bpp = image.convert("RGBA").tobytes("raw", "BGRA"), 4
        else:
            pixels, bpp = image.tobytes("raw", "BGR"), 3
        row = w * bpp
        body = bytearray()
        for r in range(h):
            body += ((y + r) * WIDTH + x).to_bytes(3, "big")
            body += w.to_bytes(2, "big")
            body += pixels[r * row:(r + 1) * row]
        header = UPDATE_BITMAP + (len(body) + 2).to_bytes(3, "big") + bytes(3) + self.update_count.to_bytes(4, "big")
        # A marca de fim EF 69 entra junto na divisão em blocos de 249 (como o app da TURZX faz).
        # Acrescentá-la depois faz o "69" cair no byte separador quando len(body) % 249 == 248, e a tela
        # trava pedindo reenvio.
        self._send(header)
        self._send(_chunk_join(bytes(body) + b"\xEF\x69"))
        status = self._send(QUERY_STATUS, read=1024)
        self.update_count += 1
        if b"needReSend:1" in status or not status:
            raise ScreenDesync("a tela pediu reenvio")

    def restart(self):
        """Reinicia a tela (o mesmo que o botão do app TURZX). Ela volta à USB em ~10 s."""
        self._send(RESTART)
