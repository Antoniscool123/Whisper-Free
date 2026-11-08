from __future__ import annotations

import json
import queue
import re
import tempfile
import threading
import wave
from pathlib import Path

import customtkinter as ctk
import keyboard
import numpy as np
import pyperclip
import sounddevice as sd
from faster_whisper import WhisperModel

APP_NAME = "Whisper Free"
SAMPLE_RATE = 16000
CHANNELS = 1
CONFIG_DIR = Path.home() / ".whisper_free"
CONFIG_FILE = CONFIG_DIR / "settings.json"

LANGUAGES = {
    "Auto detect": None, "Dansk": "da", "English": "en", "Deutsch": "de",
    "Español": "es", "Français": "fr", "Italiano": "it", "Nederlands": "nl",
    "Norsk": "no", "Svenska": "sv", "Suomi": "fi", "Polski": "pl",
    "Português": "pt", "Čeština": "cs", "Українська": "uk", "Русский": "ru",
    "Türkçe": "tr", "العربية": "ar", "עברית": "he", "हिन्दी": "hi",
    "বাংলা": "bn", "தமிழ்": "ta", "ไทย": "th", "Tiếng Việt": "vi",
    "Bahasa Indonesia": "id", "日本語": "ja", "한국어": "ko", "中文": "zh"
}

DEFAULTS = {
    "model": "small", "language": "Dansk", "hotkey": "ctrl+shift+space",
    "remove_fillers": True, "auto_paste": True
}


def load_settings():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULTS, **json.loads(CONFIG_FILE.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return DEFAULTS.copy()


def save_settings(data):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def polish(text: str, remove_fillers: bool) -> str:
    text = re.sub(r"\s+([,.;:!?])", r"\1", text.strip())
    text = re.sub(r"\s{2,}", " ", text)
    if remove_fillers:
        fillers = r"\b(um+|uh+|erm+|øh+|øhm+|altså)\b[,.]?\s*"
        text = re.sub(fillers, "", text, flags=re.IGNORECASE)
    if text:
        text = text[0].upper() + text[1:]
    return text


class WhisperFree(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.title(APP_NAME)
        self.geometry("860x620")
        self.minsize(720, 520)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.recording = False
        self.audio_queue = queue.Queue()
        self.frames = []
        self.stream = None
        self.model = None
        self.model_name = None
        self.hotkey_handle = None
        self.status_var = ctk.StringVar(value="Ready")

        self._build_ui()
        self._register_hotkey()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=24, pady=20)

        header = ctk.CTkFrame(root, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="Whisper Free", font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        ctk.CTkLabel(header, textvariable=self.status_var, text_color=("#2563eb", "#60a5fa")).pack(side="right")
        ctk.CTkLabel(root, text="Free, private voice dictation powered locally by Whisper", anchor="w").pack(fill="x", pady=(0, 16))

        controls = ctk.CTkFrame(root)
        controls.pack(fill="x", pady=(0, 14))
        controls.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(controls, text="Language").grid(row=0, column=0, sticky="w", padx=14, pady=(12, 2))
        self.language = ctk.CTkOptionMenu(controls, values=list(LANGUAGES), command=lambda _: self._persist())
        self.language.set(self.settings["language"])
        self.language.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

        ctk.CTkLabel(controls, text="Model").grid(row=0, column=1, sticky="w", padx=14, pady=(12, 2))
        self.model_choice = ctk.CTkOptionMenu(controls, values=["tiny", "base", "small", "medium", "large-v3"], command=lambda _: self._persist())
        self.model_choice.set(self.settings["model"])
        self.model_choice.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 12))

        ctk.CTkLabel(controls, text="Global hotkey").grid(row=0, column=2, sticky="w", padx=14, pady=(12, 2))
        self.hotkey = ctk.CTkEntry(controls)
        self.hotkey.insert(0, self.settings["hotkey"])
        self.hotkey.grid(row=1, column=2, sticky="ew", padx=14, pady=(0, 12))
        self.hotkey.bind("<Return>", lambda _: self._register_hotkey())

        self.textbox = ctk.CTkTextbox(root, font=ctk.CTkFont(size=17), wrap="word")
        self.textbox.pack(fill="both", expand=True)
        self.textbox.insert("1.0", "Press the microphone button or use Ctrl+Shift+Space, then speak…")

        options = ctk.CTkFrame(root, fg_color="transparent")
        options.pack(fill="x", pady=(12, 0))
        self.fillers = ctk.CTkSwitch(options, text="Remove filler words", command=self._persist)
        if self.settings["remove_fillers"]: self.fillers.select()
        self.fillers.pack(side="left")
        self.paste = ctk.CTkSwitch(options, text="Paste into active app", command=self._persist)
        if self.settings["auto_paste"]: self.paste.select()
        self.paste.pack(side="left", padx=18)

        self.record_btn = ctk.CTkButton(options, text="🎙 Start dictation", height=44, width=190, command=self.toggle_recording)
        self.record_btn.pack(side="right")
        ctk.CTkButton(options, text="Copy", height=44, width=90, command=self.copy_text).pack(side="right", padx=10)
        ctk.CTkButton(options, text="Clear", height=44, width=90, fg_color="transparent", border_width=1, command=lambda: self.textbox.delete("1.0", "end")).pack(side="right")

    def _persist(self):
        self.settings.update({
            "model": self.model_choice.get(), "language": self.language.get(),
            "hotkey": self.hotkey.get().strip() or DEFAULTS["hotkey"],
            "remove_fillers": bool(self.fillers.get()), "auto_paste": bool(self.paste.get())
        })
        save_settings(self.settings)

    def _register_hotkey(self):
        try:
            if self.hotkey_handle is not None:
                keyboard.remove_hotkey(self.hotkey_handle)
            key = self.hotkey.get().strip() or DEFAULTS["hotkey"]
            self.hotkey_handle = keyboard.add_hotkey(key, lambda: self.after(0, self.toggle_recording))
            self.status_var.set(f"Ready • {key}")
            self._persist()
        except Exception as exc:
            self.status_var.set(f"Hotkey error: {exc}")

    def _audio_callback(self, indata, frames, time_info, status):
        if self.recording:
            self.audio_queue.put(indata.copy())

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        try:
            self.frames = []
            while not self.audio_queue.empty(): self.audio_queue.get_nowait()
            self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", callback=self._audio_callback)
            self.stream.start()
            self.recording = True
            self.record_btn.configure(text="■ Stop and transcribe", fg_color="#dc2626", hover_color="#b91c1c")
            self.status_var.set("Listening…")
        except Exception as exc:
            self.status_var.set(f"Microphone error: {exc}")

    def stop_recording(self):
        self.recording = False
        if self.stream:
            self.stream.stop(); self.stream.close(); self.stream = None
        while not self.audio_queue.empty(): self.frames.append(self.audio_queue.get())
        self.record_btn.configure(text="🎙 Start dictation", fg_color=["#3a7ebf", "#1f538d"], hover_color=["#325882", "#14375e"])
        if not self.frames:
            self.status_var.set("No audio captured")
            return
        self.status_var.set("Transcribing…")
        threading.Thread(target=self._transcribe, daemon=True).start()

    def _get_model(self):
        name = self.model_choice.get()
        if self.model is None or self.model_name != name:
            self.after(0, lambda: self.status_var.set(f"Loading {name} model…"))
            self.model = WhisperModel(name, device="cpu", compute_type="int8")
            self.model_name = name
        return self.model

    def _transcribe(self):
        path = None
        try:
            audio = np.concatenate(self.frames, axis=0)
            pcm = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = tmp.name
            with wave.open(path, "wb") as wav:
                wav.setnchannels(CHANNELS); wav.setsampwidth(2); wav.setframerate(SAMPLE_RATE); wav.writeframes(pcm.tobytes())
            language = LANGUAGES[self.language.get()]
            segments, info = self._get_model().transcribe(path, language=language, vad_filter=True, beam_size=5)
            text = polish(" ".join(s.text.strip() for s in segments), bool(self.fillers.get()))
            self.after(0, lambda: self._finish(text, info.language))
        except Exception as exc:
            self.after(0, lambda: self.status_var.set(f"Transcription error: {exc}"))
        finally:
            if path:
                try: Path(path).unlink(missing_ok=True)
                except Exception: pass

    def _finish(self, text, detected):
        if not text:
            self.status_var.set("No speech detected")
            return
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", text)
        pyperclip.copy(text)
        if self.paste.get():
            keyboard.write(text, delay=0.001)
        self.status_var.set(f"Done • detected {detected}")

    def copy_text(self):
        pyperclip.copy(self.textbox.get("1.0", "end").strip())
        self.status_var.set("Copied")

    def _close(self):
        try:
            if self.hotkey_handle is not None: keyboard.remove_hotkey(self.hotkey_handle)
            if self.stream: self.stream.close()
        finally:
            self.destroy()


if __name__ == "__main__":
    WhisperFree().mainloop()
