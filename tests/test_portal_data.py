"""Unit and integration tests for Jabberwocky portal data exporter and JSON reports."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import yaml

from scripts.export_portal_data import (
    export_all,
    GameReport,
    WorldReport,
    ObjectsReport,
    SpriteReport,
    AssetsReport,
    MusicReport,
    MemoryReport,
    ReleasesReport,
    LatestReport,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def portal_data(tmp_path_factory) -> dict[str, Path]:
    """Generate all portal JSON reports into a temporary directory and return paths."""
    out_dir = tmp_path_factory.mktemp("portal_reports")
    astro_dir = tmp_path_factory.mktemp("astro_data")
    sizes = export_all(out_dir=out_dir, astro_data_dir=astro_dir, skip_network=True)
    return {name: out_dir / name for name in sizes.keys()}


def test_all_expected_reports_generated(portal_data):
    """Verify all 9 expected portal JSON files are generated and non-empty."""
    expected = [
        "game.json",
        "world.json",
        "objects.json",
        "sprites.json",
        "assets.json",
        "music.json",
        "memory.json",
        "releases.json",
        "latest.json",
    ]
    for rep in expected:
        assert rep in portal_data, f"Missing report: {rep}"
        p = portal_data[rep]
        assert p.exists(), f"File does not exist: {p}"
        assert p.stat().st_size > 0, f"File is empty: {p}"


def test_schemas_validation(portal_data):
    """Validate each generated JSON file against its corresponding Pydantic schema."""
    schemas = {
        "game.json": GameReport,
        "world.json": WorldReport,
        "objects.json": ObjectsReport,
        "sprites.json": SpriteReport,
        "assets.json": AssetsReport,
        "music.json": MusicReport,
        "memory.json": MemoryReport,
        "releases.json": ReleasesReport,
        "latest.json": LatestReport,
    }
    for filename, schema in schemas.items():
        data = json.loads(portal_data[filename].read_text(encoding="utf-8"))
        validated = schema.model_validate(data)
        assert validated is not None, f"Failed schema validation for {filename}"


def test_world_counts_match_source_yaml(portal_data):
    """Verify screen and labyrinth counts correspond directly to world/project.yaml."""
    world_src = yaml.safe_load((PROJECT_ROOT / "world/project.yaml").read_text(encoding="utf-8"))
    world_rep = json.loads(portal_data["world.json"].read_text(encoding="utf-8"))

    expected_screens = len(world_src.get("screens", []))
    expected_labyrinths = len(world_src.get("labyrinths", []))

    assert len(world_rep["screens"]) == expected_screens
    assert len(world_rep["labyrinths"]) == expected_labyrinths
    assert world_rep["grid"]["screen_width_chars"] == 40
    assert world_rep["grid"]["screen_height_chars"] == 11


def test_object_counts_match_source_catalog(portal_data):
    """Verify catalog object count and codes match world/objects.yaml exactly."""
    objects_src = yaml.safe_load((PROJECT_ROOT / "world/objects.yaml").read_text(encoding="utf-8"))
    objects_rep = json.loads(portal_data["objects.json"].read_text(encoding="utf-8"))

    src_objects = objects_src.get("objects", [])
    assert objects_rep["total_count"] == len(src_objects)
    assert len(objects_rep["objects"]) == len(src_objects)

    src_codes = {o["code"] for o in src_objects}
    rep_codes = {o["code"] for o in objects_rep["objects"]}
    assert src_codes == rep_codes


def test_sprite_metadata_consistent_with_source(portal_data):
    """Verify dragon sprite frame count and dimensions match sprites/jabberwocky.json."""
    sprite_src = json.loads((PROJECT_ROOT / "sprites/jabberwocky.json").read_text(encoding="utf-8"))
    sprite_rep = json.loads(portal_data["sprites.json"].read_text(encoding="utf-8"))

    s0 = sprite_src["sprites"][0]
    assert sprite_rep["width"] == s0["width"]
    assert sprite_rep["height"] == s0["height"]
    assert sprite_rep["total_frames"] == len(s0["frames"])
    assert len(sprite_rep["frames"]) == len(s0["frames"])

    for f in sprite_rep["frames"]:
        assert len(f["pixels"]) == s0["height"]
        assert len(f["row_bytes"]) == s0["height"]
        for row in f["pixels"]:
            assert len(row) == s0["width"]


def test_memory_segments_do_not_overlap(portal_data):
    """Verify that allocated memory segments never overlap with each other."""
    memory_rep = json.loads(portal_data["memory.json"].read_text(encoding="utf-8"))
    segments = [s for s in memory_rep["segments"] if s["type"] != "free"]

    # Filter out OS vector overrides like INITAD/RUNAD which reside in OS low RAM ($02E0-$02E3)
    user_segments = [s for s in segments if s["type"] != "vector"]
    sorted_segs = sorted(user_segments, key=lambda s: s["start_int"])

    for i in range(len(sorted_segs) - 1):
        cur = sorted_segs[i]
        nxt = sorted_segs[i + 1]
        assert cur["end_int"] < nxt["start_int"], (
            f"Segment overlap detected: {cur['name']} ({cur['start_address']}..{cur['end_address']}) "
            f"overlaps {nxt['name']} ({nxt['start_address']}..{nxt['end_address']})"
        )


def test_free_memory_ranges_do_not_overlap_allocated(portal_data):
    """Verify free space gaps do not overlap allocated segments."""
    memory_rep = json.loads(portal_data["memory.json"].read_text(encoding="utf-8"))
    allocated = [s for s in memory_rep["segments"] if s["type"] not in ("free", "vector")]
    free_gaps = [s for s in memory_rep["segments"] if s["type"] == "free"]

    for free_seg in free_gaps:
        f_start = free_seg["start_int"]
        f_end = free_seg["end_int"]
        for alloc_seg in allocated:
            a_start = alloc_seg["start_int"]
            a_end = alloc_seg["end_int"]
            # Assert no intersection
            assert f_start > a_end or f_end < a_start, (
                f"Free gap {free_seg['start_address']}..{free_seg['end_address']} "
                f"overlaps allocated segment {alloc_seg['name']} ({alloc_seg['start_address']}..{alloc_seg['end_address']})"
            )


def test_memory_totals_mathematically_consistent(portal_data):
    """Verify allocated + free headroom calculations are strictly consistent."""
    memory_rep = json.loads(portal_data["memory.json"].read_text(encoding="utf-8"))
    summary = memory_rep["space_summary"]

    alloc = summary["total_allocated_by_xex_bytes"]
    raw_free = summary["raw_free_gap_bytes"]
    reserved = summary["total_runtime_reserved_bytes"]
    net_free = summary["net_usable_free_bytes"]

    assert alloc > 0
    assert raw_free > 0
    assert reserved == 2048 + 1056 + 80  # PMG + HSCROL + status bar
    assert net_free == raw_free - reserved
    assert summary["usable_ram_ceiling_bytes"] == 0xC000  # $BFFF is 49151 + 1 = 49152 ($C000)


def test_missing_binary_data_handled_explicitly(tmp_path):
    """Verify exporter behaves cleanly when jabberwocky.xex does not exist."""
    # Temporarily remove xex if needed or test with isolated path
    xex_path = PROJECT_ROOT / "jabberwocky.xex"
    backup_path = PROJECT_ROOT / "jabberwocky.xex.bak"

    has_xex = xex_path.exists()
    try:
        if has_xex:
            xex_path.rename(backup_path)

        out_dir = tmp_path / "portal_no_xex"
        export_all(out_dir=out_dir, skip_network=True)

        mem_data = json.loads((out_dir / "memory.json").read_text(encoding="utf-8"))
        prov = mem_data["provenance"]
        assert prov["binary_present"] is False
        assert prov["binary_sha256"] == ""
        assert prov["binary_size_bytes"] == 0
        assert prov["binary_origin"] == "not built"
    finally:
        if has_xex and backup_path.exists():
            backup_path.rename(xex_path)

