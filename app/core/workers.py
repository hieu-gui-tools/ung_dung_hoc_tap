"""
app/core/workers.py — QThread workers for TTS, yt-dlp, recording
"""
import os
import asyncio
import unicodedata
import re
import wave
import struct
import threading

import edge_tts
from edge_tts.exceptions import NoAudioReceived

from PySide6.QtCore import QThread, Signal


TTS_VOICE_CHOICES = [
    ("Việt - gTTS (mặc định)", "gtts:vi"),
    ("Anh - Nữ (Sonia)",   "en-GB-SoniaNeural"),
    ("Mỹ - Nữ (Aria)",     "en-US-AriaNeural"),
    ("Mỹ - Nam (Guy)",     "en-US-GuyNeural"),
    ("Anh - Nam (Ryan)",   "en-GB-RyanNeural"),
    ("Việt - Nữ (Hoài My)", "vi-VN-HoaiMyNeural"),
    ("Việt - Nam (Nam Minh)", "vi-VN-NamMinhNeural"),
]


def normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFC", text or "")
    for old, new in [("\ufeff",""),("\xa0"," "),("\r\n","\n"),("\r","\n")]:
        t = t.replace(old, new)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def synthesize_tts(text: str, voice: str, output_path: str):
    text = normalize_text(text)
    if voice.startswith("gtts:"):
        try:
            from gtts import gTTS
        except ImportError as exc:
            raise RuntimeError("Chưa cài gTTS. Chạy: uv add gTTS") from exc

        lang = voice.split(":", 1)[1] or "vi"
        gTTS(text=text, lang=lang).save(output_path)
        return

    asyncio.run(edge_tts.Communicate(text, voice).save(output_path))


class TTSWorker(QThread):
    finished = Signal(str)   # output_path
    error    = Signal(str)

    def __init__(self, text: str, voice: str, output_path: str):
        super().__init__()
        self.text = text
        self.voice = voice
        self.output_path = output_path

    def run(self):
        try:
            synthesize_tts(self.text, self.voice, self.output_path)
            self.finished.emit(self.output_path)
        except Exception as e:
            self.error.emit(str(e))


class BatchTTSWorker(QThread):
    progress = Signal(str)
    finished = Signal(list)   # list of output_paths
    error    = Signal(str)

    def __init__(self, entries: list):
        # entries: [{"text": ..., "voice": ..., "output_path": ...}, ...]
        super().__init__()
        self.entries = entries

    def run(self):
        results = []
        try:
            for i, e in enumerate(self.entries, 1):
                self.progress.emit(f"{i}/{len(self.entries)}: {e.get('title','')}")
                synthesize_tts(e["text"], e["voice"], e["output_path"])
                results.append(e["output_path"])
            self.finished.emit(results)
        except Exception as ex:
            self.error.emit(str(ex))


class YtDlpWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error    = Signal(str)

    def __init__(self, url: str, download: bool = False, video: bool = False, out_dir: str = ""):
        super().__init__()
        self.url = url
        self.download = download
        self.video = video
        self.out_dir = out_dir

    def _hook(self, d):
        if d["status"] == "downloading":
            pct = re.sub(r"\x1b\[[0-9;]*m", "", d.get("_percent_str",""))
            self.progress.emit(pct.strip())

    def run(self):
        try:
            import yt_dlp
            fmt = ("bestvideo+bestaudio/best" if self.video and self.download
                   else "best" if self.video
                   else "bestaudio/best")
            opts = {
                "format": fmt, 
                "noplaylist": True, 
                "quiet": True, 
                "no_warnings": True,
                "extractor_args": {"youtube": {"player_client": ["android", "web"]}}
            }
            if self.download:
                os.makedirs(self.out_dir, exist_ok=True)
                opts["outtmpl"] = os.path.join(self.out_dir, "%(title)s.%(ext)s")
                opts["progress_hooks"] = [self._hook]
                if self.video:
                    opts["merge_output_format"] = "mp4"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(self.url, download=self.download)
                self.finished.emit({
                    "title":    info.get("title","Unknown"),
                    "url":      self.url,
                    "stream":   info.get("url", self.url),
                    "duration": info.get("duration", 0),
                    "file":     ydl.prepare_filename(info) if self.download else None,
                })
        except Exception as e:
            self.error.emit(str(e))


class AudioRecorder:
    """Simple WAV recorder using sounddevice and soundfile."""
    def __init__(self, samplerate: int = 44100, channels: int = 1):
        self.samplerate = samplerate
        self.channels = channels
        self._stream = None
        self._frames = []
        self._lock = threading.Lock()
        self._output_path = ""
        self._active_samplerate = samplerate

    def list_input_devices(self) -> list[tuple[int, str]]:
        import sounddevice as sd
        devices = []
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev.get("max_input_channels", 0) > 0:
                    devices.append((i, dev["name"]))
        except Exception:
            pass
        return devices

    def start(self, output_path: str, device_index: int | None = None):
        import sounddevice as sd
        import numpy

        if self._stream is not None:
            raise RuntimeError("Đang ghi âm.")

        self._output_path = output_path
        self._frames = []

        device_info = sd.query_devices(device=device_index, kind="input")
        samplerate = int(device_info.get("default_samplerate", self.samplerate))
        channels = max(1, min(self.channels, int(device_info.get("max_input_channels", self.channels))))
        sd.check_input_settings(device=device_index, samplerate=samplerate, channels=channels)
        self._active_samplerate = samplerate

        def callback(indata: numpy.ndarray, _frames: int, _time: object, _status: sd.CallbackFlags) -> None:
            with self._lock:
                self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            device=device_index,
            samplerate=samplerate,
            channels=channels,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> str:
        import soundfile as sf
        import numpy

        if self._stream is None:
            return ""

        stream = self._stream
        self._stream = None
        stream.stop()
        stream.close()

        with self._lock:
            frames = list(self._frames)
            self._frames = []

        if not frames:
            raise RuntimeError("Không thu được dữ liệu âm thanh.")

        os.makedirs(os.path.dirname(self._output_path), exist_ok=True)
        audio_data = numpy.concatenate(frames, axis=0)
        sf.write(self._output_path, audio_data, self._active_samplerate)
        return self._output_path

    def is_recording(self) -> bool:
        return self._stream is not None


class TranslateWorker(QThread):
    """Dịch văn bản EN→VI bằng Google Translate (miễn phí, không cần API key)."""
    finished = Signal(str)   # translated text
    error    = Signal(str)

    def __init__(self, text: str, src: str = "en", dest: str = "vi"):
        super().__init__()
        self.text = text
        self.src = src
        self.dest = dest

    def run(self):
        try:
            import requests
            text = self.text.strip()
            if not text:
                self.finished.emit("")
                return
            # Dùng Google Translate endpoint công khai
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": self.src,
                "tl": self.dest,
                "dt": "t",
                "q": text,
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Ghép các đoạn dịch lại
            result = "".join(
                chunk[0] for chunk in data[0] if chunk and chunk[0]
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
