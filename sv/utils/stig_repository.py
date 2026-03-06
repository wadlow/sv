"""STIG repository utilities - fetch and parse DISA content-repository.xml."""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CONTENT_REPOSITORY_URL = (
    "https://raw.githubusercontent.com/DISA-STIGS/DISA-STIGS.github.io/master/content-repository.xml"
)


@dataclass
class RepoBenchmark:
    """A benchmark entry from the content repository."""
    title: str
    version: str  # e.g. "003.011"
    download_url: str
    content_id: str  # filename


def _normalize_title_for_match(title: str) -> str:
    """Normalize title for fuzzy matching - remove common suffixes, lowercase."""
    t = title.lower()
    for suffix in [" stig scap benchmark", " scap benchmark", " stig", " benchmark"]:
        if t.endswith(suffix):
            t = t[:-len(suffix)]
    return " ".join(t.split())


def _loaded_version_to_repo_format(stig_version: str, stig_release: str) -> Optional[str]:
    """
    Convert loaded STIG version (e.g. version="3", release="R11") to repo format "003.011".
    Returns None if conversion fails.
    """
    try:
        v = str(stig_version or "").strip()
        r = str(stig_release or "").strip()
        v_match = re.search(r'v?(\d+)', v, re.I)
        r_match = re.search(r'r?(\d+)', r, re.I)
        if v_match and r_match:
            v_num = int(v_match.group(1))
            r_num = int(r_match.group(1))
            return f"{v_num:03d}.{r_num:03d}"
    except (ValueError, AttributeError):
        pass
    return None


def _parse_version_tuple(version_str: str) -> Optional[tuple]:
    """Parse repo version '003.011' to (3, 11)."""
    try:
        parts = version_str.strip().split(".")
        if len(parts) >= 2:
            return (int(parts[0]), int(parts[1]))
        if len(parts) == 1:
            return (int(parts[0]), 0)
    except (ValueError, AttributeError):
        pass
    return None


def _version_compare(loaded_tuple: Optional[tuple], repo_tuple: Optional[tuple]) -> int:
    """Compare versions. Returns -1 if loaded < repo, 0 if equal, 1 if loaded > repo."""
    if loaded_tuple is None or repo_tuple is None:
        return 0
    if loaded_tuple < repo_tuple:
        return -1
    if loaded_tuple > repo_tuple:
        return 1
    return 0


def fetch_repository() -> List[RepoBenchmark]:
    """Fetch and parse the DISA content-repository.xml."""
    benchmarks = []
    try:
        req = Request(CONTENT_REPOSITORY_URL, headers={"User-Agent": "STIG-Viewer/1.0"})
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
    except (URLError, HTTPError, OSError) as e:
        raise RuntimeError(f"Failed to fetch content repository: {e}") from e

    root = ET.fromstring(data)
    contents = root.find(".//{*}contents") or root.find("contents")
    if contents is None:
        return benchmarks

    for scap in contents:
        tag = scap.tag.split("}")[-1] if "}" in scap.tag else scap.tag
        if "scap-content" not in tag and tag != "scap-content":
            continue
        content_id = None
        location = None
        for child in scap:
            ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if ctag == "content-id" and child.text:
                content_id = child.text.strip()
            elif ctag == "location" and child.text:
                location = child.text.strip()
        if not content_id or not location:
            continue
        benchmarks_elem = scap.find(".//{*}benchmarks") or scap.find("benchmarks")
        if benchmarks_elem is None:
            continue
        bench = benchmarks_elem.find(".//{*}benchmark") or benchmarks_elem.find("benchmark")
        if bench is None:
            continue
        title = None
        version = None
        for bchild in bench:
            btag = bchild.tag.split("}")[-1] if "}" in bchild.tag else bchild.tag
            if btag == "title" and bchild.text:
                title = bchild.text.strip()
            elif btag == "version" and bchild.text:
                version = bchild.text.strip()
        if title and version:
            benchmarks.append(RepoBenchmark(
                title=title,
                version=version,
                download_url=location,
                content_id=content_id,
            ))
    return benchmarks


def find_repo_benchmark(
    repo_benchmarks: List[RepoBenchmark],
    stig_name: str,
    stig_version: str,
    stig_release: str,
) -> Optional[tuple]:
    """
    Find matching repo benchmark for a loaded STIG.
    Returns (RepoBenchmark, is_newer) or None if no match.
    is_newer: True if repo has newer version (should stay checked for download).
    """
    loaded_norm = _normalize_title_for_match(stig_name)
    loaded_ver = _loaded_version_to_repo_format(stig_version, stig_release)
    loaded_tuple = _parse_version_tuple(loaded_ver) if loaded_ver else None

    best_match = None
    best_score = -1

    for rb in repo_benchmarks:
        repo_norm = _normalize_title_for_match(rb.title)
        if loaded_norm in repo_norm or repo_norm in loaded_norm:
            overlap = len(set(loaded_norm.split()) & set(repo_norm.split()))
            if overlap > best_score:
                best_score = overlap
                best_match = rb

    if best_match is None:
        return None

    repo_tuple = _parse_version_tuple(best_match.version)
    cmp = _version_compare(loaded_tuple, repo_tuple)
    is_newer = cmp == -1
    return (best_match, is_newer)
