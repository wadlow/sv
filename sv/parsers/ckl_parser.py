"""CKL file parser for checklist XML format."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from ..models.ckl_file import CklFile, CklAsset, CklStigInfo, CklVuln
from ..models.checklist_status import ChecklistStatus
from ..models.vuln_code import Severity


class CklParserError(Exception):
    """Error parsing CKL file."""
    pass


class CklParser:
    """Parser for CKL checklist files."""
    
    @staticmethod
    def _ns_tag(tag: str, namespace: str) -> str:
        """Return namespace-qualified tag if namespace is present."""
        if namespace:
            return f"{{{namespace}}}{tag}"
        return tag
    
    @staticmethod
    def parse(file_path: Path) -> CklFile:
        """
        Parse a CKL file.
        
        Args:
            file_path: Path to the CKL file
            
        Returns:
            CklFile object
            
        Raises:
            CklParserError: If parsing fails
        """
        file_name = file_path.name
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract namespace if present
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag[1:root.tag.index('}')]
                print(f"CklParser: Detected namespace: {namespace}")  # Debug
            
        except ET.ParseError as e:
            raise CklParserError(f"XML parse error: {e}")
        except FileNotFoundError:
            raise CklParserError(f"File not found: {file_path}")
        except PermissionError:
            raise CklParserError(f"Permission denied: {file_path}")
        except Exception as e:
            raise CklParserError(f"Cannot read CKL file: {e}")
        
        # Parse ASSET
        asset = CklParser._parse_asset(root, namespace)
        
        # Parse STIGS
        stigs = CklParser._parse_stigs(root, namespace)
        
        # Parse VULNs
        vulns = CklParser._parse_vulns(root, stigs, namespace)
        
        return CklFile(
            file_path=file_path,
            file_name=file_name,
            asset=asset,
            stigs=stigs,
            vulns=vulns,
        )
    
    @staticmethod
    def _parse_asset(root: ET.Element, namespace: str = '') -> CklAsset:
        """Parse ASSET element."""
        asset = CklAsset()
        
        asset_elem = root.find(CklParser._ns_tag('ASSET', namespace))
        if asset_elem is None:
            return asset
        
        for child in asset_elem:
            # Strip namespace from tag for comparison
            tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
            text = (child.text or "").strip()
            
            if tag == 'ROLE':
                asset.role = text
            elif tag == 'ASSET_TYPE':
                asset.asset_type = text
            elif tag == 'HOST_NAME':
                asset.host_name = text
            elif tag == 'HOST_IP':
                asset.host_ip = text
            elif tag == 'HOST_MAC':
                asset.host_mac = text
            elif tag == 'HOST_FQDN':
                asset.host_fqdn = text
            elif tag == 'TECH_AREA':
                asset.tech_area = text
            elif tag == 'TARGET_KEY':
                asset.target_key = text
            elif tag == 'WEB_OR_DATABASE':
                asset.web_or_database = text.lower() == "true"
            elif tag == 'WEB_DB_SITE':
                asset.web_db_site = text
            elif tag == 'WEB_DB_INSTANCE':
                asset.web_db_instance = text
        
        return asset
    
    @staticmethod
    def _parse_stigs(root: ET.Element, namespace: str = '') -> list[CklStigInfo]:
        """Parse STIGS section."""
        stigs = []
        stigs_elem = root.find(CklParser._ns_tag('STIGS', namespace))
        if stigs_elem is None:
            return stigs
        
        for istig in stigs_elem.findall(CklParser._ns_tag('iSTIG', namespace)):
            stig_info_elem = istig.find(CklParser._ns_tag('STIG_INFO', namespace))
            if stig_info_elem is None:
                continue
            
            # Parse SI_DATA pairs
            stig_data = {}
            last_sid_name = None
            
            for si_data in stig_info_elem.findall(CklParser._ns_tag('SI_DATA', namespace)):
                sid_name_elem = si_data.find(CklParser._ns_tag('SID_NAME', namespace))
                sid_data_elem = si_data.find(CklParser._ns_tag('SID_DATA', namespace))
                
                if sid_name_elem is not None and sid_data_elem is not None:
                    sid_name = (sid_name_elem.text or "").strip()
                    sid_data = (sid_data_elem.text or "").strip()
                    stig_data[sid_name] = sid_data
            
            # Build CklStigInfo
            stig_id = stig_data.get('stigid', '')
            version = stig_data.get('version', 'Unknown')
            title = stig_data.get('title', '')
            raw_release_info = stig_data.get('releaseinfo', '')
            release_info = raw_release_info
            
            # Extract benchmark date (e.g., "01 Oct 2025" from "Release: 4 Benchmark Date: 01 Oct 2025")
            benchmark_date = ''
            benchmark_match = re.search(r'Benchmark Date:\s*(.+)', raw_release_info, re.IGNORECASE)
            if benchmark_match:
                benchmark_date = benchmark_match.group(1).strip()
            
            classification = stig_data.get('classification', '') or stig_data.get('Classification', '') or 'Unclass'
            
            # Parse release_info to extract just the release number in "RX" format
            # Format can be: "Release: 6", "Release: R6", "Release: Unknown", or just "R6"
            if release_info:
                if release_info.startswith('Release: '):
                    # Strip "Release: " prefix
                    release_value = release_info[9:].strip()
                    
                    # If it's "Unknown", set to empty
                    if release_value.upper() == 'UNKNOWN':
                        release_info = ''
                    # If it's just a number, add "R" prefix
                    elif release_value.isdigit():
                        release_info = f"R{release_value}"
                    # If it already has "R" prefix (e.g., "R6"), keep it
                    elif release_value.upper().startswith('R') and release_value[1:].isdigit():
                        release_info = release_value.upper()
                    else:
                        # Unknown format, keep as-is
                        release_info = release_value
                # If no "Release: " prefix, assume it's already in correct format (e.g., "R6")
                elif not release_info.upper().startswith('R'):
                    # If it's just a number, add "R" prefix
                    if release_info.isdigit():
                        release_info = f"R{release_info}"
            
            uuid = stig_data.get('uuid', '')
            filename = stig_data.get('filename', '')
            
            if stig_id:
                stig_info = CklStigInfo(
                    stig_id=stig_id,
                    version=version,
                    title=title,
                    release_info=release_info,
                    uuid=uuid,
                    filename=filename,
                    classification=classification or 'Unclass',
                    benchmark_date=benchmark_date,
                )
                stigs.append(stig_info)
        
        return stigs
    
    @staticmethod
    def _parse_vulns(root: ET.Element, stigs: list[CklStigInfo], namespace: str = '') -> list[CklVuln]:
        """Parse VULN elements."""
        vulns = []
        stigs_elem = root.find(CklParser._ns_tag('STIGS', namespace))
        if stigs_elem is None:
            return vulns
        
        # Map stig_id to CklStigInfo
        stig_map = {stig.stig_id: stig for stig in stigs}
        
        for istig in stigs_elem.findall(CklParser._ns_tag('iSTIG', namespace)):
            stig_info_elem = istig.find(CklParser._ns_tag('STIG_INFO', namespace))
            if stig_info_elem is None:
                continue
            
            # Get STIG ID for this iSTIG
            stig_id = None
            for si_data in stig_info_elem.findall(CklParser._ns_tag('SI_DATA', namespace)):
                sid_name_elem = si_data.find(CklParser._ns_tag('SID_NAME', namespace))
                sid_data_elem = si_data.find(CklParser._ns_tag('SID_DATA', namespace))
                if sid_name_elem is not None and sid_data_elem is not None:
                    if (sid_name_elem.text or "").strip() == 'stigid':
                        stig_id = (sid_data_elem.text or "").strip()
                        break
            
            if not stig_id or stig_id not in stig_map:
                continue
            
            stig_info = stig_map[stig_id]
            
            # Parse VULN elements
            for vuln_elem in istig.findall(CklParser._ns_tag('VULN', namespace)):
                vuln_data = {}
                last_vuln_attribute = None
                
                # Parse STIG_DATA pairs
                for stig_data in vuln_elem.findall(CklParser._ns_tag('STIG_DATA', namespace)):
                    vuln_attr_elem = stig_data.find(CklParser._ns_tag('VULN_ATTRIBUTE', namespace))
                    attr_data_elem = stig_data.find(CklParser._ns_tag('ATTRIBUTE_DATA', namespace))
                    
                    if vuln_attr_elem is not None and attr_data_elem is not None:
                        attr_name = (vuln_attr_elem.text or "").strip()
                        attr_data = (attr_data_elem.text or "").strip()
                        vuln_data[attr_name] = attr_data
                
                # Extract status
                status_elem = vuln_elem.find(CklParser._ns_tag('STATUS', namespace))
                status_text = (status_elem.text or "").strip() if status_elem is not None else ""
                status = ChecklistStatus.from_ckl_string(status_text) or ChecklistStatus.NOT_REVIEWED
                
                # Extract finding details and comments
                finding_details_elem = vuln_elem.find(CklParser._ns_tag('FINDING_DETAILS', namespace))
                finding_details = (finding_details_elem.text or "").strip() if finding_details_elem is not None else ""
                
                comments_elem = vuln_elem.find(CklParser._ns_tag('COMMENTS', namespace))
                comments = (comments_elem.text or "").strip() if comments_elem is not None else ""
                
                # Build CklVuln
                v_code = vuln_data.get('Vuln_Num', '')
                if not v_code:
                    continue
                
                severity_str = vuln_data.get('Severity', 'medium')
                severity = Severity.from_string(severity_str)
                
                # Extract legacy IDs (various attribute names used in CKL format)
                legacy_ids = (
                    vuln_data.get('Legacy_IDs', '') or
                    vuln_data.get('Legacy_ID', '') or
                    vuln_data.get('Legacy', '') or
                    vuln_data.get('Identifiers', '') or
                    ''
                )
                
                # Extract references (CCI, NIST 800-53) from IA_Controls or References
                references = (
                    vuln_data.get('IA_Controls', '') or
                    vuln_data.get('References', '') or
                    vuln_data.get('IAControls', '') or
                    ''
                )
                
                vuln = CklVuln(
                    id=f"{v_code}-{stig_id}",
                    v_code=v_code,
                    severity=severity,
                    rule_title=vuln_data.get('Rule_Title', ''),
                    discussion=vuln_data.get('Vuln_Discuss', ''),
                    check_text=vuln_data.get('Check_Content', ''),
                    fix_text=vuln_data.get('Fix_Text', ''),
                    group_title=vuln_data.get('Group_Title', ''),
                    rule_id=vuln_data.get('Rule_ID', ''),
                    rule_ver=vuln_data.get('Rule_Ver'),
                    status=status,
                    finding_details=finding_details,
                    comments=comments,
                    stig_info=stig_info,
                    legacy_ids=legacy_ids,
                    references=references,
                )
                vulns.append(vuln)
        
        return vulns

