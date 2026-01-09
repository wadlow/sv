"""CKL file writer for creating new checklist files."""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List
from datetime import datetime

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
            stig_info = CklStigInfo(
                stig_id=stig_file.stig_name.replace(' ', '_'),
                version=stig_file.stig_version,
                title=stig_file.stig_name,
                release_info=f"Release: {stig_file.stig_release}",
                uuid="",  # Will be generated if needed
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
        """Write CKL file to disk."""
        # Create root element
        checklist = ET.Element('CHECKLIST')
        checklist.set('xmlns', 'http://checklists.nist.gov/xccdf/1.1')
        checklist.set('xmlns:dsig', 'http://www.w3.org/2000/09/xmldsig#')
        checklist.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        checklist.set('xsi:schemaLocation', 
                     'http://checklists.nist.gov/xccdf/1.1 http://nvd.nist.gov/schema/xccdf-1.1.4.xsd')
        
        # Add comment
        checklist.append(ET.Comment('DISA STIG Viewer :: 2.10'))
        
        # Add ASSET
        asset_elem = ET.SubElement(checklist, 'ASSET')
        ET.SubElement(asset_elem, 'ROLE').text = ckl_file.asset.role
        ET.SubElement(asset_elem, 'ASSET_TYPE').text = ckl_file.asset.asset_type
        ET.SubElement(asset_elem, 'HOST_NAME').text = ckl_file.asset.host_name
        ET.SubElement(asset_elem, 'HOST_IP').text = ckl_file.asset.host_ip
        ET.SubElement(asset_elem, 'HOST_MAC').text = ckl_file.asset.host_mac
        ET.SubElement(asset_elem, 'HOST_FQDN').text = ckl_file.asset.host_fqdn
        ET.SubElement(asset_elem, 'TECH_AREA').text = ckl_file.asset.tech_area
        ET.SubElement(asset_elem, 'TARGET_KEY').text = ckl_file.asset.target_key
        ET.SubElement(asset_elem, 'WEB_OR_DATABASE').text = str(ckl_file.asset.web_or_database).lower()
        ET.SubElement(asset_elem, 'WEB_DB_SITE').text = ckl_file.asset.web_db_site
        ET.SubElement(asset_elem, 'WEB_DB_INSTANCE').text = ckl_file.asset.web_db_instance
        
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
                ET.SubElement(si_data, 'SID_NAME').text = name
                ET.SubElement(si_data, 'SID_DATA').text = data or ''
            
            add_si_data(stig_info_elem, 'version', stig_info.version)
            add_si_data(stig_info_elem, 'classification', 'UNCLASSIFIED')
            add_si_data(stig_info_elem, 'customname', '')
            add_si_data(stig_info_elem, 'stigid', stig_info.stig_id)
            add_si_data(stig_info_elem, 'description', 
                       'This Security Technical Implementation Guide is published as a tool to improve the security of Department of Defense (DOD) information systems.')
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
                    ET.SubElement(stig_data, 'VULN_ATTRIBUTE').text = attr_name
                    ET.SubElement(stig_data, 'ATTRIBUTE_DATA').text = attr_data or ''
                
                add_stig_data(vuln_elem, 'Vuln_Num', vuln.v_code)
                add_stig_data(vuln_elem, 'Severity', vuln.severity)
                add_stig_data(vuln_elem, 'Group_Title', vuln.group_title)
                add_stig_data(vuln_elem, 'Rule_ID', vuln.rule_id)
                add_stig_data(vuln_elem, 'Rule_Ver', vuln.rule_ver or '')
                add_stig_data(vuln_elem, 'Rule_Title', vuln.rule_title)
                add_stig_data(vuln_elem, 'Vuln_Discuss', vuln.discussion)
                add_stig_data(vuln_elem, 'IA_Controls', '')
                add_stig_data(vuln_elem, 'Check_Content', vuln.check_text)
                add_stig_data(vuln_elem, 'Fix_Text', vuln.fix_text)
                add_stig_data(vuln_elem, 'False_Positives', '')
                add_stig_data(vuln_elem, 'False_Negatives', '')
                add_stig_data(vuln_elem, 'Documentable', '')
                add_stig_data(vuln_elem, 'Mitigations', '')
                add_stig_data(vuln_elem, 'Potential_Impact', '')
                add_stig_data(vuln_elem, 'Third_Party_Tools', '')
                add_stig_data(vuln_elem, 'Mitigation_Control', '')
                add_stig_data(vuln_elem, 'Responsibility', '')
                add_stig_data(vuln_elem, 'Security_Override_Guidance', '')
                add_stig_data(vuln_elem, 'Check_Content_Ref', '')
                add_stig_data(vuln_elem, 'Weight', '')
                add_stig_data(vuln_elem, 'Class', '')
                add_stig_data(vuln_elem, 'STIGRef', '')
                add_stig_data(vuln_elem, 'TargetKey', '')
                add_stig_data(vuln_elem, 'STIGRef', '')
                add_stig_data(vuln_elem, 'STIGRef', '')
                
                ET.SubElement(vuln_elem, 'STATUS').text = vuln.status.ckl_string
                ET.SubElement(vuln_elem, 'FINDING_DETAILS').text = vuln.finding_details
                ET.SubElement(vuln_elem, 'COMMENTS').text = vuln.comments
                ET.SubElement(vuln_elem, 'SEVERITY_OVERRIDE', {'AUTHORITY': ''})
                ET.SubElement(vuln_elem, 'SEVERITY_JUSTIFICATION', {'AUTHORITY': ''})
        
        # Write to file
        try:
            tree = ET.ElementTree(checklist)
            ET.indent(tree, space='  ')
            
            # Write with XML declaration
            with open(ckl_file.file_path, 'wb') as f:
                f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
                tree.write(f, encoding='utf-8', xml_declaration=False)
        except PermissionError:
            raise Exception(f"Permission denied: cannot write to {ckl_file.file_path}")
        except Exception as e:
            raise Exception(f"Error writing CKL file: {e}")

