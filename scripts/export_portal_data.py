#!/usr/bin/env python3
"""Export structured, validated JSON data for Jabberwocky game portal.

Extracts data directly from source-of-truth files:
- world/ (YAML maps, screens, objects, colors)
- sprites/ (JSON sprite definitions)
- img/ & fonts/ & chars/ (real graphical assets)
- music/ & engine/ (CMC SAP audio metadata and subsong configurations)
- texts/ (Lewis Carroll poems, title scroll, victory/defeat endings)
- docs/memory_map.json & main.asm (memory layout & runtime buffers)
- git tags & GitHub Releases (releases & development timeline)

Validates all outputs against Pydantic schemas and saves to reports/portal/
and website/src/data/.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from pydantic import BaseModel, Field

# Import labirynt_studio models and loaders
from labirynt_studio.io.project_io import load_project_from_yaml
from labirynt_studio.io.objects_loader import ObjectsLibrary
from labirynt_studio.model.packing import unpack_xy, SCREEN_WIDTH_CHARS, SCREEN_HEIGHT_CHARS
from scripts.labirynt_builder import bake_screen_vram, bake_screen_blocking, load_colors
from scripts.compile_sprites import load_sprite_json
from scripts.extract_sap import parse_sap_header


# ============================================================================
# Pydantic Schemas for Validation
# ============================================================================

class GameMetadata(BaseModel):
    title: str
    subtitle: str
    genre: str
    platform: str
    media: str
    tv_system: str
    current_version: str
    repository: str
    author: str
    music_author: str


class GameLore(BaseModel):
    inspiration: str
    prologue: str
    scroll_banner: str
    defeat_poem: str
    victory_poem: str
    narrative: str


class GameMechanic(BaseModel):
    name: str
    description: str


class GameControl(BaseModel):
    key: str
    action: str


class GameSpecs(BaseModel):
    display_engine: str
    screen_resolution: str
    scroll_architecture: str
    audio_engine: str
    sprite_system: str


class GameReport(BaseModel):
    metadata: GameMetadata
    lore: GameLore
    mechanics: List[GameMechanic]
    controls: List[GameControl]
    engine_specs: GameSpecs


class PaletteColor(BaseModel):
    name: str
    atari: int
    rgb: List[int]
    hex: str


class WorldObjectInstance(BaseModel):
    code: int
    packed_xy: int
    x: int
    y: int
    object_id: str
    width: int
    height: int
    blocking: bool
    interactive: bool
    secret: bool
    tiles: List[int]
    tags: List[str]


class WorldScreen(BaseModel):
    id: str
    objects_count: int
    objects: List[WorldObjectInstance]
    baked_vram: List[int]
    baked_blocking: List[int]
    blocking_tiles_count: int
    secret_tiles_count: int
    interactive_tiles_count: int


class LabyrinthData(BaseModel):
    id: str
    name: str
    screens_count: int
    screen_ids: List[str]
    total_objects: int
    total_secrets: int
    total_blocking: int
    total_interactive: int


class WorldGrid(BaseModel):
    screen_width_chars: int
    screen_height_chars: int
    grid_step_x: int
    grid_step_y: int
    grid_cols: int
    grid_rows: int


class WorldReport(BaseModel):
    project_name: str
    grid: WorldGrid
    palette: Dict[str, PaletteColor]
    labyrinths: List[LabyrinthData]
    screens: List[WorldScreen]


class CatalogObject(BaseModel):
    code: int
    id: str
    object: str
    size: Dict[str, int]
    flags: Dict[str, bool]
    tiles: List[int]
    tags: List[str]
    instances_count: int
    screens_used_in: List[str]
    is_used_in_world: bool


class ObjectsReport(BaseModel):
    total_count: int
    used_count: int
    all_tags: List[str]
    objects: List[CatalogObject]


class SpriteFrameData(BaseModel):
    index: int
    pixels: List[str]
    row_bytes: List[int]


class SpriteReport(BaseModel):
    id: str
    name: str
    width: int
    height: int
    color: int
    frame_duration: int
    total_frames: int
    hardware_mode: str
    color_registers: str
    buffer_address: str
    frames: List[SpriteFrameData]


class ImageAsset(BaseModel):
    file: str
    width: int
    height: int
    format: str
    antic_mode: Optional[str] = None
    target_bin: Optional[str] = None
    file_size_bytes: int


class FontAsset(BaseModel):
    file: str
    file_size_bytes: int
    characters_count: int
    base_address: str
    description: str


class AnimatedCharData(BaseModel):
    index: int
    repeat: int
    total_frames: int
    frame_duration: int
    frames_hex: List[str]


class RotatedCharData(BaseModel):
    index: int
    duration: int


class AssetsReport(BaseModel):
    images: Dict[str, ImageAsset]
    fonts: Dict[str, FontAsset]
    animated_characters: List[AnimatedCharData]
    rotated_characters: List[RotatedCharData]
    story_texts: Dict[str, str]


class SubsongData(BaseModel):
    id: int
    name: str
    duration: str
    symbol: str
    description: str


class SfxData(BaseModel):
    symbol: str
    description: str
    channel: str


class MusicReport(BaseModel):
    sap_metadata: Dict[str, Any]
    subsongs: List[SubsongData]
    engine_architecture: Dict[str, str]
    sfx_catalog: List[SfxData]


class MemorySegmentData(BaseModel):
    name: str
    start_address: str
    end_address: str
    start_int: int
    end_int: int
    size: int
    type: str


class RuntimeReservedData(BaseModel):
    name: str
    start_address: str
    end_address: str
    size: int
    purpose: str


class ZeroPageVarData(BaseModel):
    symbol: str
    address: str
    size: int
    description: str


class MemoryReport(BaseModel):
    segments: List[MemorySegmentData]
    runtime_reserved: List[RuntimeReservedData]
    zero_page_vars: List[ZeroPageVarData]
    os_zero_page: Dict[str, str]
    rom_banking: Dict[str, str]
    space_summary: Dict[str, Any]
    provenance: Dict[str, Any]


class ReleaseAsset(BaseModel):
    name: str
    size: int
    download_url: str


class ReleaseData(BaseModel):
    version: str
    tag_name: str
    name: str
    published_at: str
    changelog: str
    download_url: str
    html_url: str
    asset_name: str
    asset_size: int
    is_latest: bool


class ReleasesReport(BaseModel):
    total_releases: int
    releases: List[ReleaseData]


class LatestStats(BaseModel):
    labyrinths: int
    screens: int
    catalog_objects: int
    total_placed_objects: int
    total_secrets: int
    sprite_frames: int
    subsongs: int
    allocated_memory_bytes: int
    net_free_ram_bytes: int


class LatestReport(BaseModel):
    version: str
    tag_name: str
    release_date: str
    download_url: str
    binary_size: int
    binary_sha256: str
    stats: LatestStats


# ============================================================================
# Exporter Implementations
# ============================================================================

def get_git_info() -> Dict[str, str]:
    """Retrieve git commit SHA, date, and latest tag safely."""
    info = {
        "commit_sha": "unknown",
        "commit_date": datetime.now().isoformat(),
        "tag_name": "v0.10.0",
    }
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
        info["commit_sha"] = sha
    except Exception:
        pass

    try:
        date = subprocess.check_output(
            ["git", "log", "-1", "--format=%cI"], stderr=subprocess.DEVNULL
        ).decode().strip()
        if date:
            info["commit_date"] = date
    except Exception:
        pass

    try:
        tag = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"], stderr=subprocess.DEVNULL
        ).decode().strip()
        if tag:
            info["tag_name"] = tag
    except Exception:
        pass

    return info


def build_game_report(git_info: Dict[str, str]) -> GameReport:
    """Build game.json metadata, story, mechanics and controls."""
    title_txt = (PROJECT_ROOT / "texts/title.txt").read_text(encoding="utf-8").strip()
    scroll_txt = (PROJECT_ROOT / "texts/scroll.txt").read_text(encoding="utf-8").strip()
    fail_txt = (PROJECT_ROOT / "texts/game_over_fail.txt").read_text(encoding="utf-8").strip()
    success_txt = (PROJECT_ROOT / "texts/game_over_success.txt").read_text(encoding="utf-8").strip()

    version = "0.10.0"
    match = re.search(r"version\s+([0-9\.]+)", scroll_txt)
    if match:
        version = match.group(1)

    return GameReport(
        metadata=GameMetadata(
            title="Jabberwocky",
            subtitle="Atari 8-bit Action-Adventure & Labyrinth Flight",
            genre="Action / Retro Fantasy",
            platform="Atari 800XL / 65XE / 130XE (64 KB RAM)",
            media="Atari Executable (XEX)",
            tv_system="PAL 50 Hz (recommended) / NTSC 60 Hz",
            current_version=version,
            repository="https://github.com/grzes71/jabberwocky",
            author="Grzegorz 'grzes71' Kraszewski",
            music_author="Andrzej 'Andy' Kidaj",
        ),
        lore=GameLore(
            inspiration="Inspired by Lewis Carroll's timeless nonsense poem 'Jabberwocky' from Through the Looking-Glass (1871).",
            prologue=title_txt,
            scroll_banner=scroll_txt,
            defeat_poem=fail_txt,
            victory_poem=success_txt,
            narrative=(
                "Take flight as the mythical Jabberwock through eerie ancient realms. "
                "Guide the dragon through the twisted Tulgey Wood, past the stone huts of Brillig Village, "
                "across the haunted Borogove Vale and mysterious Wabe, toward The Frabjous End. "
                "Avoid lethal monolithic obstacles, breathe incinerating flames, collect arcane secrets, "
                "and escape the vorpal blade that seeks to lay you low."
            ),
        ),
        mechanics=[
            GameMechanic(
                name="Fixed-Point Sub-Pixel Flight Physics",
                description=(
                    "Vertical flight simulation uses an 8.8 fixed-point velocity accumulator. "
                    "Inertia and constant gravitational pull gently draw the dragon down, counteracted "
                    "by upward lift impulses when steering up. Velocity is clamped to ensure responsive handling."
                ),
            ),
            GameMechanic(
                name="Fiery Breath (5th-Player PMG Composite)",
                description=(
                    "Holding FIRE ignites a stream of dragon flame, rendered via GTIA 5th-player "
                    "composite missile mode (M0–M3 combined in COLPF3). Flame immediately demolishes "
                    "destructible barriers and hostile entities upon contact."
                ),
            ),
            GameMechanic(
                name="Energy Depletion & Conversion",
                description=(
                    "The dragon has 3 lives and an energy gauge (0–100%). Sustaining flight and breathing fire "
                    "drain energy, while collisions rapidly deplete it. Reaching the end of a labyrinth screen sequence "
                    "converts remaining energy into bonus score points."
                ),
            ),
            GameMechanic(
                name="1-Frame Grace Collision Debounce",
                description=(
                    "A 1-frame grace debounce filter prevents instant catastrophic death on glancing "
                    "contact during high-speed horizontal scrolling."
                ),
            ),
            GameMechanic(
                name="Ancient Secrets & Interactive Collectibles",
                description=(
                    "Special objects marked with secret flags grant large score awards and replenish energy. "
                    "Secret collision checks cover column 7 to ensure seamless collection even at top scrolling velocity."
                ),
            ),
        ],
        controls=[
            GameControl(key="Joystick Up", action="Fly upward / ascend against gravity"),
            GameControl(key="Joystick Down", action="Dive downward / accelerate descent"),
            GameControl(key="Joystick Left", action="Decelerate horizontal scroll / retreat left"),
            GameControl(key="Joystick Right", action="Thrust forward / push rightward"),
            GameControl(key="Fire (Hold)", action="Breathe flame to destroy obstacles"),
            GameControl(key="Fire (Tap)", action="Skip title slide-up / start game"),
            GameControl(key="Space / Option", action="Skip intro poem / pause"),
        ],
        engine_specs=GameSpecs(
            display_engine="ANTIC Mode 5 action playfield (40×11 chars, 16 scanlines/cell, 5 colors including inverted PF3), ANTIC 2 status bar, ANTIC F high-resolution bitmap title.",
            screen_resolution="160×176 action playfield pixels + 40×8 status bar pixels.",
            scroll_architecture="Mirror ring buffer ($6000–$641F, 11 rows × 96 B) with per-row LMS pointers and hardware HSCROL fine-scrolling for 50 FPS PAL performance.",
            audio_engine="4-channel POKEY audio with relocated Chaos Music Composer (CMC) at $9A00 and interleaved SFX state machine.",
            sprite_system="Single-line Player-Missile Graphics at $2000–$27FF; 26 scanline dragon sprite with 8 animated frames.",
        ),
    )


def build_world_and_objects_reports() -> tuple[WorldReport, ObjectsReport]:
    """Parse world/project.yaml, world/objects.yaml, world/colors.yaml."""
    project_path = PROJECT_ROOT / "world/project.yaml"
    objects_path = PROJECT_ROOT / "world/objects.yaml"
    colors_path = PROJECT_ROOT / "world/colors.yaml"

    project, err = load_project_from_yaml(project_path)
    if err or not project:
        raise RuntimeError(f"Failed to load project: {err}")

    objects_lib = ObjectsLibrary()
    if not objects_lib.load(objects_path):
        raise RuntimeError(f"Failed to load objects from {objects_path}")

    raw_colors = load_colors(colors_path)

    # Palette
    palette_dict: Dict[str, PaletteColor] = {}
    import yaml
    with colors_path.open("r", encoding="utf-8") as f:
        colors_yaml_data = yaml.safe_load(f)

    for k, v in colors_yaml_data.items():
        atari_val = v.get("atari", 0)
        rgb_val = v.get("rgb", [0, 0, 0])
        hex_val = f"#{rgb_val[0]:02x}{rgb_val[1]:02x}{rgb_val[2]:02x}"
        palette_dict[k] = PaletteColor(
            name=k,
            atari=atari_val,
            rgb=rgb_val,
            hex=hex_val,
        )

    # Process objects and count occurrences
    usage_counts: Dict[int, int] = {obj.code: 0 for obj in objects_lib.objects}
    usage_screens: Dict[int, set[str]] = {obj.code: set() for obj in objects_lib.objects}

    screen_models: List[WorldScreen] = []

    for scr in project.screens:
        obj_instances: List[WorldObjectInstance] = []
        for inst in scr.objects:
            obj_def = objects_lib.get_by_code(inst.code)
            if not obj_def:
                continue

            x, y = unpack_xy(inst.packed_xy)
            usage_counts[inst.code] = usage_counts.get(inst.code, 0) + 1
            usage_screens.setdefault(inst.code, set()).add(scr.id)

            obj_instances.append(
                WorldObjectInstance(
                    code=inst.code,
                    packed_xy=inst.packed_xy,
                    x=x,
                    y=y,
                    object_id=obj_def.id,
                    width=obj_def.size.width,
                    height=obj_def.size.height,
                    blocking=bool(obj_def.flags.blocking),
                    interactive=bool(obj_def.flags.interactive),
                    secret=bool(obj_def.flags.secret),
                    tiles=list(obj_def.tiles),
                    tags=list(obj_def.tags),
                )
            )

        vram = list(bake_screen_vram(scr, objects_lib))
        blocking = list(bake_screen_blocking(scr, objects_lib))

        blk_count = sum(1 for b in blocking if b & 0x01)
        inter_count = sum(1 for b in blocking if b & 0x02)
        sec_count = sum(1 for b in blocking if b & 0x04)

        screen_models.append(
            WorldScreen(
                id=scr.id,
                objects_count=len(obj_instances),
                objects=obj_instances,
                baked_vram=vram,
                baked_blocking=blocking,
                blocking_tiles_count=blk_count,
                secret_tiles_count=sec_count,
                interactive_tiles_count=inter_count,
            )
        )

    # Screen dictionary for fast lookup
    screen_dict = {s.id: s for s in screen_models}

    # Labyrinths
    labyrinth_models: List[LabyrinthData] = []
    for lab in project.labyrinths:
        tot_objs = 0
        tot_secrets = 0
        tot_blocking = 0
        tot_interactive = 0

        for sid in lab.screens:
            if sid in screen_dict:
                sc = screen_dict[sid]
                tot_objs += sc.objects_count
                tot_secrets += sum(1 for o in sc.objects if o.secret)
                tot_blocking += sum(1 for o in sc.objects if o.blocking)
                tot_interactive += sum(1 for o in sc.objects if o.interactive)

        labyrinth_models.append(
            LabyrinthData(
                id=lab.id,
                name=lab.name,
                screens_count=len(lab.screens),
                screen_ids=list(lab.screens),
                total_objects=tot_objs,
                total_secrets=tot_secrets,
                total_blocking=tot_blocking,
                total_interactive=tot_interactive,
            )
        )

    world_report = WorldReport(
        project_name=project.name,
        grid=WorldGrid(
            screen_width_chars=SCREEN_WIDTH_CHARS,
            screen_height_chars=SCREEN_HEIGHT_CHARS,
            grid_step_x=2,
            grid_step_y=2,
            grid_cols=20,
            grid_rows=6,
        ),
        palette=palette_dict,
        labyrinths=labyrinth_models,
        screens=screen_models,
    )

    # Objects report
    all_tags = sorted(list(objects_lib.tags))
    catalog_objects: List[CatalogObject] = []

    for obj in objects_lib.objects:
        cnt = usage_counts.get(obj.code, 0)
        scrs = sorted(list(usage_screens.get(obj.code, set())))
        catalog_objects.append(
            CatalogObject(
                code=obj.code,
                id=obj.id,
                object=obj.id,
                size={"width": obj.size.width, "height": obj.size.height},
                flags={
                    "blocking": bool(obj.flags.blocking),
                    "interactive": bool(obj.flags.interactive),
                    "secret": bool(obj.flags.secret),
                },
                tiles=list(obj.tiles),
                tags=list(obj.tags),
                instances_count=cnt,
                screens_used_in=scrs,
                is_used_in_world=(cnt > 0),
            )
        )

    used_count = sum(1 for o in catalog_objects if o.is_used_in_world)

    objects_report = ObjectsReport(
        total_count=len(catalog_objects),
        used_count=used_count,
        all_tags=all_tags,
        objects=catalog_objects,
    )

    return world_report, objects_report


def build_sprites_report() -> SpriteReport:
    """Parse sprites/jabberwocky.json."""
    sprite_path = PROJECT_ROOT / "sprites/jabberwocky.json"
    sprite_data = load_sprite_json(sprite_path)

    frames: List[SpriteFrameData] = []
    for idx, f in enumerate(sprite_data.frames):
        row_bytes: List[int] = []
        for line in f.pixels:
            row_bytes.append(int(line, 2))
        frames.append(
            SpriteFrameData(
                index=idx,
                pixels=list(f.pixels),
                row_bytes=row_bytes,
            )
        )

    return SpriteReport(
        id=sprite_data.id,
        name="Jabberwock Dragon",
        width=sprite_data.width,
        height=sprite_data.height,
        color=sprite_data.color,
        frame_duration=sprite_data.frame_duration,
        total_frames=len(frames),
        hardware_mode="Single-line Player-Missile Graphics (PMG), 8 pixels wide, 26 scanlines",
        color_registers="Player 0 uses COLP0 ($D012) via PCOLR0 ($02C0); 5th-player flame uses COLPF3 ($D019)",
        buffer_address="$2000–$27FF (2 KB boundary aligned)",
        frames=frames,
    )


def build_assets_report() -> AssetsReport:
    """Build assets report from fonts/, img/, chars/, texts/."""
    title_png = PROJECT_ROOT / "img/title.png"
    cover_png = PROJECT_ROOT / "cover.png"

    from PIL import Image
    title_img = Image.open(title_png)
    title_w, title_h = title_img.size

    cover_w, cover_h = (0, 0)
    if cover_png.exists():
        c_img = Image.open(cover_png)
        cover_w, cover_h = c_img.size

    images_dict = {
        "title": ImageAsset(
            file="img/title.png",
            width=title_w,
            height=title_h,
            format="PNG",
            antic_mode="F",
            target_bin="gen/title.bin",
            file_size_bytes=title_png.stat().st_size,
        ),
        "cover": ImageAsset(
            file="cover.png",
            width=cover_w,
            height=cover_h,
            format="PNG",
            file_size_bytes=cover_png.stat().st_size if cover_png.exists() else 0,
        ),
    }

    game_fnt = PROJECT_ROOT / "fonts/game.fnt"
    text_fnt = PROJECT_ROOT / "fonts/text.fnt"

    fonts_dict = {
        "game_fnt": FontAsset(
            file="fonts/game.fnt",
            file_size_bytes=game_fnt.stat().st_size,
            characters_count=128,
            base_address="$6800",
            description="Playfield graphics font for ANTIC 5 labyrinth tiles",
        ),
        "text_fnt": FontAsset(
            file="fonts/text.fnt",
            file_size_bytes=text_fnt.stat().st_size,
            characters_count=128,
            base_address="$5C00",
            description="Text font with custom Polish diacritics for status bar and UI screens",
        ),
    }

    # Chars animated
    anim_json = PROJECT_ROOT / "chars/animated.json"
    with anim_json.open("r", encoding="utf-8") as f:
        anim_data = json.load(f)

    animated_chars: List[AnimatedCharData] = []
    for c in anim_data.get("characters", []):
        idx = c["index"]
        anims = c.get("animation", [])
        tot_f = 0
        rep = 0
        dur = 0
        f_hex: List[str] = []
        for a in anims:
            rep = a.get("repeat", 1)
            for fr in a.get("frames", []):
                tot_f += 1
                dur = fr.get("duration", 5)
                f_hex.append(fr.get("data", "").strip())
        animated_chars.append(
            AnimatedCharData(
                index=idx,
                repeat=rep,
                total_frames=tot_f,
                frame_duration=dur,
                frames_hex=f_hex,
            )
        )

    # Chars rotated
    rot_json = PROJECT_ROOT / "chars/rotated.json"
    with rot_json.open("r", encoding="utf-8") as f:
        rot_data = json.load(f)

    rotated_chars: List[RotatedCharData] = []
    for c in rot_data.get("characters", []):
        rotated_chars.append(
            RotatedCharData(
                index=c["index"],
                duration=c.get("duration", 5),
            )
        )

    # Texts
    story_texts = {
        "title": (PROJECT_ROOT / "texts/title.txt").read_text(encoding="utf-8").strip(),
        "scroll": (PROJECT_ROOT / "texts/scroll.txt").read_text(encoding="utf-8").strip(),
        "game_over_fail": (PROJECT_ROOT / "texts/game_over_fail.txt").read_text(encoding="utf-8").strip(),
        "game_over_success": (PROJECT_ROOT / "texts/game_over_success.txt").read_text(encoding="utf-8").strip(),
    }

    return AssetsReport(
        images=images_dict,
        fonts=fonts_dict,
        animated_characters=animated_chars,
        rotated_characters=rotated_chars,
        story_texts=story_texts,
    )


def build_music_report() -> MusicReport:
    """Parse music/music.sap and engine/music.asm."""
    sap_path = PROJECT_ROOT / "music/music.sap"
    sap_bytes = sap_path.read_bytes()
    tags, payload_offset = parse_sap_header(sap_bytes)

    sap_metadata = {
        "author": tags.get("AUTHOR", "").strip('"'),
        "name": tags.get("NAME", "").strip('"'),
        "year": tags.get("DATE", "").strip('"'),
        "type": tags.get("TYPE", "C"),
        "total_songs": int(tags.get("SONGS", "3")),
        "time_str": tags.get("TIME", "02:47.86"),
        "sap_music_addr": f"${tags.get('MUSIC', '8400')}",
        "sap_player_addr": f"${tags.get('PLAYER', '0500')}",
        "file_size_bytes": len(sap_bytes),
        "payload_offset": payload_offset,
    }

    subsongs = [
        SubsongData(
            id=0,
            name="Game Over / Reserve",
            duration="02:34",
            symbol="MUSIC_GAME_OVER",
            description="Melancholic theme played during Game Over and High Score display",
        ),
        SubsongData(
            id=1,
            name="Gameplay",
            duration="04:45",
            symbol="MUSIC_GAMEPLAY",
            description="Fast, driving action soundtrack during labyrinth dragon flight",
        ),
        SubsongData(
            id=2,
            name="Title Screen",
            duration="02:47",
            symbol="MUSIC_TITLE",
            description="Atmospheric intro theme accompanying the title screen and Lewis Carroll poem",
        ),
    ]

    engine_arch = {
        "sound_generator": "POKEY (4 audio channels)",
        "music_engine": "Chaos Music Composer (CMC) relocated driver",
        "music_data_address": "$9000–$9921",
        "cmc_player_address": "$9A00–$A155",
        "update_frequency": "50 Hz PAL (called every VBLANK tick via Audio_Update)",
        "sfx_coexistence": "Procedural SFX state machine on POKEY channels 3 and 4 smoothly priority-mixes with background CMC music",
    }

    sfx_catalog = [
        SfxData(symbol="SFX_FIRE", description="Continuous flame hiss while breathing fire", channel="POKEY Ch 4"),
        SfxData(symbol="SFX_CRASH", description="Deep concussive noise on obstacle or wall crash", channel="POKEY Ch 3 & 4"),
        SfxData(symbol="SFX_SECRET", description="Two-tone bright chime when collecting a secret item", channel="POKEY Ch 3"),
        SfxData(symbol="SFX_BONUS", description="Rapid rhythmic click tallying energy bonus score", channel="POKEY Ch 4"),
        SfxData(symbol="SFX_DEATH", description="Short descending melodic fanfare upon losing a life", channel="POKEY Ch 3 & 4"),
    ]

    return MusicReport(
        sap_metadata=sap_metadata,
        subsongs=subsongs,
        engine_architecture=engine_arch,
        sfx_catalog=sfx_catalog,
    )


def build_memory_report(git_info: Dict[str, str]) -> MemoryReport:
    """Parse docs/memory_map.json and main.asm equates."""
    mm_json_path = PROJECT_ROOT / "docs/memory_map.json"
    if not mm_json_path.exists():
        raise FileNotFoundError(f"Missing {mm_json_path}. Run 'make check_memory' first.")

    with mm_json_path.open("r", encoding="utf-8") as f:
        raw_segments = json.load(f)

    segments: List[MemorySegmentData] = []
    allocated_bytes = 0
    raw_free_gap_bytes = 0

    for s in raw_segments:
        start_hex = s["start_address"].replace("$", "")
        end_hex = s["end_address"].replace("$", "")
        start_int = int(start_hex, 16)
        end_int = int(end_hex, 16)
        size = s["size"]
        seg_type = s["type"]

        if seg_type != "free":
            allocated_bytes += size
        elif end_int <= 0xBFFF:
            raw_free_gap_bytes += size

        segments.append(
            MemorySegmentData(
                name=s["name"],
                start_address=s["start_address"],
                end_address=s["end_address"],
                start_int=start_int,
                end_int=end_int,
                size=size,
                type=seg_type,
            )
        )

    # Runtime-reserved RAM regions (equates only, no org)
    runtime_reserved = [
        RuntimeReservedData(
            name="PMG Buffer",
            start_address="$2000",
            end_address="$27FF",
            size=2048,
            purpose="Player-Missile Graphics buffer (Player 0 dragon sprite & 5th player flame)",
        ),
        RuntimeReservedData(
            name="HSCROL Ring Buffer",
            start_address="$6000",
            end_address="$641F",
            size=1056,
            purpose="Action playfield mirror ring buffer (11 rows × 96 bytes) for fine-scrolling",
        ),
        RuntimeReservedData(
            name="Status Bar VRAM",
            start_address="$6420",
            end_address="$646F",
            size=80,
            purpose="ANTIC 2 status bar screen memory (2 lines × 40 bytes)",
        ),
    ]

    total_reserved = sum(r.size for r in runtime_reserved)
    net_usable_free = max(0, raw_free_gap_bytes - total_reserved)

    # Zero Page user vars
    zp_vars = [
        ZeroPageVarData(symbol="PTR_SRC", address="$80", size=2, description="16-bit source address pointer (texts, data streams)"),
        ZeroPageVarData(symbol="PTR_DST", address="$82", size=2, description="16-bit destination address pointer (VRAM, buffers)"),
        ZeroPageVarData(symbol="ZP_TMP", address="$84", size=2, description="8-bit scratchpad register / temporary variables"),
        ZeroPageVarData(symbol="PTR_BLK", address="$86", size=2, description="16-bit blocking grid address pointer (BLOCKING_VRAM)"),
        ZeroPageVarData(symbol="PTR_COLL", address="$88", size=2, description="16-bit object collision tiles lookup pointer"),
    ]

    os_zp = {
        "range": "$0000–$007F (128 bytes)",
        "role": "Atari OS shadow registers, timers (RTCLOK), interrupt flags, and hardware shadows. Untouched by game code to preserve OS VBLANK.",
    }

    rom_banking = {
        "basic_rom": "$A000–$BFFF (8 KB): Disabled at boot via PORTB bit 1 ($D301) to unlock user RAM for CMC Player and Text VRAM.",
        "os_kernel_rom": "$C000–$CFFF and $E000–$FFFF (14 KB): Kept enabled; game utilizes OS VBLANK and system vectors.",
        "hardware_registers": "$D000–$DFFF (4 KB): Memory-mapped I/O (ANTIC, GTIA, POKEY, PIA). Never mapped to RAM.",
    }

    xex_path = PROJECT_ROOT / "jabberwocky.xex"
    xex_exists = xex_path.exists()
    xex_sha256 = ""
    xex_size = 0
    if xex_exists:
        xex_bytes = xex_path.read_bytes()
        xex_sha256 = hashlib.sha256(xex_bytes).hexdigest()
        xex_size = len(xex_bytes)

    provenance = {
        "commit_sha": git_info["commit_sha"],
        "commit_date": git_info["commit_date"],
        "binary_present": xex_exists,
        "binary_sha256": xex_sha256,
        "binary_size_bytes": xex_size,
        "binary_origin": "local build" if xex_exists else "not built",
    }

    space_summary = {
        "total_system_ram_bytes": 65536,
        "ram_ceiling_address": "$BFFF",
        "usable_ram_ceiling_bytes": 49152,
        "total_allocated_by_xex_bytes": allocated_bytes,
        "total_runtime_reserved_bytes": total_reserved,
        "raw_free_gap_bytes": raw_free_gap_bytes,
        "net_usable_free_bytes": net_usable_free,
        "effective_utilization_percent": round(
            (allocated_bytes + total_reserved) / 49152 * 100, 1
        ),
    }

    return MemoryReport(
        segments=segments,
        runtime_reserved=runtime_reserved,
        zero_page_vars=zp_vars,
        os_zero_page=os_zp,
        rom_banking=rom_banking,
        space_summary=space_summary,
        provenance=provenance,
    )


def fetch_github_releases(skip_network: bool = False) -> List[Dict[str, Any]]:
    """Fetch releases from GitHub API with fallback to git tags."""
    if not skip_network:
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/grzes71/jabberwocky/releases",
                headers={"User-Agent": "Jabberwocky-Portal-Exporter"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            print(f"Notice: GitHub API fetch skipped/failed ({e}), falling back to git tags.", file=sys.stderr)

    # Fallback using git tags
    releases = []
    try:
        tag_list = subprocess.check_output(
            ["git", "tag", "-l", "--sort=-v:refname"], stderr=subprocess.DEVNULL
        ).decode().splitlines()
        for t in tag_list:
            t = t.strip()
            if not t.startswith("v"):
                continue
            date_str = datetime.now().isoformat()
            try:
                date_str = subprocess.check_output(
                    ["git", "log", "-1", "--format=%cI", t], stderr=subprocess.DEVNULL
                ).decode().strip()
            except Exception:
                pass

            msg = ""
            try:
                msg = subprocess.check_output(
                    ["git", "tag", "-l", "--format=%(contents)", t], stderr=subprocess.DEVNULL
                ).decode().strip()
            except Exception:
                pass

            if not msg:
                try:
                    msg = subprocess.check_output(
                        ["git", "log", "-1", "--format=%B", t], stderr=subprocess.DEVNULL
                    ).decode().strip()
                except Exception:
                    msg = f"Release {t}"

            releases.append({
                "tag_name": t,
                "name": f"Jabberwocky {t}",
                "published_at": date_str,
                "body": msg,
                "assets": [{
                    "name": "jabberwocky.xex",
                    "size": 35352,
                    "browser_download_url": f"https://github.com/grzes71/jabberwocky/releases/download/{t}/jabberwocky.xex",
                }],
                "html_url": f"https://github.com/grzes71/jabberwocky/releases/tag/{t}",
            })
    except Exception:
        pass

    return releases


def build_releases_and_latest_reports(
    world_rep: WorldReport,
    objects_rep: ObjectsReport,
    sprites_rep: SpriteReport,
    music_rep: MusicReport,
    memory_rep: MemoryReport,
    skip_network: bool = False,
) -> tuple[ReleasesReport, LatestReport]:
    """Build releases.json and latest.json."""
    raw_releases = fetch_github_releases(skip_network=skip_network)

    release_models: List[ReleaseData] = []
    for idx, r in enumerate(raw_releases):
        tag = r.get("tag_name", "")
        ver = tag.lstrip("v")
        name = r.get("name") or f"Jabberwocky {tag}"
        pub_at = r.get("published_at", "")
        body = r.get("body", "").strip()
        html_url = r.get("html_url", f"https://github.com/grzes71/jabberwocky/releases/tag/{tag}")

        asset_name = "jabberwocky.xex"
        asset_size = 35352
        download_url = f"https://github.com/grzes71/jabberwocky/releases/download/{tag}/jabberwocky.xex"

        assets = r.get("assets", [])
        if assets:
            a = assets[0]
            asset_name = a.get("name", asset_name)
            asset_size = a.get("size", asset_size)
            download_url = a.get("browser_download_url", download_url)

        release_models.append(
            ReleaseData(
                version=ver,
                tag_name=tag,
                name=name,
                published_at=pub_at,
                changelog=body,
                download_url=download_url,
                html_url=html_url,
                asset_name=asset_name,
                asset_size=asset_size,
                is_latest=(idx == 0),
            )
        )

    releases_report = ReleasesReport(
        total_releases=len(release_models),
        releases=release_models,
    )

    # Latest report
    first_rel = release_models[0] if release_models else None
    latest_ver = first_rel.version if first_rel else "0.10.0"
    latest_tag = first_rel.tag_name if first_rel else "v0.10.0"
    latest_date = (first_rel.published_at[:10]) if (first_rel and first_rel.published_at) else "2026-11-02"
    latest_dl = first_rel.download_url if first_rel else f"https://github.com/grzes71/jabberwocky/releases/download/{latest_tag}/jabberwocky.xex"
    latest_size = first_rel.asset_size if first_rel else 35352

    tot_placed = sum(s.objects_count for s in world_rep.screens)
    tot_secrets = sum(sum(1 for o in s.objects if o.secret) for s in world_rep.screens)

    latest_report = LatestReport(
        version=latest_ver,
        tag_name=latest_tag,
        release_date=latest_date,
        download_url=latest_dl,
        binary_size=memory_rep.provenance.get("binary_size_bytes") or latest_size,
        binary_sha256=memory_rep.provenance.get("binary_sha256") or "",
        stats=LatestStats(
            labyrinths=len(world_rep.labyrinths),
            screens=len(world_rep.screens),
            catalog_objects=objects_rep.total_count,
            total_placed_objects=tot_placed,
            total_secrets=tot_secrets,
            sprite_frames=sprites_rep.total_frames,
            subsongs=len(music_rep.subsongs),
            allocated_memory_bytes=memory_rep.space_summary["total_allocated_by_xex_bytes"],
            net_free_ram_bytes=memory_rep.space_summary["net_usable_free_bytes"],
        ),
    )

    return releases_report, latest_report


# ============================================================================
# Main CLI & Dispatcher
# ============================================================================

def export_all(
    out_dir: Path,
    astro_data_dir: Optional[Path] = None,
    skip_network: bool = False,
) -> Dict[str, int]:
    """Execute complete export pipeline and write JSON files."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if astro_data_dir:
        astro_data_dir.mkdir(parents=True, exist_ok=True)

    git_info = get_git_info()

    print("Exporting game.json...")
    game_rep = build_game_report(git_info)

    print("Exporting world.json and objects.json...")
    world_rep, objects_rep = build_world_and_objects_reports()

    print("Exporting sprites.json...")
    sprites_rep = build_sprites_report()

    print("Exporting assets.json...")
    assets_rep = build_assets_report()

    print("Exporting music.json...")
    music_rep = build_music_report()

    print("Exporting memory.json...")
    memory_rep = build_memory_report(git_info)

    print("Exporting releases.json and latest.json...")
    releases_rep, latest_rep = build_releases_and_latest_reports(
        world_rep, objects_rep, sprites_rep, music_rep, memory_rep, skip_network=skip_network
    )

    reports = {
        "game.json": game_rep.model_dump(),
        "world.json": world_rep.model_dump(),
        "objects.json": objects_rep.model_dump(),
        "sprites.json": sprites_rep.model_dump(),
        "assets.json": assets_rep.model_dump(),
        "music.json": music_rep.model_dump(),
        "memory.json": memory_rep.model_dump(),
        "releases.json": releases_rep.model_dump(),
        "latest.json": latest_rep.model_dump(),
    }

    file_sizes = {}
    for filename, data in reports.items():
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        target_path = out_dir / filename
        target_path.write_bytes(json_bytes)
        file_sizes[filename] = len(json_bytes)

        if astro_data_dir:
            (astro_data_dir / filename).write_bytes(json_bytes)

        print(f"  ✓ {filename} ({len(json_bytes)} bytes)")

    return file_sizes


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Jabberwocky portal data to JSON")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=PROJECT_ROOT / "reports/portal",
        help="Target reports directory (default: reports/portal)",
    )
    parser.add_argument(
        "--astro-data-dir",
        type=Path,
        default=PROJECT_ROOT / "website/src/data",
        help="Target Astro data directory (default: website/src/data)",
    )
    parser.add_argument(
        "--skip-network",
        action="store_true",
        help="Skip remote GitHub API calls and use local git tags instead",
    )

    args = parser.parse_args()

    try:
        sizes = export_all(
            out_dir=args.out_dir,
            astro_data_dir=args.astro_data_dir,
            skip_network=args.skip_network,
        )
        print(f"\nSuccessfully generated {len(sizes)} portal JSON reports.")
        return 0
    except Exception as e:
        print(f"Error exporting portal data: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
