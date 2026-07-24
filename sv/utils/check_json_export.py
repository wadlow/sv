"""Build and export check JSON files for V-codes."""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..models.vuln_code import VulnCode


def _looks_like_shell_command(text: str) -> bool:
    if not text:
        return False
    first = text.split()[0].lower()
    starters = (
        "grep", "sudo", "cat", "ls", "find", "psql", "apachectl", "httpd",
        "netstat", "systemctl", "authconfig", "rpm", "yum", "dnf", "auditctl",
    )
    return first in starters or "|" in text or text.startswith("-")


def _extract_command(line: str) -> Optional[str]:
    if line.startswith("$ "):
        return line[2:].strip()
    if line.startswith("# "):
        candidate = line[2:].strip()
        if _looks_like_shell_command(candidate):
            return candidate
    run_match = re.match(r'^run\s+"(.+?)"\.?\s*$', line, re.IGNORECASE)
    if run_match:
        return run_match.group(1)
    return None


def _make_check(section, description: str, commands: List[str]) -> Dict:
    return {
        "section": section,
        "description": description,
        "commands": commands,
        "finding_condition": None,
    }


def _parse_paragraph_check_text(check_text: str) -> List[Dict]:
    raw_blocks = [
        block.strip()
        for block in re.split(r"\n\s*\n", check_text.strip())
        if block.strip()
    ]
    checks: List[Dict] = []
    pending_desc: List[str] = []

    for block in raw_blocks:
        desc_lines: List[str] = []
        commands: List[str] = []
        for line in block.splitlines():
            command = _extract_command(line.strip())
            if command is not None:
                commands.append(command)
            else:
                desc_lines.append(line.rstrip())

        if commands:
            description_parts = pending_desc + desc_lines
            checks.append(_make_check(None, "\n".join(description_parts).strip(), commands))
            pending_desc = []
        else:
            pending_desc.extend(desc_lines)

    if pending_desc and not checks:
        checks.append(_make_check(None, "\n".join(pending_desc).strip(), []))

    if checks:
        return checks
    return [_make_check(None, check_text.strip(), [])]


def _parse_sectioned_check_text(check_text: str) -> List[Dict]:
    checks: List[Dict] = []
    pattern = re.compile(r"^####\s+(.+?)\s*$", re.MULTILINE)
    matches = list(pattern.finditer(check_text))
    if not matches:
        return _parse_paragraph_check_text(check_text)

    intro = check_text[: matches[0].start()].strip()
    if intro:
        checks.extend(_parse_paragraph_check_text(intro))

    for index, match in enumerate(matches):
        section = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(check_text)
        content = check_text[start:end].strip()
        for check in _parse_paragraph_check_text(content):
            check["section"] = section
            checks.append(check)

    return checks


def parse_check_text_to_checks(check_text: str) -> List[Dict]:
    """Parse STIG check text into the checks array used by check JSON files."""
    if not (check_text or "").strip():
        return [_make_check(None, "", [])]

    if re.search(r"^####\s+", check_text, flags=re.MULTILINE):
        return _parse_sectioned_check_text(check_text)
    return _parse_paragraph_check_text(check_text)


def build_check_json(vuln: VulnCode) -> Dict:
    """Build a check JSON document for a V-code."""
    return {
        "v_code": vuln.v_code,
        "severity": (vuln.severity or "medium").lower(),
        "rule_id": vuln.rule_id or "",
        "rule_ver": vuln.rule_ver or "",
        "rule_title": vuln.rule_title or "",
        "check_text": vuln.check_text or "",
        "checks": parse_check_text_to_checks(vuln.check_text or ""),
    }


def export_check_json(vuln: VulnCode, checks_dir: Path) -> Path:
    """Write a V-code check JSON file from STIG data, overwriting if present."""
    checks_dir.mkdir(parents=True, exist_ok=True)
    path = checks_dir / f"{vuln.v_code}.json"
    payload = build_check_json(vuln)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
