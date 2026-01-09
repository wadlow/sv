"""Fake data generator for debug mode."""

from pathlib import Path
from typing import List

from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode, Severity


def generate_fake_stig() -> StigFile:
    """Generate a fake STIG file for testing."""
    fake_vuln_codes = generate_fake_vuln_codes(10)
    
    fake_stig = StigFile(
        file_path=Path("/fake/debug_stig.xml"),
        file_name="DEBUG - Fake STIG (Test Data)",
        stig_name="Fake STIG for Testing",
        stig_version="1.0",
        stig_release="Debug",
        vuln_codes=fake_vuln_codes,
        is_checked=True
    )
    
    return fake_stig


def generate_fake_vuln_codes(count: int = 10) -> List[VulnCode]:
    """Generate fake vulnerability codes for testing."""
    severities = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
    long_titles = [
        "The system must enforce password complexity by requiring that at least one upper-case character be used in all passwords",
        "The information system must automatically terminate a user session after organization-defined conditions or trigger events requiring session disconnect",
        "Applications must not store sensitive information in hidden fields on web forms and must validate all input from client-side scripts",
        "The operating system must implement cryptographic mechanisms to prevent unauthorized disclosure of information at rest on all system components",
        "Network devices must authenticate all SNMP messages using a FIPS 140-2 approved cryptographic hash algorithm with message authentication",
        "Database management systems must maintain the authenticity of communications sessions by guarding against man-in-the-middle attacks",
        "The application must protect the confidentiality and integrity of transmitted information during preparation for transmission",
        "Mobile devices must enforce a minimum password length of 15 characters for user authentication to the device",
        "Web servers must use cryptography to protect the integrity of remote sessions and must use FIPS-validated cryptographic modules",
        "The system must generate audit records containing information that establishes what type of event occurred, when and where it occurred"
    ]
    fake_codes = []
    
    for i in range(1, count + 1):
        severity = severities[i % len(severities)]
        v_code = f"V-{250000 + i:06d}"
        
        vuln_code = VulnCode(
            id=v_code,
            v_code=v_code,
            severity=severity,
            rule_title=long_titles[(i-1) % len(long_titles)],
            discussion=f"This is a detailed discussion for {v_code}. It describes a potential security vulnerability and its implications. "
                      f"The vulnerability could allow an attacker to compromise the confidentiality, integrity, or availability of the system. "
                      f"This requirement is critical for maintaining the security posture of the information system. "
                      f"The severity level is {severity}.",
            check_text=f"To verify compliance with {v_code}, check the following:\n"
                      f"1. Review system configuration files and settings\n"
                      f"2. Interview system administrators about security procedures\n"
                      f"3. Examine audit logs and security documentation\n"
                      f"4. Test the security control implementation\n"
                      f"5. Document findings and any deviations from requirements",
            fix_text=f"To remediate findings for {v_code}, perform the following:\n"
                    f"1. Update system configuration according to STIG requirements\n"
                    f"2. Apply necessary security patches and updates\n"
                    f"3. Configure access controls and authentication mechanisms\n"
                    f"4. Document all changes made to the system\n"
                    f"5. Verify the fix resolves the vulnerability",
            group_title=f"Fake Group {i}",
            rule_id=f"xccdf_org.ssgproject.content_rule_fake_{i}",
            rule_ver="1.0",
            stig_name="Fake STIG for Testing",
            stig_version="1.0",
            stig_release="Debug"
        )
        fake_codes.append(vuln_code)
    
    return fake_codes

