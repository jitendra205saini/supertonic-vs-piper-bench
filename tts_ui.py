"""Supertonic 3 vs Piper test bench ki chhoti si UI.

Chalane ke liye:
    python tts_ui.py
"""

import threading
import tkinter as tk
import winsound
from tkinter import ttk

from tts_bench import (
    PIPER_DEFAULT_VOICES,
    PIPER_VOICE_DIR,
    PiperEngine,
    SupertonicEngine,
    benchmark,
)

RUNS = 3
WARMUP = 1
SUPERTONIC_VOICES = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]

ROWS = [
    ("Synthesis time", lambda r: f"{r['avg'] * 1000:.0f} ms"),
    ("Audio length", lambda r: f"{r['audio']:.2f} s"),
    ("Speed vs realtime", lambda r: f"{1 / r['rtf']:.1f}x"),
]


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.engines = {}  # models ek baar load hote hain, phir yahin se milte hain
        self.results = []

        root.title("Supertonic 3 vs Piper")
        root.minsize(520, 0)
        frame = ttk.Frame(root, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Text").pack(anchor="w")
        self.text = tk.Text(frame, height=5, wrap="word", font=("Nirmala UI", 12))
        self.text.pack(fill="both", expand=True, pady=(2, 8))
        self.text.insert("1.0", "नमस्ते, आज मौसम बहुत अच्छा है।")

        options = ttk.Frame(frame)
        options.pack(fill="x", pady=(0, 8))
        self.lang = tk.StringVar(value="hi")
        self.voice = tk.StringVar(value="M1")
        self.steps = tk.IntVar(value=8)
        ttk.Label(options, text="Language").pack(side="left")
        ttk.Combobox(
            options, textvariable=self.lang, values=list(PIPER_DEFAULT_VOICES),
            width=4, state="readonly",
        ).pack(side="left", padx=(4, 12))
        ttk.Label(options, text="Supertonic voice").pack(side="left")
        ttk.Combobox(
            options, textvariable=self.voice, values=SUPERTONIC_VOICES,
            width=4, state="readonly",
        ).pack(side="left", padx=(4, 12))
        ttk.Label(options, text="Steps").pack(side="left")
        ttk.Spinbox(options, from_=1, to=20, textvariable=self.steps, width=4).pack(
            side="left", padx=(4, 12)
        )
        self.run_button = ttk.Button(options, text="Run test", command=self.run)
        self.run_button.pack(side="right")

        self.table = ttk.Treeview(
            frame, columns=("supertonic", "piper"), height=len(ROWS), selectmode="none"
        )
        self.table.heading("#0", text="")
        self.table.heading("supertonic", text="Supertonic 3")
        self.table.heading("piper", text="Piper")
        self.table.column("#0", width=160)
        self.table.column("supertonic", width=150, anchor="center")
        self.table.column("piper", width=150, anchor="center")
        for label, _ in ROWS:
            self.table.insert("", "end", iid=label, text=label, values=("-", "-"))
        self.table.pack(fill="x")

        play = ttk.Frame(frame)
        play.pack(fill="x", pady=8)
        self.play_buttons = [
            ttk.Button(play, text="▶ Supertonic 3", state="disabled", command=lambda: self.play(0)),
            ttk.Button(play, text="▶ Piper", state="disabled", command=lambda: self.play(1)),
        ]
        for button in self.play_buttons:
            button.pack(side="left", padx=(0, 8))

        self.status = ttk.Label(frame, text="Text likhiye aur Run test dabaiye.")
        self.status.pack(anchor="w")

    def run(self) -> None:
        text = self.text.get("1.0", "end").strip()
        if not text:
            self.status.config(text="Pehle text likhiye.")
            return
        try:
            steps = self.steps.get()
        except tk.TclError:
            self.status.config(text="Steps me number likhiye.")
            return

        winsound.PlaySound(None, winsound.SND_PURGE)  # bajti file overwrite nahi ho sakti
        self.run_button.config(state="disabled")
        for button in self.play_buttons:
            button.config(state="disabled")
        self.status.config(text="Chal raha hai... (pehli baar model load hone me time lagta hai)")
        threading.Thread(
            target=self.worker, args=(text, self.lang.get(), self.voice.get(), steps), daemon=True
        ).start()

    def worker(self, text: str, lang: str, voice: str, steps: int) -> None:
        try:
            from piper.download_voices import download_voice

            piper_voice = PIPER_DEFAULT_VOICES[lang]
            PIPER_VOICE_DIR.mkdir(exist_ok=True)
            download_voice(piper_voice, PIPER_VOICE_DIR)

            makers = [
                lambda: self.engine(SupertonicEngine, voice, lang, steps, None),
                lambda: self.engine(PiperEngine, piper_voice, None),
            ]
            results = [benchmark(make, text, RUNS, WARMUP) for make in makers]
            self.root.after(0, self.show, results)
        except Exception as error:
            self.root.after(0, self.fail, error)

    def engine(self, cls, *args):
        key = (cls, args)
        if key not in self.engines:
            self.engines[key] = cls(*args)
        return self.engines[key]

    def show(self, results: list[dict]) -> None:
        self.results = results
        for label, fmt in ROWS:
            self.table.item(label, values=[fmt(r) for r in results])
        fast, slow = sorted(results, key=lambda r: r["avg"])
        self.status.config(
            text=f"{fast['name']} fast hai — {slow['name']} se {slow['avg'] / fast['avg']:.1f}x"
        )
        self.run_button.config(state="normal")
        for button in self.play_buttons:
            button.config(state="normal")

    def fail(self, error: Exception) -> None:
        self.status.config(text=f"Error: {error}")
        self.run_button.config(state="normal")

    def play(self, index: int) -> None:
        winsound.PlaySound(
            str(self.results[index]["file"]), winsound.SND_FILENAME | winsound.SND_ASYNC
        )


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
