"""Analyzer for comparing Finding Details against Check Text criteria."""

import re
from typing import Dict, List, Tuple


class CheckTextAnalyzer:
    """Analyzes Finding Details against Check Text to determine if criteria are met."""
    
    @staticmethod
    def analyze(check_text: str, finding_details: str) -> Dict[str, any]:
        """Analyze Finding Details against Check Text.
        
        Args:
            check_text: The Check Text from the STIG (what to check)
            finding_details: The Finding Details from the checklist (what was found)
        
        Returns:
            Dictionary with:
                - 'met': bool - Whether criteria appear to be met
                - 'confidence': str - 'high', 'medium', or 'low'
                - 'analysis': str - Detailed analysis text
                - 'key_criteria': List[str] - Key criteria found in check text
                - 'findings_summary': str - Summary of what was found
        """
        print(f"CheckTextAnalyzer.analyze: Analyzing...")  # Debug
        print(f"CheckTextAnalyzer.analyze: Check text length: {len(check_text)}")  # Debug
        print(f"CheckTextAnalyzer.analyze: Finding details length: {len(finding_details)}")  # Debug
        
        if not check_text or not finding_details:
            return {
                'met': False,
                'confidence': 'low',
                'analysis': "Unable to analyze: Check Text or Finding Details is empty.",
                'key_criteria': [],
                'findings_summary': "No data available"
            }
        
        # Extract key criteria from check text
        key_criteria = CheckTextAnalyzer._extract_criteria(check_text)
        print(f"CheckTextAnalyzer.analyze: Found {len(key_criteria)} key criteria")  # Debug
        
        # Analyze finding details
        findings_lower = finding_details.lower()
        check_lower = check_text.lower()
        
        # Look for common indicators
        met_indicators = [
            'compliant', 'satisfied', 'configured', 'enabled', 'set to',
            'found', 'verified', 'confirmed', 'implemented', 'in place',
            'correct', 'properly', 'successfully'
        ]
        
        not_met_indicators = [
            'not found', 'missing', 'not configured', 'not enabled', 'not set',
            'failed', 'not implemented', 'absent', 'lacking', 'not compliant',
            'vulnerability', 'finding', 'fail', 'invalid argument'
        ]
        
        # Count indicators in finding details
        met_count = sum(1 for indicator in met_indicators if indicator in findings_lower)
        not_met_count = sum(1 for indicator in not_met_indicators if indicator in findings_lower)
        
        print(f"CheckTextAnalyzer.analyze: met_count={met_count}, not_met_count={not_met_count}")  # Debug
        
        # Check for command outputs and their results
        has_commands = bool(re.search(r'[$#]\s+\w+', finding_details))
        has_error_output = bool(re.search(r'(error|no such|permission denied|not found)', findings_lower))
        
        # Determine if criteria are met
        met = False
        confidence = 'low'
        
        if not_met_count > met_count:
            met = False
            confidence = 'high' if not_met_count >= 2 else 'medium'
        elif met_count > not_met_count:
            met = True
            confidence = 'high' if met_count >= 2 else 'medium'
        elif has_error_output:
            met = False
            confidence = 'medium'
        elif has_commands and not has_error_output:
            # If commands were run without errors, might be met
            met = True
            confidence = 'low'
        
        # Check for criteria matches
        criteria_matches = CheckTextAnalyzer._check_criteria_matches(key_criteria, finding_details)
        
        # Build analysis text
        analysis = CheckTextAnalyzer._build_analysis_report(
            met, confidence, key_criteria, criteria_matches, 
            met_count, not_met_count, has_commands, has_error_output,
            check_text, finding_details
        )
        
        return {
            'met': met,
            'confidence': confidence,
            'analysis': analysis,
            'key_criteria': key_criteria,
            'findings_summary': CheckTextAnalyzer._summarize_findings(finding_details)
        }
    
    @staticmethod
    def _extract_criteria(check_text: str) -> List[str]:
        """Extract key criteria from check text."""
        criteria = []
        
        # Look for numbered steps or bullet points
        numbered_pattern = r'(?:^|\n)\s*(?:\d+[\.)]\s*|[-*]\s*)([^\n]+)'
        matches = re.findall(numbered_pattern, check_text, re.MULTILINE)
        if matches:
            criteria.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        # Look for "Verify" or "Check" statements
        verify_pattern = r'(?:Verify|Check|Ensure|Confirm)\s+([^.!?\n]{20,150}[.!?])'
        verify_matches = re.findall(verify_pattern, check_text, re.IGNORECASE)
        if verify_matches:
            criteria.extend([m.strip() for m in verify_matches])
        
        # If no specific criteria found, use first few sentences
        if not criteria:
            sentences = re.split(r'[.!?]\s+', check_text)
            criteria = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]
        
        return criteria[:5]  # Limit to 5 key criteria
    
    @staticmethod
    def _check_criteria_matches(criteria: List[str], finding_details: str) -> Dict[str, bool]:
        """Check which criteria appear to be addressed in finding details."""
        matches = {}
        findings_lower = finding_details.lower()
        
        for criterion in criteria:
            # Extract key terms from criterion (nouns, verbs)
            criterion_lower = criterion.lower()
            # Remove common words
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
            words = [w for w in re.findall(r'\w+', criterion_lower) if w not in common_words and len(w) > 3]
            
            # Check if at least 30% of key words appear in findings
            if words:
                found_words = sum(1 for w in words if w in findings_lower)
                matches[criterion] = (found_words / len(words)) >= 0.3
            else:
                matches[criterion] = False
        
        return matches
    
    @staticmethod
    def _summarize_findings(finding_details: str) -> str:
        """Create a brief summary of the finding details."""
        lines = finding_details.split('\n')
        # Get first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()[:100] + ("..." if len(line.strip()) > 100 else "")
        return "No summary available"
    
    @staticmethod
    def _build_analysis_report(met: bool, confidence: str, key_criteria: List[str], 
                               criteria_matches: Dict[str, bool], met_count: int, 
                               not_met_count: int, has_commands: bool, 
                               has_error_output: bool, check_text: str, 
                               finding_details: str) -> str:
        """Build the detailed analysis report."""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("CHECK TEXT COMPARISON ANALYSIS")
        lines.append("=" * 80)
        lines.append("")
        
        # Overall result
        result_text = "CRITERIA APPEAR TO BE MET" if met else "CRITERIA DO NOT APPEAR TO BE MET"
        lines.append(f"RESULT: {result_text}")
        lines.append(f"CONFIDENCE: {confidence.upper()}")
        lines.append("")
        
        # Summary statistics
        lines.append("ANALYSIS SUMMARY:")
        lines.append("-" * 80)
        lines.append(f"  Positive indicators found: {met_count}")
        lines.append(f"  Negative indicators found: {not_met_count}")
        lines.append(f"  Commands detected: {'Yes' if has_commands else 'No'}")
        lines.append(f"  Errors detected: {'Yes' if has_error_output else 'No'}")
        lines.append("")
        
        # Key criteria
        if key_criteria:
            lines.append("KEY CRITERIA FROM CHECK TEXT:")
            lines.append("-" * 80)
            for i, criterion in enumerate(key_criteria, 1):
                addressed = criteria_matches.get(criterion, False)
                status = "✓ Addressed" if addressed else "✗ Not clearly addressed"
                lines.append(f"{i}. {status}")
                lines.append(f"   {criterion[:150]}")
                if len(criterion) > 150:
                    lines.append(f"   {criterion[150:300]}...")
                lines.append("")
        
        # Check Text excerpt
        lines.append("CHECK TEXT (first 500 characters):")
        lines.append("-" * 80)
        lines.append(check_text[:500])
        if len(check_text) > 500:
            lines.append("...")
        lines.append("")
        
        # Finding Details excerpt
        lines.append("FINDING DETAILS (first 500 characters):")
        lines.append("-" * 80)
        lines.append(finding_details[:500])
        if len(finding_details) > 500:
            lines.append("...")
        lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS:")
        lines.append("-" * 80)
        if met and confidence == 'high':
            lines.append("  The finding details provide strong evidence that the check criteria")
            lines.append("  have been met. No further action appears necessary.")
        elif met and confidence in ['medium', 'low']:
            lines.append("  The finding details suggest the criteria may be met, but the evidence")
            lines.append("  is not conclusive. Consider providing more detailed findings.")
        elif not met and confidence == 'high':
            lines.append("  The finding details clearly indicate that the check criteria have not")
            lines.append("  been met. Remediation is recommended.")
        else:
            lines.append("  The finding details do not clearly demonstrate that the check criteria")
            lines.append("  have been met. Additional verification or documentation is recommended.")
        lines.append("")
        
        lines.append("NOTE: This is an automated analysis and may not be fully accurate.")
        lines.append("Please review the findings manually to confirm the assessment.")
        lines.append("=" * 80)
        
        return "\n".join(lines)
