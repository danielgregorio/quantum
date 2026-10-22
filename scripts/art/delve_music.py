"""Delve's music: two original loops, written here note by note and synthesized.

    python scripts/art/delve_music.py     # writes projects/delve/assets/torchlight.ogg and crypt.ogg

- `torchlight.ogg`: the title and the end. D minor, 84 beats a minute, a
  plucked harp over a held low fifth, a bell melody that echoes; 16 bars.
- `crypt.ogg`: the three crypts. D minor, 66 beats a minute, a dark drone
  that swells, a slow heartbeat, a high bell now and then and a breath of
  wind; 16 bars.
- `warden.ogg`: the fight with the vault's warden, the skeleton archer.
  D minor, 132 beats a minute: a beat on every beat, a plucked ostinato on
  the low D and its fifth, the drone of the crypt a fifth higher and bell
  stabs; 8 bars.
- `bones1.ogg`, `bones2.ogg`, `bones3.ogg`: a skeleton falling apart, a
  few dry clicks each, so that no two fall alike (qg:play sounds=).

The voices, the loop (what rings past the end comes back at the start, so it
loops without a seam) and the .ogg writer are scripts/art/rpg_music.py's.
The music is this script's own and is dedicated to the public domain (CC0),
as the script is. Needs numpy and ffmpeg (with libvorbis).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rpg_music import RATE, Loop, _envelope, freq, kick, noise, pluck, write_ogg  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'delve' / 'assets'


# --- voices of their own ---

def bell(f: float, seconds: float) -> np.ndarray:
    """Two inharmonic partials over the fundamental, a long fall: a small bell."""
    t = np.arange(int(seconds * RATE)) / RATE
    tone = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 3) \
        + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 6)
    return tone * np.exp(-t * 1.6) * _envelope(len(t), 0.003, 0.05)


def pad(f: float, seconds: float) -> np.ndarray:
    """Three slightly detuned sines that swell in and out: a held, dark chord tone."""
    t = np.arange(int(seconds * RATE)) / RATE
    tone = sum(np.sin(2 * np.pi * f * d * t + p) for d, p in ((1.0, 0.0), (1.004, 1.3), (0.996, 2.1))) / 3
    return tone * _envelope(len(t), min(1.5, seconds / 3), min(1.5, seconds / 3))


def thump(seconds: float = 0.4) -> np.ndarray:
    """A muffled low beat: the kick, slower and darker."""
    return kick(seconds) * 0.8


def wind(seconds: float, seed: int) -> np.ndarray:
    """Noise smoothed into a low hiss that swells and fades."""
    smooth = noise(seconds, 0.0, seed)
    for k in (90, 90, 90):            # three passes of a moving average: below a few hundred hertz
        smooth = np.convolve(smooth, np.ones(k) / k, mode='same')
    return smooth / (np.max(np.abs(smooth)) or 1.0) * _envelope(len(smooth), seconds / 2, seconds / 2)


# --- the two pieces ---

def torchlight() -> np.ndarray:
    song = Loop(bpm=84, bars=16)
    # Dm  Bb  F  C | Dm  Bb  Gm  A | Dm  Bb  F  C | Gm  A  Dm  Dm
    chords = ['D3 F3 A3', 'Bb2 D3 F3', 'F3 A3 C4', 'C3 E3 G3', 'D3 F3 A3', 'Bb2 D3 F3', 'G2 Bb2 D3', 'A2 C#3 E3',
              'D3 F3 A3', 'Bb2 D3 F3', 'F3 A3 C4', 'C3 E3 G3', 'G2 Bb2 D3', 'A2 C#3 E3', 'D3 F3 A3', 'D3 F3 A3']
    for bar, chord in enumerate(chords):
        notes = chord.split()
        for i, beat in enumerate((0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5)):     # the harp, up and down the chord
            n = notes[[0, 1, 2, 1, 0, 1, 2, 1][i]]
            octave = n[:-1] + str(int(n[-1]) + 1)
            song.put(pluck(freq(octave), 1.2), bar * 4 + beat, 0.09)
        root = notes[0][:-1] + str(int(notes[0][-1]) - 1)
        song.put(pad(freq(root), 4 * song.beat), bar * 4, 0.35)
    melody = ('A4:2 F4:1 D4:1  D5:2 C5:1 Bb4:1  A4:3 F4:1  G4:4  '
              'A4:2 F4:1 D4:1  D5:2 F5:1 E5:1  D5:2 Bb4:2  C#5:4  '
              'F5:2 E5:1 D5:1  D5:2 C5:1 Bb4:1  C5:2 A4:2  G4:4  '
              'Bb4:2 A4:1 G4:1  A4:2 C#5:2  D5:4  r:4')
    song.line(bell, melody, 0.14, length=1.0)
    return song.finish(echo=0.35)


def crypt() -> np.ndarray:
    song = Loop(bpm=66, bars=16)
    roots = ['D2', 'D2', 'Bb1', 'Bb1', 'G1', 'G1', 'A1', 'A1'] * 2
    for bar, root in enumerate(roots):
        fifth = {'D2': 'A2', 'Bb1': 'F2', 'G1': 'D2', 'A1': 'E2'}[root]
        song.put(pad(freq(root), 4 * song.beat), bar * 4, 0.5)
        song.put(pad(freq(fifth), 4 * song.beat), bar * 4, 0.25)
        song.put(thump(), bar * 4, 0.55)                                  # a slow heartbeat: one-and
        song.put(thump(), bar * 4 + 0.5, 0.3)
        if bar % 4 == 3:
            song.put(wind(3.5 * song.beat, 7 + bar), bar * 4 + 0.5, 0.12)
    bells = ('r:6 A5:2  r:4 F5:4  r:6 D5:2  r:2 C#5:2 r:4  '
             'r:6 A5:2  r:4 Bb5:4  r:6 G5:2  r:2 A5:2 r:4')
    song.line(bell, bells, 0.1, length=1.0)
    return song.finish(echo=0.45)


def warden() -> np.ndarray:
    song = Loop(bpm=132, bars=8)
    roots = ['D2', 'D2', 'Bb1', 'A1', 'D2', 'D2', 'G1', 'A1']
    for bar, root in enumerate(roots):
        fifth = {'D2': 'A2', 'Bb1': 'F2', 'G1': 'D2', 'A1': 'E2'}[root]
        song.put(pad(freq(fifth), 4 * song.beat), bar * 4, 0.35)
        for beat in range(4):                                             # a beat on every beat
            song.put(thump(0.25), bar * 4 + beat, 0.6 if beat % 2 == 0 else 0.4)
        for i, beat in enumerate((0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5)):       # the ostinato: the root and its fifth
            n = (root, fifth)[i % 2]
            up = n[:-1] + str(int(n[-1]) + 1)
            song.put(pluck(freq(up), 0.4), bar * 4 + beat, 0.12)
    stabs = 'D5:1 r:3  D5:1 r:1 F5:1 r:1  Bb4:1 r:3  A4:2 C#5:2  D5:1 r:3  D5:1 r:1 F5:1 r:1  G5:2 F5:2  E5:2 C#5:2'
    song.line(bell, stabs, 0.12, length=0.6)
    return song.finish(echo=0.2)


def bones(seed: int) -> np.ndarray:
    """A skeleton falling apart: a few dry clicks, each a short burst of bright noise, a little apart."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(0.45 * RATE))
    at = 0.0
    for _ in range(int(rng.integers(4, 7))):
        click = noise(0.04, 120.0, int(rng.integers(0, 1 << 30))) * rng.uniform(0.5, 1.0)
        start = int(at * RATE)
        end = min(len(out), start + len(click))
        out[start:end] += click[:end - start]
        at += rng.uniform(0.03, 0.09)
    return out / (np.max(np.abs(out)) or 1.0) * 0.8


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for k in (1, 2, 3):
        write_ogg(bones(40 + k), OUT / f'bones{k}.ogg')
    for name, piece in (('torchlight', torchlight), ('crypt', crypt), ('warden', warden)):
        samples = piece()
        write_ogg(samples, OUT / f'{name}.ogg')
        print(f'{name}.ogg: {len(samples) / RATE:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
