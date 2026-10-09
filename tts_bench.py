"""TTS test bench: Supertonic 3 vs Piper, ek hi text par speed compare karta hai.

Examples:
    python tts_bench.py "नमस्ते, आप कैसे हैं?" --lang hi
    python tts_bench.py "Hello, how are you today?" --lang en --runs 5
    python tts_bench.py --file input.txt --lang hi --piper-voice hi_IN-priyamvada-medium
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

SUPERTONIC_MODEL = "supertonic-3"
PIPER_VOICE_DIR = Path(__file__).parent / "piper_voices"
OUTPUT_DIR = Path(__file__).parent / "bench_output"

# Language code -> default Piper voice. Dusri language ke liye --piper-voice do.
PIPER_DEFAULT_VOICES = {
    "hi": "hi_IN-pratham-medium",
    "en": "en_US-lessac-medium",
}


class SupertonicEngine:
    name = "Supertonic 3"

    def __init__(self, voice: str, lang: str, steps: int, threads: int | None):
        from supertonic import TTS

        self.tts = TTS(model=SUPERTONIC_MODEL, intra_op_num_threads=threads)
        self.style = self.tts.get_voice_style(voice)
        self.lang = lang
        self.steps = steps
        self.sample_rate = self.tts.sample_rate
        self.detail = f"voice={voice}, steps={steps}"

    def synthesize(self, text: str) -> np.ndarray:
        wav, _ = self.tts.synthesize(
            text, voice_style=self.style, lang=self.lang, total_steps=self.steps
        )
        return wav.squeeze()


class PiperEngine:
    name = "Piper"

    def __init__(self, voice: str, threads: int | None):
        import onnxruntime
        from piper import PiperVoice

        self.voice = PiperVoice.load(PIPER_VOICE_DIR / f"{voice}.onnx")
        if threads is not None:
            # PiperVoice.load me thread option nahi hai, isliye session dobara banate hain
            options = onnxruntime.SessionOptions()
            options.intra_op_num_threads = threads
            self.voice.session = onnxruntime.InferenceSession(
                str(PIPER_VOICE_DIR / f"{voice}.onnx"),
                sess_options=options,
                providers=["CPUExecutionProvider"],
            )
        self.sample_rate = self.voice.config.sample_rate
        self.detail = f"voice={voice}"

    def synthesize(self, text: str) -> np.ndarray:
        chunks = [chunk.audio_float_array for chunk in self.voice.synthesize(text)]
        return np.concatenate(chunks)


def benchmark(make_engine, text: str, runs: int, warmup: int) -> dict:
    start = time.perf_counter()
    engine = make_engine()
    load_time = time.perf_counter() - start

    for _ in range(warmup):
        engine.synthesize(text)

    times = []
    for _ in range(runs):
        start = time.perf_counter()
        wav = engine.synthesize(text)
        times.append(time.perf_counter() - start)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{engine.name.lower().replace(' ', '_')}.wav"
    sf.write(str(out_path), wav, engine.sample_rate)

    audio_sec = len(wav) / engine.sample_rate
    avg = statistics.mean(times)
    return {
        "name": engine.name,
        "detail": engine.detail,
        "load": load_time,
        "avg": avg,
        "best": min(times),
        "audio": audio_sec,
        "rtf": avg / audio_sec,
        "chars_per_sec": len(text) / avg,
        "sample_rate": engine.sample_rate,
        "file": out_path,
    }


def print_report(results: list[dict], text: str, runs: int) -> None:
    rows = [
        ("Model load (s)", lambda r: f"{r['load']:.2f}"),
        (f"Synthesis avg of {runs} (s)", lambda r: f"{r['avg']:.3f}"),
        ("Synthesis best (s)", lambda r: f"{r['best']:.3f}"),
        ("Audio length (s)", lambda r: f"{r['audio']:.2f}"),
        ("RTF (kam = fast)", lambda r: f"{r['rtf']:.3f}"),
        ("Speed vs realtime", lambda r: f"{1 / r['rtf']:.1f}x"),
        ("Chars / sec", lambda r: f"{r['chars_per_sec']:.0f}"),
        ("Sample rate (Hz)", lambda r: f"{r['sample_rate']}"),
    ]
    width = 28
    col = 22

    print(f"\nText: {len(text)} characters")
    print("-" * (width + col * len(results)))
    print(f"{'':<{width}}" + "".join(f"{r['name']:>{col}}" for r in results))
    print("-" * (width + col * len(results)))
    for label, fmt in rows:
        print(f"{label:<{width}}" + "".join(f"{fmt(r):>{col}}" for r in results))
    print("-" * (width + col * len(results)))

    for r in results:
        print(f"{r['name']}: {r['detail']} -> {r['file']}")

    if len(results) == 2:
        fast, slow = sorted(results, key=lambda r: r["avg"])
        print(
            f"\nWinner: {fast['name']} — synthesis me {slow['name']} se "
            f"{slow['avg'] / fast['avg']:.2f}x fast "
            f"({fast['avg']:.3f}s vs {slow['avg']:.3f}s)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Supertonic 3 vs Piper TTS speed bench")
    parser.add_argument("text", nargs="?", help="Test text")
    parser.add_argument("--file", "-f", help="Text file ka path (text ki jagah)")
    parser.add_argument("--lang", "-l", default="hi", help="Language code: hi, en, ...")
    parser.add_argument("--runs", "-r", type=int, default=3, help="Timed runs per model")
    parser.add_argument("--warmup", type=int, default=1, help="Untimed warmup runs")
    parser.add_argument("--supertonic-voice", default="M1", help="M1-M5 / F1-F5")
    parser.add_argument("--steps", type=int, default=8, help="Supertonic denoising steps")
    parser.add_argument("--piper-voice", help="Piper voice, jaise hi_IN-pratham-medium")
    parser.add_argument("--threads", type=int, help="Dono models ke liye CPU threads fix karo")
    parser.add_argument("--only", choices=["supertonic", "piper"], help="Sirf ek model chalao")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.text:
        text = args.text
    else:
        parser.error("text ya --file me se ek dena zaroori hai")

    piper_voice = args.piper_voice or PIPER_DEFAULT_VOICES.get(args.lang)
    if piper_voice is None and args.only != "supertonic":
        parser.error(f"lang '{args.lang}' ke liye default Piper voice nahi hai, --piper-voice do")

    engines = []
    if args.only != "piper":
        engines.append(
            lambda: SupertonicEngine(args.supertonic_voice, args.lang, args.steps, args.threads)
        )
    if args.only != "supertonic":
        # Download ko load time me nahi ginna, isliye pehle hi kar lete hain
        from piper.download_voices import download_voice

        PIPER_VOICE_DIR.mkdir(exist_ok=True)
        download_voice(piper_voice, PIPER_VOICE_DIR)
        engines.append(lambda: PiperEngine(piper_voice, args.threads))

    results = []
    for make_engine in engines:
        print(f"Running {len(results) + 1}/{len(engines)}...", flush=True)
        results.append(benchmark(make_engine, text, args.runs, args.warmup))

    print_report(results, text, args.runs)
    return 0


if __name__ == "__main__":
    # Windows console me Hindi text / symbols print karne ke liye
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
