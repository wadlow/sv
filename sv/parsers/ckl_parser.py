"""CKL file parser for checklist XML format."""

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
        except ET.ParseError as e:
            raise CklParserError(f"XML parse error: {e}")
        except FileNotFoundError:
            raise CklParserError(f"File not found: {file_path}")
        except PermissionError:
            raise CklParserError(f"Permission denied: {file_path}")
        except Exception as e:
            raise CklParserError(f"Cannot read CKL file: {e}")
        
        # Parse ASSET
        asset = CklParser._parse_asset(root)
        
        # Parse STIGS
        stigs = CklParser._parse_stigs(root)
        
        # Parse VULNs
        vulns = CklParser._parse_vulns(root, stigs)
        
        return CklFile(
            file_path=file_path,
            file_name=file_name,
            asset=asset,
            stigs=stigs,
            vulns=vulns,
        )
    
    @staticmethod
    def _parse_asset(root: ET.Element) -> CklAsset:
        """Parse ASSET element."""
        asset = CklAsset()
        
        asset_elem = root.find('ASSET')
        if asset_elem is None:
            return asset
        
        for child in asset_elem:
            tag = child.tag
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
    def _parse_stigs(root: ET.Element) -> list[CklStigInfo]:
        """Parse STIGS section."""
        stigs = []
        stigs_elem = root.find('STIGS')
        if stigs_elem is None:
            return stigs
        
        for istig in stigs_elem.findall('iSTIG'):
            stig_info_elem = istig.find('STIG_INFO')
            if stig_info_elem is None:
                continue
            
            # Parse SI_DATA pairs
            stig_data = {}
            last_sid_name = None
            
            for si_data in stig_info_elem.findall('SI_DATA'):
                sid_name_elem = si_data.find('SID_NAME')
                sid_data_elem = si_data.find('SID_DATA')
                
                if sid_name_elem is not None and sid_data_elem is not None:
                    sid_name = (sid_name_elem.text or "").strip()
                    sid_data = (sid_data_elem.text or "").strip()
                    stig_data[sid_name] = sid_data
            
            # Build CklStigInfo
            stig_id = stig_data.get('stigid', '')
            version = stig_data.get('version', 'Unknown')
            title = stig_data.get('title', '')
            release_info = stig_data.get('releaseinfo', '')
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
                )
                stigs.append(stig_info)
        
        return stigs
    
    @staticmethod
    def _parse_vulns(root: ET.Element, stigs: list[CklStigInfo]) -> list[CklVuln]:
        """Parse VULN elements."""
        vulns = []
        stigs_elem = root.find('STIGS')
        if stigs_elem is None:
            return vulns
        
        # Map stig_id to CklStigInfo
        stig_map = {stig.stig_id: stig for stig in stigs}
        
        for istig in stigs_elem.findall('iSTIG'):
            stig_info_elem = istig.find('STIG_INFO')
            if stig_info_elem is None:
                continue
            
            # Get STIG ID for this iSTIG
            stig_id = None
            for si_data in stig_info_elem.findall('SI_DATA'):
                sid_name_elem = si_data.find('SID_NAME')
                sid_data_elem = si_data.find('SID_DATA')
                if sid_name_elem is not None and sid_data_elem is not None:
                    if (sid_name_elem.text or "").strip() == 'stigid':
                        stig_id = (sid_data_elem.text or "").strip()
                        break
            
            if not stig_id or stig_id not in stig_map:
                continue
            
            stig_info = stig_map[stig_id]
            
            # Parse VULN elements
            for vuln_elem in istig.findall('VULN'):
                vuln_data = {}
                last_vuln_attribute = None
                
                # Parse STIG_DATA pairs
                for stig_data in vuln_elem.findall('STIG_DATA'):
                    vuln_attr_elem = stig_data.find('VULN_ATTRIBUTE')
                    attr_data_elem = stig_data.find('ATTRIBUTE_DATA')
                    
                    if vuln_attr_elem is not None and attr_data_elem is not None:
                        attr_name = (vuln_attr_elem.text or "").strip()
                        attr_data = (attr_data_elem.text or "").strip()
                        vuln_data[attr_name] = attr_data
                
                # Extract status
                status_elem = vuln_elem.find('STATUS')
                status_text = (status_elem.text or "").strip() if status_elem is not None else ""
                status = ChecklistStatus.from_ckl_string(status_text) or ChecklistStatus.NOT_REVIEWED
                
                # Extract finding details and comments
                finding_details_elem = vuln_elem.find('FINDING_DETAILS')
                finding_details = (finding_details_elem.text or "").strip() if finding_details_elem is not None else ""
                
                comments_elem = vuln_elem.find('COMMENTS')
                comments = (comments_elem.text or "").strip() if comments_elem is not None else ""
                
                # Build CklVuln
                v_code = vuln_data.get('Vuln_Num', '')
                if not v_code:
                    continue
                
                severity_str = vuln_data.get('Severity', 'medium')
                severity = Severity.from_string(severity_str)
                
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
                )
                vulns.append(vuln)
        
        return vulns

