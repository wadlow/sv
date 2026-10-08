"""CKLB file parser for checklist JSON format (STIG Viewer 3, cklb_version 1.0)."""

import json
import re
from pathlib import Path

from ..models.ckl_file import CklFile, CklAsset, CklStigInfo, CklVuln
from ..models.checklist_status import ChecklistStatus
from ..models.vuln_code import Severity


class CklbParserError(Exception):
    """Error parsing CKLB file."""
    pass


# Map cklb status strings to ChecklistStatus.
_STATUS_MAP = {
    "not_reviewed": ChecklistStatus.NOT_REVIEWED,
    "open": ChecklistStatus.OPEN,
    "not_a_finding": ChecklistStatus.NOT_A_FINDING,
    "not_applicable": ChecklistStatus.NOT_APPLICABLE,
}


class CklbParser:
    """Parser for .cklb checklist files (JSON)."""

    @staticmethod
    def parse(file_path: Path) -> CklFile:
        """
        Parse a .cklb file into a CklFile.

        Args:
            file_path: Path to the .cklb file

        Returns:
            CklFile object

        Raises:
            CklbParserError: If parsing fails
        """
        file_name = file_path.name

        try:
            with open(file_path, "r", encoding="UTF-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CklbParserError(f"JSON parse error: {e}")
        except FileNotFoundError:
            raise CklbParserError(f"File not found: {file_path}")
        except PermissionError:
            raise CklbParserError(f"Permission denied: {file_path}")
        except Exception as e:
            raise CklbParserError(f"Cannot read CKLB file: {e}")

        if not isinstance(data, dict):
            raise CklbParserError("Unexpected CKLB structure: top level is not an object")

        asset = CklbParser._parse_asset(data.get("target_data") or {})

        stigs = []
        vulns = []
        for stig in data.get("stigs", []):
            stig_info = CklbParser._build_stig_info(stig)
            stigs.append(stig_info)
            for rule in stig.get("rules", []):
                vulns.append(CklbParser._build_vuln(rule, stig_info))

        return CklFile(
            file_path=file_path,
            file_name=file_name,
            asset=asset,
            stigs=stigs,
            vulns=vulns,
            file_format="cklb",
        )

    @staticmethod
    def _parse_asset(target_data: dict) -> CklAsset:
        """Build a CklAsset from the cklb target_data block."""
        return CklAsset(
            role=target_data.get("role", "") or "",
            asset_type=target_data.get("target_type", "") or "",
            host_name=target_data.get("host_name", "") or "",
            host_ip=target_data.get("ip_address", "") or "",
            host_mac=target_data.get("mac_address", "") or "",
            host_fqdn=target_data.get("fqdn", "") or "",
            tech_area=target_data.get("technology_area", "") or "",
            target_key="",
            web_or_database=bool(target_data.get("is_web_database", False)),
            web_db_site=target_data.get("web_db_site", "") or "",
            web_db_instance=target_data.get("web_db_instance", "") or "",
        )

    @staticmethod
    def _normalize_release_info(raw_release_info: str) -> str:
        """Convert a cklb release_info string into the app's 'RX' short form."""
        release_info = raw_release_info or ""
        match = re.search(r"Release:\s*([^\s]+)", release_info, re.IGNORECASE)
        if not match:
            return ""
        release_value = match.group(1).strip()
        if release_value.upper() == "UNKNOWN":
            return ""
        if release_value.isdigit():
            return f"R{release_value}"
        if release_value.upper().startswith("R") and release_value[1:].isdigit():
            return release_value.upper()
        return release_value

    @staticmethod
    def _build_stig_info(stig: dict) -> CklStigInfo:
        """Build a CklStigInfo from a cklb stig entry."""
        raw_release_info = stig.get("release_info", "") or ""

        benchmark_date = ""
        bm = re.search(r"Benchmark Date:\s*(.+)", raw_release_info, re.IGNORECASE)
        if bm:
            benchmark_date = bm.group(1).strip()

        # cklb has no stig-level filename; fall back to a rule's check_content_ref href.
        filename = ""
        rules = stig.get("rules") or []
        if rules:
            ccr = rules[0].get("check_content_ref")
            if isinstance(ccr, dict):
                filename = ccr.get("href", "") or ""
            classification = rules[0].get("classification", "") or ""
        else:
            classification = ""

        return CklStigInfo(
            stig_id=stig.get("stig_id", "") or "",
            version=str(stig.get("version", "") or "Unknown"),
            title=stig.get("stig_name", "") or stig.get("display_name", "") or "",
            release_info=CklbParser._normalize_release_info(raw_release_info),
            uuid=stig.get("uuid", "") or "",
            filename=filename,
            classification=classification or "Unclass",
            benchmark_date=benchmark_date,
        )

    @staticmethod
    def _build_vuln(rule: dict, stig_info: CklStigInfo) -> CklVuln:
        """Build a CklVuln from a cklb rule entry."""
        v_code = rule.get("group_id", "") or rule.get("group_id_src", "") or ""

        status = _STATUS_MAP.get(
            (rule.get("status") or "").lower(), ChecklistStatus.NOT_REVIEWED
        )

        ccr = rule.get("check_content_ref")
        check_content_ref = ccr.get("name", "") if isinstance(ccr, dict) else (ccr or "")

        ccis = rule.get("ccis") or []
        legacy_ids = rule.get("legacy_ids") or []

        # In the app model, group_title carries the SRG identifier (as with the XML
        # parser). cklb stores the SRG separately in srg_id, with group_title holding
        # the human-readable rule title.
        group_title = rule.get("srg_id", "") or rule.get("group_title", "") or ""

        return CklVuln(
            id=f"{v_code}-{stig_info.stig_id}",
            v_code=v_code,
            severity=Severity.from_string(rule.get("severity", "medium")),
            rule_title=rule.get("rule_title", "") or "",
            discussion=rule.get("discussion", "") or "",
            check_text=rule.get("check_content", "") or "",
            fix_text=rule.get("fix_text", "") or "",
            group_title=group_title,
            rule_id=rule.get("rule_id", "") or "",
            rule_ver=rule.get("rule_version", "") or "",
            status=status,
            finding_details=rule.get("finding_details", "") or "",
            comments=rule.get("comments", "") or "",
            stig_info=stig_info,
            legacy_ids="\n".join(legacy_ids),
            references=rule.get("ia_controls", "") or "",
            cci_ref="\n".join(ccis),
            check_content_ref=check_content_ref,
            classification=rule.get("classification", "") or "",
            legacy_id="\n".join(legacy_ids),
            stig_ref="",
            stig_uuid=rule.get("stig_uuid", "") or "",
            target_key="",
            weight=rule.get("weight", "") or "",
        )
