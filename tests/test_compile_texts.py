"""Unit tests for scripts/compile_texts.py."""

from pathlib import Path
from scripts.compile_texts import (
    POLISH_CHAR_MAP,
    compile_scroll_text,
    compile_title_text,
    text_to_mads_dta,
)


def test_polish_char_map_completeness():
    """Ensure all expected lowercase and uppercase Polish diacritics are mapped."""
    expected_lower = ["ą", "ć", "ę", "ł", "ń", "ó", "ś", "ź", "ż"]
    expected_upper = ["Ą", "Ć", "Ę", "Ł", "Ń", "Ó", "Ś", "Ź", "Ż"]

    for i, ch in enumerate(expected_lower):
        assert POLISH_CHAR_MAP[ch] == 64 + i

    for i, ch in enumerate(expected_upper):
        assert POLISH_CHAR_MAP[ch] == 73 + i


def test_text_to_mads_dta_simple():
    """Verify standard ASCII string conversion."""
    res = text_to_mads_dta("HELLO", invert=False, length_prefix=True)
    assert res == ["    dta 5", "    dta d'HELLO'"]


def test_text_to_mads_dta_with_polish_diacritics():
    """Verify split into ASCII and mapped Polish codes."""
    res = text_to_mads_dta("było", invert=False, length_prefix=True)
    assert res == [
        "    dta 4",
        "    dta d'by'",
        "    dta 67",  # ł
        "    dta d'o'",
    ]


def test_text_to_mads_dta_inverted():
    """Verify inverted strings have * suffix and +$80 on code points."""
    res = text_to_mads_dta("było", invert=True, length_prefix=False)
    assert res == [
        "    dta d'by'*",
        "    dta 195",  # 67 + 128 = 195
        "    dta d'o'*",
    ]


def test_compile_title_text(tmp_path: Path):
    """Verify compiling title.txt produces valid MADS structure."""
    sample_file = tmp_path / "title.txt"
    sample_file.write_text("było smaszno\nświdrokrętnie\n", encoding="utf-8")

    out = compile_title_text(sample_file)
    assert "intro_txt_line1" in out
    assert "intro_txt_line2" in out
    assert "67" in out  # ł
    assert "70" in out  # ś
    assert "66" in out  # ę


def test_compile_scroll_text(tmp_path: Path):
    """Verify compiling scroll.txt produces ticker structure with correct length."""
    sample_file = tmp_path / "scroll.txt"
    sample_file.write_text("TEKST TESTOWY", encoding="utf-8")

    out = compile_scroll_text(sample_file)
    assert "TITLE_SCROLL_TEXT_LEN = 13" in out
    assert "title_scroll_text" in out
    assert "d'TEKST TESTOWY'*" in out
