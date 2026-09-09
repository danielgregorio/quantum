#!/usr/bin/env python3
"""Backup/Restore protected Godot files before/after codegen.

Usage:
    python projects/mario/tools/backup_restore.py backup
    python projects/mario/tools/backup_restore.py restore
    python projects/mario/tools/backup_restore.py status

This script protects manually-tuned files from being overwritten by the
Quantum codegen. Run 'backup' BEFORE codegen, then 'restore' AFTER.
"""
import sys
import os
import shutil

GODOT_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "godot"))
BACKUP_DIR = os.path.join(GODOT_DIR, "_codegen_backup")

# Files that must be protected from codegen overwrite
PROTECTED_FILES = [
    "main.tscn",
    "scripts/scene_main.gd",
    "scripts/player_controller.gd",
    "scripts/prefab_rex.gd",
    "scripts/camera_follow.gd",
    "scripts/quantum_bridge.gd",
    "scripts/quantum_event_bus.gd",
    "scripts/tilemap_loader.gd",
    "scripts/prefab_checkpoint.gd",
    "scripts/prefab_coin.gd",
    "scripts/prefab_qblock.gd",
    "scripts/prefab_rotating_block.gd",
    "scripts/prefab_yoshi_coin.gd",
    "scripts/game_over_screen.gd",
    "collision_tileset.tres",
    "tile_map.json",
    "prefabs/checkpoint.tscn",
    "prefabs/coin.tscn",
    "prefabs/mushroom.tscn",
    "prefabs/qblock.tscn",
    "prefabs/rex.tscn",
    "prefabs/rotating_block.tscn",
    "prefabs/yoshi_coin.tscn",
    "scripts/prefab_banzai_bill.gd",
    "scripts/prefab_flying_qblock.gd",
    "scripts/prefab_piranha_plant.gd",
    "prefabs/banzai_bill.tscn",
    "prefabs/flying_qblock.tscn",
    "prefabs/piranha_plant.tscn",
]


def backup():
    """Backup all protected files before codegen."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    count = 0
    for rel_path in PROTECTED_FILES:
        src = os.path.join(GODOT_DIR, rel_path)
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    print(f"Backed up {count}/{len(PROTECTED_FILES)} protected files to {BACKUP_DIR}")
    return count


def restore():
    """Restore all protected files after codegen."""
    if not os.path.exists(BACKUP_DIR):
        print("ERROR: No backup found! Run 'backup' first.")
        sys.exit(1)
    count = 0
    for rel_path in PROTECTED_FILES:
        src = os.path.join(BACKUP_DIR, rel_path)
        if os.path.exists(src):
            dst = os.path.join(GODOT_DIR, rel_path)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            count += 1
    print(f"Restored {count} protected files from backup")
    # Clean up backup dir
    shutil.rmtree(BACKUP_DIR)
    print("Backup directory cleaned up")
    return count


def status():
    """Show status of protected files and backups."""
    has_backup = os.path.exists(BACKUP_DIR)
    print(f"Backup exists: {'YES' if has_backup else 'NO'}")
    print(f"\nProtected files ({len(PROTECTED_FILES)}):")
    for rel_path in PROTECTED_FILES:
        src = os.path.join(GODOT_DIR, rel_path)
        exists = "OK" if os.path.exists(src) else "MISSING"
        backed_up = ""
        if has_backup:
            bak = os.path.join(BACKUP_DIR, rel_path)
            backed_up = " [backed up]" if os.path.exists(bak) else " [NOT backed up]"
        print(f"  {exists:7s} {rel_path}{backed_up}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "backup":
        backup()
    elif cmd == "restore":
        restore()
    elif cmd == "status":
        status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)
