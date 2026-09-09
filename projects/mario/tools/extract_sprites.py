#!/usr/bin/env python3
"""
SMW Sprite Sheet Extractor
Extracts individual sprites from 10 reference sprite sheets.

Usage:
    python projects/mario/tools/extract_sprites.py [--sheet N] [--verify]

Options:
    --sheet N    Extract only sheet N (1-10), default: all
    --verify     Show dimensions of extracted sprites without writing
    --list       List all extraction targets
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import numpy as np


# ─── Directories ────────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).parent.parent / "assets"
SPRITES_DIR = ASSETS_DIR / "sprites"
REFERENCE_DIR = ASSETS_DIR / "reference"
OUTPUT_DIR = SPRITES_DIR  # extracted sprites go alongside existing ones


# ─── Key Colors (background colors to make transparent) ─────────────────
KEY_BLUE    = (0, 100, 250)     # #0064FA  — foreground-tiles-animated
KEY_GREEN   = (0, 158, 0)       # #009E00  — banzai, piranha, rex, objects
KEY_CYAN    = (1, 162, 215)     # #01A2D7  — charging-chucks
KEY_OW_BLUE = (64, 136, 248)    # #4088F8  — overworld
KEY_OW_GRN  = (10, 104, 32)     # #0A6820  — overworld-sprites
KEY_MAGENTA = (255, 0, 255)     # #FF00FF  — magenta transparency (some sheets)


# ─── Utility Functions ──────────────────────────────────────────────────

def load_sheet(name: str) -> Image.Image:
    """Load a sprite sheet from SPRITES_DIR, convert to RGBA."""
    path = SPRITES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Sheet not found: {path}")
    img = Image.open(path).convert("RGBA")
    return img


def remove_key_color(img: Image.Image, key_color: Tuple[int, int, int],
                     tolerance: int = 15) -> Image.Image:
    """Convert key_color pixels to transparent."""
    arr = np.array(img)
    r, g, b = key_color
    mask = (
        (np.abs(arr[:, :, 0].astype(int) - r) <= tolerance) &
        (np.abs(arr[:, :, 1].astype(int) - g) <= tolerance) &
        (np.abs(arr[:, :, 2].astype(int) - b) <= tolerance)
    )
    arr[mask] = [0, 0, 0, 0]
    return Image.fromarray(arr)


def remove_multi_key(img: Image.Image,
                     key_colors: List[Tuple[int, int, int]],
                     tolerance: int = 15) -> Image.Image:
    """Remove multiple key colors."""
    for kc in key_colors:
        img = remove_key_color(img, kc, tolerance)
    return img


def auto_trim(img: Image.Image) -> Image.Image:
    """Remove fully transparent borders."""
    arr = np.array(img)
    if arr.shape[2] < 4:
        return img
    alpha = arr[:, :, 3]
    rows = np.any(alpha > 0, axis=1)
    cols = np.any(alpha > 0, axis=0)
    if not rows.any() or not cols.any():
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    return img.crop((int(cmin), int(rmin), int(cmax) + 1, int(rmax) + 1))


def extract_region(sheet: Image.Image, bbox: Tuple[int, int, int, int],
                   key_color: Optional[Tuple[int, int, int]] = None,
                   tolerance: int = 15,
                   trim: bool = True) -> Image.Image:
    """Crop region from sheet, optionally remove key color and trim."""
    x1, y1, x2, y2 = bbox
    region = sheet.crop((x1, y1, x2, y2))
    if key_color:
        region = remove_key_color(region, key_color, tolerance)
    if trim:
        region = auto_trim(region)
    return region


def find_frame_columns(img: Image.Image, min_gap: int = 1) -> List[Tuple[int, int]]:
    """Find individual frame boundaries by detecting transparent column gaps.
    Returns list of (x_start, x_end) for each frame."""
    arr = np.array(img)
    if arr.shape[2] < 4:
        return [(0, img.width)]
    alpha = arr[:, :, 3]
    col_has_content = np.any(alpha > 0, axis=0)

    frames = []
    in_frame = False
    start = 0
    for x in range(len(col_has_content)):
        if col_has_content[x] and not in_frame:
            start = x
            in_frame = True
        elif not col_has_content[x] and in_frame:
            frames.append((start, x))
            in_frame = False
    if in_frame:
        frames.append((start, len(col_has_content)))

    return frames


def find_frame_rows(img: Image.Image) -> List[Tuple[int, int]]:
    """Find row boundaries by detecting transparent row gaps."""
    arr = np.array(img)
    if arr.shape[2] < 4:
        return [(0, img.height)]
    alpha = arr[:, :, 3]
    row_has_content = np.any(alpha > 0, axis=1)

    frames = []
    in_frame = False
    start = 0
    for y in range(len(row_has_content)):
        if row_has_content[y] and not in_frame:
            start = y
            in_frame = True
        elif not row_has_content[y] and in_frame:
            frames.append((start, y))
            in_frame = False
    if in_frame:
        frames.append((start, len(row_has_content)))

    return frames


def extract_frames_grid(img: Image.Image, frame_w: int, frame_h: int,
                        count: Optional[int] = None) -> List[Image.Image]:
    """Extract frames from a regular grid."""
    frames = []
    cols = img.width // frame_w
    rows = img.height // frame_h
    n = 0
    for r in range(rows):
        for c in range(cols):
            if count and n >= count:
                break
            frame = img.crop((c * frame_w, r * frame_h,
                            (c + 1) * frame_w, (r + 1) * frame_h))
            # Skip empty frames
            arr = np.array(frame)
            if arr.shape[2] >= 4 and np.any(arr[:, :, 3] > 0):
                frames.append(frame)
            n += 1
    return frames


def make_strip(frames: List[Image.Image],
               frame_w: Optional[int] = None,
               frame_h: Optional[int] = None) -> Image.Image:
    """Combine frames into a horizontal strip."""
    if not frames:
        raise ValueError("No frames to combine")
    if frame_w is None:
        frame_w = max(f.width for f in frames)
    if frame_h is None:
        frame_h = max(f.height for f in frames)

    strip = Image.new("RGBA", (frame_w * len(frames), frame_h), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        # Center each frame in its cell
        dx = (frame_w - frame.width) // 2
        dy = (frame_h - frame.height) // 2
        strip.paste(frame, (i * frame_w + dx, dy))
    return strip


def scale_nearest(img: Image.Image, factor: int) -> Image.Image:
    """Scale image using nearest-neighbor interpolation."""
    return img.resize((img.width * factor, img.height * factor),
                     Image.Resampling.NEAREST)


def save_sprite(img: Image.Image, name: str, verify: bool = False):
    """Save sprite to OUTPUT_DIR."""
    path = OUTPUT_DIR / name
    if verify:
        print(f"  [VERIFY] {name}: {img.width}x{img.height}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path))
        print(f"  [SAVED] {name}: {img.width}x{img.height}")


# ─── Sheet 1: foreground-tiles-animated.png ─────────────────────────────

def _extract_frames_dual_bg(sheet, bbox, key_colors, min_w=6, min_h=6,
                             frame_w=None, frame_h=None):
    """Extract frames from a region that uses alternating blue/magenta backgrounds.
    Removes both key colors, finds frame columns, filters by size."""
    region = sheet.crop(bbox)
    for kc in key_colors:
        region = remove_key_color(region, kc, tolerance=18)
    frames_cols = find_frame_columns(region)
    frames = []
    for xs, xe in frames_cols:
        f = region.crop((xs, 0, xe, region.height))
        f = auto_trim(f)
        if f.width >= min_w and f.height >= min_h:
            frames.append(f)
    return frames


def extract_sheet1(verify=False):
    """Foreground tiles: coins, yoshi coin, qblock, rotating block, etc."""
    print("\n=== Sheet 1: foreground-tiles-animated.png ===")
    sheet = load_sheet("foreground-tiles-animated.png")
    kc_both = [KEY_BLUE, KEY_MAGENTA]

    # === LEFT COLUMN (x=0..80) ===
    # Verified coordinates from visual inspection:

    # Berries — y=24-88, 3 color rows (red y=24, pink y=48, green y=72)
    # Each row has 3 frames of 8x8 on alternating blue/green/magenta bg
    for i, (y_start, name) in enumerate([
        (24, "berry_red"), (48, "berry_pink"), (72, "berry_green")
    ]):
        frames = _extract_frames_dual_bg(
            sheet, (0, y_start, 72, y_start + 16),
            [KEY_BLUE, KEY_MAGENTA, KEY_GREEN], min_w=4, min_h=4)
        if frames:
            strip = make_strip(frames, 8, 8)
            save_sprite(strip, f"{name}.png", verify)

    # All berries combined strip
    all_berry_frames = _extract_frames_dual_bg(
        sheet, (0, 24, 72, 88),
        [KEY_BLUE, KEY_MAGENTA, KEY_GREEN], min_w=4, min_h=4)
    if all_berry_frames:
        strip = make_strip(all_berry_frames, 8, 8)
        save_sprite(strip, "berries.png", verify)

    # Yoshi Coin — y=112-136, 16x16 frames on blue/magenta bg
    frames = _extract_frames_dual_bg(
        sheet, (0, 112, 72, 144), kc_both, min_w=10, min_h=12)
    if frames:
        # Take unique frames (skip palette duplicates — every other frame)
        unique = frames[::2] if len(frames) > 4 else frames
        strip = make_strip(unique, 16, 24)
        save_sprite(strip, "yoshi_coin.png", verify)

    # Coin (loop) — y=184-200, small 8x8 coins, scale to 16x16
    frames = _extract_frames_dual_bg(
        sheet, (0, 184, 72, 200), kc_both, min_w=2, min_h=4)
    if frames:
        unique = frames[::2] if len(frames) > 4 else frames
        scaled = [scale_nearest(f, 2) for f in unique]
        strip = make_strip(scaled, 16, 16)
        save_sprite(strip, "coin_animated.png", verify)

    # Blue Coin — y=224-240, silver/blue coins, 8x8 → 16x16
    frames = _extract_frames_dual_bg(
        sheet, (0, 224, 72, 240), kc_both, min_w=2, min_h=4)
    if frames:
        unique = frames[::2] if len(frames) > 4 else frames
        scaled = [scale_nearest(f, 2) for f in unique]
        strip = make_strip(scaled, 16, 16)
        save_sprite(strip, "blue_coin.png", verify)

    # ?-Block (loop) — y=264-280, 16x16 frames
    frames = _extract_frames_dual_bg(
        sheet, (0, 264, 80, 280), kc_both, min_w=10, min_h=10)
    if frames:
        unique = frames[::2] if len(frames) > 4 else frames
        strip = make_strip(unique, 16, 16)
        save_sprite(strip, "qblock_animated.png", verify)

    # Rotating Block (loop) — y=304-320, 16x16 frames
    frames = _extract_frames_dual_bg(
        sheet, (0, 304, 80, 320), kc_both, min_w=10, min_h=10)
    if frames:
        unique = frames[::2] if len(frames) > 4 else frames
        strip = make_strip(unique, 16, 16)
        save_sprite(strip, "rotating_block.png", verify)

    # === RIGHT SIDE ===

    # Interim Goal — x=128, y=0-144 (tall section with goal tape frames)
    region = extract_region(sheet, (128, 0, 260, 160), KEY_BLUE)
    if region.width > 1:
        save_sprite(region, "interim_goal.png", verify)

    # Escalator — x=184, y=192-232
    frames = _extract_frames_dual_bg(
        sheet, (184, 208, 280, 240), kc_both, min_w=10, min_h=10)
    if frames:
        strip = make_strip(frames)
        save_sprite(strip, "escalator.png", verify)

    # Note Block — x=184, y=264-280 (16x16 face blocks)
    frames = _extract_frames_dual_bg(
        sheet, (184, 264, 280, 280), kc_both, min_w=10, min_h=10)
    if frames:
        strip = make_strip(frames, 16, 16)
        save_sprite(strip, "note_block.png", verify)

    # Muncher — x=184, y=296-312
    frames = _extract_frames_dual_bg(
        sheet, (184, 296, 280, 312), kc_both, min_w=6, min_h=6)
    if frames:
        strip = make_strip(frames)
        save_sprite(strip, "muncher.png", verify)

    # Athletic Engine — top-right x=354, y=0-32
    region = extract_region(sheet, (354, 0, 512, 40), KEY_BLUE, trim=False)
    region = remove_key_color(region, KEY_BLUE)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "athletic_engine.png", verify)

    # Water Waves — right side x=340, y=48-88
    region = extract_region(sheet, (340, 48, 490, 88), KEY_BLUE, trim=False)
    region = remove_key_color(region, KEY_BLUE)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "water_waves.png", verify)

    # Seaweed — right side
    region = extract_region(sheet, (390, 88, 480, 136), KEY_BLUE, trim=False)
    region = remove_key_color(region, KEY_BLUE)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "seaweed.png", verify)

    # Conveyor Rope — right side x=340, y=144-200
    region = extract_region(sheet, (340, 148, 490, 200), KEY_BLUE, trim=False)
    region = remove_key_color(region, KEY_BLUE)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "conveyor_rope.png", verify)


# ─── Sheet 2: banzai.png ───────────────────────────────────────────────

def extract_sheet2(verify=False):
    """Banzai Bill, Bullet Bill, Thwomp, Grinder, etc."""
    print("\n=== Sheet 2: banzai.png ===")
    sheet = load_sheet("banzai.png")
    kc = KEY_GREEN

    # Green Bubble (top-left) — large ~48x48 frames
    region = extract_region(sheet, (0, 8, 200, 88), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "green_bubble.png", verify)

    # Banzai Bill — top right ~x=320, y=0, large sprite ~64x64
    region = extract_region(sheet, (288, 0, 488, 88), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        # Take the largest frame(s) — Banzai Bill is the big one
        banzai_frames = [f for f in frames if f.width > 30]
        if banzai_frames:
            strip = make_strip(banzai_frames)
            save_sprite(strip, "banzai_bill.png", verify)
        # Bullet Bill is the small one
        bullet_frames = [f for f in frames if f.width <= 30 and f.width >= 8]
        if bullet_frames:
            strip = make_strip(bullet_frames, 16, 16)
            save_sprite(strip, "bullet_bill.png", verify)

    # Grinder — ~y=88, x=0
    region = extract_region(sheet, (0, 88, 120, 160), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "grinder.png", verify)

    # Floating Mine — ~y=88, x=128
    region = extract_region(sheet, (120, 88, 240, 160), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "floating_mine.png", verify)

    # Ball'n'Chain — ~y=88, x=280
    region = extract_region(sheet, (256, 88, 400, 160), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "ball_n_chain.png", verify)

    # Thwomp — ~y=160, x=0
    region = extract_region(sheet, (0, 152, 120, 240), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "thwomp.png", verify)

    # Thwimp — ~y=160, x=128
    region = extract_region(sheet, (112, 152, 220, 220), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "thwimp.png", verify)

    # Wandering Pit — ~y=160, x=224
    region = extract_region(sheet, (216, 152, 340, 220), kc)
    save_sprite(region, "wandering_pit.png", verify)

    # Torpedo Ted — ~y=224, x=0
    region = extract_region(sheet, (0, 220, 160, 280), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "torpedo_ted.png", verify)

    # Gray Bowser Statue — ~y=224, x=168
    region = extract_region(sheet, (160, 224, 296, 320), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "bowser_statue_gray.png", verify)

    # Gold Bowser Statue — ~y=224, x=330
    region = extract_region(sheet, (296, 224, 440, 320), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "bowser_statue_gold.png", verify)

    # Enemy Cast Roll row — ~y=328
    region = extract_region(sheet, (0, 320, 100, 368), kc, trim=False)
    region = remove_key_color(region, kc)
    region = auto_trim(region)
    if region.width > 1 and region.height > 1:
        save_sprite(region, "propeller_sfx.png", verify)

    # Loose Spike — ~y=336, x=120
    region = extract_region(sheet, (112, 336, 200, 384), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "loose_spike.png", verify)

    # Bullet Bill (regular) — ~y=336, x=224
    region = extract_region(sheet, (216, 328, 320, 372), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        if not any(f.width > 4 for f in frames):
            pass  # too small, skip
        else:
            strip = make_strip(frames, 16, 16)
            save_sprite(strip, "bullet_bill.png", verify)

    # Pidgit Bill — ~y=336, x=360
    region = extract_region(sheet, (344, 328, 440, 376), kc, trim=False)
    region = remove_key_color(region, kc)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "pidgit_bill.png", verify)

    # Wooden Spear — ~y=384, x=0
    region = extract_region(sheet, (0, 376, 80, 440), kc, trim=False)
    region = remove_key_color(region, kc)
    region = auto_trim(region)
    save_sprite(region, "wooden_spear.png", verify)

    # Chainsaw — ~y=384, x=96
    region = extract_region(sheet, (88, 376, 200, 440), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "chainsaw.png", verify)

    # Big Steely — bottom, ~y=450, x=0
    region = extract_region(sheet, (0, 440, 200, 504), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        strip = make_strip(frames)
        save_sprite(strip, "big_steely.png", verify)


# ─── Sheet 3: piranha_plants.png ────────────────────────────────────────

def extract_sheet3(verify=False):
    """Piranha plants, Jumping Piranha, Volcano Lotus, Pokey, Fireballs."""
    print("\n=== Sheet 3: piranha_plants.png ===")
    sheet = load_sheet("piranha_plants.png")
    kc = KEY_GREEN

    # The sheet is in palette mode (P), convert to RGBA
    sheet = sheet.convert("RGBA")

    # Piranha Plant — top area, multiple variants
    # Standard green piranha — ~y=0, x=0, chomping animation
    region = extract_region(sheet, (0, 0, 140, 70), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        # Filter to actual piranha frames (should be ~16x24 each)
        good_frames = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good_frames:
            strip = make_strip(good_frames)
            save_sprite(strip, "piranha_plant.png", verify)

    # Red piranha
    region = extract_region(sheet, (0, 64, 140, 130), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good_frames = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good_frames:
            strip = make_strip(good_frames)
            save_sprite(strip, "piranha_plant_red.png", verify)

    # Jumping Piranha — further down
    region = extract_region(sheet, (0, 128, 200, 200), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good_frames = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good_frames:
            strip = make_strip(good_frames)
            save_sprite(strip, "jumping_piranha.png", verify)

    # Volcano Lotus — middle area
    region = extract_region(sheet, (0, 192, 200, 272), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good_frames = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good_frames:
            strip = make_strip(good_frames)
            save_sprite(strip, "volcano_lotus.png", verify)

    # Fireball — small projectile sprites
    region = extract_region(sheet, (200, 0, 340, 80), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good_frames = [f for f in frames if f.width >= 4 and f.height >= 4]
        if good_frames:
            strip = make_strip(good_frames)
            save_sprite(strip, "fireball.png", verify)

    # Pokey — right side cactus
    region = extract_region(sheet, (300, 0, 424, 200), kc, trim=False)
    region = remove_key_color(region, kc)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "pokey.png", verify)


# ─── Sheet 4: backgrounds.png ──────────────────────────────────────────

def extract_sheet4(verify=False):
    """Static backgrounds from all biomes.

    The sheet is 2070x3992. Backgrounds are arranged in columns (~512px wide)
    with multiple palette variants per row. Each bg is ~512x256.
    We extract the FIRST (leftmost) palette variant of each unique biome.
    """
    print("\n=== Sheet 4: backgrounds.png ===")
    sheet = load_sheet("backgrounds.png")
    W = 512  # width of one background panel
    H = 256  # height including label space

    # Layout from visual analysis (overview at 1/4 scale):
    # Row 0 (y=0-500):    Outdoor sky with clouds + hills (Yoshi's Island)
    # Row 1 (y=500-900):  Mountains (green → dark → green variants)
    # Row 2 (y=900-1300): More mountain variants (green, dark, black, lime)
    # Row 3 (y=1300-1700): Mountain/hills more variants
    # Row 4 (y=1700-2100): Beige/dark/blue mountain variants
    # Row 5 (y=2100-2500): Green mtns, sand, city/castle, snow
    # Row 6 (y=2500-2900): Castle/fortress interior
    # Row 7 (y=2900-3300): Ghost house / indoor backgrounds
    # Row 8 (y=3300-3700): Special (underwater/lava/etc)
    # Row 9 (y=3700-3992): Credits/misc

    # Extract first panel from each row
    bg_defs = [
        # (name, x, y, w, h) — crop region
        ("bg_yoshi_island.png",       0, 96, W, 224),    # sky+hills (skip header)
        ("bg_mountains_green.png",    0, 544, W, 224),   # green mountains
        ("bg_mountains_dark.png",     512, 544, W, 224), # dark mountains
        ("bg_mountains_night.png",    0, 1024, W, 224),  # night mountains
        ("bg_forest.png",             1024, 544, W, 224),# forest/lime mountains
        ("bg_hills_beige.png",        0, 1744, W, 224),  # beige hills
        ("bg_snow.png",               1536, 2256, W, 224), # snow
        ("bg_castle.png",             0, 2576, W, 224),  # castle interior
        ("bg_ghost_house.png",        0, 2960, W, 224),  # ghost house
        ("bg_underwater.png",         0, 3344, W, 224),  # underwater/special
    ]

    for name, x, y, w, h in bg_defs:
        try:
            if y + h > sheet.height or x + w > sheet.width:
                print(f"  [SKIP] {name}: out of bounds ({x},{y},{w},{h})")
                continue
            region = sheet.crop((x, y, x + w, y + h))
            arr = np.array(region)
            if arr.std() > 3:
                save_sprite(region, name, verify)
            else:
                print(f"  [SKIP] {name}: low variance ({arr.std():.1f})")
        except Exception as e:
            print(f"  [SKIP] {name}: {e}")


# ─── Sheet 5: backgrounds-animated.png ──────────────────────────────────

def extract_sheet5(verify=False):
    """Animated backgrounds (water, lava, etc.)."""
    print("\n=== Sheet 5: backgrounds-animated.png ===")
    sheet = load_sheet("backgrounds-animated.png")

    # These are large animated sections. Extract key ones.
    bg_anim_defs = [
        ("bg_anim_water.png",   (0, 0, 256, 224)),
        ("bg_anim_lava.png",    (0, 224, 256, 448)),
    ]

    for name, bbox in bg_anim_defs:
        try:
            region = sheet.crop(bbox)
            arr = np.array(region)
            if arr.std() > 5:
                save_sprite(region, name, verify)
        except Exception as e:
            print(f"  [SKIP] {name}: {e}")


# ─── Sheet 6: rex-blarg-dino.png ───────────────────────────────────────

def extract_sheet6(verify=False):
    """Rex, Blargg, Dino-Rhino, Dino-Torch."""
    print("\n=== Sheet 6: rex-blarg-dino.png ===")
    sheet = load_sheet("rex-blarg-dino.png")
    kc = KEY_GREEN

    # Rex — top-left, ~y=0..48, small sprites with palette indicators
    # Rex walk frames — the actual sprites start after the palette swatches
    # Looking at the image: Rex is at top-left, about 2-4 frames around 16x32
    region = extract_region(sheet, (0, 0, 100, 48), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        # Rex walk: take the walking frames (filtering out palette swatches)
        walk_frames = [f for f in frames if f.width >= 10 and f.height >= 16]
        if walk_frames:
            strip = make_strip(walk_frames)
            save_sprite(strip, "rex_walk.png", verify)
        # Rex squished: shorter frames
        squish_frames = [f for f in frames if f.width >= 10 and f.height < 16 and f.height >= 8]
        if squish_frames:
            strip = make_strip(squish_frames)
            save_sprite(strip, "rex_squished.png", verify)

    # Blargg — middle area, large mouth/body sprites
    region = extract_region(sheet, (88, 0, 280, 72), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 16 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "blargg.png", verify)

    # Dino-Rhino — top-right, ~x=360, large 4-legged dino
    region = extract_region(sheet, (340, 0, 470, 56), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 16 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "dino_rhino.png", verify)

    # Dino-Torch — bottom area (smaller dino with fire)
    region = extract_region(sheet, (0, 72, 260, 160), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8 and f.height >= 12]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "dino_torch.png", verify)

    # Fire breath animations — bottom rows
    region = extract_region(sheet, (0, 144, 400, 230), kc, trim=False)
    region = remove_key_color(region, kc)
    # Find rows of frames
    frame_rows = find_frame_rows(region)
    for i, (ys, ye) in enumerate(frame_rows[:2]):
        row = region.crop((0, ys, region.width, ye))
        cols = find_frame_columns(row)
        if cols:
            frames = [auto_trim(row.crop((xs, 0, xe, row.height))) for xs, xe in cols]
            good = [f for f in frames if f.width >= 8]
            if good:
                strip = make_strip(good)
                save_sprite(strip, f"dino_fire_{i}.png", verify)


# ─── Sheet 7: charging-chucks.png ──────────────────────────────────────

def extract_sheet7(verify=False):
    """Charging Chucks variants and projectiles."""
    print("\n=== Sheet 7: charging-chucks.png ===")
    sheet = load_sheet("charging-chucks.png")
    kc = KEY_CYAN

    # Chucks are arranged in labeled rows
    chuck_defs = [
        # (name, y_start, y_end, description)
        ("chuck_passin.png",     8, 56,    "Passin' Chuck"),
        ("chuck_clappin.png",    8, 56,    "Clappin' Chuck - same row"),
        ("chuck_splittin.png",   8, 56,    "Splittin' Chuck - same row"),
        ("chuck_whistlin.png",   64, 128,  "Whistlin' Chuck"),
        ("chuck_lookout.png",    136, 208, "Lookout Chuck"),
        ("chuck_diggin.png",     216, 304, "Diggin' Chuck"),
        ("chuck_confused.png",   312, 384, "Confused Chuck"),
    ]

    # Extract each chuck type from its labeled section
    # Row 1 (y=8-56): Passin', Clappin', Splittin' side by side
    # Passin' Chuck — left portion
    region = extract_region(sheet, (0, 16, 80, 56), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_passin.png", verify)

    # Clappin' Chuck — middle
    region = extract_region(sheet, (96, 16, 224, 56), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_clappin.png", verify)

    # Splittin'/Bouncin' Chuck — right portion of first row
    region = extract_region(sheet, (224, 16, 400, 56), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_splittin.png", verify)

    # Whistlin' Chuck
    region = extract_region(sheet, (0, 64, 300, 128), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_whistlin.png", verify)

    # Lookout Chuck
    region = extract_region(sheet, (0, 136, 300, 208), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_lookout.png", verify)

    # Diggin' Chuck
    region = extract_region(sheet, (0, 216, 300, 312), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_diggin.png", verify)

    # Confused Chuck
    region = extract_region(sheet, (0, 312, 300, 384), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_confused.png", verify)

    # Defeat animations (shared) — ~y=384+
    region = extract_region(sheet, (0, 384, 350, 500), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_defeated.png", verify)

    # Projectiles — bottom area
    region = extract_region(sheet, (200, 710, 420, 760), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 6]
        if len(good) >= 2:
            # First is football, second is baseball
            save_sprite(good[0], "projectile_football.png", verify)
            if len(good) > 1:
                save_sprite(good[1], "projectile_baseball.png", verify)
        elif good:
            save_sprite(good[0], "projectile_football.png", verify)

    # Ingame sprites — bottom rows (~y=620+)
    region = extract_region(sheet, (0, 616, 300, 700), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "chuck_ingame.png", verify)


# ─── Sheet 8: overworld.png ────────────────────────────────────────────

def extract_sheet8(verify=False):
    """World maps from overworld sheet."""
    print("\n=== Sheet 8: overworld.png ===")
    sheet = load_sheet("overworld.png")

    # The overworld sheet stacks world maps vertically
    # Each map is approximately 256 pixels wide, varying heights
    # Extract sections — these are larger composite maps
    w = sheet.width

    # Divide into major sections (approximate, based on 1025x2235 size)
    # Each world map is roughly 200-300px tall
    map_defs = [
        ("world1_map.png",   (0, 0, w, 250)),
        ("world2_map.png",   (0, 250, w, 500)),
        ("world3_map.png",   (0, 500, w, 750)),
        ("world4_map.png",   (0, 750, w, 1000)),
        ("world5_map.png",   (0, 1000, w, 1250)),
        ("world6_map.png",   (0, 1250, w, 1500)),
        ("world7_map.png",   (0, 1500, w, 1750)),
        ("star_road_map.png", (0, 1750, w, 2000)),
        ("special_map.png",  (0, 2000, w, 2235)),
    ]

    for name, bbox in map_defs:
        try:
            region = sheet.crop(bbox)
            arr = np.array(region)
            if arr.std() > 3:
                save_sprite(region, name, verify)
        except Exception as e:
            print(f"  [SKIP] {name}: {e}")


# ─── Sheet 9: overworld-sprites.png ────────────────────────────────────

def extract_sheet9(verify=False):
    """Mario/Luigi map sprites, Yoshi variants, signs."""
    print("\n=== Sheet 9: overworld-sprites.png ===")
    sheet = load_sheet("overworld-sprites.png")
    kc = KEY_OW_GRN

    # Mario map sprites — top rows (moving down, up, sideways, climbing)
    # Each direction has a small animation strip
    region = extract_region(sheet, (0, 8, 80, 192), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good:
            strip = make_strip(good, 16, 24)
            save_sprite(strip, "mario_map.png", verify)

    # Luigi map sprites — second column
    region = extract_region(sheet, (72, 8, 152, 192), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good:
            strip = make_strip(good, 16, 24)
            save_sprite(strip, "luigi_map.png", verify)

    # Castle/Bowser signs — middle area
    region = extract_region(sheet, (208, 136, 400, 216), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "castle_sign.png", verify)

    # Ghost House Boo
    region = extract_region(sheet, (0, 208, 100, 248), kc, trim=False)
    region = remove_key_color(region, kc)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "ghost_house_boo.png", verify)

    # Cheep-Cheep and other enemies
    region = extract_region(sheet, (0, 268, 500, 308), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "map_enemies.png", verify)

    # Mario/Luigi on Yoshi — bottom large section
    region = extract_region(sheet, (0, 344, 400, 440), kc, trim=False)
    region = remove_key_color(region, kc)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 16]
        if good:
            # Group by approximate x-position — different Yoshi colors
            strip = make_strip(good)
            save_sprite(strip, "mario_yoshi_map.png", verify)


# ─── Sheet 10: objects-animated.png ─────────────────────────────────────

def extract_sheet10(verify=False):
    """P-Switch, Starman, Fire Flower, various animated objects."""
    print("\n=== Sheet 10: objects-animated.png ===")
    sheet = load_sheet("objects-animated.png")
    kc = KEY_GREEN

    # Also remove magenta (used for some transparency in this sheet)
    # Disco Light Palettes — top, very large area, skip for now

    # Fire Flower — ~y=264, x=224
    region = extract_region(sheet, (216, 260, 350, 310), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good:
            strip = make_strip(good, 16, 16)
            save_sprite(strip, "fire_flower.png", verify)

    # Silver Coin — ~y=160, x=160
    region = extract_region(sheet, (152, 148, 300, 180), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 6]
        if good:
            strip = make_strip(good, 16, 16)
            save_sprite(strip, "silver_coin.png", verify)

    # Grab Block (Blinking) — ~y=200
    region = extract_region(sheet, (0, 192, 200, 248), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12 and f.height >= 12]
        if good:
            strip = make_strip(good, 16, 16)
            save_sprite(strip, "grab_block.png", verify)

    # Skull Raft — ~y=296
    region = extract_region(sheet, (0, 290, 200, 330), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "skull_raft.png", verify)

    # Trampoline — ~y=328
    region = extract_region(sheet, (152, 320, 300, 366), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "trampoline.png", verify)

    # Bubble — ~y=384
    region = extract_region(sheet, (0, 378, 160, 440), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "bubble.png", verify)

    # Starman — ~y=480
    region = extract_region(sheet, (0, 472, 160, 520), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8 and f.height >= 8]
        if good:
            strip = make_strip(good, 16, 16)
            save_sprite(strip, "starman.png", verify)

    # P-Switch (Blue) — ~y=504, x=360
    region = extract_region(sheet, (344, 488, 420, 530), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good, 16, 16)
            save_sprite(strip, "p_switch_blue.png", verify)

    # P-Switch (Gray) — ~y=528, x=360
    region = extract_region(sheet, (344, 530, 420, 568), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good, 16, 16)
            save_sprite(strip, "p_switch_gray.png", verify)

    # Yoshi Cloud — ~y=544, x=360
    region = extract_region(sheet, (344, 560, 536, 624), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 12]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "yoshi_cloud.png", verify)

    # Ghost House Entrance — ~y=640
    region = extract_region(sheet, (0, 632, 350, 700), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "ghost_house_entrance.png", verify)

    # Ghost House Exit — ~y=640, right side
    region = extract_region(sheet, (270, 632, 536, 700), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 16]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "ghost_house_exit.png", verify)

    # Spin Gate — bottom ~y=800
    region = extract_region(sheet, (0, 792, 400, 870), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "spin_gate.png", verify)

    # Beanstalk Heads — top-right ~y=48, x=376
    region = extract_region(sheet, (360, 40, 536, 88), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "beanstalk.png", verify)

    # Fireworks — ~y=88, x=376
    region = extract_region(sheet, (360, 80, 536, 136), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "fireworks.png", verify)

    # Winged Objects — right side
    region = extract_region(sheet, (370, 296, 536, 440), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "winged_objects.png", verify)

    # Count-Lift — ~y=576, x=0
    region = extract_region(sheet, (0, 568, 200, 630), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    frames_cols = find_frame_columns(region)
    if frames_cols:
        frames = [auto_trim(region.crop((xs, 0, xe, region.height))) for xs, xe in frames_cols]
        good = [f for f in frames if f.width >= 8]
        if good:
            strip = make_strip(good)
            save_sprite(strip, "count_lift.png", verify)

    # Disco Light — top section (palette variants)
    region = extract_region(sheet, (0, 0, 130, 136), kc, trim=False)
    region = remove_key_color(region, kc)
    region = remove_key_color(region, KEY_MAGENTA, tolerance=5)
    region = auto_trim(region)
    if region.width > 1:
        save_sprite(region, "disco_light.png", verify)


# ─── Main Dispatcher ────────────────────────────────────────────────────

EXTRACTORS = {
    1: extract_sheet1,
    2: extract_sheet2,
    3: extract_sheet3,
    4: extract_sheet4,
    5: extract_sheet5,
    6: extract_sheet6,
    7: extract_sheet7,
    8: extract_sheet8,
    9: extract_sheet9,
    10: extract_sheet10,
}

SHEET_NAMES = {
    1: "foreground-tiles-animated.png",
    2: "banzai.png",
    3: "piranha_plants.png",
    4: "backgrounds.png",
    5: "backgrounds-animated.png",
    6: "rex-blarg-dino.png",
    7: "charging-chucks.png",
    8: "overworld.png",
    9: "overworld-sprites.png",
    10: "objects-animated.png",
}


def main():
    parser = argparse.ArgumentParser(description="SMW Sprite Sheet Extractor")
    parser.add_argument("--sheet", type=int, help="Extract only sheet N (1-10)")
    parser.add_argument("--verify", action="store_true",
                       help="Show dimensions without writing files")
    parser.add_argument("--list", action="store_true",
                       help="List all extraction targets")
    args = parser.parse_args()

    if args.list:
        for n, name in sorted(SHEET_NAMES.items()):
            print(f"  Sheet {n:2d}: {name}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.sheet:
        if args.sheet not in EXTRACTORS:
            print(f"Error: sheet must be 1-10, got {args.sheet}")
            sys.exit(1)
        EXTRACTORS[args.sheet](verify=args.verify)
    else:
        for n in sorted(EXTRACTORS):
            try:
                EXTRACTORS[n](verify=args.verify)
            except Exception as e:
                print(f"  [ERROR] Sheet {n}: {e}")

    if not args.verify:
        print(f"\nDone! Sprites saved to: {OUTPUT_DIR}")
    else:
        print(f"\nVerification complete (no files written).")


if __name__ == "__main__":
    main()
