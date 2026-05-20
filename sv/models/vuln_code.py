"""VulnCode data model for vulnerability codes."""

from dataclasses import dataclass
from typing import Optional


class Severity:
    """Severity levels for vulnerabilities."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    
    @classmethod
    def from_string(cls, value: str):
        """Create from string value."""
        value_lower = value.lower() if value else "medium"
        if value_lower in [cls.LOW, cls.MEDIUM, cls.HIGH, cls.CRITICAL]:
            return value_lower
        return cls.MEDIUM  # Default
    
    @classmethod
    def display_name(cls, severity: str) -> str:
        """Human-readable display name."""
        return severity.capitalize()
    
    @classmethod
    def to_cat_format(cls, severity: str) -> str:
        """Convert severity to official STIGViewer CAT format (CAT I, CAT II, CAT III)."""
        value_lower = (severity or "").lower()
        if value_lower in (cls.HIGH, cls.CRITICAL):
            return "CAT I"
        if value_lower == cls.MEDIUM:
            return "CAT II"
        if value_lower == cls.LOW:
            return "CAT III"
        return "CAT II"  # Default for unknown


@dataclass
class VulnCode:
    """Represents a vulnerability code from a STIG file."""
    
    id: str  # V-code identifier
    v_code: str  # e.g., "V-214277"
    severity: str  # low, medium, high, critical
    rule_title: str
    discussion: str
    check_text: str
    fix_text: str
    group_title: str
    rule_id: str
    rule_ver: Optional[str]
    stig_name: str
    stig_version: str
    stig_release: str
    references: str = ""        # Non-CCI references (IAControls, NIST 800-53, etc.)
    cci_ref: str = ""           # Newline-separated CCI identifiers (e.g. "CCI-000001\nCCI-000002")
    check_content_ref: str = "" # Check content reference name (e.g. "M")
    classification: str = ""    # Classification class (e.g. "Unclass")
    legacy_id: str = ""         # Newline-separated legacy vulnerability identifiers
    stig_ref: str = ""          # Full STIG reference string
    stig_uuid: str = ""         # STIG unique identifier
    target_key: str = ""        # Numeric target key from description XML
    weight: str = ""            # Finding weight value from Rule element
    
    def __hash__(self):
        """Make hashable for use in sets/dicts."""
        return hash(self.id)
    
    def __eq__(self, other):
        """Equality comparison."""
        if not isinstance(other, VulnCode):
            return False
        return self.id == other.id

