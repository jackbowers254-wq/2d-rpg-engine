"""
tools/gen_demo_audio.py
=====================
Generates the demo's placeholder audio as valid 16-bit mono WAV files using only
the standard library (wave + struct + math) -- no extra dependencies. In a real
project you'd drop your own .ogg/.wav music + SFX in assets/audio/ instead.

Re-run with:  python tools/gen_demo_audio.py

Outputs (assets/audio/): overworld.wav, cave.wav, battle.wav (looping beds) and
pickup.wav, hit.wav, confirm.wav, level.wav (SFX).
"""

import math
import os
import struct
import wave

RATE = 22050


def _write(path, samples):
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples)
        w.writeframes(frames)


def _env(i, n, attack=0.01, release=0.05):
    """Simple attack/release envelope (0..1) to avoid clicks."""
    a = int(n * attack)
    r = int(n * release)
    if i < a:
        return i / max(1, a)
    if i > n - r:
        return (n - i) / max(1, r)
    return 1.0


def tone(freq, dur, vol=0.3, wave_kind="sine"):
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        if wave_kind == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
        elif wave_kind == "saw":
            v = 2 * (t * freq - math.floor(0.5 + t * freq))
        else:
            v = math.sin(2 * math.pi * freq * t)
        out.append(v * vol * _env(i, n))
    return out


def arpeggio(freqs, note_dur, vol=0.28, kind="sine", reps=1):
    seq = []
    for _ in range(reps):
        for f in freqs:
            seq += tone(f, note_dur, vol, kind)
    return seq


def noise(dur, vol=0.4):
    import random
    n = int(RATE * dur)
    rnd = random.Random(7)
    return [(rnd.uniform(-1, 1)) * vol * _env(i, n, 0.001, 0.3) for i in range(n)]


# Notes (Hz)
C4, D4, E4, G4, A4, C5, E5 = 261.6, 293.7, 329.6, 392.0, 440.0, 523.3, 659.3
A2, A3 = 110.0, 220.0


def main():
    os.makedirs("assets/audio", exist_ok=True)

    # Looping music beds (kept short; the mixer loops them).
    _write("assets/audio/overworld.wav", arpeggio([C4, E4, G4, E4], 0.22, kind="sine", reps=2))
    _write("assets/audio/cave.wav", arpeggio([A2, A3, A2, E4], 0.30, vol=0.22, kind="saw"))
    _write("assets/audio/battle.wav", arpeggio([A4, C5, E5, C5], 0.13, vol=0.26, kind="square", reps=3))

    # SFX.
    _write("assets/audio/pickup.wav", tone(G4, 0.06, 0.3) + tone(C5, 0.08, 0.3))
    _write("assets/audio/hit.wav", tone(A3, 0.05, 0.35, "square") + noise(0.06, 0.25))
    _write("assets/audio/confirm.wav", tone(E5, 0.05, 0.25))
    _write("assets/audio/level.wav", tone(C5, 0.08, 0.3) + tone(E5, 0.08, 0.3) + tone(G4 * 2, 0.12, 0.3))
    print("wrote 7 audio files to assets/audio/")


if __name__ == "__main__":
    main()
