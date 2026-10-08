"""CKLB file writer for creating new checklist files (STIG Viewer 3 JSON format)."""

import json
import uuid
from pathlib import Path
from typing import List

from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode
from ..models.ckl_file import CklFile, CklStigInfo, CklVuln
from ..models.checklist_status import ChecklistStatus


# Map ChecklistStatus back to the cklb status string.
_STATUS_TO_CKLB = {
    ChecklistStatus.NOT_REVIEWED: "not_reviewed",
    ChecklistStatus.OPEN: "open",
    ChecklistStatus.NOT_A_FINDING: "not_a_finding",
    ChecklistStatus.NOT_APPLICABLE: "not_applicable",
}


class CklbWriter:
    """Writer for creating .cklb checklist files (JSON, cklb_version 1.0)."""

    @staticmethod
    def create_from_stigs(file_path: Path, stig_files: List[StigFile]) -> dict:
        """
        Create a new .cklb file from selected STIG files.

        Args:
            file_path: Path where the .cklb file will be saved
            stig_files: List of StigFile objects to include

        Returns:
            The dict representing the created checklist (as written to disk).
        """
        stigs = [CklbWriter._build_stig(stig_file) for stig_file in stig_files]

        checklist = {
            "title": file_path.stem or "New Checklist",
            "id": str(uuid.uuid4()),
            "stigs": stigs,
            "active": True,
            "mode": 1,
            "has_path": False,
            "target_data": CklbWriter._default_target_data(),
            "cklb_version": "1.0",
        }

        CklbWriter.write(file_path, checklist)
        return checklist

    @staticmethod
    def create_from_ckl_file(file_path: Path, ckl_file: CklFile) -> dict:
        """
        Write an opened/loaded CklFile out as a .cklb file, preserving status,
        finding details, and comments. Used for Save as CKLB (including CKL->CKLB
        conversion and CKLB round-tripping).
        """
        # Group vulns by stig_id so each stig entry gets its own rules.
        vulns_by_stig = {}
        for vuln in ckl_file.vulns:
            vulns_by_stig.setdefault(vuln.stig_info.stig_id, []).append(vuln)

        stigs = [
            CklbWriter._build_stig_from_ckl(stig_info, vulns_by_stig.get(stig_info.stig_id, []))
            for stig_info in ckl_file.stigs
        ]

        checklist = {
            "title": file_path.stem or "New Checklist",
            "id": str(uuid.uuid4()),
            "stigs": stigs,
            "active": True,
            "mode": 1,
            "has_path": False,
            "target_data": CklbWriter._target_data_from_asset(ckl_file.asset),
            "cklb_version": "1.0",
        }

        CklbWriter.write(file_path, checklist)
        return checklist

    @staticmethod
    def _target_data_from_asset(asset) -> dict:
        """Build a cklb target_data block from a CklAsset."""
        return {
            "target_type": asset.asset_type or "Computing",
            "host_name": asset.host_name or "",
            "ip_address": asset.host_ip or "",
            "mac_address": asset.host_mac or "",
            "fqdn": asset.host_fqdn or "",
            "comments": "",
            "role": asset.role or "None",
            "is_web_database": bool(asset.web_or_database),
            "technology_area": asset.tech_area or "",
            "web_db_site": asset.web_db_site or "",
            "web_db_instance": asset.web_db_instance or "",
            "classification": None,
        }

    @staticmethod
    def _build_stig_from_ckl(stig_info: CklStigInfo, vulns: List[CklVuln]) -> dict:
        """Build a single cklb stig entry from a CklStigInfo and its CklVulns."""
        stig_uuid = stig_info.uuid or str(uuid.uuid4())

        # CklStigInfo.release_info is normalized to the short "RX" form; rebuild
        # the cklb "Release: X [Benchmark Date: ...]" string.
        release_value = (stig_info.release_info or "").strip()
        if release_value.upper().startswith("R") and release_value[1:].isdigit():
            release_num = release_value[1:]
        else:
            release_num = release_value
        release_info = f"Release: {release_num}" if release_num else "Release: Unknown"
        if stig_info.benchmark_date:
            release_info = f"{release_info} Benchmark Date: {stig_info.benchmark_date}"

        # Derive a display_name by stripping the common STIG title boilerplate.
        display_name = stig_info.title or ""
        for phrase in ("Security Technical Implementation Guide",
                       "Technical Implementation Guide", "Implementation Guide", "STIG"):
            display_name = display_name.replace(phrase, "")
        display_name = " ".join(display_name.split()).strip()

        rules = [
            CklbWriter._build_rule_from_ckl(vuln, stig_info, stig_uuid)
            for vuln in vulns
        ]

        return {
            "stig_name": stig_info.title or "",
            "display_name": display_name,
            "stig_id": stig_info.stig_id or "",
            "release_info": release_info,
            "version": str(stig_info.version or ""),
            "uuid": stig_uuid,
            "reference_identifier": "",
            "size": len(rules),
            "rules": rules,
        }

    @staticmethod
    def _build_rule_from_ckl(vuln: CklVuln, stig_info: CklStigInfo, stig_uuid: str) -> dict:
        """Build a single cklb rule entry from a CklVuln."""
        severity = (vuln.severity or "medium").lower()
        if severity == "critical":
            severity = "high"

        ccis = [line.strip() for line in (vuln.cci_ref or "").splitlines() if line.strip()]
        legacy_ids = [line.strip() for line in (vuln.legacy_id or "").splitlines() if line.strip()]

        rule_id_full = vuln.rule_id or ""
        if rule_id_full.endswith("_rule"):
            rule_id_src = rule_id_full
            rule_id = rule_id_full[:-len("_rule")]
        else:
            rule_id = rule_id_full
            rule_id_src = f"{rule_id_full}_rule" if rule_id_full else ""

        # CklVuln.group_title holds the SRG identifier.
        srg_id = vuln.group_title or ""

        status = _STATUS_TO_CKLB.get(vuln.status, "not_reviewed")

        return {
            "group_id_src": vuln.v_code,
            "group_tree": [
                {
                    "id": vuln.v_code,
                    "title": srg_id,
                    "description": "<GroupDescription></GroupDescription>",
                }
            ],
            "group_id": vuln.v_code,
            "severity": severity,
            "group_title": vuln.rule_title or "",
            "rule_id_src": rule_id_src,
            "rule_id": rule_id,
            "rule_version": vuln.rule_ver or "",
            "rule_title": vuln.rule_title or "",
            "fix_text": vuln.fix_text or "",
            "weight": vuln.weight or "10.0",
            "check_content": vuln.check_text or "",
            "check_content_ref": {
                "href": stig_info.filename or "",
                "name": vuln.check_content_ref or "M",
            },
            "classification": vuln.classification or "Unclassified",
            "discussion": vuln.discussion or "",
            "false_positives": "",
            "false_negatives": "",
            "documentable": "false",
            "security_override_guidance": "",
            "potential_impacts": "",
            "third_party_tools": "",
            "ia_controls": vuln.references or "",
            "responsibility": "",
            "mitigations": "",
            "mitigation_control": "",
            "legacy_ids": legacy_ids,
            "ccis": ccis,
            "reference_identifier": "",
            "uuid": str(uuid.uuid4()),
            "stig_uuid": stig_uuid,
            "status": status,
            "overrides": {},
            "comments": vuln.comments or "",
            "finding_details": vuln.finding_details or "",
            "srg_id": srg_id,
        }

    @staticmethod
    def _default_target_data() -> dict:
        """Return an empty target_data block matching the standard cklb template."""
        return {
            "target_type": "Computing",
            "host_name": "",
            "ip_address": "",
            "mac_address": "",
            "fqdn": "",
            "comments": "",
            "role": "None",
            "is_web_database": False,
            "technology_area": "",
            "web_db_site": "",
            "web_db_instance": "",
            "classification": None,
        }

    @staticmethod
    def _build_stig(stig_file: StigFile) -> dict:
        """Build a single stig entry (with its rules) from a StigFile."""
        stig_uuid = str(uuid.uuid4())

        release_str = stig_file.stig_release or ""
        if release_str.upper().startswith("R") and len(release_str) > 1:
            release_num = release_str[1:]
        else:
            release_num = release_str
        release_info = f"Release: {release_num}" if release_num else "Release: Unknown"

        stig_id = stig_file.stig_name.replace(" ", "_")

        rules = [
            CklbWriter._build_rule(vuln_code, stig_file, stig_uuid)
            for vuln_code in stig_file.vuln_codes
        ]

        return {
            "stig_name": stig_file.stig_name,
            "display_name": stig_file.display_name,
            "stig_id": stig_id,
            "release_info": release_info,
            "version": stig_file.stig_version or "",
            "uuid": stig_uuid,
            "reference_identifier": "",
            "size": len(rules),
            "rules": rules,
        }

    @staticmethod
    def _build_rule(vuln: VulnCode, stig_file: StigFile, stig_uuid: str) -> dict:
        """Build a single rule entry from a VulnCode."""
        severity = (vuln.severity or "medium").lower()
        if severity == "critical":
            severity = "high"

        ccis = [line.strip() for line in (vuln.cci_ref or "").splitlines() if line.strip()]
        legacy_ids = [line.strip() for line in (vuln.legacy_id or "").splitlines() if line.strip()]

        # VulnCode.rule_id carries the "_rule" suffix (e.g. "SV-...r..._rule").
        # cklb uses that full form for rule_id_src and the stripped form for rule_id.
        rule_id_src = vuln.rule_id or ""
        rule_id = rule_id_src[:-len("_rule")] if rule_id_src.endswith("_rule") else rule_id_src

        # VulnCode.group_title holds the SRG identifier (e.g. "SRG-OS-000480-GPOS-00227");
        # in cklb that value belongs in srg_id and group_tree title, while cklb's
        # group_title mirrors the human-readable rule title.
        srg_id = vuln.group_title or ""

        return {
            "group_id_src": vuln.v_code,
            "group_tree": [
                {
                    "id": vuln.v_code,
                    "title": srg_id,
                    "description": "<GroupDescription></GroupDescription>",
                }
            ],
            "group_id": vuln.v_code,
            "severity": severity,
            "group_title": vuln.rule_title or "",
            "rule_id_src": rule_id_src,
            "rule_id": rule_id,
            "rule_version": vuln.rule_ver or "",
            "rule_title": vuln.rule_title or "",
            "fix_text": vuln.fix_text or "",
            "weight": vuln.weight or "10.0",
            "check_content": vuln.check_text or "",
            "check_content_ref": {
                "href": stig_file.file_name or "",
                "name": vuln.check_content_ref or "M",
            },
            "classification": vuln.classification or "Unclassified",
            "discussion": vuln.discussion or "",
            "false_positives": "",
            "false_negatives": "",
            "documentable": "false",
            "security_override_guidance": "",
            "potential_impacts": "",
            "third_party_tools": "",
            "ia_controls": "",
            "responsibility": "",
            "mitigations": "",
            "mitigation_control": "",
            "legacy_ids": legacy_ids,
            "ccis": ccis,
            "reference_identifier": "",
            "uuid": str(uuid.uuid4()),
            "stig_uuid": stig_uuid,
            "status": "not_reviewed",
            "overrides": {},
            "comments": "",
            "finding_details": "",
            "srg_id": srg_id,
        }

    @staticmethod
    def write(file_path: Path, checklist: dict):
        """Write the checklist dict to disk as JSON."""
        try:
            # Match STIG Viewer's minified output (no inter-token whitespace).
            with open(file_path, "w", encoding="UTF-8") as f:
                json.dump(checklist, f, separators=(",", ":"))
        except PermissionError:
            raise Exception(f"Permission denied: cannot write to {file_path}")
        except Exception as e:
            raise Exception(f"Error writing CKLB file: {e}")
