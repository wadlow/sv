"""CklFile data model and related structures."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from .checklist_status import ChecklistStatus
from .vuln_code import VulnCode


@dataclass
class CklAsset:
    """Asset information from a CKL file."""
    
    role: str = ""
    asset_type: str = ""
    host_name: str = ""
    host_ip: str = ""
    host_mac: str = ""
    host_fqdn: str = ""
    tech_area: str = ""
    target_key: str = ""
    web_or_database: bool = False
    web_db_site: str = ""
    web_db_instance: str = ""


@dataclass
class CklStigInfo:
    """STIG information from a CKL file."""
    
    stig_id: str
    version: str
    title: str
    release_info: str
    uuid: str
    filename: str
    classification: str = ""
    benchmark_date: str = ""


@dataclass
class CklVuln:
    """Vulnerability from a CKL file with status information."""
    
    id: str  # Combination of vCode and stigID for uniqueness
    v_code: str
    severity: str
    rule_title: str
    discussion: str
    check_text: str
    fix_text: str
    group_title: str
    rule_id: str
    rule_ver: Optional[str]
    status: ChecklistStatus
    finding_details: str
    comments: str
    stig_info: CklStigInfo
    legacy_ids: str = ""
    references: str = ""  # CCI, NIST 800-53, etc.
    
    @classmethod
    def from_vuln_code(cls, vuln_code: VulnCode, stig_info: CklStigInfo, 
                       status: ChecklistStatus = None) -> 'CklVuln':
        """Create CklVuln from VulnCode."""
        if status is None:
            status = ChecklistStatus.NOT_REVIEWED
        
        return cls(
            id=f"{vuln_code.v_code}-{stig_info.stig_id}",
            v_code=vuln_code.v_code,
            severity=vuln_code.severity,
            rule_title=vuln_code.rule_title,
            discussion=vuln_code.discussion,
            check_text=vuln_code.check_text,
            fix_text=vuln_code.fix_text,
            group_title=vuln_code.group_title,
            rule_id=vuln_code.rule_id,
            rule_ver=vuln_code.rule_ver,
            status=status,
            finding_details="",
            comments="",
            stig_info=stig_info,
            legacy_ids="",
            references=getattr(vuln_code, 'references', '') or "",
        )


@dataclass
class CklFile:
    """Represents a CKL checklist file."""
    
    file_path: Path
    file_name: str
    asset: CklAsset
    stigs: List[CklStigInfo] = field(default_factory=list)
    vulns: List[CklVuln] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """Display name for the CKL file."""
        return Path(self.file_name).stem

