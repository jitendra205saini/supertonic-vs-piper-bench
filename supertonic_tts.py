"""Supertonic 3 se text ko voice (WAV) me convert karta hai.

Examples:
    python supertonic_tts.py "Namaste, aap kaise hain?"
    python supertonic_tts.py "नमस्ते, आप कैसे हैं?" --lang hi --voice F1 -o hindi.wav
    python supertonic_tts.py --file input.txt --lang en --speed 1.2 -o out.wav
"""

import argparse
import sys
import time
from pathlib import Path

from supertonic import TTS

MODEL = "supertonic-3"
VOICES = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]


def text_to_voice(
    text: str,
    output_path: str = "output.wav",
    voice: str = "M1",
    lang: str = "na",
    speed: float = 1.05,
    steps: int = 8,
    tts: TTS | None = None,
) -> float:
    """Text ko WAV file me likhta hai aur audio ki duration (seconds) return karta hai.

    lang="na" ka matlab language auto/unknown; Hindi ke liye "hi", English ke liye "en".
    Kai texts convert karne ho to ek hi `tts` object pass karo, model baar-baar load nahi hoga.
    """
    if tts is None:
        tts = TTS(model=MODEL)

    style = tts.get_voice_style(voice)
    wav, duration = tts.synthesize(
        text, voice_style=style, lang=lang, speed=speed, total_steps=steps
    )
    tts.save_audio(wav, output_path)
    return float(duration[0])


def main() -> int:
    parser = argparse.ArgumentParser(description="Supertonic 3 text-to-voice converter")
    parser.add_argument("text", nargs="?", help="Bolne wala text")
    parser.add_argument("--file", "-f", help="Text file ka path (text ki jagah)")
    parser.add_argument("--output", "-o", default="output.wav", help="Output WAV file")
    parser.add_argument("--voice", "-v", default="M1", choices=VOICES, help="Voice style")
    parser.add_argument("--lang", "-l", default="na", help="Language code: hi, en, ... (na = auto)")
    parser.add_argument("--speed", "-s", type=float, default=1.05, help="Speed 0.7 - 2.0")
    parser.add_argument("--steps", type=int, default=8, help="Zyada steps = better quality, slow")
    args = parser.parse_args()

    if args.file:
        text = Path(args.file).read_text(encoding="utf-8").strip()
    elif args.text:
        text = args.text
    else:
        parser.error("text ya --file me se ek dena zaroori hai")

    print(f"Model load ho raha hai ({MODEL})... pehli baar download me time lagega")
    tts = TTS(model=MODEL)

    start = time.perf_counter()
    duration = text_to_voice(
        text, args.output, args.voice, args.lang, args.speed, args.steps, tts=tts
    )
    elapsed = time.perf_counter() - start

    print(f"Saved: {args.output}")
    print(f"Audio: {duration:.2f}s | Synthesis time: {elapsed:.2f}s | RTF: {elapsed / duration:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
