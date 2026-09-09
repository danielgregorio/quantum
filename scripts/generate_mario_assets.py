"""
Generate game assets for Super Mario Bros World 1-1.

Extracts authentic NES sprites from reference sheets (mariouniverse.com)
and assembles them into the format needed by the Quantum Game Engine.

Reference sheets expected in projects/mario/static/:
  _mario_ref.png, _enemies_ref.png, _blocks_ref.png,
  _items_objects_ref.png, _tiles_ref.png

Generates:
  - tileset.png  (8x4 grid of 16x16 tiles)
  - player.png   (5 frames, 16x32 each = 80x32)
  - goomba.png   (2 frames, 16x16 each = 32x16)
  - coin.png     (4 frames, 16x16 each = 64x16)
  - jump.wav, coin.wav, powerup.wav (8-bit generated sounds)
"""

import struct
import wave
import math
from pathlib import Path

from PIL import Image, ImageDraw

OUTPUT_DIR = Path(__file__).parent.parent / "projects" / "mario" / "static"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

T = (0, 0, 0, 0)  # Transparent


def load_ref(name):
    """Load a reference sprite sheet."""
    path = OUTPUT_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Reference sheet not found: {path}")
    return Image.open(path).convert('RGBA')


def extract_sprite(img, x, y, w, h):
    """Extract a sprite region from a reference sheet."""
    return img.crop((x, y, x + w, y + h))


def find_sprite_bounds(img, start_x, start_y, scan_w=32, scan_h=32):
    """Find tight bounding box of non-transparent pixels near a start point."""
    min_x, max_x = start_x + scan_w, start_x
    min_y, max_y = start_y + scan_h, start_y
    for y in range(start_y, min(start_y + scan_h, img.height)):
        for x in range(start_x, min(start_x + scan_w, img.width)):
            if img.getpixel((x, y))[3] > 10:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)
    if max_x < min_x:
        return None
    return (min_x, min_y, max_x + 1, max_y + 1)


def center_in_frame(sprite, frame_w, frame_h, align_bottom=True):
    """Center a sprite in a frame of given size, optionally bottom-aligned."""
    frame = Image.new('RGBA', (frame_w, frame_h), T)
    sw, sh = sprite.size
    x = (frame_w - sw) // 2
    if align_bottom:
        y = frame_h - sh
    else:
        y = (frame_h - sh) // 2
    frame.paste(sprite, (x, y), sprite)
    return frame


# =============================================================================
# Player Spritesheet (Big Mario, 5 frames, 16x32 each = 80x32)
# =============================================================================

def generate_player():
    """Extract Big Mario sprites from reference sheet."""
    mario_ref = load_ref('_mario_ref.png')

    # Big Mario upright sprites are in row at y=90-121 (32px tall)
    # Row y=90 verified positions:
    #   Sprite 0 (x=1):   Standing idle facing right
    #   Sprite 1 (x=28):  Walk frame (similar)
    #   Sprite 2 (x=52):  Walk/run frame 1
    #   Sprite 3 (x=78):  Walk frame
    #   Sprite 4 (x=103): Walk frame
    #   Sprite 5 (x=127): Walk/run frame 2
    #   Sprite 6 (x=152): Jump pose

    # Our spritesheet layout: idle, walk1, walk2, jump, dead
    ROW_Y = 90
    frame_defs = [
        ('idle',  1,   16),  # Frame 0: standing idle facing right
        ('walk1', 52,  18),  # Frame 1: run frame 1
        ('walk2', 127, 18),  # Frame 2: run frame 2
        ('jump',  152, 18),  # Frame 3: jump pose
        ('dead',  1,   16),  # Frame 4: reuse idle for dead
    ]

    img = Image.new('RGBA', (80, 32), T)

    for frame_idx, (name, x, scan_w) in enumerate(frame_defs):
        bounds = find_sprite_bounds(mario_ref, x, ROW_Y, scan_w, 32)
        if bounds:
            sprite = mario_ref.crop(bounds)
            # Flip each frame so Mario faces RIGHT (standard for platformers)
            sprite = sprite.transpose(Image.FLIP_LEFT_RIGHT)
            framed = center_in_frame(sprite, 16, 32, align_bottom=True)
            img.paste(framed, (frame_idx * 16, 0), framed)

    path = OUTPUT_DIR / "player.png"
    img.save(path)
    print(f"  Created {path}")


# =============================================================================
# Goomba Spritesheet (2 frames, 16x16 each = 32x16)
# =============================================================================

def generate_goomba():
    """Extract Goomba sprites from reference sheet."""
    enemies_ref = load_ref('_enemies_ref.png')

    # Find goomba sprites - they're in the top row
    sprites = []
    in_sprite = False
    start_x = None

    for x in range(min(80, enemies_ref.width)):
        has_pixel = any(enemies_ref.getpixel((x, y))[3] > 10
                       for y in range(20))
        if has_pixel and not in_sprite:
            start_x = x
            in_sprite = True
        elif not has_pixel and in_sprite:
            sprites.append((start_x, x - 1))
            in_sprite = False
            if len(sprites) >= 2:
                break
    if in_sprite and len(sprites) < 2:
        sprites.append((start_x, min(79, enemies_ref.width - 1)))

    img = Image.new('RGBA', (32, 16), T)

    for i, (sx, ex) in enumerate(sprites[:2]):
        bounds = find_sprite_bounds(enemies_ref, sx, 0, ex - sx + 1, 20)
        if bounds:
            sprite = enemies_ref.crop(bounds)
            framed = center_in_frame(sprite, 16, 16, align_bottom=True)
            img.paste(framed, (i * 16, 0), framed)

    path = OUTPUT_DIR / "goomba.png"
    img.save(path)
    print(f"  Created {path}")


# =============================================================================
# Coin Spritesheet (4 frames, 16x16 each = 64x16)
# =============================================================================

def generate_coin():
    """Extract coin sprites from items_objects reference sheet."""
    items_ref = load_ref('_items_objects_ref.png')

    img = Image.new('RGBA', (64, 16), T)

    coin_regions = [
        (1, 85, 14, 16),    # Frame 0: full front
        (17, 85, 14, 16),   # Frame 1: 3/4 turn
        (33, 85, 14, 16),   # Frame 2: side/edge
        (49, 85, 14, 16),   # Frame 3: 3/4 turn back
    ]

    for i, (cx, cy, cw, ch) in enumerate(coin_regions):
        bounds = find_sprite_bounds(items_ref, cx, cy, cw, ch)
        if bounds:
            sprite = items_ref.crop(bounds)
            framed = center_in_frame(sprite, 16, 16, align_bottom=False)
            img.paste(framed, (i * 16, 0), framed)
        else:
            # Fallback: use first frame
            if i > 0:
                first = img.crop((0, 0, 16, 16))
                img.paste(first, (i * 16, 0), first)

    path = OUTPUT_DIR / "coin.png"
    img.save(path)
    print(f"  Created {path}")


# =============================================================================
# Tileset (8x4 grid of 16x16 tiles = 128x64)
# =============================================================================

def generate_tileset():
    """Build tileset from reference sheets + NES-accurate programmatic tiles."""
    blocks_ref = load_ref('_blocks_ref.png')

    img = Image.new('RGBA', (128, 64), T)
    draw = ImageDraw.Draw(img)

    # ---- Authentic tiles from reference sheets ----

    # Tile 1: Ground Top = OW Brick from blocks_ref (272, 112)
    brick = extract_sprite(blocks_ref, 272, 112, 16, 16)
    img.paste(brick, (0, 0), brick)

    # Tile 2: Ground Fill = same brick pattern
    img.paste(brick, (16, 0), brick)

    # Tile 3: Brick = same OW Brick
    img.paste(brick, (32, 0), brick)

    # Tile 4: Question Block from blocks_ref (81, 112)
    qblock = extract_sprite(blocks_ref, 81, 112, 16, 16)
    img.paste(qblock, (48, 0), qblock)

    # Tile 5: Used Block from blocks_ref (129, 112)
    used = extract_sprite(blocks_ref, 129, 112, 16, 16)
    img.paste(used, (64, 0), used)

    # ---- NES-accurate programmatic tiles ----

    # Pipe tiles (NES overworld green pipe colors)
    _draw_pipe_tl(img, 80, 0)   # Tile 6: Pipe Top-Left
    _draw_pipe_tr(img, 96, 0)   # Tile 7: Pipe Top-Right
    _draw_pipe_bl(img, 112, 0)  # Tile 8: Pipe Body-Left

    # Tile 9: Pipe Body-Right
    _draw_pipe_br(img, 0, 16)

    # Tile 10: Sky (transparent) - skip

    # Tile 11: Cloud
    _draw_cloud(img, 32, 16)

    # Tile 12: Bush
    _draw_bush(img, 48, 16)

    # Tile 13: Hill
    _draw_hill(img, 64, 16)

    # Tile 14: Stair Block = use OW Brick (NES-accurate for stairs)
    img.paste(brick, (80, 16), brick)

    # Tile 15: Flagpole
    _draw_flagpole(img, 96, 16)

    # Tile 16: Flag
    _draw_flag(img, 112, 16)

    path = OUTPUT_DIR / "tileset.png"
    img.save(path)
    print(f"  Created {path}")


# NES pipe colors (overworld palette)
_PH = (184, 248, 24, 255)    # highlight (light yellow-green)
_PG = (0, 168, 0, 255)       # main green
_PD = (0, 88, 0, 255)        # dark green
_PK = (0, 0, 0, 255)         # outline black


def _draw_pipe_tl(img, ox, oy):
    """Pipe top-left tile: rim at top, body below."""
    # Rim (rows 0-3): full width with highlight on left
    for y in range(4):
        for x in range(16):
            if y == 0 or x == 0:
                img.putpixel((ox + x, oy + y), _PK)
            elif x <= 4:
                img.putpixel((ox + x, oy + y), _PH)
            elif x <= 12:
                img.putpixel((ox + x, oy + y), _PG)
            else:
                img.putpixel((ox + x, oy + y), _PD)
    # Body (rows 4-15): narrower, starts at x=2
    for y in range(4, 16):
        for x in range(2, 16):
            if x == 2:
                img.putpixel((ox + x, oy + y), _PK)
            elif x <= 5:
                img.putpixel((ox + x, oy + y), _PH)
            elif x <= 12:
                img.putpixel((ox + x, oy + y), _PG)
            else:
                img.putpixel((ox + x, oy + y), _PD)


def _draw_pipe_tr(img, ox, oy):
    """Pipe top-right tile: rim at top, body below."""
    # Rim (rows 0-3): full width with dark on right
    for y in range(4):
        for x in range(16):
            if y == 0 or x == 15:
                img.putpixel((ox + x, oy + y), _PK)
            elif x <= 2:
                img.putpixel((ox + x, oy + y), _PG)
            elif x <= 12:
                img.putpixel((ox + x, oy + y), _PG)
            else:
                img.putpixel((ox + x, oy + y), _PD)
    # Body (rows 4-15): narrower, ends at x=13
    for y in range(4, 16):
        for x in range(0, 14):
            if x <= 2:
                img.putpixel((ox + x, oy + y), _PG)
            elif x <= 10:
                img.putpixel((ox + x, oy + y), _PG)
            elif x <= 12:
                img.putpixel((ox + x, oy + y), _PD)
            else:
                img.putpixel((ox + x, oy + y), _PK)


def _draw_pipe_bl(img, ox, oy):
    """Pipe body-left tile."""
    for y in range(16):
        for x in range(2, 16):
            if x == 2:
                img.putpixel((ox + x, oy + y), _PK)
            elif x <= 5:
                img.putpixel((ox + x, oy + y), _PH)
            elif x <= 12:
                img.putpixel((ox + x, oy + y), _PG)
            else:
                img.putpixel((ox + x, oy + y), _PD)


def _draw_pipe_br(img, ox, oy):
    """Pipe body-right tile."""
    for y in range(16):
        for x in range(0, 14):
            if x <= 2:
                img.putpixel((ox + x, oy + y), _PG)
            elif x <= 10:
                img.putpixel((ox + x, oy + y), _PG)
            elif x <= 12:
                img.putpixel((ox + x, oy + y), _PD)
            else:
                img.putpixel((ox + x, oy + y), _PK)


def _draw_cloud(img, ox, oy):
    """NES-style cloud tile: white puff with light blue outline."""
    CW = (252, 252, 252, 255)  # cloud white
    CO = (148, 208, 252, 255)  # cloud outline (light blue)
    # Draw cloud shape (rounded puffs)
    cloud_rows = [
        "                ",
        "                ",
        "     OOOO       ",
        "    OWWWWO      ",
        "   OWWWWWWOO    ",
        "  OWWWWWWWWWO   ",
        " OWWWWWWWWWWWO  ",
        " OWWWWWWWWWWWO  ",
        "OWWWWWWWWWWWWWO ",
        "OWWWWWWWWWWWWWO ",
        "OWWWWWWWWWWWWWWO",
        " OWWWWWWWWWWWWO ",
        "  OOOWWWWWOOO   ",
        "     OOOOO      ",
        "                ",
        "                ",
    ]
    for y, row in enumerate(cloud_rows):
        for x, ch in enumerate(row):
            if ch == 'W':
                img.putpixel((ox + x, oy + y), CW)
            elif ch == 'O':
                img.putpixel((ox + x, oy + y), CO)


def _draw_bush(img, ox, oy):
    """NES-style bush tile: green rounded shape on ground."""
    BG = (0, 168, 0, 255)     # bush green
    BD = (0, 104, 0, 255)     # bush dark
    BH = (80, 208, 24, 255)   # bush highlight
    bush_rows = [
        "                ",
        "                ",
        "                ",
        "                ",
        "                ",
        "     DDDD       ",
        "    DGGGGD      ",
        "   DGHGGGGD     ",
        "  DGHHGGGGDD    ",
        " DGHGGGGGGGGD   ",
        " DGGGGGGGGGGGD  ",
        "DGGGGGGGGGGGGGD ",
        "DGGGGGGGGGGGGGD ",
        "DDDDDDDDDDDDDDD",
        "                ",
        "                ",
    ]
    cmap = {'G': BG, 'D': BD, 'H': BH}
    for y, row in enumerate(bush_rows):
        for x, ch in enumerate(row):
            if ch in cmap:
                img.putpixel((ox + x, oy + y), cmap[ch])


def _draw_hill(img, ox, oy):
    """NES-style hill tile: green triangular mound."""
    HG = (80, 176, 48, 255)   # hill green
    HD = (0, 128, 0, 255)     # hill dark outline
    HH = (148, 224, 68, 255)  # hill highlight
    hill_rows = [
        "                ",
        "                ",
        "                ",
        "       DD       ",
        "      DHHD      ",
        "     DHGGHD     ",
        "    DHGGGGHD    ",
        "   DHGGGGGGHD   ",
        "  DHGGGGGGGGHD  ",
        " DHGGGGGGGGGGHD ",
        "DHGGGGGGGGGGGGHD",
        "DGGGGGGGGGGGGGD ",
        "DGGGGGGGGGGGGD  ",
        "DGGGGGGGGGGGD   ",
        "DDDDDDDDDDDDD  ",
        "                ",
    ]
    cmap = {'G': HG, 'D': HD, 'H': HH}
    for y, row in enumerate(hill_rows):
        for x, ch in enumerate(row):
            if ch in cmap:
                img.putpixel((ox + x, oy + y), cmap[ch])


def _draw_flagpole(img, ox, oy):
    FP = (168, 168, 168, 255)
    FP2 = (120, 120, 120, 255)
    for y in range(16):
        img.putpixel((ox + 7, oy + y), FP)
        img.putpixel((ox + 8, oy + y), FP2)


def _draw_flag(img, ox, oy):
    FP = (168, 168, 168, 255)
    FG = (0, 200, 0, 255)
    for y in range(16):
        img.putpixel((ox + 8, oy + y), FP)
    for y in range(8):
        for x in range(8 - y):
            img.putpixel((ox + x, oy + y + 1), FG)


# =============================================================================
# Sound Generation (8-bit style)
# =============================================================================

def generate_tone(frequency, duration, sample_rate=22050, volume=0.3,
                  envelope='decay', duty_cycle=0.5):
    n_samples = int(sample_rate * duration)
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        env_t = i / n_samples
        phase = (t * frequency) % 1.0
        value = 1.0 if phase < duty_cycle else -1.0
        if envelope == 'decay':
            env = max(0, 1.0 - env_t * 2)
        elif envelope == 'pluck':
            env = max(0, 1.0 - env_t * 3)
        elif envelope == 'sustain':
            env = 1.0 if env_t < 0.8 else max(0, 1.0 - (env_t - 0.8) * 5)
        else:
            env = 1.0
        sample = int(value * env * volume * 32767)
        samples.append(max(-32768, min(32767, sample)))
    return samples


def write_wav(filename, samples, sample_rate=22050):
    path = OUTPUT_DIR / filename
    with wave.open(str(path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = struct.pack(f'<{len(samples)}h', *samples)
        wf.writeframes(data)
    print(f"  Created {path}")


# =============================================================================
# Koopa Troopa Spritesheet (2 frames, 16x24 each = 32x24)
# =============================================================================

def generate_koopa():
    """Draw NES-style Koopa Troopa (green turtle) programmatically."""
    img = Image.new('RGBA', (32, 24), T)

    # NES Koopa colors
    GS = (0, 168, 0, 255)       # shell green
    GD = (0, 104, 0, 255)       # shell dark
    GH = (148, 224, 68, 255)    # shell highlight
    SK = (224, 168, 80, 255)    # skin tan
    SD = (168, 112, 40, 255)    # skin dark
    WH = (252, 252, 252, 255)   # white (eyes)
    BK = (0, 0, 0, 255)         # black (outline/pupils)

    # Frame 0: walking right, left foot forward
    f0 = [
        "      GGGG      ",
        "     GHGGGD     ",
        "    GHHGGGGD    ",
        "    GHGGGGDD    ",
        "   GGGGGGGGD    ",
        "   GGGGGGGDD    ",
        "    DDDDDDDD    ",
        "     SSBBSS     ",
        "    SSWBBWSS    ",
        "    SSSBBBSS    ",
        "     SSSSSS     ",
        "    SSSSSSSS    ",
        "   SSSSSSSSSS   ",
        "    SSSSSSSS    ",
        "     SS  SS     ",
        "    SS    SS    ",
        "    DD    DD    ",
    ]
    # Frame 1: walking right, right foot forward
    f1 = [
        "      GGGG      ",
        "     GHGGGD     ",
        "    GHHGGGGD    ",
        "    GHGGGGDD    ",
        "   GGGGGGGGD    ",
        "   GGGGGGGDD    ",
        "    DDDDDDDD    ",
        "     SSBBSS     ",
        "    SSWBBWSS    ",
        "    SSSBBBSS    ",
        "     SSSSSS     ",
        "    SSSSSSSS    ",
        "   SSSSSSSSSS   ",
        "    SSSSSSSS    ",
        "     SS  SS     ",
        "      SS  SS    ",
        "      DD  DD    ",
    ]

    cmap = {'G': GS, 'H': GH, 'D': GD, 'S': SK, 'B': BK, 'W': WH}
    for frame_idx, frame_data in enumerate([f0, f1]):
        ox = frame_idx * 16
        for y, row in enumerate(frame_data):
            for x, ch in enumerate(row[:16]):
                if ch in cmap:
                    img.putpixel((ox + x, y + (24 - len(frame_data)), ), cmap[ch])

    path = OUTPUT_DIR / "koopa.png"
    img.save(path)
    print(f"  Created {path}")


# =============================================================================
# Individual block sprites (16x16 each, extracted from blocks_ref)
# =============================================================================

def generate_block_sprites():
    """Extract individual brick and Q-block tiles for use as sprites."""
    blocks_ref = load_ref('_blocks_ref.png')

    # Brick (OW palette) at (272, 112)
    brick = extract_sprite(blocks_ref, 272, 112, 16, 16)
    path = OUTPUT_DIR / "brick_tile.png"
    brick.save(path)
    print(f"  Created {path}")

    # Q-block (OW palette) at (81, 112)
    qblock = extract_sprite(blocks_ref, 81, 112, 16, 16)
    path = OUTPUT_DIR / "qblock_tile.png"
    qblock.save(path)
    print(f"  Created {path}")

    # Used block at (129, 112)
    used = extract_sprite(blocks_ref, 129, 112, 16, 16)
    path = OUTPUT_DIR / "used_tile.png"
    used.save(path)
    print(f"  Created {path}")


def _square_wave(freq, t, duty=0.25):
    """NES-style square wave with configurable duty cycle."""
    if freq == 0:
        return 0.0
    phase = (t * freq) % 1.0
    return 1.0 if phase < duty else -1.0


def generate_overworld_theme():
    """Generate 8-bit approximation of SMB World 1-1 overworld theme.

    Uses 44100 Hz sample rate, 25% duty cycle (NES pulse channel 1),
    tempo ~180 BPM (eighth note = 0.167s).
    Melody + bass accompaniment for fuller sound.
    """
    sr = 44100
    # Eighth note duration for ~180 BPM
    eighth = 0.167
    R = 0  # rest

    # SMB overworld melody (frequencies in Hz, durations in eighth notes)
    melody = [
        # Intro (bars 1-2): E5 E5 . E5 . C5 E5 . G5 ... G4 ...
        (659, 1), (659, 1), (R, 1), (659, 1), (R, 1), (523, 1), (659, 2),
        (784, 2), (R, 2), (392, 2), (R, 2),
        # Bars 3-4
        (523, 3), (R, 1), (392, 3), (R, 1), (330, 3), (R, 1),
        (440, 2), (494, 1), (R, 1), (466, 1), (440, 2), (R, 1),
        # Bars 5-6
        (392, 1.5), (659, 1.5), (784, 1.5), (880, 2), (R, 1),
        (698, 1.5), (784, 2), (R, 1), (659, 2), (R, 1),
        (523, 1.5), (587, 1.5), (494, 1.5), (R, 2),
        # Bars 7-8 (repeat 3-4)
        (523, 3), (R, 1), (392, 3), (R, 1), (330, 3), (R, 1),
        (440, 2), (494, 1), (R, 1), (466, 1), (440, 2), (R, 1),
        # Bars 9-10 (repeat 5-6)
        (392, 1.5), (659, 1.5), (784, 1.5), (880, 2), (R, 1),
        (698, 1.5), (784, 2), (R, 1), (659, 2), (R, 1),
        (523, 1.5), (587, 1.5), (494, 1.5), (R, 2),
    ]

    # Simple bass accompaniment (root notes, lower octave)
    bass = [
        # Bars 1-2
        (165, 1), (R, 1), (165, 1), (R, 1), (165, 1), (R, 1), (165, 1), (R, 1),
        (196, 2), (R, 2), (131, 2), (R, 2),
        # Bars 3-4
        (131, 3), (R, 1), (131, 3), (R, 1), (110, 3), (R, 1),
        (147, 2), (165, 1), (R, 1), (156, 1), (147, 2), (R, 1),
        # Bars 5-6
        (131, 1.5), (165, 1.5), (196, 1.5), (220, 2), (R, 1),
        (175, 1.5), (196, 2), (R, 1), (165, 2), (R, 1),
        (131, 1.5), (147, 1.5), (123, 1.5), (R, 2),
        # Bars 7-10 (repeat)
        (131, 3), (R, 1), (131, 3), (R, 1), (110, 3), (R, 1),
        (147, 2), (165, 1), (R, 1), (156, 1), (147, 2), (R, 1),
        (131, 1.5), (165, 1.5), (196, 1.5), (220, 2), (R, 1),
        (175, 1.5), (196, 2), (R, 1), (165, 2), (R, 1),
        (131, 1.5), (147, 1.5), (123, 1.5), (R, 2),
    ]

    def render_track(notes, duty, volume):
        """Render a list of (freq, dur_eighths) to samples."""
        samples = []
        for freq, dur_eighths in notes:
            dur = dur_eighths * eighth
            n = int(sr * dur)
            for i in range(n):
                t = i / sr
                env_t = i / n
                if freq == 0:
                    samples.append(0.0)
                else:
                    val = _square_wave(freq, t, duty)
                    # Smooth envelope: attack + sustain + release
                    attack = min(1.0, i / (sr * 0.005))  # 5ms attack
                    release = max(0.0, 1.0 - max(0, env_t - 0.85) * (1.0 / 0.15))
                    env = attack * release * (1.0 - env_t * 0.15)
                    samples.append(val * env * volume)
        return samples

    all_samples = []
    for _ in range(4):  # Loop 4x for ~45 seconds
        mel_samples = render_track(melody, duty=0.25, volume=0.20)
        bas_samples = render_track(bass, duty=0.50, volume=0.10)
        # Mix: pad shorter track
        max_len = max(len(mel_samples), len(bas_samples))
        for i in range(max_len):
            m = mel_samples[i] if i < len(mel_samples) else 0.0
            b = bas_samples[i] if i < len(bas_samples) else 0.0
            all_samples.append(max(-32768, min(32767, int((m + b) * 32767))))

    write_wav("theme.wav", all_samples, sr)


def generate_jump_sound():
    sr = 22050
    dur = 0.25
    n = int(sr * dur)
    samples = []
    for i in range(n):
        t = i / sr
        env_t = i / n
        freq = 300 + 500 * (t / dur)
        phase = (t * freq) % 1.0
        val = 1.0 if phase < 0.5 else -1.0
        env = max(0, 1.0 - env_t * 1.5)
        samples.append(max(-32768, min(32767, int(val * env * 0.25 * 32767))))
    write_wav("jump.wav", samples, sr)


def generate_coin_sound():
    samples = []
    samples.extend(generate_tone(988, 0.08, envelope='pluck', volume=0.25))
    samples.extend(generate_tone(1319, 0.15, envelope='decay', volume=0.25))
    write_wav("coin.wav", samples)


def generate_powerup_sound():
    samples = []
    for freq in [523, 659, 784, 1047]:
        samples.extend(generate_tone(freq, 0.08, envelope='pluck', volume=0.2))
    write_wav("powerup.wav", samples)


def generate_fanfare():
    """Generate SMB stage clear / flagpole fanfare."""
    sr = 22050
    beat = 0.12  # Fast tempo

    # Iconic SMB stage clear fanfare melody
    # G4 C5 E5 G5 C6 E6 G6-E6-G6 (ascending fanfare)
    fanfare_notes = [
        # First phrase - ascending
        (392, 1),   # G4
        (523, 1),   # C5
        (659, 1),   # E5
        (784, 2),   # G5 (held)
        (659, 1),   # E5
        (784, 4),   # G5 (held longer)
        (0, 1),     # rest
        # Second phrase - even higher
        (440, 1),   # A4
        (587, 1),   # D5
        (740, 1),   # F#5
        (880, 2),   # A5
        (740, 1),   # F#5
        (880, 4),   # A5
        (0, 1),
        # Final phrase - triumphant
        (494, 1),   # B4
        (659, 1),   # E5
        (831, 1),   # Ab5
        (988, 2),   # B5
        (831, 1),   # Ab5
        (988, 2),   # B5
        (1047, 4),  # C6 (final note, held)
        (0, 2),
    ]

    all_samples = []
    for freq, dur_beats in fanfare_notes:
        dur = dur_beats * beat
        n = int(sr * dur)
        for i in range(n):
            t = i / sr
            env_t = i / n
            if freq == 0:
                all_samples.append(0)
            else:
                phase = (t * freq) % 1.0
                val = 1.0 if phase < 0.5 else -1.0
                env = max(0, 1.0 - env_t * 0.2)
                all_samples.append(max(-32768, min(32767,
                                  int(val * env * 0.22 * 32767))))

    write_wav("fanfare.wav", all_samples, sr)


# =============================================================================
# Main
# =============================================================================

def main():
    print("Generating Super Mario assets (from NES reference sprites)...")
    print()

    print("[1/7] Tileset...")
    generate_tileset()

    print("[2/7] Player spritesheet...")
    generate_player()

    print("[3/7] Goomba spritesheet...")
    generate_goomba()

    print("[4/7] Coin spritesheet...")
    generate_coin()

    print("[5/9] Block sprites...")
    generate_block_sprites()

    print("[6/9] Koopa spritesheet...")
    generate_koopa()

    print("[7/9] Jump sound...")
    generate_jump_sound()

    print("[8/9] Coin sound...")
    generate_coin_sound()

    print("[9/10] Overworld theme...")
    generate_overworld_theme()

    print("[10/11] Powerup sound...")
    generate_powerup_sound()

    print("[11/11] Fanfare sound...")
    generate_fanfare()

    print()
    print("All assets generated in:", OUTPUT_DIR)


if __name__ == '__main__':
    main()
