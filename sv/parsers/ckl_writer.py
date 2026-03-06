"""CKL file writer for creating new checklist files."""

import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape as xml_escape
from pathlib import Path
from typing import List
from datetime import datetime
import uuid

from ..models.stig_file import StigFile
from ..models.ckl_file import CklFile, CklAsset, CklStigInfo, CklVuln
from ..models.checklist_status import ChecklistStatus


class CklWriter:
    """Writer for creating CKL checklist files."""
    
    @staticmethod
    def create_from_stigs(file_path: Path, stig_files: List[StigFile]) -> CklFile:
        """
        Create a new CKL file from selected STIG files.
        
        Args:
            file_path: Path where the CKL file will be saved
            stig_files: List of StigFile objects to include
            
        Returns:
            CklFile object representing the created file
        """
        # Create default asset
        asset = CklAsset()
        
        # Create STIG info and vulns from each STIG file
        stigs = []
        vulns = []
        
        for stig_file in stig_files:
            # Create CklStigInfo from StigFile
            # Format release_info in the standard CKL format: "Release: X"
            release_str = stig_file.stig_release or ""
            if release_str:
                # If release already has "R" prefix (e.g., "R6"), strip it for the CKL format
                if release_str.upper().startswith('R') and len(release_str) > 1:
                    release_num = release_str[1:]
                else:
                    release_num = release_str
                release_info = f"Release: {release_num}"
            else:
                release_info = "Release: Unknown"
            
            stig_info = CklStigInfo(
                stig_id=stig_file.stig_name.replace(' ', '_'),
                version=stig_file.stig_version,
                title=stig_file.stig_name,
                release_info=release_info,
                uuid=str(uuid.uuid4()),  # Generate a valid UUID
                filename=stig_file.file_name,
            )
            stigs.append(stig_info)
            
            # Convert VulnCodes to CklVulns
            for vuln_code in stig_file.vuln_codes:
                ckl_vuln = CklVuln.from_vuln_code(vuln_code, stig_info)
                vulns.append(ckl_vuln)
        
        # Create CklFile
        ckl_file = CklFile(
            file_path=file_path,
            file_name=file_path.name,
            asset=asset,
            stigs=stigs,
            vulns=vulns,
        )
        
        # Write to file
        CklWriter.write(ckl_file)
        
        return ckl_file
    
    @staticmethod
    def write(ckl_file: CklFile):
        """Write CKL file to disk in DISA STIG Viewer 2.10 format."""
        # Create root element WITHOUT namespaces (to match template)
        checklist = ET.Element('CHECKLIST')
        
        # Don't add comment as Element - we'll add it manually in serialization
        
        # Add ASSET
        asset_elem = ET.SubElement(checklist, 'ASSET')
        
        # Helper to add elements with text content (never self-closing)
        def add_element(parent, tag, text=''):
            elem = ET.SubElement(parent, tag)
            # Strip trailing whitespace from text to avoid XML parsing issues
            # But preserve internal formatting (don't strip leading/internal whitespace)
            if text:
                elem.text = text.rstrip()
            else:
                elem.text = ''
            return elem
        
        add_element(asset_elem, 'ROLE', ckl_file.asset.role or 'None')
        add_element(asset_elem, 'ASSET_TYPE', ckl_file.asset.asset_type or 'Computing')
        add_element(asset_elem, 'HOST_NAME', ckl_file.asset.host_name)
        add_element(asset_elem, 'HOST_IP', ckl_file.asset.host_ip)
        add_element(asset_elem, 'HOST_MAC', ckl_file.asset.host_mac)
        add_element(asset_elem, 'HOST_FQDN', ckl_file.asset.host_fqdn)
        add_element(asset_elem, 'TECH_AREA', ckl_file.asset.tech_area)
        add_element(asset_elem, 'TARGET_KEY', ckl_file.asset.target_key)
        add_element(asset_elem, 'WEB_OR_DATABASE', str(ckl_file.asset.web_or_database).lower())
        add_element(asset_elem, 'WEB_DB_SITE', ckl_file.asset.web_db_site)
        add_element(asset_elem, 'WEB_DB_INSTANCE', ckl_file.asset.web_db_instance)
        
        # Add STIGS
        stigs_elem = ET.SubElement(checklist, 'STIGS')
        
        # Group vulns by stig_info
        vulns_by_stig = {}
        for vuln in ckl_file.vulns:
            stig_id = vuln.stig_info.stig_id
            if stig_id not in vulns_by_stig:
                vulns_by_stig[stig_id] = []
            vulns_by_stig[stig_id].append(vuln)
        
        # Create iSTIG for each STIG
        for stig_info in ckl_file.stigs:
            istig_elem = ET.SubElement(stigs_elem, 'iSTIG')
            
            # Add STIG_INFO
            stig_info_elem = ET.SubElement(istig_elem, 'STIG_INFO')
            
            def add_si_data(parent, name, data):
                si_data = ET.SubElement(parent, 'SI_DATA')
                add_element(si_data, 'SID_NAME', name)
                add_element(si_data, 'SID_DATA', data)
            
            add_si_data(stig_info_elem, 'version', stig_info.version or '2')
            add_si_data(stig_info_elem, 'classification', 'UNCLASSIFIED')
            add_si_data(stig_info_elem, 'customname', '')
            add_si_data(stig_info_elem, 'stigid', stig_info.stig_id)
            add_si_data(stig_info_elem, 'description', 
                       'This Security Technical Implementation Guide is published as a tool to improve the security of Department of Defense (DOD) information systems. The requirements are derived from the National Institute of Standards and Technology (NIST) 800-53 and related documents. Comments or proposed revisions to this document should be sent via email to the following address: disa.stig_spt@mail.mil.')
            add_si_data(stig_info_elem, 'filename', stig_info.filename)
            add_si_data(stig_info_elem, 'releaseinfo', stig_info.release_info)
            add_si_data(stig_info_elem, 'title', stig_info.title)
            add_si_data(stig_info_elem, 'uuid', stig_info.uuid or '')
            add_si_data(stig_info_elem, 'notice', 'terms-of-use')
            add_si_data(stig_info_elem, 'source', '')
            
            # Add VULNs for this STIG
            vulns = vulns_by_stig.get(stig_info.stig_id, [])
            for vuln in vulns:
                vuln_elem = ET.SubElement(istig_elem, 'VULN')
                
                def add_stig_data(parent, attr_name, attr_data):
                    stig_data = ET.SubElement(parent, 'STIG_DATA')
                    add_element(stig_data, 'VULN_ATTRIBUTE', attr_name)
                    add_element(stig_data, 'ATTRIBUTE_DATA', attr_data)
                
                add_stig_data(vuln_elem, 'Vuln_Num', vuln.v_code)
                add_stig_data(vuln_elem, 'Severity', vuln.severity.lower() if vuln.severity else 'medium')
                add_stig_data(vuln_elem, 'Group_Title', vuln.group_title)
                add_stig_data(vuln_elem, 'Rule_ID', vuln.rule_id)
                add_stig_data(vuln_elem, 'Rule_Ver', vuln.rule_ver or '')
                add_stig_data(vuln_elem, 'Rule_Title', vuln.rule_title)
                add_stig_data(vuln_elem, 'Vuln_Discuss', vuln.discussion or '')
                add_stig_data(vuln_elem, 'IA_Controls', vuln.references or '')
                add_stig_data(vuln_elem, 'Check_Content', vuln.check_text or '')
                add_stig_data(vuln_elem, 'Fix_Text', vuln.fix_text or '')
                add_stig_data(vuln_elem, 'False_Positives', '')
                add_stig_data(vuln_elem, 'False_Negatives', '')
                add_stig_data(vuln_elem, 'Documentable', 'false')
                add_stig_data(vuln_elem, 'Mitigations', '')
                add_stig_data(vuln_elem, 'Potential_Impact', '')
                add_stig_data(vuln_elem, 'Third_Party_Tools', '')
                add_stig_data(vuln_elem, 'Mitigation_Control', '')
                add_stig_data(vuln_elem, 'Responsibility', '')
                add_stig_data(vuln_elem, 'Security_Override_Guidance', '')
                
                # Add STATUS, FINDING_DETAILS, COMMENTS (always have content)
                add_element(vuln_elem, 'STATUS', vuln.status.ckl_string)
                add_element(vuln_elem, 'FINDING_DETAILS', vuln.finding_details or '')
                add_element(vuln_elem, 'COMMENTS', vuln.comments or '')
                add_element(vuln_elem, 'SEVERITY_OVERRIDE', '')
                add_element(vuln_elem, 'SEVERITY_JUSTIFICATION', '')
        
        # Write to file with tabs and proper formatting
        try:
            # Custom serialization to match DISA format
            xml_str = CklWriter._serialize_with_tabs(checklist)
            
            # Write with XML declaration and comment
            with open(ckl_file.file_path, 'w', encoding='UTF-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<!--DISA STIG Viewer :: 2.10-->\n')
                f.write(xml_str)
        except PermissionError:
            raise Exception(f"Permission denied: cannot write to {ckl_file.file_path}")
        except Exception as e:
            raise Exception(f"Error writing CKL file: {e}")
    
    @staticmethod
    def _serialize_with_tabs(elem, level=0):
        """Serialize XML with tabs for indentation (matching DISA format)."""
        indent = '\t' * level
        result = []
        
        # Opening tag
        result.append(f"{indent}<{elem.tag}>")
        
        # Handle text content
        has_children = len(elem) > 0
        has_text = elem.text and elem.text.strip()
        
        if has_text:
            # Escape XML special characters in text content
            escaped_text = xml_escape(elem.text)
            result.append(escaped_text)
            # Check if we need to add newline before children
            if has_children and not elem.text.endswith('\n'):
                result.append('\n')
        elif has_children:
            # No text but has children - newline after opening tag
            result.append('\n')
        
        # Children
        for child in elem:
            result.append(CklWriter._serialize_with_tabs(child, level + 1))
        
        # Closing tag
        if has_children:
            # Element has children - closing tag on new line with indent
            result.append(f"{indent}</{elem.tag}>\n")
        else:
            # Leaf element - closing tag immediately after content (no newline before it)
            result.append(f"</{elem.tag}>\n")
        
        return ''.join(result)

