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
        # Use STIG name instead of filename
        display = self.stig_name
        
        # Remove "Security Technical Implementation Guide" and similar variations
        display = display.replace("Security Technical Implementation Guide", "")
        display = display.replace("Technical Implementation Guide", "")
        display = display.replace("Implementation Guide", "")
        display = display.replace("STIG", "")
        
        # Clean up extra whitespace
        display = " ".join(display.split())
        
        return display.strip()

