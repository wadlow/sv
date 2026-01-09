"""StigFile data model."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List
from .vuln_code import VulnCode


@dataclass
class StigFile:
    """Represents a loaded STIG file."""
    
    file_path: Path
    file_name: str
    stig_name: str
    stig_version: str
    stig_release: str
    vuln_codes: List[VulnCode] = field(default_factory=list)
    is_checked: bool = True
    
    @property
    def display_name(self) -> str:
        """Display name for the STIG file."""
        return self.file_name

