"""Imagens, GIFs e vídeos usados nos widgets e fundos.

Vídeos são decodificados pelo ffmpeg já no tamanho do widget, em uma thread.
"""
import hashlib
import os
import re
import shutil
import subprocess
import threading
import time

from PIL import Image, ImageOps, ImageSequence

def find_ffmpeg(configured=""):
    """configured pode ser o ffmpeg.exe ou uma pasta (por exemplo a do app TURZX, que traz um)."""
    if configured and os.path.isdir(configured):
        configured = os.path.join(configured, "ffmpeg.exe")
    for p in [configured, shutil.which("ffmpeg")]:
        if p and os.path.isfile(p):
            return p
    return None


def fit(img, size, mode):
    """mode: cover (preenche e corta), contain (cabe inteiro), stretch (estica)."""
    if mode == "stretch":
        return img.resize(size, Image.LANCZOS)
    if mode == "contain":
        out = Image.new("RGBA", size, (0, 0, 0, 0))
        im = ImageOps.contain(img, size, Image.LANCZOS)
        out.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
        return out
    return ImageOps.fit(img, size, Image.LANCZOS)


class StillImage:
    def __init__(self, path, size, mode):
        self.frame = fit(Image.open(path).convert("RGBA"), size, mode)

    def get(self, now):
        return self.frame

    def close(self):
        pass


class Gif:
    def __init__(self, path, size, mode, speed=1.0):
        src = Image.open(path)
        self.frames, self.times = [], []
        total = 0
        for fr in ImageSequence.Iterator(src):
            self.frames.append(fit(fr.convert("RGBA"), size, mode))
            total += max(fr.info.get("duration", 100), 20) / 1000 / max(speed, 0.05)
            self.times.append(total)
        self.total = total or 1
        self.start = time.time()

    def get(self, now):
        t = (now - self.start) % self.total
        for i, end in enumerate(self.times):
            if t < end:
                return self.frames[i]
        return self.frames[-1]

    def close(self):
        pass


class Video:
    def __init__(self, path, size, mode, fps, ffmpeg):
        self.size, self.frame = size, Image.new("RGBA", size, (0, 0, 0, 255))
        w, h = size
        if mode == "stretch":
            vf = f"scale={w}:{h}"
        elif mode == "contain":
            vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
        else:
            vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        cmd = [ffmpeg, "-loglevel", "error", "-re", "-stream_loop", "-1", "-i", path, "-an",
               "-vf", f"{vf},fps={fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     creationflags=0x08000000)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        n = self.size[0] * self.size[1] * 3
        while True:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:
                return
            self.frame = Image.frombytes("RGB", self.size, buf).convert("RGBA")

    def get(self, now):
        return self.frame

    def close(self):
        self.proc.kill()


class VideoThumb:
    """Primeiro quadro do vídeo, para a prévia do editor."""

    def __init__(self, path, size, mode, ffmpeg):
        out = subprocess.run([ffmpeg, "-loglevel", "error", "-i", path, "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "png", "-"], capture_output=True, timeout=20, creationflags=0x08000000).stdout
        import io
        self.frame = fit(Image.open(io.BytesIO(out)).convert("RGBA"), size, mode)

    def get(self, now):
        return self.frame

    def close(self):
        pass


class MediaCache:
    """Mantém uma fonte por (arquivo, tamanho, modo). Fecha as que saíram de uso."""

    def __init__(self, media_dir, ffmpeg="", static=False):
        self.media_dir = media_dir
        self.static = static
        self.ffmpeg = find_ffmpeg(ffmpeg)
        self.items = {}
        self.used = set()

    def get(self, name, size, mode="cover", fps=10, speed=1.0):
        if not name:
            return None
        key = (name, size, mode, fps, speed)
        self.used.add(key)
        if key not in self.items:
            path = os.path.join(self.media_dir, name)
            if not os.path.isfile(path):
                return None
            ext = os.path.splitext(name)[1].lower()
            try:
                if ext in (".mp4", ".mkv", ".webm", ".mov", ".avi"):
                    if not self.ffmpeg:
                        return None
                    self.items[key] = (VideoThumb(path, size, mode, self.ffmpeg) if self.static
                                       else Video(path, size, mode, fps, self.ffmpeg))
                elif ext == ".gif" or (ext == ".webp" and getattr(Image.open(path), "n_frames", 1) > 1):
                    self.items[key] = Gif(path, size, mode, speed)
                else:
                    self.items[key] = StillImage(path, size, mode)
            except Exception as e:
                print("mídia:", name, e)
                return None
        return self.items[key].get(time.time())

    def sweep(self):
        """Chamar uma vez por quadro, depois do render: libera mídias não usadas."""
        for key in list(self.items):
            if key not in self.used:
                self.items.pop(key).close()
        self.used = set()


# ---------------------------------------------------------------- vídeo tocado pela própria tela

# Giro aplicado depois de ajustar ao tamanho lógico, igual ao que o motor faz com as imagens.
DEVICE_ROTATION = {"landscape": ((800, 480), ""), "landscape_flipped": ((800, 480), "transpose=1,transpose=1,"),
                   "portrait": ((480, 800), "transpose=2,"), "portrait_flipped": ((480, 800), "transpose=1,")}


_digests = {}


def _digest(path):
    """SHA-1 do conteúdo (com cache): o nome não muda se o arquivo for só copiado ou movido."""
    st = os.stat(path)
    key = (path, st.st_size, st.st_mtime_ns)
    if key not in _digests:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        _digests[key] = h.hexdigest()
    return _digests[key]


def device_video_name(src_path, orientation):
    """Nome curto em ASCII, que muda quando o conteúdo do arquivo ou a orientação mudam."""
    tag = hashlib.sha1(f"{_digest(src_path)}|{orientation}".encode()).hexdigest()[:6]
    stem = re.sub(r"[^a-z0-9]+", "_", os.path.splitext(os.path.basename(src_path))[0].lower()).strip("_")[:16] or "video"
    return f"{stem}_{tag}.mp4"


def convert_for_device(src_path, orientation, ffmpeg, cache_dir):
    """Converte para o formato que o TURZX usa: H.264 24 fps 2400 kbps, 800x480 nativo."""
    os.makedirs(cache_dir, exist_ok=True)
    name = device_video_name(src_path, orientation)
    out = os.path.join(cache_dir, name)
    if not os.path.isfile(out):
        (w, h), rot = DEVICE_ROTATION.get(orientation, DEVICE_ROTATION["landscape"])
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},{rot}setsar=1:1"
        tmp = out + ".tmp.mp4"
        subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", src_path, "-vf", vf, "-c:v", "libx264",
                        "-b:v", "2400k", "-bufsize", "2400k", "-r", "24", "-an", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", "-f", "mp4", tmp],
                       check=True, capture_output=True, timeout=600, creationflags=0x08000000)
        os.replace(tmp, out)
    return name, out
