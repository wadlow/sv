"""Compare STIG and JSON check text for the Check Texts Explorer."""

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Set, Tuple

from AppKit import (
    NSBackgroundColorAttributeName,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSForegroundColorAttributeName,
)
from Foundation import NSAttributedString


def normalize_check_text(text: str) -> str:
    """Normalize check text for comparison."""
    if not text:
        return ""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in normalized.split("\n")).strip()


def load_json_check_text(v_code: str, checks_dir: Path) -> Optional[str]:
    """Load check_text from a V-code JSON file."""
    path = checks_dir / f"{v_code}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("check_text", "")


def check_texts_mismatch(
    stig_check_text: str,
    json_check_text: Optional[str],
) -> bool:
    """Return True when JSON check text exists and differs from STIG check text."""
    if json_check_text is None:
        return False
    return normalize_check_text(stig_check_text) != normalize_check_text(json_check_text)


def _line_diff_indexes(
    left_lines: List[str],
    right_lines: List[str],
) -> Tuple[Set[int], Set[int]]:
    """Return line indexes removed/changed on left and added/changed on right."""
    matcher = SequenceMatcher(None, left_lines, right_lines)
    left_changed: Set[int] = set()
    right_changed: Set[int] = set()
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("delete", "replace"):
            left_changed.update(range(i1, i2))
        if tag in ("insert", "replace"):
            right_changed.update(range(j1, j2))
    return left_changed, right_changed


def _append_plain(storage, text: str, font, color) -> None:
    if not text:
        return
    attrs = {
        NSFontAttributeName: font,
        NSForegroundColorAttributeName: color,
    }
    storage.appendAttributedString_(
        NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    )


def _append_lines_with_highlights(
    storage,
    title: str,
    lines: List[str],
    changed_indexes: Set[int],
    font,
    text_color,
    highlight_color,
) -> None:
    _append_plain(storage, title, font, text_color)
    for index, line in enumerate(lines):
        line_text = line + ("\n" if index < len(lines) - 1 else "")
        if not line_text and index < len(lines) - 1:
            line_text = "\n"
        attrs = {
            NSFontAttributeName: font,
            NSForegroundColorAttributeName: text_color,
        }
        if index in changed_indexes:
            attrs[NSBackgroundColorAttributeName] = highlight_color
        storage.appendAttributedString_(
            NSAttributedString.alloc().initWithString_attributes_(line_text, attrs)
        )
    if lines:
        _append_plain(storage, "\n", font, text_color)


def build_mismatch_attributed_text(
    v_code: str,
    rule_title: str,
    severity: str,
    stig_check_text: str,
    json_check_text: str,
):
    """Build attributed text showing STIG and JSON check text with diff highlights."""
    from Foundation import NSMutableAttributedString

    font = NSFont.systemFontOfSize_(12)
    text_color = NSColor.whiteColor()
    stig_highlight = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.12, 0.12, 1.0)
    json_highlight = NSColor.colorWithCalibratedRed_green_blue_alpha_(0.12, 0.35, 0.12, 1.0)

    stig_lines = (stig_check_text or "").splitlines()
    json_lines = (json_check_text or "").splitlines()
    stig_changed, json_changed = _line_diff_indexes(stig_lines, json_lines)

    storage = NSMutableAttributedString.alloc().init()
    header = (
        f"{v_code}: {rule_title}\n"
        f"Severity: {(severity or 'unknown').upper()}\n\n"
    )
    _append_plain(storage, header, font, text_color)

    _append_lines_with_highlights(
        storage,
        "STIG Check Text:\n",
        stig_lines or ["(No check text available)"],
        stig_changed,
        font,
        text_color,
        stig_highlight,
    )
    _append_plain(storage, "\n", font, text_color)
    _append_lines_with_highlights(
        storage,
        "JSON Check Text:\n",
        json_lines or ["(No check text available)"],
        json_changed,
        font,
        text_color,
        json_highlight,
    )
    return storage
