"""ChecklistStatus enum for CKL file status values."""

from enum import Enum


class ChecklistStatus(Enum):
    """Status values for checklist vulnerabilities."""
    
    OPEN = "Open"
    NOT_A_FINDING = "NotAFinding"
    NOT_REVIEWED = "Not_Reviewed"
    NOT_APPLICABLE = "Not_Applicable"
    
    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return {
            ChecklistStatus.OPEN: "Open",
            ChecklistStatus.NOT_A_FINDING: "Not a Finding",
            ChecklistStatus.NOT_REVIEWED: "Not Reviewed",
            ChecklistStatus.NOT_APPLICABLE: "Not Applicable",
        }[self]
    
    @classmethod
    def from_ckl_string(cls, value: str):
        """Create from CKL string value."""
        mapping = {
            "Open": cls.OPEN,
            "NotAFinding": cls.NOT_A_FINDING,
            "Not_Reviewed": cls.NOT_REVIEWED,
            "Not_Applicable": cls.NOT_APPLICABLE,
        }
        return mapping.get(value)
    
    @property
    def ckl_string(self) -> str:
        """CKL format string value."""
        return self.value

