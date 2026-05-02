
import tkinter as tk
from tkinter import ttk
import threading
import pyperclip
from deep_translator import GoogleTranslator
from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES
from gtts import gTTS
import tempfile
import pygame
import os


# ─────────────────────────────────────────────
#  LANGUAGE SYSTEM
# ─────────────────────────────────────────────
LANG_NAME_TO_CODE = GOOGLE_LANGUAGES_TO_CODES
LANG_NAMES = sorted(LANG_NAME_TO_CODE.keys())


class TranslationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🌐 Language Translation Tool")
        self.root.geometry("780x580")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(True, True)

        pygame.mixer.init()

        self._build_ui()

    # ───────────────────────── UI ─────────────────────────
    def _build_ui(self):
        header = tk.Frame(self.root, bg="#16213e", pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="🌐 Language Translator",
            font=("Helvetica", 20, "bold"),
            bg="#16213e",
            fg="#e94560"
        ).pack()

        tk.Label(
            header,
            text="Made By Sunny Lakhwani",
            font=("Helvetica", 10),
            bg="#16213e",
            fg="#a8a8b3"
        ).pack()

        lang_frame = tk.Frame(self.root, bg="#1a1a2e", pady=10)
        lang_frame.pack(fill="x", padx=20)

        tk.Label(lang_frame, text="From:", bg="#1a1a2e", fg="white").grid(row=0, column=0)

        self.src_lang_var = tk.StringVar(value="Auto Detect")
        self.src_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.src_lang_var,
            values=["Auto Detect"] + LANG_NAMES,
            state="readonly",
            width=25
        )
        self.src_combo.grid(row=0, column=1, padx=10)

        tk.Label(lang_frame, text="To:", bg="#1a1a2e", fg="white").grid(row=0, column=2)

        self.tgt_lang_var = tk.StringVar(value="Urdu")
        self.tgt_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.tgt_lang_var,
            values=LANG_NAMES,
            state="readonly",
            width=25
        )
        self.tgt_combo.grid(row=0, column=3, padx=10)

        self.src_text = tk.Text(self.root, height=10, wrap="word")
        self.src_text.pack(fill="both", expand=True, padx=20, pady=10)

        self.tgt_text = tk.Text(self.root, height=10, wrap="word", state="disabled")
        self.tgt_text.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = tk.Frame(self.root, bg="#1a1a2e")
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="Translate",
            bg="#e94560",
            fg="white",
            width=15,
            command=self._translate_thread
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            btn_frame,
            text="Copy",
            width=15,
            command=self._copy
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            btn_frame,
            text="Clear",
            width=15,
            command=self._clear
        ).grid(row=0, column=2, padx=5)

        tk.Button(
            btn_frame,
            text="Speak",
            width=15,
            command=self._tts_thread
        ).grid(row=0, column=3, padx=5)

        self.status = tk.Label(self.root, text="Ready", bg="#16213e", fg="white")
        self.status.pack(fill="x", side="bottom")

    # ───────────────────────── HELPERS ─────────────────────────
    def _get_code(self, name):
        if name == "Auto Detect":
            return "auto"
        return LANG_NAME_TO_CODE.get(name, "en")

    # ───────────────────────── TRANSLATION ─────────────────────────
    def _translate_thread(self):
        threading.Thread(target=self._translate, daemon=True).start()

    def _translate(self):
        try:
            text = self.src_text.get("1.0", "end-1c").strip()
            if not text:
                self._set_status("Enter text first")
                return

            src = self._get_code(self.src_lang_var.get())
            tgt = self._get_code(self.tgt_lang_var.get())

            translated = GoogleTranslator(
                source=src,
                target=tgt
            ).translate(text)

            self.root.after(0, self._show, translated)

        except Exception as e:
            self.root.after(0, self._set_status, f"Error: {e}")

    def _show(self, text):
        self.tgt_text.config(state="normal")
        self.tgt_text.delete("1.0", "end")
        self.tgt_text.insert("end", text)
        self.tgt_text.config(state="disabled")
        self._set_status("Translated ✓")

    # ───────────────────────── COPY ─────────────────────────
    def _copy(self):
        text = self.tgt_text.get("1.0", "end-1c")
        if text:
            pyperclip.copy(text)
            self._set_status("Copied ✓")

    # ───────────────────────── CLEAR ─────────────────────────
    def _clear(self):
        self.src_text.delete("1.0", "end")
        self.tgt_text.config(state="normal")
        self.tgt_text.delete("1.0", "end")
        self.tgt_text.config(state="disabled")
        self._set_status("Cleared")

    # ───────────────────────── TEXT TO SPEECH ─────────────────────────
    def _tts_thread(self):
        threading.Thread(target=self._tts, daemon=True).start()

    def _tts(self):
        try:
            text = self.tgt_text.get("1.0", "end-1c").strip()
            if not text:
                self._set_status("Nothing to speak")
                return

            lang = self._get_code(self.tgt_lang_var.get())

            # Supported languages for gTTS
            supported_langs = [
                "en", "ur", "hi", "ar", "fr", "de", "es", "it", "pt"
            ]

            if lang not in supported_langs:
                self._set_status("Voice not available for this language, using English voice")
                lang = "en"

            tts = gTTS(text=text, lang=lang)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                path = f.name

            tts.save(path)

            pygame.mixer.music.load(path)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():
                continue

            os.remove(path)

            self._set_status("Played ✓")

        except Exception as e:
            self._set_status(f"TTS Error: {e}")

    # ───────────────────────── STATUS ─────────────────────────
    def _set_status(self, msg):
        self.status.config(text=msg)


# ───────────────────────── RUN APP ─────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = TranslationApp(root)
    root.mainloop()