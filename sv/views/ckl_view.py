"""CKL view with three-column layout."""

from AppKit import NSView, NSRect, NSSplitView, NSViewWidthSizable, NSViewHeightSizable
from Foundation import NSObject
from typing import Optional
from pathlib import Path
import objc
import os

from ..models.ckl_file import CklFile, CklVuln
from ..models.stig_file import StigFile
from ..models.vuln_code import VulnCode
from .status_pie_chart import StatusPieChart
from .ckl_detail_pane import CklDetailPane
from .status_filter_pane import StatusFilterPane
from .view_helpers import get_view_attrs, get_bounds_size

# Check if verbose CKL debug logging is enabled
_CKL_DEBUG = os.environ.get('SV_CKL_DEBUG') == '1'


class CklView(NSView):
    """CKL tab view with three columns."""
    
    def init(self):
        """Initialize the CKL view."""
        self = NSView.alloc().init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['ckl_file'] = None
        attrs['stigs_pane'] = None
        attrs['pie_chart'] = None
        attrs['status_filter_pane'] = None
        attrs['vcode_list_pane'] = None
        attrs['vcode_detail_pane'] = None
        CklView.createLayout(self)
        return self
    
    def createLayout(self):
        """Create the three-column layout."""
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 1200, 800
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"CklView.createLayout: Set default frame {width}x{height}")  # Debug
        
        print(f"CklView.createLayout: Creating layout with bounds {width}x{height}")  # Debug
        
        # Main horizontal split view (three columns)
        main_split = NSSplitView.alloc().initWithFrame_(bounds)
        main_split.setVertical_(True)
        main_split.setDividerStyle_(1)  # NSSplitViewDividerStyleThin
        main_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Column 1: STIG checklist + Pie chart + Search (3 panes stacked vertically, each 33%)
        col1_frame = NSRect((0, 0), (width * 0.33, height))
        col1_split = NSSplitView.alloc().initWithFrame_(col1_frame)
        col1_split.setVertical_(False)  # Horizontal divider (stacks vertically)
        col1_split.setDividerStyle_(1)
        col1_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # STIG checklist pane (top - 33%)
        attrs = get_view_attrs(self)
        from .stigs_pane import StigsPane
        stigs_pane = StigsPane.alloc().init()
        stigs_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['stigs_pane'] = stigs_pane
        
        # Pie chart (middle - 33%)
        pie_chart = StatusPieChart.alloc().init()
        pie_chart.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['pie_chart'] = pie_chart
        
        # Status filter pane (bottom - 33%)
        status_filter_pane = StatusFilterPane.alloc().init()
        status_filter_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['status_filter_pane'] = status_filter_pane
        
        col1_split.addSubview_(stigs_pane)
        col1_split.addSubview_(pie_chart)
        col1_split.addSubview_(status_filter_pane)
        col1_split.adjustSubviews()
        
        # Set divider positions for equal thirds (after adding to parent)
        # Will be adjusted later when the view has actual size
        attrs['col1_split'] = col1_split
        
        # Column 2: V-code list with Status (33% width)
        col2_frame = NSRect((0, 0), (width * 0.33, height))
        from .vcode_list_pane import VCodeListPane
        vcode_list_pane = VCodeListPane.alloc().init()
        vcode_list_pane.setFrame_(col2_frame)
        vcode_list_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['vcode_list_pane'] = vcode_list_pane
        
        # Column 3: CKL detail with four panes (34% width)
        col3_frame = NSRect((0, 0), (width * 0.34, height))
        ckl_detail_pane = CklDetailPane.alloc().init()
        ckl_detail_pane.setFrame_(col3_frame)
        ckl_detail_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['vcode_detail_pane'] = ckl_detail_pane  # Keep same key name for compatibility
        
        # Add columns to main split view
        main_split.addSubview_(col1_split)
        main_split.addSubview_(vcode_list_pane)
        main_split.addSubview_(ckl_detail_pane)
        main_split.adjustSubviews()
        
        # Store main_split for later reference
        attrs['main_split'] = main_split
        
        # Set initial divider positions
        if width > 0:
            main_split.setPosition_ofDividerAtIndex_(width * 0.33, 0)
            main_split.setPosition_ofDividerAtIndex_(width * 0.66, 1)
        
        self.addSubview_(main_split)
        
        print(f"CklView.createLayout: Layout complete - added 3-column split view")  # Debug
    
    @objc.python_method
    def set_ckl_file(self, ckl_file: CklFile):
        """Set the CKL file to display."""
        attrs = get_view_attrs(self)
        attrs['ckl_file'] = ckl_file
        
        # Ensure layout is properly sized
        main_split = attrs.get('main_split')
        if main_split:
            bounds = self.bounds()
            width, height = get_bounds_size(bounds)
            print(f"CklView.set_ckl_file: Current bounds {width}x{height}")  # Debug
            if width > 0 and height > 0:
                # Update main split view frame and divider positions
                main_split.setFrame_(bounds)
                main_split.setPosition_ofDividerAtIndex_(width * 0.33, 0)
                main_split.setPosition_ofDividerAtIndex_(width * 0.66, 1)
                main_split.adjustSubviews()
                
                # Update column 1 split view divider positions (equal thirds)
                col1_split = attrs.get('col1_split')
                if col1_split:
                    col1_bounds = col1_split.bounds()
                    col1_height = col1_bounds.size.height
                    if col1_height > 0:
                        col1_split.setPosition_ofDividerAtIndex_(col1_height / 3, 0)
                        col1_split.setPosition_ofDividerAtIndex_(col1_height * 2 / 3, 1)
                        col1_split.adjustSubviews()
                        print(f"CklView.set_ckl_file: Set col1 dividers at {col1_height/3} and {col1_height*2/3}")  # Debug
                
                print(f"CklView.set_ckl_file: Updated layout to {width}x{height}")  # Debug
        
        CklView.updateDisplay(self)
    
    @objc.python_method
    def updateDisplay(self):
        """Update the display based on current CKL file."""
        attrs = get_view_attrs(self)
        ckl_file = attrs.get('ckl_file')
        if not ckl_file:
            return
        
        if _CKL_DEBUG:
            print(f"CklView.updateDisplay: Updating display for {ckl_file.file_name}")  # Debug
        
        # Convert CKL STIGs to StigFile objects for display
        stig_files = []
        for stig_info in ckl_file.stigs:
            # Get vulns for this STIG
            stig_vulns = [v for v in ckl_file.vulns if v.stig_info.stig_id == stig_info.stig_id]
            
            # Convert CklVuln to VulnCode for this STIG
            vuln_codes = []
            for ckl_vuln in stig_vulns:
                vuln_code = VulnCode(
                    id=ckl_vuln.id,  # Use the CklVuln's id (V-code + STIG ID)
                    v_code=ckl_vuln.v_code,
                    severity=ckl_vuln.severity,
                    rule_title=ckl_vuln.rule_title,
                    discussion=ckl_vuln.discussion,
                    check_text=ckl_vuln.check_text,
                    fix_text=ckl_vuln.fix_text,
                    group_title=ckl_vuln.group_title,
                    rule_id=ckl_vuln.rule_id,
                    rule_ver=ckl_vuln.rule_ver,
                    stig_name=stig_info.title,
                    stig_version=stig_info.version,
                    stig_release=stig_info.release_info
                )
                vuln_codes.append(vuln_code)
            
            # Create a StigFile representation
            stig_file = StigFile(
                file_path=Path(stig_info.filename),
                file_name=stig_info.filename,
                stig_name=stig_info.title,
                stig_version=stig_info.version,
                stig_release=stig_info.release_info,
                vuln_codes=vuln_codes,
                is_checked=True  # Initially checked
            )
            stig_files.append(stig_file)
        
        if _CKL_DEBUG:
            print(f"CklView.updateDisplay: Converted {len(stig_files)} STIGs")  # Debug
        
        # Update STIG list in first column
        stigs_pane = attrs.get('stigs_pane')
        if stigs_pane:
            from .stigs_pane import StigsPane
            # Set the selection callback in the stigs_pane attrs
            stigs_attrs = get_view_attrs(stigs_pane)
            stigs_attrs['on_selection_changed'] = lambda: CklView._on_stig_selection_changed(self)
            # Now set the STIG files (which will wire up the callback)
            StigsPane.set_stig_files(stigs_pane, stig_files)
            if _CKL_DEBUG:
                print(f"CklView.updateDisplay: Updated STIGs pane with {len(stig_files)} STIGs")  # Debug
        
        # Wire up status filter callback
        status_filter_pane = attrs.get('status_filter_pane')
        if _CKL_DEBUG:
            print(f"CklView.updateDisplay: status_filter_pane={status_filter_pane}")  # Debug
        if status_filter_pane:
            from .status_filter_pane import StatusFilterPane
            StatusFilterPane.set_on_filter_changed(status_filter_pane, lambda: CklView._on_status_filter_changed(self))
            if _CKL_DEBUG:
                print("CklView.updateDisplay: Wired up status filter callback")  # Debug
        else:
            if _CKL_DEBUG:
                print("CklView.updateDisplay: WARNING - No status_filter_pane found!")  # Debug
        
        # Store stig_files and vuln code to CKL vuln mapping for later use
        attrs['stig_files'] = stig_files
        
        # Create mapping from VulnCode ID to CklVuln for quick lookup
        vuln_code_to_ckl_vuln = {}
        for ckl_vuln in ckl_file.vulns:
            vuln_code_to_ckl_vuln[ckl_vuln.id] = ckl_vuln
        attrs['vuln_code_to_ckl_vuln'] = vuln_code_to_ckl_vuln
        
        if _CKL_DEBUG:
            print(f"CklView.updateDisplay: About to call _update_vcode_list and _update_pie_chart")  # Debug
            print(f"CklView.updateDisplay: pie_chart={attrs.get('pie_chart')}, status_filter_pane={attrs.get('status_filter_pane')}")  # Debug
        
        # Update V-code list and pie chart based on checked STIGs
        CklView._update_vcode_list(self)
        CklView._update_pie_chart(self)
        
        if _CKL_DEBUG:
            print("CklView.updateDisplay: Update complete")  # Debug
    
    @objc.python_method
    def set_selected_vuln(self, vuln: Optional[CklVuln]):
        """Set the selected vulnerability for detail display."""
        attrs = get_view_attrs(self)
        vcode_detail_pane = attrs.get('vcode_detail_pane')
        if vcode_detail_pane and vuln:
            # Convert CklVuln to display format
            # We'll need to adapt the detail pane
            pass
    
    @objc.python_method
    def _on_stig_selection_changed(self):
        """Handle STIG selection change."""
        if _CKL_DEBUG:
            print("CklView._on_stig_selection_changed: STIG selection changed")  # Debug
        CklView._update_vcode_list(self)
        CklView._update_pie_chart(self)
    
    @objc.python_method
    def _on_status_filter_changed(self):
        """Handle status filter change."""
        if _CKL_DEBUG:
            print("CklView._on_status_filter_changed: Status filter changed")  # Debug
        CklView._update_vcode_list(self)
        CklView._update_pie_chart(self)
    
    @objc.python_method
    def _update_vcode_list(self):
        """Update V-code list based on checked STIGs and status filters."""
        attrs = get_view_attrs(self)
        stigs_pane = attrs.get('stigs_pane')
        
        if not stigs_pane:
            if _CKL_DEBUG:
                print("CklView._update_vcode_list: No stigs_pane")  # Debug
            return
        
        # Get checked STIGs
        from .stigs_pane import StigsPane
        checked_stigs = StigsPane.get_checked_stigs(stigs_pane)
        if _CKL_DEBUG:
            print(f"CklView._update_vcode_list: {len(checked_stigs)} STIGs checked")  # Debug
        
        if len(checked_stigs) == 0:
            # Clear V-code list
            vcode_list_pane = attrs.get('vcode_list_pane')
            if vcode_list_pane:
                from .vcode_list_pane import VCodeListPane
                VCodeListPane.set_vuln_codes(vcode_list_pane, [])
            
            # Clear detail pane
            vcode_detail_pane = attrs.get('vcode_detail_pane')
            if vcode_detail_pane:
                CklDetailPane.set_vuln_code(vcode_detail_pane, None)
            return
        
        # Collect all V-codes from checked STIGs
        all_vuln_codes = []
        for stig_file in checked_stigs:
            all_vuln_codes.extend(stig_file.vuln_codes)
        
        if _CKL_DEBUG:
            print(f"CklView._update_vcode_list: Collected {len(all_vuln_codes)} V-codes")  # Debug
        
        # Apply status, severity, MTF, and Invalid Arg filters
        status_filter_pane = attrs.get('status_filter_pane')
        if status_filter_pane:
            from .status_filter_pane import StatusFilterPane
            enabled_statuses = StatusFilterPane.get_enabled_statuses(status_filter_pane)
            enabled_severities = StatusFilterPane.get_enabled_severities(status_filter_pane)
            mtf_filter_enabled = StatusFilterPane.is_mtf_filter_enabled(status_filter_pane)
            invalid_arg_filter_enabled = StatusFilterPane.is_invalid_arg_filter_enabled(status_filter_pane)
            if _CKL_DEBUG:
                print(f"CklView._update_vcode_list: {len(enabled_statuses)} statuses, {len(enabled_severities)} severities enabled, MTF={mtf_filter_enabled}, Invalid Arg={invalid_arg_filter_enabled}")  # Debug
            
            # Filter V-codes based on their status in the CKL, severity, MTF, and Invalid Arg
            vuln_code_to_ckl_vuln = attrs.get('vuln_code_to_ckl_vuln', {})
            filtered_vuln_codes = []
            for vc in all_vuln_codes:
                # Check status filter
                ckl_vuln = vuln_code_to_ckl_vuln.get(vc.id)
                if ckl_vuln and ckl_vuln.status in enabled_statuses:
                    # Check severity filter
                    severity = vc.severity.lower() if vc.severity else "low"
                    # Map critical to high for filtering
                    if severity == "critical":
                        severity = "high"
                    if severity in enabled_severities:
                        comments = ckl_vuln.comments.lower() if ckl_vuln.comments else ""
                        finding_details = ckl_vuln.finding_details.lower() if ckl_vuln.finding_details else ""
                        
                        # Check MTF filter (hide MTF items when enabled)
                        if mtf_filter_enabled:
                            # Skip if comments contain "MTF" or "risk-accepted"
                            if "mtf" in comments or "risk-accepted" in comments:
                                continue  # Skip this V-code
                        
                        # Check Invalid Arg filter (show ONLY Invalid Argument items when enabled)
                        if invalid_arg_filter_enabled:
                            # Only include if finding_details contain "invalid argument"
                            if "invalid argument" not in finding_details:
                                continue  # Skip this V-code
                        
                        filtered_vuln_codes.append(vc)
            
            all_vuln_codes = filtered_vuln_codes
            if _CKL_DEBUG:
                print(f"CklView._update_vcode_list: Filtered to {len(all_vuln_codes)} V-codes")  # Debug
        
        # Update V-code list
        vcode_list_pane = attrs.get('vcode_list_pane')
        if vcode_list_pane:
            from .vcode_list_pane import VCodeListPane
            # Set the selection callback in the vcode_list_pane attrs
            vcode_attrs = get_view_attrs(vcode_list_pane)
            vcode_attrs['on_selection_changed'] = lambda vc: CklView._on_vcode_selected(self, vc)
            # Now set the vuln codes (which will wire up the callback)
            # Pass vuln_code_to_ckl_vuln mapping for status-based coloring
            vuln_code_to_ckl_vuln = attrs.get('vuln_code_to_ckl_vuln', {})
            VCodeListPane.set_vuln_codes(vcode_list_pane, all_vuln_codes, vuln_code_to_ckl_vuln)
            if _CKL_DEBUG:
                print(f"CklView._update_vcode_list: Updated V-code list with {len(all_vuln_codes)} V-codes")  # Debug
    
    @objc.python_method
    def _update_pie_chart(self):
        """Update pie chart based on checked STIGs and status filters."""
        attrs = get_view_attrs(self)
        pie_chart = attrs.get('pie_chart')
        ckl_file = attrs.get('ckl_file')
        
        if _CKL_DEBUG:
            print(f"CklView._update_pie_chart: pie_chart={pie_chart is not None}, ckl_file={ckl_file.file_name if ckl_file else None}")  # Debug
        
        if not pie_chart or not ckl_file:
            if _CKL_DEBUG:
                print("CklView._update_pie_chart: No pie_chart or ckl_file")  # Debug
            return
        
        # Get checked STIGs
        stigs_pane = attrs.get('stigs_pane')
        if not stigs_pane:
            if _CKL_DEBUG:
                print("CklView._update_pie_chart: No stigs_pane")  # Debug
            return
        
        from .stigs_pane import StigsPane
        checked_stigs = StigsPane.get_checked_stigs(stigs_pane)
        if _CKL_DEBUG:
            print(f"CklView._update_pie_chart: {len(checked_stigs)} checked STIGs")  # Debug
        
        if len(checked_stigs) == 0:
            # Clear pie chart
            from .status_pie_chart import StatusPieChart
            StatusPieChart.set_vulns(pie_chart, [])
            if _CKL_DEBUG:
                print("CklView._update_pie_chart: Cleared pie chart (no STIGs checked)")  # Debug
            return
        
        # Get checked STIG IDs
        checked_stig_ids = set()
        for stig_file in checked_stigs:
            # Extract STIG ID from the stig_files
            if _CKL_DEBUG:
                print(f"CklView._update_pie_chart: Looking for STIG: {stig_file.stig_name}")  # Debug
            for stig_info in ckl_file.stigs:
                if stig_info.title == stig_file.stig_name:
                    checked_stig_ids.add(stig_info.stig_id)
                    if _CKL_DEBUG:
                        print(f"CklView._update_pie_chart: Found STIG ID: {stig_info.stig_id}")  # Debug
        
        if _CKL_DEBUG:
            print(f"CklView._update_pie_chart: checked_stig_ids={checked_stig_ids}")  # Debug
            print(f"CklView._update_pie_chart: Total CKL vulns={len(ckl_file.vulns)}")  # Debug
        
        # Filter CKL vulns by checked STIGs
        filtered_vulns = [v for v in ckl_file.vulns if v.stig_info.stig_id in checked_stig_ids]
        
        # Apply status filter
        status_filter_pane = attrs.get('status_filter_pane')
        if status_filter_pane:
            from .status_filter_pane import StatusFilterPane
            enabled_statuses = StatusFilterPane.get_enabled_statuses(status_filter_pane)
            filtered_vulns = [v for v in filtered_vulns if v.status in enabled_statuses]
            if _CKL_DEBUG:
                print(f"CklView._update_pie_chart: After status filter, {len(filtered_vulns)} vulns remain")
        
        if _CKL_DEBUG:
            print(f"CklView._update_pie_chart: Updating pie chart with {len(filtered_vulns)} vulns")  # Debug
        
        # Update pie chart
        from .status_pie_chart import StatusPieChart
        StatusPieChart.set_vulns(pie_chart, filtered_vulns)
        
        # Force redraw
        pie_chart.setNeedsDisplay_(True)
        if _CKL_DEBUG:
            print("CklView._update_pie_chart: Pie chart updated and setNeedsDisplay called")  # Debug
    
    @objc.python_method
    def _on_vcode_selected(self, vuln_code: Optional[VulnCode]):
        """Handle V-code selection change."""
        if _CKL_DEBUG:
            print(f"CklView._on_vcode_selected: V-code selected: {vuln_code.v_code if vuln_code else 'None'}")  # Debug
        attrs = get_view_attrs(self)
        vcode_detail_pane = attrs.get('vcode_detail_pane')
        
        if not vcode_detail_pane:
            if _CKL_DEBUG:
                print("CklView._on_vcode_selected: No detail pane")  # Debug
            return
        
        if vuln_code is None:
            CklDetailPane.set_vuln_code(vcode_detail_pane, None)
            if _CKL_DEBUG:
                print("CklView._on_vcode_selected: Cleared detail pane")  # Debug
            return
        
        # Look up the corresponding CklVuln to get finding_details and comments
        vuln_code_to_ckl_vuln = attrs.get('vuln_code_to_ckl_vuln', {})
        ckl_vuln = vuln_code_to_ckl_vuln.get(vuln_code.id)
        
        if ckl_vuln:
            if _CKL_DEBUG:
                print(f"CklView._on_vcode_selected: Found CKL vuln with finding_details and comments")  # Debug
            CklDetailPane.set_vuln_code(
                vcode_detail_pane,
                vuln_code,
                finding_details=ckl_vuln.finding_details,
                comments=ckl_vuln.comments
            )
        else:
            if _CKL_DEBUG:
                print(f"CklView._on_vcode_selected: No CKL vuln found, using defaults")  # Debug
            CklDetailPane.set_vuln_code(vcode_detail_pane, vuln_code, finding_details="", comments="")
        
        if _CKL_DEBUG:
            print(f"CklView._on_vcode_selected: Updated detail pane")  # Debug

