"""STIG file parser for XCCDF XML format."""

import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional
from zipfile import ZipFile

from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode, Severity


class StigParserError(Exception):
    """Error parsing STIG file."""
    pass


class StigParser:
    """Parser for STIG files in XCCDF XML format."""
    
    @staticmethod
    def parse(file_path: Path, progress_callback=None) -> List[StigFile]:
        """
        Parse a STIG file (ZIP or XML).
        
        Args:
            file_path: Path to the STIG file
            progress_callback: Optional callback function(current, total) for progress updates
            
        Returns:
            List of StigFile objects (multiple if ZIP contains multiple XCCDFs)
            
        Raises:
            StigParserError: If parsing fails
        """
        file_name = file_path.name
        
        # Check if it's a ZIP file
        if file_path.suffix.lower() == ".zip":
            return StigParser._parse_from_zip(file_path, file_name, progress_callback)
        elif file_path.suffix.lower() == ".xml":
            # XML files return a single-item list for consistency
            return [StigParser._parse_from_xml(file_path, file_name, progress_callback)]
        else:
            raise StigParserError(f"Unsupported file format: {file_path.suffix}")
    
    @staticmethod
    def _parse_from_zip(zip_path: Path, file_name: str, progress_callback=None) -> List[StigFile]:
        """Extract and parse all XCCDF XML files from ZIP archive."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract ZIP
            try:
                with ZipFile(zip_path, 'r') as zip_file:
                    zip_file.extractall(temp_path)
            except Exception as e:
                raise StigParserError(f"Cannot open ZIP archive: {e}")
            
            # Find all XCCDF XML files
            all_xml_files = list(temp_path.rglob("*.xml"))
            xccdf_files = []
            
            for xml_file in all_xml_files:
                if "xccdf" in xml_file.name.lower():
                    xccdf_files.append(xml_file)
            
            if not xccdf_files:
                raise StigParserError("No XCCDF XML files found in archive")
            
            print(f"StigParser._parse_from_zip: Found {len(xccdf_files)} XCCDF files in {file_name}")  # Debug
            
            # Parse all XCCDF files as separate STIGs
            stig_files = []
            for i, xccdf_file in enumerate(xccdf_files):
                try:
                    print(f"StigParser._parse_from_zip: Parsing XCCDF {i+1}/{len(xccdf_files)}: {xccdf_file.name}")  # Debug
                    stig = StigParser._parse_xccdf(xccdf_file.read_bytes(), file_name, zip_path, progress_callback, xccdf_file.name)
                    stig_files.append(stig)
                except Exception as e:
                    print(f"StigParser._parse_from_zip: Error parsing {xccdf_file.name}: {e}")  # Debug
                    continue
            
            if not stig_files:
                raise StigParserError("Failed to parse any XCCDF files from archive")
            
            print(f"StigParser._parse_from_zip: Successfully parsed {len(stig_files)} STIGs from {file_name}")  # Debug
            return stig_files
    
    @staticmethod
    def _parse_multiple_xccdf(xccdf_files: List[Path], file_name: str, zip_path: Path, progress_callback=None) -> StigFile:
        """Parse multiple XCCDF files and combine into a single StigFile."""
        print(f"StigParser._parse_multiple_xccdf: Parsing {len(xccdf_files)} XCCDF files")  # Debug
        
        # Parse the first file to get metadata
        first_stig = StigParser._parse_xccdf(xccdf_files[0].read_bytes(), file_name, zip_path, None)
        all_vuln_codes = list(first_stig.vuln_codes)
        
        # Parse remaining files and add their V-codes
        for i, xccdf_file in enumerate(xccdf_files[1:], start=1):
            try:
                print(f"StigParser._parse_multiple_xccdf: Parsing file {i+1}/{len(xccdf_files)}: {xccdf_file.name}")  # Debug
                additional_stig = StigParser._parse_xccdf(xccdf_file.read_bytes(), xccdf_file.name, zip_path, None)
                
                # Add V-codes that aren't already present (deduplicate by v_code)
                existing_vcodes = {vc.v_code for vc in all_vuln_codes}
                for vc in additional_stig.vuln_codes:
                    if vc.v_code not in existing_vcodes:
                        all_vuln_codes.append(vc)
                        existing_vcodes.add(vc.v_code)
                
                print(f"StigParser._parse_multiple_xccdf: Added {len(additional_stig.vuln_codes)} V-codes from {xccdf_file.name}")  # Debug
            except Exception as e:
                print(f"StigParser._parse_multiple_xccdf: Error parsing {xccdf_file.name}: {e}")  # Debug
                continue
        
        # Sort V-codes by v_code for consistency
        all_vuln_codes.sort(key=lambda vc: vc.v_code)
        
        print(f"StigParser._parse_multiple_xccdf: Total V-codes: {len(all_vuln_codes)}")  # Debug
        
        # Call progress callback with final count
        if progress_callback:
            progress_callback(len(all_vuln_codes), len(all_vuln_codes))
        
        # Create combined StigFile using metadata from first file
        return StigFile(
            file_path=zip_path,
            file_name=file_name,
            stig_name=first_stig.stig_name,
            stig_version=first_stig.stig_version,
            stig_release=first_stig.stig_release,
            vuln_codes=all_vuln_codes,
        )
    
    @staticmethod
    def _parse_from_xml(xml_path: Path, file_name: str, progress_callback=None) -> StigFile:
        """Parse XCCDF XML file directly."""
        try:
            xml_data = xml_path.read_bytes()
        except Exception as e:
            raise StigParserError(f"Cannot read XML file: {e}")
        
        return StigParser._parse_xccdf(xml_data, file_name, xml_path, progress_callback)
    
    @staticmethod
    def _parse_xccdf(xml_data: bytes, file_name: str, file_path: Path, progress_callback=None, xccdf_filename: str = None) -> StigFile:
        """Parse XCCDF XML data.
        
        Args:
            xml_data: The XCCDF XML content as bytes
            file_name: Display name for the STIG
            file_path: Path to store in StigFile (ZIP path or XML path)
            progress_callback: Optional callback for progress updates
            xccdf_filename: Optional XCCDF filename for release extraction
        """
        print(f"StigParser._parse_xccdf: progress_callback = {progress_callback}")  # Debug
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            raise StigParserError(f"XML parse error: {e}")
        except Exception as e:
            raise StigParserError(f"Error parsing XML: {e}")
        
        # Find Benchmark element (handle namespaces)
        benchmark = None
        for elem in root.iter():
            if elem.tag.endswith('Benchmark') or elem.tag == 'Benchmark':
                benchmark = elem
                break
        
        if benchmark is None:
            raise StigParserError("Invalid XCCDF structure: no Benchmark element found")
        
        # Extract namespace
        ns = {}
        if benchmark.tag.startswith('{'):
            ns_uri = benchmark.tag[1:benchmark.tag.index('}')]
            ns = {'xccdf': ns_uri}
            # Register namespace for easier searching
            ET.register_namespace('xccdf', ns_uri)
        
        # Extract Benchmark metadata
        stig_name = StigParser._get_text(benchmark, 'title', ns) or file_name
        stig_version = StigParser._get_text(benchmark, 'version', ns) or "Unknown"
        # Use xccdf_filename for release extraction if provided, otherwise use file_path
        filename_for_release = xccdf_filename if xccdf_filename else (file_path.name if file_path else None)
        stig_release = StigParser._extract_release(benchmark, ns, filename_for_release)
        
        # Extract Groups and Rules
        vuln_codes = []
        
        # Parse all groups
        groups = benchmark.findall('.//Group', ns) or benchmark.findall('.//{*}Group')
        total_groups = len(groups)
        print(f"StigParser: Found {total_groups} groups to parse, callback={progress_callback}")  # Debug
        
        for i, group in enumerate(groups):
            
            rule = group.find('Rule') or group.find('{*}Rule')
            if rule is None:
                continue
            
            v_code = StigParser._extract_v_code(rule)
            if v_code is None:
                continue
            
            severity = StigParser._extract_severity(rule)
            rule_title = StigParser._get_text(rule, 'title', ns) or ""
            description_raw = StigParser._get_text(rule, 'description', ns) or ""
            # Extract just the VulnDiscussion text from the description XML
            description = StigParser._extract_vuln_discussion(description_raw)
            
            # Extract check text
            check_text = ""
            check_elem = rule.find('check') or rule.find('{*}check')
            if check_elem is not None:
                check_content = check_elem.find('check-content') or check_elem.find('{*}check-content')
                if check_content is not None:
                    check_text = (check_content.text or "").strip()
            
            # Extract fix text
            fix_text = StigParser._get_text(rule, 'fixtext', ns) or ""
            group_title = StigParser._get_text(group, 'title', ns) or ""
            rule_id = rule.get('id', '')
            rule_ver = rule.find('version') or rule.find('{*}version')
            rule_ver_text = rule_ver.text if rule_ver is not None and rule_ver.text else None
            
            vuln_code_obj = VulnCode(
                id=v_code,
                v_code=v_code,
                severity=severity,
                rule_title=rule_title,
                discussion=description,
                check_text=check_text,
                fix_text=fix_text,
                group_title=group_title,
                rule_id=rule_id,
                rule_ver=rule_ver_text,
                stig_name=stig_name,
                stig_version=stig_version,
                stig_release=stig_release,
            )
            vuln_codes.append(vuln_code_obj)
            
            # Call progress callback every 10 records or on last record
            if progress_callback and (i % 10 == 0 or i == total_groups - 1):
                print(f"StigParser: Calling progress_callback({len(vuln_codes)}, {total_groups})")  # Debug
                progress_callback(len(vuln_codes), total_groups)
        
        return StigFile(
            file_path=file_path,
            file_name=file_name,
            stig_name=stig_name,
            stig_version=stig_version,
            stig_release=stig_release,
            vuln_codes=vuln_codes,
        )
    
    @staticmethod
    def _extract_release(benchmark: ET.Element, ns: dict, filename: str = None) -> str:
        """Extract release information from Benchmark element.
        
        Tries multiple methods:
        1. Extract from XCCDF filename (e.g., "U_RHEL_9_STIG_V2R6_Manual-xccdf.xml" -> "R6")
        2. Simple <release> element
        3. <status>/<plain-text> element (e.g., "Release: 4 Benchmark Date: 23 Oct 2024")
        4. Extract from version text (e.g., "V2R4" -> "R4")
        """
        # Try to extract from filename first (highest priority)
        if filename:
            # Look for pattern like V#R# in the filename
            match = re.search(r'V\d+R(\d+)', filename, re.IGNORECASE)
            if match:
                release_num = match.group(1)
                print(f"StigParser: Extracted release R{release_num} from filename {filename}")
                return f"R{release_num}"
        
        # Try simple <release> element
        release = StigParser._get_text(benchmark, 'release', ns)
        if release and release != "Unknown":
            return release
        
        # Try <status>/<plain-text> element
        status_elem = None
        if ns:
            status_elem = benchmark.find('.//{{xccdf}}status', ns)
        if status_elem is None:
            status_elem = benchmark.find('.//status') or benchmark.find('.//{*}status')
        
        if status_elem is not None:
            plain_text_elem = None
            if ns:
                plain_text_elem = status_elem.find('.//{{xccdf}}plain-text', ns)
            if plain_text_elem is None:
                plain_text_elem = status_elem.find('.//plain-text') or status_elem.find('.//{*}plain-text')
            
            if plain_text_elem is not None and plain_text_elem.text:
                plain_text = plain_text_elem.text.strip()
                # Extract "Release: X" from text like "Release: 4 Benchmark Date: 23 Oct 2024"
                match = re.search(r'Release:\s*(\S+)', plain_text, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        # Try to extract from version (e.g., "V2R4" -> "R4")
        version = StigParser._get_text(benchmark, 'version', ns)
        if version:
            match = re.search(r'(R\d+)', version, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Unknown"
    
    @staticmethod
    def _get_text(elem: ET.Element, tag: str, ns: dict) -> Optional[str]:
        """Get text content from element, handling namespaces."""
        # Try with namespace
        if ns:
            result = elem.find(f'.//{{xccdf}}{tag}', ns)
            if result is not None and result.text:
                return result.text.strip()
        
        # Try without namespace
        result = elem.find(f'.//{tag}')
        if result is not None and result.text:
            return result.text.strip()
        
        # Try with any namespace
        for child in elem.iter():
            if child.tag.endswith(tag):
                if child.text:
                    return child.text.strip()
        
        return None
    
    @staticmethod
    def _extract_v_code(rule: ET.Element) -> Optional[str]:
        """Extract V-code from rule element."""
        # Check version field first
        version_elem = rule.find('version') or rule.find('{*}version')
        if version_elem is not None and version_elem.text:
            version_text = version_elem.text.strip()
            if version_text.startswith('V-'):
                return version_text
        
        # Check rule ID
        rule_id = rule.get('id', '')
        if 'V-' in rule_id:
            # Extract V-code pattern
            match = re.search(r'V-\d+', rule_id)
            if match:
                return match.group(0)
        
        return None
    
    @staticmethod
    def _extract_severity(rule: ET.Element) -> str:
        """Extract severity from rule element."""
        severity = rule.get('severity', '')
        if not severity:
            # Try to find severity element
            severity_elem = rule.find('severity') or rule.find('{*}severity')
            if severity_elem is not None and severity_elem.text:
                severity = severity_elem.text.strip()
        
        return Severity.from_string(severity)
    
    @staticmethod
    def _extract_vuln_discussion(description_text: str) -> str:
        """Extract text from within VulnDiscussion tags."""
        if not description_text:
            print("_extract_vuln_discussion: Empty description_text")  # Debug
            return ""
        
        print(f"_extract_vuln_discussion: Input length={len(description_text)}, first 100 chars: {description_text[:100]}")  # Debug
        
        # Try to parse as XML and extract VulnDiscussion content
        try:
            # Wrap in a root element to make it valid XML
            wrapped = f"<root>{description_text}</root>"
            root = ET.fromstring(wrapped)
            
            # Find VulnDiscussion element
            vuln_disc = root.find('.//VulnDiscussion')
            if vuln_disc is not None and vuln_disc.text:
                result = vuln_disc.text.strip()
                print(f"_extract_vuln_discussion: Extracted from XML, length={len(result)}")  # Debug
                return result
        except ET.ParseError as e:
            # If parsing fails, try simple string extraction
            print(f"_extract_vuln_discussion: XML parsing failed: {e}")  # Debug
            pass
        
        # Fallback: use regex to extract text between <VulnDiscussion> tags
        match = re.search(r'<VulnDiscussion>(.*?)</VulnDiscussion>', description_text, re.DOTALL)
        if match:
            result = match.group(1).strip()
            print(f"_extract_vuln_discussion: Extracted via regex, length={len(result)}")  # Debug
            return result
        
        # If no VulnDiscussion tags found, return the original text
        print(f"_extract_vuln_discussion: No VulnDiscussion tags found, returning original text")  # Debug
        return description_text

