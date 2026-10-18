"""The RPG's music: two original loops, written here note by note and synthesized.

    python scripts/art/rpg_music.py        # writes projects/rpg/assets/meadow.ogg and clash.ogg

- `meadow.ogg`: the map. G major, 96 beats a minute, a soft square lead over
  a triangle bass and plucked chords; 16 bars.
- `clash.ogg`: the fight. A minor, 144 beats a minute, a driving bass, a
  pulse lead and a drum kit made of noise and a falling sine; 8 bars.

Each loop is exactly its bars long, and what rings past the end (a release,
a reverb tail) is folded onto its start, so it loops without a seam. The
music is this script's own and is dedicated to the public domain (CC0), as
the script is. Needs numpy and ffmpeg (with libvorbis).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

RATE = 32000
OUT = Path(__file__).resolve().parents[2] / 'projects' / 'rpg' / 'assets'

NOTES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def freq(name: str) -> float:
    """'A4' -> 440.0; 'F#3', 'Bb2'."""
    pitch, octave = name[:-1], int(name[-1])
    n = NOTES[pitch[0]] + (1 if pitch[1:] == '#' else -1 if pitch[1:] == 'b' else 0)
    return 440.0 * 2 ** ((n - 9) / 12 + (octave - 4))


# --- voices ---

def _envelope(n: int, attack: float, release: float) -> np.ndarray:
    env = np.ones(n)
    a = min(n, int(attack * RATE))
    r = min(n - a, int(release * RATE))
    if a:
        env[:a] = np.linspace(0, 1, a)
    if r:
        env[n - r:] = np.linspace(1, 0, r)
    return env


def square(f: float, seconds: float, duty: float = 0.5) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    return np.where((t * f) % 1.0 < duty, 1.0, -1.0) * _envelope(len(t), 0.005, min(0.08, seconds / 3))


def triangle(f: float, seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    return (2 * np.abs(2 * ((t * f) % 1.0) - 1) - 1) * _envelope(len(t), 0.004, min(0.05, seconds / 4))


def pluck(f: float, seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    tone = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t)
    return tone * np.exp(-t * 5.0) * _envelope(len(t), 0.002, 0.02)


def kick(seconds: float = 0.25) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    f = 120 * np.exp(-t * 18) + 45
    return np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 14)


def noise(seconds: float, decay: float, seed: int) -> np.ndarray:
    t = np.arange(int(seconds * RATE)) / RATE
    rng = np.random.default_rng(seed)
    hiss = rng.uniform(-1, 1, len(t))
    hiss = hiss - np.concatenate([[0], hiss[:-1]]) * 0.6   # a little brighter
    return hiss * np.exp(-t * decay)


# --- a loop of bars ---

class Loop:
    def __init__(self, bpm: float, bars: int, beats_per_bar: int = 4):
        self.beat = 60.0 / bpm
        self.length = int(round(bars * beats_per_bar * self.beat * RATE))
        self.mix = np.zeros(self.length + RATE * 2)   # room for tails, folded back at the end

    def put(self, sound: np.ndarray, at_beat: float, gain: float) -> None:
        start = int(round(at_beat * self.beat * RATE))
        self.mix[start:start + len(sound)] += sound * gain

    def line(self, voice, notes: str, gain: float, start: float = 0.0, length: float = 1.0) -> None:
        """'G4:1 A4:.5 r:.5 B4:2' — a note and its beats ('r' rests), one after another."""
        at = start
        for token in notes.split():
            name, _, beats = token.partition(':')
            beats = float(beats) if beats else 1.0
            if name != 'r':
                self.put(voice(freq(name), beats * self.beat * length), at, gain)
            at += beats

    def finish(self, echo: float = 0.0) -> np.ndarray:
        mix = self.mix.copy()
        if echo:
            d = int(self.beat * 0.75 * RATE)
            for k in (1, 2, 3):
                mix[d * k:] += self.mix[:len(mix) - d * k] * echo ** k
        out = mix[:self.length].copy()
        tail = mix[self.length:]
        out[:len(tail)] += tail[:self.length]   # what rings past the end comes back at the start
        peak = np.max(np.abs(out)) or 1.0
        return out / peak * 0.85


# --- the two pieces ---

def meadow() -> np.ndarray:
    song = Loop(bpm=96, bars=16)
    # G  Em  C  D | G  Em  Am  D | C  D  Bm  Em | C  D  G  G
    chords = ['G3 B3 D4', 'E3 G3 B3', 'C3 E3 G3', 'D3 F#3 A3',
              'G3 B3 D4', 'E3 G3 B3', 'A3 C4 E4', 'D3 F#3 A3',
              'C3 E3 G3', 'D3 F#3 A3', 'B2 D3 F#3', 'E3 G3 B3',
              'C3 E3 G3', 'D3 F#3 A3', 'G3 B3 D4', 'G3 B3 D4']
    roots = ['G2', 'E2', 'C2', 'D2', 'G2', 'E2', 'A2', 'D2', 'C2', 'D2', 'B1', 'E2', 'C2', 'D2', 'G2', 'G2']
    for bar, (chord, root) in enumerate(zip(chords, roots)):
        for beat in (0, 1.5, 2, 3):
            for n in chord.split():
                song.put(pluck(freq(n), 0.9), bar * 4 + beat, 0.10)
        song.line(triangle, f'{root}:2 {root}:1 {root}:1', 0.55, start=bar * 4, length=0.9)
    melody = ('D5:1 B4:.5 G4:.5 A4:1 B4:1  G4:1.5 E4:.5 E4:2  E4:1 G4:1 C5:1 B4:1  A4:3 r:1 '
              'D5:1 B4:.5 G4:.5 A4:1 B4:1  G4:1 B4:1 E5:2  E5:.5 D5:.5 C5:1 A4:1 C5:1  D5:3 r:1 '
              'E5:1 D5:.5 C5:.5 B4:1 G4:1  A4:1 B4:.5 C5:.5 D5:2  D5:1 F#4:1 B4:1 D5:1  B4:2 G4:2 '
              'C5:1 B4:.5 A4:.5 G4:1 E4:1  F#4:1 A4:1 D5:2  B4:1 A4:.5 G4:.5 A4:1 B4:1  G4:3 r:1')
    song.line(lambda f, s: square(f, s, 0.25), melody, 0.16, length=0.92)
    return song.finish(echo=0.25)


def clash() -> np.ndarray:
    song = Loop(bpm=144, bars=8)
    roots = ['A1', 'A1', 'F1', 'G1', 'A1', 'A1', 'F1', 'E1']
    for bar, root in enumerate(roots):
        octave = root[:-1] + str(int(root[-1]) + 1)
        song.line(triangle, ' '.join([f'{root}:.5', f'{root}:.5', f'{octave}:.5', f'{root}:.5'] * 2), 0.6,
                  start=bar * 4, length=0.85)
        for beat in range(4):
            song.put(kick(), bar * 4 + beat, 0.9 if beat % 2 == 0 else 0.0)
            song.put(noise(0.18, 22, bar * 8 + beat), bar * 4 + beat, 0.45 if beat % 2 else 0.0)   # snare
            song.put(noise(0.05, 90, 1000 + bar * 8 + beat), bar * 4 + beat + 0.5, 0.18)       # hat
    lead = ('A4:.5 C5:.5 E5:.5 A5:.5 G5:1 E5:1  A4:.5 C5:.5 E5:.5 G5:.5 F5:1 E5:1  '
            'F5:.5 E5:.5 D5:.5 C5:.5 D5:1 A4:1  G4:.5 B4:.5 D5:.5 G5:.5 F5:1 D5:1  '
            'A4:.5 C5:.5 E5:.5 A5:.5 B5:1 A5:1  G5:.5 F5:.5 E5:.5 D5:.5 E5:1 C5:1  '
            'F5:.5 A5:.5 G5:.5 F5:.5 E5:1 D5:1  E5:1 G#4:1 B4:1 E5:1')
    song.line(lambda f, s: square(f, s, 0.5), lead, 0.13, length=0.8)
    return song.finish(echo=0.15)


def write_ogg(samples: np.ndarray, path: Path) -> None:
    pcm = (np.clip(samples, -1, 1) * 32767).astype('<i2')
    with tempfile.TemporaryDirectory() as tmp:
        wav_path = Path(tmp) / 'x.wav'
        with wave.open(str(wav_path), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(wav_path), '-c:a', 'libvorbis', '-q:a', '3',
                        '-map_metadata', '-1', '-fflags', '+bitexact', str(path)], check=True)


def main() -> int:
    for name, piece in (('meadow', meadow), ('clash', clash)):
        samples = piece()
        write_ogg(samples, OUT / f'{name}.ogg')
        print(f'{name}.ogg: {len(samples) / RATE:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
