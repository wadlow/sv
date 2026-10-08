"""Run check-stigs and compare CKL STIG versions against current releases."""

import re
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.ckl_file import CklFile, CklStigInfo

CHECK_STIGS_SCRIPT = Path("/Users/wadlow/cust/Medweb/check-stigs/check-stigs")
VERSION_RELEASE_RE = re.compile(r"V(\d+)R(\d+)", re.IGNORECASE)
FILENAME_VR_RE = re.compile(r"_V(\d+)R(\d+)_", re.IGNORECASE)
APACHE_COMPONENT_DIR_RE = re.compile(
    r"U_Apache_Server_2-4_Unix_(Server|Site)_V(\d+)R(\d+)_Manual_STIG/"
)
APACHE_SUB_LINE_RE = re.compile(r"^\s+(Server|Site)\s+V(\d+)R(\d+)")


@dataclass(frozen=True)
class VersionRelease:
    version: int
    release: int

    def label(self) -> str:
        return f"V{self.version}R{self.release}"


@dataclass
class StigVersionStatus:
    ckl_version: Optional[VersionRelease]
    current_version: Optional[VersionRelease]
    status: str  # current, out_of_date, unknown


def run_check_stigs(timeout_seconds: int = 300) -> str:
    """Run the check-stigs script and return combined stdout/stderr output."""
    if not CHECK_STIGS_SCRIPT.is_file():
        raise FileNotFoundError(f"check-stigs script not found: {CHECK_STIGS_SCRIPT}")

    result = subprocess.run(
        [str(CHECK_STIGS_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0 and not _parse_version_lines(result.stdout):
        raise RuntimeError(output.strip() or f"check-stigs exited with code {result.returncode}")
    return output


def _parse_version_lines(text: str) -> List[str]:
    lines = []
    for raw in (text or "").splitlines():
        line = re.sub(r"^\[NEWER\]\s*", "", raw.strip())
        if not line or line.startswith("Saved history:"):
            continue
        if "No data found" in line:
            continue
        if re.match(r"^(ASD|CDPSQL16|Apache|RHEL9)\b", line) or APACHE_SUB_LINE_RE.match(line):
            lines.append(line)
    return lines


def parse_check_stigs_output(text: str) -> Dict[str, object]:
    """Parse check-stigs output into current version data keyed by abbreviation."""
    entries: Dict[str, object] = {}
    for raw in (text or "").splitlines():
        line = re.sub(r"^\[NEWER\]\s*", "", raw.rstrip())
        if not line.strip() or line.startswith("Saved history:"):
            continue

        sub_match = APACHE_SUB_LINE_RE.match(line)
        if sub_match:
            component = sub_match.group(1)
            version = VersionRelease(int(sub_match.group(2)), int(sub_match.group(3)))
            apache = entries.setdefault("Apache", {"components": {}})
            if isinstance(apache, dict):
                apache["components"][component] = version
            continue

        parts = line.split()
        if len(parts) < 2:
            continue
        abbrev = parts[0].rstrip(":")
        if abbrev.endswith(":"):
            continue

        version_match = VERSION_RELEASE_RE.search(parts[1])
        if version_match:
            entries[abbrev] = VersionRelease(
                int(version_match.group(1)),
                int(version_match.group(2)),
            )
        elif parts[1] == "-" and abbrev == "Apache":
            entries.setdefault("Apache", {"components": {}})

    return entries


def _classify_ckl_stig(stig: CklStigInfo) -> Tuple[Optional[str], Optional[str]]:
    """Return (check-stigs abbrev, Apache component name)."""
    filename = (stig.filename or "").upper()
    title = (stig.title or "").lower()
    stig_id = (stig.stig_id or "").lower()

    if "RHEL_9" in filename or "red hat enterprise linux 9" in title:
        return "RHEL9", None
    if "ASD" in filename or "application security and development" in title:
        return "ASD", None
    if "PGSQL16" in filename or "POSTGRES_16" in filename or "postgres 16" in title:
        return "CDPSQL16", None
    if "PGSQL" in filename or "postgres" in title:
        return None, None
    if "apache" in title or "apache" in filename:
        if " site" in title or "_site_" in stig_id:
            return "Apache", "Site"
        if " server" in title or "_server_" in stig_id:
            return "Apache", "Server"
        return "Apache", None
    return None, None


def _stig_zip_search_dirs(ckl_file: CklFile) -> List[Path]:
    dirs = [ckl_file.file_path.parent]
    medweb = Path("/Users/wadlow/cust/Medweb")
    for subdir in ("ACAS", "STIGs"):
        base = medweb / subdir
        if not base.is_dir():
            continue
        dirs.append(base)
        for child in base.iterdir():
            if child.is_dir():
                dirs.append(child)
    return dirs


def _find_stig_zip(filename: str, search_dirs: List[Path]) -> Optional[Path]:
    if not filename:
        return None
    name = Path(filename).name
    for directory in search_dirs:
        if not directory.is_dir():
            continue
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def _parse_apache_components_from_zip(zip_path: Path) -> Dict[str, VersionRelease]:
    components: Dict[str, VersionRelease] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            match = APACHE_COMPONENT_DIR_RE.match(member)
            if not match:
                continue
            label = match.group(1)
            if label in components:
                continue
            components[label] = VersionRelease(int(match.group(2)), int(match.group(3)))
    return components


def extract_ckl_version_release(
    stig: CklStigInfo,
    ckl_file: CklFile,
) -> Optional[VersionRelease]:
    """Extract the STIG version/release encoded in a CKL STIG entry."""
    filename = stig.filename or ""
    match = FILENAME_VR_RE.search(filename)
    if match:
        return VersionRelease(int(match.group(1)), int(match.group(2)))

    abbrev, component = _classify_ckl_stig(stig)
    if abbrev != "Apache" or not component:
        return None

    search_dirs = _stig_zip_search_dirs(ckl_file)
    zip_path = _find_stig_zip(filename, search_dirs)
    if not zip_path:
        return None

    components = _parse_apache_components_from_zip(zip_path)
    return components.get(component)


def _current_version_for_stig(
    abbrev: Optional[str],
    component: Optional[str],
    current_entries: Dict[str, object],
) -> Optional[VersionRelease]:
    if not abbrev:
        return None
    entry = current_entries.get(abbrev)
    if isinstance(entry, VersionRelease):
        return entry
    if isinstance(entry, dict) and abbrev == "Apache":
        components = entry.get("components") or {}
        if component and component in components:
            value = components[component]
            if isinstance(value, VersionRelease):
                return value
    return None


def evaluate_stig_version(
    stig: CklStigInfo,
    ckl_file: CklFile,
    current_entries: Dict[str, object],
) -> StigVersionStatus:
    """Compare one CKL STIG against parsed check-stigs output."""
    abbrev, component = _classify_ckl_stig(stig)
    ckl_version = extract_ckl_version_release(stig, ckl_file)
    current_version = _current_version_for_stig(abbrev, component, current_entries)

    if ckl_version is None or current_version is None:
        return StigVersionStatus(ckl_version, current_version, "unknown")

    if (ckl_version.version, ckl_version.release) >= (
        current_version.version,
        current_version.release,
    ):
        return StigVersionStatus(ckl_version, current_version, "current")
    return StigVersionStatus(ckl_version, current_version, "out_of_date")


def evaluate_ckl_stigs(
    ckl_file: CklFile,
    current_entries: Dict[str, object],
) -> List[StigVersionStatus]:
    return [
        evaluate_stig_version(stig, ckl_file, current_entries)
        for stig in ckl_file.stigs
    ]


def status_label(status: str) -> str:
    if status == "current":
        return "[current]"
    if status == "out_of_date":
        return "[OUT OF DATE]"
    return "[UNKNOWN]"
