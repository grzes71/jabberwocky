import pytest
from scripts.release_helper import (
    parse_commit_message,
    determine_bump_type,
    parse_semver,
    compute_next_version,
    generate_changelog,
    process_github_pr_event,
    get_pr_commit_messages,
    update_scroll_version,
)

def test_parse_commit_message_feat():
    msg = "feat(world): add new screen for SAMOTNIA"
    parsed = parse_commit_message(msg)
    assert parsed is not None
    assert parsed["type"] == "feat"
    assert parsed["scope"] == "world"
    assert parsed["desc"] == "add new screen for SAMOTNIA"
    assert parsed["is_breaking"] is False

def test_parse_commit_message_fix():
    msg = "fix: resolve enemy right click deletion bug"
    parsed = parse_commit_message(msg)
    assert parsed is not None
    assert parsed["type"] == "fix"
    assert parsed["scope"] is None
    assert parsed["desc"] == "resolve enemy right click deletion bug"
    assert parsed["is_breaking"] is False

def test_parse_commit_message_breaking_marker():
    msg = "feat!: redesign memory map layout"
    parsed = parse_commit_message(msg)
    assert parsed is not None
    assert parsed["type"] == "feat"
    assert parsed["is_breaking"] is True

def test_parse_commit_message_breaking_body():
    msg = "refactor: restructure engine scheduler\n\nBREAKING CHANGE: changes module signature"
    parsed = parse_commit_message(msg)
    assert parsed is not None
    assert parsed["type"] == "refactor"
    assert parsed["is_breaking"] is True

def test_determine_bump_type():
    # Only chore
    c_chore = parse_commit_message("chore: update readme")
    assert determine_bump_type([c_chore]) is None
    
    # Fix
    c_fix = parse_commit_message("fix: fix typo")
    assert determine_bump_type([c_chore, c_fix]) == "patch"
    
    # Feat
    c_feat = parse_commit_message("feat: add new enemy")
    assert determine_bump_type([c_chore, c_fix, c_feat]) == "minor"
    
    # Breaking
    c_breaking = parse_commit_message("feat!: rewrite engine")
    assert determine_bump_type([c_chore, c_fix, c_feat, c_breaking]) == "major"

def test_compute_next_version():
    # Initial versions when no previous tag exists
    assert compute_next_version(None, "minor") == "v0.1.0"
    assert compute_next_version(None, "patch") == "v0.0.1"
    assert compute_next_version(None, "major") == "v1.0.0"
    
    # Incremental bumps
    assert compute_next_version("v0.1.0", "patch") == "v0.1.1"
    assert compute_next_version("v0.1.0", "minor") == "v0.2.0"
    assert compute_next_version("v0.1.0", "major") == "v1.0.0"
    assert compute_next_version("v1.2.3", "patch") == "v1.2.4"
    assert compute_next_version("v1.2.3", "minor") == "v1.3.0"
    assert compute_next_version("v1.2.3", "major") == "v2.0.0"

def test_generate_changelog():
    c1 = parse_commit_message("feat(enemies): add dragon flight animation")
    c2 = parse_commit_message("fix(canvas): correct sprite mask rendering")
    
    changelog = generate_changelog([c1, c2], pr_number=42, pr_author="jabberdev", pr_url="https://github.com/repo/pull/42")
    assert "### 🚀 Nowości (Features)" in changelog
    assert "**enemies:** add dragon flight animation" in changelog
    assert "### 🐛 Poprawki (Bug Fixes)" in changelog
    assert "**canvas:** correct sprite mask rendering" in changelog
    assert "[#42](https://github.com/repo/pull/42)" in changelog
    assert "@jabberdev" in changelog

def test_process_github_pr_event_not_merged():
    event = {
        "pull_request": {
            "merged": False,
            "title": "feat: new feature"
        }
    }
    res = process_github_pr_event(event)
    assert res["should_release"] is False

def test_process_github_pr_event_merged_feat():
    event = {
        "pull_request": {
            "merged": True,
            "number": 10,
            "html_url": "https://github.com/user/repo/pull/10",
            "title": "feat: add flame breath attack",
            "body": "Implements fire breath mechanics.",
            "user": {"login": "jabberdev"}
        }
    }
    res = process_github_pr_event(event)
    assert res["should_release"] is True
    assert res["bump_type"] == "minor"
    assert res["tag_name"] == "v0.1.0" or res["tag_name"].startswith("v")
    assert res["release_title"] == f"Jabberwocky {res['tag_name']}"
    assert "flame breath attack" in res["changelog"]

def test_get_pr_commit_messages_none():
    assert get_pr_commit_messages(None) == []
    assert get_pr_commit_messages("") == []

def test_update_scroll_version(tmp_path):
    scroll_file = tmp_path / "scroll.txt"
    scroll_file.write_text(
        "JABBERWOCKY - ATARI 8-bit GAME - https://github.com/grzes71/jabberwocky - version 0.0.1 -PRESS FIRE TO START...                                        ",
        encoding="utf-8"
    )

    assert update_scroll_version("v0.2.0", scroll_file) is True
    content = scroll_file.read_text(encoding="utf-8")
    assert "version 0.2.0" in content
    assert "version 0.0.1" not in content
    assert "JABBERWOCKY - ATARI 8-bit GAME" in content
    assert content.endswith("                                        ")

def test_update_scroll_version_no_pattern(tmp_path):
    scroll_file = tmp_path / "scroll.txt"
    scroll_file.write_text("SOME TEXT WITHOUT VERSION", encoding="utf-8")
    assert update_scroll_version("0.1.0", scroll_file) is False

def test_update_scroll_version_nonexistent(tmp_path):
    assert update_scroll_version("0.1.0", tmp_path / "nonexistent.txt") is False
