"""Compare view for comparing two STIG files."""

from AppKit import (
    NSView, NSRect, NSSplitView, NSTextField, NSButton, NSScrollView, NSTextView,
    NSTableView, NSTableColumn,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
import objc

from .view_helpers import get_view_attrs, get_bounds_size


class CompareListDataSource(NSObject):
    """Data source for comparison list tables."""
    
    def init(self):
        """Initialize the data source."""
        self = objc.super(CompareListDataSource, self).init()
        if self is None:
            return None
        attrs = get_view_attrs(self)
        attrs['data'] = []
        return self
    
    @objc.python_method
    def set_data(self, vcodes):
        """Set the V-code list data."""
        attrs = get_view_attrs(self)
        attrs['data'] = list(vcodes) if vcodes else []
    
    def numberOfRowsInTableView_(self, table_view):
        """Return the number of rows."""
        attrs = get_view_attrs(self)
        return len(attrs.get('data', []))
    
    def tableView_objectValueForTableColumn_row_(self, table_view, table_column, row):
        """Return the value for a cell."""
        attrs = get_view_attrs(self)
        data = attrs.get('data', [])
        if 0 <= row < len(data):
            return data[row]
        return ""


class CompareListDelegate(NSObject):
    """Delegate for comparison list table selection."""
    
    def init(self):
        """Initialize the delegate."""
        self = objc.super(CompareListDelegate, self).init()
        if self is None:
            return None
        attrs = get_view_attrs(self)
        attrs['compare_view'] = None
        attrs['list_index'] = 0  # 0=B-only, 1=A-only, 2=Both-different
        return self
    
    @objc.python_method
    def set_compare_view(self, compare_view):
        """Set the compare view reference."""
        attrs = get_view_attrs(self)
        attrs['compare_view'] = compare_view
    
    @objc.python_method
    def set_list_index(self, index):
        """Set which list this delegate is for."""
        attrs = get_view_attrs(self)
        attrs['list_index'] = index
    
    def tableViewSelectionDidChange_(self, notification):
        """Handle table view selection change."""
        attrs = get_view_attrs(self)
        compare_view = attrs.get('compare_view')
        if not compare_view:
            return
        
        table_view = notification.object()
        selected_row = table_view.selectedRow()
        
        if selected_row >= 0:
            # Get the V-code ID from the data source
            data_source = table_view.dataSource()
            data = get_view_attrs(data_source).get('data', [])
            if 0 <= selected_row < len(data):
                vcode_id = data[selected_row]
                list_index = attrs.get('list_index', 0)
                compare_view.on_vcode_selected(vcode_id, list_index)


class CompareView(NSView):
    """Compare tab view with three columns for STIG comparison."""
    
    def init(self):
        """Initialize the compare view."""
        self = objc.super(CompareView, self).init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['stig_a'] = None
        attrs['stig_b'] = None
        attrs['main_window'] = None  # Will be set by main_window when tab is added
        attrs['table_data_sources'] = []  # Will store 3 data sources for the 3 lists
        attrs['table_views'] = []  # Will store 3 table views
        attrs['table_delegates'] = []  # Will store 3 delegates for the 3 lists
        attrs['detail_text_views'] = []  # Will store 4 text views for Column 3
        attrs['severity_filters'] = {'high': True, 'medium': True, 'low_other': True}  # Default: all checked
        attrs['unfiltered_data'] = {'in_b_not_a': [], 'in_a_not_b': [], 'different': []}  # Store original data
        CompareView.createLayout(self)
        return self
    
    def createLayout(self):
        """Create the three-column layout."""
        print("CompareView.createLayout: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 1200, 800
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
        
        # Create main horizontal split view (3 columns)
        main_split = NSSplitView.alloc().initWithFrame_(bounds)
        main_split.setVertical_(True)  # Vertical divider (splits horizontally)
        main_split.setDividerStyle_(1)  # NSSplitViewDividerStyleThin
        main_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Column 1: STIG loader + search pane (20% width)
        col1_frame = NSRect((0, 0), (width * 0.2, height))
        col1 = self._create_column1(col1_frame)
        main_split.addSubview_(col1)
        
        # Column 2: Three comparison lists (40% width)
        col2_frame = NSRect((0, 0), (width * 0.4, height))
        col2 = self._create_column2(col2_frame)
        main_split.addSubview_(col2)
        
        # Column 3: Four detail panes (40% width)
        col3_frame = NSRect((0, 0), (width * 0.4, height))
        col3 = self._create_column3(col3_frame)
        main_split.addSubview_(col3)
        
        main_split.adjustSubviews()
        
        self.addSubview_(main_split)
        
        # Store references
        attrs = get_view_attrs(self)
        attrs['main_split'] = main_split
        attrs['col1'] = col1
        attrs['col2'] = col2
        attrs['col3'] = col3
        
        print("CompareView.createLayout: Complete")  # Debug
    
    def closeCompareTab_(self, sender):
        """Close the Compare tab."""
        print("CompareView.closeCompareTab_: Called")  # Debug
        attrs = get_view_attrs(self)
        main_window = attrs.get('main_window')
        if main_window:
            print("CompareView.closeCompareTab_: Calling main_window.remove_compare_tab")  # Debug
            main_window.remove_compare_tab()
        else:
            print("CompareView.closeCompareTab_: WARNING - No main_window reference!")  # Debug
    
    def highSeverityFilterChanged_(self, sender):
        """Handle High severity filter checkbox change."""
        attrs = get_view_attrs(self)
        attrs['severity_filters']['high'] = (sender.state() == 1)
        print(f"CompareView.highSeverityFilterChanged_: High filter = {attrs['severity_filters']['high']}")  # Debug
        self._apply_filters()
    
    def mediumSeverityFilterChanged_(self, sender):
        """Handle Medium severity filter checkbox change."""
        attrs = get_view_attrs(self)
        attrs['severity_filters']['medium'] = (sender.state() == 1)
        print(f"CompareView.mediumSeverityFilterChanged_: Medium filter = {attrs['severity_filters']['medium']}")  # Debug
        self._apply_filters()
    
    def lowOtherSeverityFilterChanged_(self, sender):
        """Handle Low/Other severity filter checkbox change."""
        attrs = get_view_attrs(self)
        attrs['severity_filters']['low_other'] = (sender.state() == 1)
        print(f"CompareView.lowOtherSeverityFilterChanged_: Low/Other filter = {attrs['severity_filters']['low_other']}")  # Debug
        self._apply_filters()
    
    @objc.python_method
    def on_vcode_selected(self, display_string, list_index):
        """Handle V-code selection from one of the comparison lists.
        
        Args:
            display_string: The display string (may include Rule Title: "V-257987 - Rule Title" or just "V-257987")
            list_index: 0=In B not A, 1=In A not B, 2=In Both (Different)
        """
        print(f"CompareView.on_vcode_selected: display_string={display_string}, list_index={list_index}")  # Debug
        
        # Extract just the V-code from the display string (before " - " if present)
        if ' - ' in display_string:
            vcode_str = display_string.split(' - ')[0]
        else:
            vcode_str = display_string
        
        print(f"CompareView.on_vcode_selected: Extracted vcode_str={vcode_str}")  # Debug
        
        attrs = get_view_attrs(self)
        stig_a = attrs.get('stig_a')
        stig_b = attrs.get('stig_b')
        detail_text_views = attrs.get('detail_text_views', [])
        
        if len(detail_text_views) != 4:
            print(f"CompareView.on_vcode_selected: ERROR - Expected 4 detail text views, got {len(detail_text_views)}")
            return
        
        # Find the VulnCode objects (match by v_code field, not id)
        vuln_a = None
        vuln_b = None
        
        if stig_a:
            for vc in stig_a.vuln_codes:
                if vc.v_code == vcode_str:
                    vuln_a = vc
                    break
        
        if stig_b:
            for vc in stig_b.vuln_codes:
                if vc.v_code == vcode_str:
                    vuln_b = vc
                    break
        
        # Populate Column 3 based on which list was selected
        if list_index == 0:  # In B, not in A
            self._populate_detail_panes(None, vuln_b, detail_text_views)
        elif list_index == 1:  # In A, not in B
            self._populate_detail_panes(vuln_a, None, detail_text_views)
        elif list_index == 2:  # In both (different)
            self._populate_detail_panes(vuln_a, vuln_b, detail_text_views)
    
    @objc.python_method
    def _populate_detail_panes(self, vuln_a, vuln_b, detail_text_views):
        """Populate the 4 detail text views with V-code information."""
        from AppKit import NSColor, NSFont
        
        # Check if this is a comparison (both exist) or single-sided
        is_comparison = (vuln_a is not None and vuln_b is not None)
        
        # Pane 0: STIG A General Info
        if vuln_a:
            content = f"V-Code: {vuln_a.v_code}\n"
            content += f"Rule ID: {vuln_a.rule_id}\n"
            content += f"Severity: {vuln_a.severity.upper()}\n"
            content += f"Group Title: {vuln_a.group_title}\n"
            content += f"Rule Title: {vuln_a.rule_title}\n"
            detail_text_views[0].setString_(content)
        else:
            detail_text_views[0].setString_("(No V-code in STIG A)")
        
        # Pane 1: STIG A Details
        if vuln_a:
            content = f"Discussion:\n{vuln_a.discussion}\n\n"
            content += f"Check:\n{vuln_a.check_text}\n\n"
            content += f"Fix:\n{vuln_a.fix_text}\n"
            detail_text_views[1].setString_(content)
        else:
            detail_text_views[1].setString_("(No V-code in STIG A)")
        
        # Pane 2: STIG B General Info (or Differences if comparing)
        if is_comparison:
            # Show only differences
            content = self._build_general_differences(vuln_a, vuln_b)
            detail_text_views[2].setString_(content if content else "(No differences in general info)")
        elif vuln_b:
            content = f"V-Code: {vuln_b.v_code}\n"
            content += f"Rule ID: {vuln_b.rule_id}\n"
            content += f"Severity: {vuln_b.severity.upper()}\n"
            content += f"Group Title: {vuln_b.group_title}\n"
            content += f"Rule Title: {vuln_b.rule_title}\n"
            detail_text_views[2].setString_(content)
        else:
            detail_text_views[2].setString_("(No V-code in STIG B)")
        
        # Pane 3: STIG B Details (or Differences if comparing)
        if is_comparison:
            # Show only differences
            content = self._build_detail_differences(vuln_a, vuln_b)
            detail_text_views[3].setString_(content if content else "(No differences in details)")
        elif vuln_b:
            content = f"Discussion:\n{vuln_b.discussion}\n\n"
            content += f"Check:\n{vuln_b.check_text}\n\n"
            content += f"Fix:\n{vuln_b.fix_text}\n"
            detail_text_views[3].setString_(content)
        else:
            detail_text_views[3].setString_("(No V-code in STIG B)")
        
        # Set text appearance for all panes
        for text_view in detail_text_views:
            text_view.setTextColor_(NSColor.whiteColor())
            text_view.setBackgroundColor_(NSColor.blackColor())
            text_view.setFont_(NSFont.systemFontOfSize_(12))
            text_view.setNeedsDisplay_(True)
    
    @objc.python_method
    def _build_general_differences(self, vuln_a, vuln_b):
        """Build a string showing only the general info fields that differ."""
        differences = []
        
        # Compare V-Code
        if vuln_a.v_code != vuln_b.v_code:
            differences.append(f"V-Code:\n  A: {vuln_a.v_code}\n  B: {vuln_b.v_code}\n")
        
        # Compare Rule ID
        if vuln_a.rule_id != vuln_b.rule_id:
            differences.append(f"Rule ID:\n  A: {vuln_a.rule_id}\n  B: {vuln_b.rule_id}\n")
        
        # Compare Severity
        if vuln_a.severity != vuln_b.severity:
            differences.append(f"Severity:\n  A: {vuln_a.severity.upper()}\n  B: {vuln_b.severity.upper()}\n")
        
        # Compare Group Title
        if vuln_a.group_title != vuln_b.group_title:
            differences.append(f"Group Title:\n  A: {vuln_a.group_title}\n  B: {vuln_b.group_title}\n")
        
        # Compare Rule Title
        if vuln_a.rule_title != vuln_b.rule_title:
            differences.append(f"Rule Title:\n  A: {vuln_a.rule_title}\n  B: {vuln_b.rule_title}\n")
        
        return "\n".join(differences)
    
    @objc.python_method
    def _build_detail_differences(self, vuln_a, vuln_b):
        """Build a string showing only the detail fields that differ."""
        differences = []
        
        # Compare Discussion
        if vuln_a.discussion != vuln_b.discussion:
            differences.append(f"Discussion:\n  A: {vuln_a.discussion}\n\n  B: {vuln_b.discussion}\n")
        
        # Compare Check Text
        if vuln_a.check_text != vuln_b.check_text:
            differences.append(f"Check:\n  A: {vuln_a.check_text}\n\n  B: {vuln_b.check_text}\n")
        
        # Compare Fix Text
        if vuln_a.fix_text != vuln_b.fix_text:
            differences.append(f"Fix:\n  A: {vuln_a.fix_text}\n\n  B: {vuln_b.fix_text}\n")
        
        return "\n".join(differences)
    
    def loadStigA_(self, sender):
        """Load STIG A file."""
        print("CompareView.loadStigA_: Called")  # Debug
        from AppKit import NSOpenPanel, NSFileHandlingPanelOKButton
        from pathlib import Path
        
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setMessage_("Select STIG A file")
        panel.setAllowedFileTypes_(["zip", "xml"])
        
        result = panel.runModal()
        if result == NSFileHandlingPanelOKButton:
            file_url = panel.URL()
            if file_url:
                file_path = file_url.path()
                print(f"CompareView.loadStigA_: Selected file: {file_path}")  # Debug
                
                # Store the path
                attrs = get_view_attrs(self)
                attrs['stig_a_path'] = file_path
                
                # Update the text field to show filename
                stig_a_field = attrs.get('stig_a_field')
                if stig_a_field:
                    filename = Path(file_path).name
                    stig_a_field.setStringValue_(filename)
                    from AppKit import NSColor
                    stig_a_field.setTextColor_(NSColor.whiteColor())  # Change to white when file selected
                    print(f"CompareView.loadStigA_: Updated field with '{filename}'")  # Debug
                else:
                    print("CompareView.loadStigA_: WARNING - stig_a_field not found!")  # Debug
                
                # Check if we should enable the Compare button
                self._update_compare_button_state()
        else:
            print("CompareView.loadStigA_: User cancelled")  # Debug
    
    def loadStigB_(self, sender):
        """Load STIG B file."""
        print("CompareView.loadStigB_: Called")  # Debug
        from AppKit import NSOpenPanel, NSFileHandlingPanelOKButton
        from pathlib import Path
        
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setMessage_("Select STIG B file")
        panel.setAllowedFileTypes_(["zip", "xml"])
        
        result = panel.runModal()
        if result == NSFileHandlingPanelOKButton:
            file_url = panel.URL()
            if file_url:
                file_path = file_url.path()
                print(f"CompareView.loadStigB_: Selected file: {file_path}")  # Debug
                
                # Store the path
                attrs = get_view_attrs(self)
                attrs['stig_b_path'] = file_path
                
                # Update the text field to show filename
                stig_b_field = attrs.get('stig_b_field')
                if stig_b_field:
                    filename = Path(file_path).name
                    stig_b_field.setStringValue_(filename)
                    from AppKit import NSColor
                    stig_b_field.setTextColor_(NSColor.whiteColor())  # Change to white when file selected
                    print(f"CompareView.loadStigB_: Updated field with '{filename}'")  # Debug
                else:
                    print("CompareView.loadStigB_: WARNING - stig_b_field not found!")  # Debug
                
                # Check if we should enable the Compare button
                self._update_compare_button_state()
        else:
            print("CompareView.loadStigB_: User cancelled")  # Debug
    
    @objc.python_method
    def _update_compare_button_state(self):
        """Enable Compare button if both STIG A and B are loaded."""
        attrs = get_view_attrs(self)
        stig_a_path = attrs.get('stig_a_path')
        stig_b_path = attrs.get('stig_b_path')
        compare_btn = attrs.get('compare_btn')
        
        if compare_btn:
            should_enable = bool(stig_a_path and stig_b_path)
            compare_btn.setEnabled_(should_enable)
            status = "enabled" if should_enable else "disabled"
            print(f"CompareView._update_compare_button_state: Compare button {status} (A={bool(stig_a_path)}, B={bool(stig_b_path)})")  # Debug
        else:
            print("CompareView._update_compare_button_state: WARNING - compare_btn not found!")  # Debug
    
    def compareStigs_(self, sender):
        """Compare the two loaded STIGs."""
        print("CompareView.compareStigs_: Called")  # Debug
        attrs = get_view_attrs(self)
        stig_a_path = attrs.get('stig_a_path')
        stig_b_path = attrs.get('stig_b_path')
        
        if not stig_a_path or not stig_b_path:
            print("CompareView.compareStigs_: ERROR - Missing STIG file(s)")  # Debug
            return
        
        print(f"CompareView.compareStigs_: Comparing {stig_a_path} vs {stig_b_path}")  # Debug
        
        try:
            # Load and parse both STIGs
            from ..parsers.stig_parser import StigParser
            from pathlib import Path
            
            print("CompareView.compareStigs_: Loading STIG A...")  # Debug
            stig_a = StigParser.parse(Path(stig_a_path))
            print(f"CompareView.compareStigs_: STIG A loaded: {len(stig_a.vuln_codes)} V-codes")  # Debug
            
            print("CompareView.compareStigs_: Loading STIG B...")  # Debug
            stig_b = StigParser.parse(Path(stig_b_path))
            print(f"CompareView.compareStigs_: STIG B loaded: {len(stig_b.vuln_codes)} V-codes")  # Debug
            
            # Store the parsed STIGs
            attrs['stig_a'] = stig_a
            attrs['stig_b'] = stig_b
            
            # Compare V-codes
            print("CompareView.compareStigs_: Comparing V-codes...")  # Debug
            a_vcodes = {vc.id for vc in stig_a.vuln_codes}
            b_vcodes = {vc.id for vc in stig_b.vuln_codes}
            
            in_b_not_a = sorted(b_vcodes - a_vcodes)
            in_a_not_b = sorted(a_vcodes - b_vcodes)
            in_both = sorted(a_vcodes & b_vcodes)
            
            print(f"CompareView.compareStigs_: In B, not in A: {len(in_b_not_a)}")  # Debug
            print(f"CompareView.compareStigs_: In A, not in B: {len(in_a_not_b)}")  # Debug
            print(f"CompareView.compareStigs_: In both: {len(in_both)}")  # Debug
            
            # Find V-codes that are in both but have differences
            print("CompareView.compareStigs_: Checking for differences...")  # Debug
            different = self._find_different_vcodes(stig_a, stig_b, in_both)
            print(f"CompareView.compareStigs_: V-codes with differences: {len(different)}")  # Debug
            
            # Store unfiltered data (as V-code IDs)
            attrs['unfiltered_data'] = {
                'in_b_not_a': in_b_not_a,
                'in_a_not_b': in_a_not_b,
                'different': different
            }
            
            # Apply filters and update the three lists
            self._apply_filters()
            
        except Exception as e:
            import traceback
            print(f"CompareView.compareStigs_: ERROR - {e}")  # Debug
            traceback.print_exc()
    
    @objc.python_method
    def _apply_filters(self):
        """Apply severity filters to the comparison lists."""
        attrs = get_view_attrs(self)
        stig_a = attrs.get('stig_a')
        stig_b = attrs.get('stig_b')
        unfiltered_data = attrs.get('unfiltered_data', {})
        severity_filters = attrs.get('severity_filters', {})
        
        if not stig_a or not stig_b:
            return
        
        # Build lookup dictionaries
        a_lookup = {vc.id: vc for vc in stig_a.vuln_codes}
        b_lookup = {vc.id: vc for vc in stig_b.vuln_codes}
        
        # Filter and format "In B, Not in A" list
        in_b_not_a_filtered = []
        for vcode_id in unfiltered_data.get('in_b_not_a', []):
            vuln = b_lookup.get(vcode_id)
            if vuln and self._passes_severity_filter(vuln.severity, severity_filters):
                # Format: "V-257987 - Rule Title"
                in_b_not_a_filtered.append(f"{vuln.v_code} - {vuln.rule_title}")
        
        # Filter and format "In A, Not in B" list
        in_a_not_b_filtered = []
        for vcode_id in unfiltered_data.get('in_a_not_b', []):
            vuln = a_lookup.get(vcode_id)
            if vuln and self._passes_severity_filter(vuln.severity, severity_filters):
                # Format: "V-257987 - Rule Title"
                in_a_not_b_filtered.append(f"{vuln.v_code} - {vuln.rule_title}")
        
        # Filter "In Both (Different)" list (no Rule Title, just V-code)
        different_filtered = []
        for vcode_id in unfiltered_data.get('different', []):
            # Check if either A or B passes the filter (show if at least one version is relevant)
            vuln_a = a_lookup.get(vcode_id)
            vuln_b = b_lookup.get(vcode_id)
            if ((vuln_a and self._passes_severity_filter(vuln_a.severity, severity_filters)) or
                (vuln_b and self._passes_severity_filter(vuln_b.severity, severity_filters))):
                # Just show V-code for "different" list
                if vuln_a:
                    different_filtered.append(vuln_a.v_code)
                elif vuln_b:
                    different_filtered.append(vuln_b.v_code)
        
        # Update the three lists
        self._update_comparison_lists(in_b_not_a_filtered, in_a_not_b_filtered, different_filtered)
        
        print(f"CompareView._apply_filters: Filtered to {len(in_b_not_a_filtered)}, {len(in_a_not_b_filtered)}, {len(different_filtered)} items")  # Debug
    
    @objc.python_method
    def _passes_severity_filter(self, severity, severity_filters):
        """Check if a severity passes the current filters.
        
        Args:
            severity: The severity string (e.g. 'high', 'medium', 'low')
            severity_filters: Dict with 'high', 'medium', 'low_other' keys
            
        Returns:
            True if this severity should be shown, False if filtered out
        """
        severity_lower = severity.lower() if severity else 'low'
        
        if severity_lower == 'high':
            return severity_filters.get('high', True)
        elif severity_lower == 'medium':
            return severity_filters.get('medium', True)
        else:  # low, critical, or anything else
            return severity_filters.get('low_other', True)
    
    @objc.python_method
    def _find_different_vcodes(self, stig_a, stig_b, common_vcode_ids):
        """Find V-codes that exist in both STIGs but have differences.
        
        Args:
            stig_a: First STIG file object
            stig_b: Second STIG file object
            common_vcode_ids: Set of V-code IDs present in both STIGs
            
        Returns:
            List of V-code IDs that have differences
        """
        different = []
        
        # Build lookup dictionaries for fast access
        a_lookup = {vc.id: vc for vc in stig_a.vuln_codes}
        b_lookup = {vc.id: vc for vc in stig_b.vuln_codes}
        
        for vcode_id in common_vcode_ids:
            vuln_a = a_lookup.get(vcode_id)
            vuln_b = b_lookup.get(vcode_id)
            
            if not vuln_a or not vuln_b:
                continue
            
            # Check if any field differs
            if self._has_differences(vuln_a, vuln_b):
                different.append(vcode_id)
        
        return sorted(different)
    
    @objc.python_method
    def _has_differences(self, vuln_a, vuln_b):
        """Check if two VulnCode objects have any differences.
        
        Returns:
            True if any field differs, False if all fields are identical
        """
        # Check general info fields
        if vuln_a.v_code != vuln_b.v_code:
            return True
        if vuln_a.rule_id != vuln_b.rule_id:
            return True
        if vuln_a.severity != vuln_b.severity:
            return True
        if vuln_a.group_title != vuln_b.group_title:
            return True
        if vuln_a.rule_title != vuln_b.rule_title:
            return True
        
        # Check detail fields
        if vuln_a.discussion != vuln_b.discussion:
            return True
        if vuln_a.check_text != vuln_b.check_text:
            return True
        if vuln_a.fix_text != vuln_b.fix_text:
            return True
        
        # All fields are identical
        return False
    
    @objc.python_method
    def _update_comparison_lists(self, in_b_not_a, in_a_not_b, different):
        """Update the three comparison list panes with results."""
        print(f"CompareView._update_comparison_lists: Called with {len(in_b_not_a)}, {len(in_a_not_b)}, {len(different)} items")  # Debug
        
        attrs = get_view_attrs(self)
        col2 = attrs.get('col2')
        if not col2:
            print("CompareView._update_comparison_lists: WARNING - col2 not found!")  # Debug
            return
        
        # Get the three list panes from col2 split view
        subviews = col2.subviews()
        if len(subviews) < 3:
            print(f"CompareView._update_comparison_lists: WARNING - Expected 3 subviews, got {len(subviews)}")  # Debug
            return
        
        # Update each list
        self._update_list_pane(subviews[0], "In B, Not in A", in_b_not_a)
        self._update_list_pane(subviews[1], "In A, Not in B", in_a_not_b)
        self._update_list_pane(subviews[2], "In Both (Different)", different)
        
        print("CompareView._update_comparison_lists: All lists updated")  # Debug
    
    @objc.python_method
    def _update_list_pane(self, scroll_view, title, vcodes):
        """Update a single list pane with V-codes."""
        print(f"CompareView._update_list_pane: Updating '{title}' with {len(vcodes)} V-codes...")  # Debug
        
        # The pane is now the scroll view directly
        if scroll_view.className() == "NSScrollView":
            table_view = scroll_view.documentView()
            if table_view and table_view.className() == "NSTableView":
                # Get the data source and update it
                data_source = table_view.dataSource()
                if data_source:
                    data_source.set_data(vcodes)
                    table_view.reloadData()
                    print(f"CompareView._update_list_pane: Updated '{title}' table with {len(vcodes)} rows")  # Debug
                    return
        
        print(f"CompareView._update_list_pane: WARNING - Could not find table view in '{title}' pane")  # Debug
    
    def _create_column1(self, frame):
        """Create Column 1: STIG loader pane + search pane."""
        width, height = get_bounds_size(frame)
        
        col1_split = NSSplitView.alloc().initWithFrame_(frame)
        col1_split.setVertical_(False)  # Horizontal divider (stacks vertically)
        col1_split.setDividerStyle_(1)  # Visible divider
        col1_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Top: STIG loader pane
        loader_frame = NSRect((0, 0), (width, height * 0.6))
        loader_pane = self._create_loader_pane(loader_frame)
        col1_split.addSubview_(loader_pane)
        
        # Bottom: Search pane
        search_frame = NSRect((0, 0), (width, height * 0.4))
        search_pane = self._create_search_pane(search_frame)
        col1_split.addSubview_(search_pane)
        
        col1_split.adjustSubviews()
        
        return col1_split
    
    def _create_loader_pane(self, frame):
        """Create STIG loader pane with Load A/B buttons and Compare button."""
        from AppKit import NSColor, NSBox
        width, height = get_bounds_size(frame)
        
        print(f"CompareView._create_loader_pane: frame size = {width}x{height}")  # Debug
        
        # Use NSBox for border
        pane = NSBox.alloc().initWithFrame_(frame)
        pane.setBoxType_(3)  # NSBoxCustom
        pane.setBorderType_(1)  # NSLineBorder
        pane.setTitlePosition_(0)  # NSNoTitle
        pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Content view inside the box
        content = pane.contentView()
        content_bounds = content.bounds()
        content_width, content_height = get_bounds_size(content_bounds)
        
        print(f"CompareView._create_loader_pane: content size = {content_width}x{content_height}")  # Debug
        
        # Position elements from top down (use actual content height)
        y_pos = content_height - 45  # Start from top with larger margin to avoid clipping
        
        # Load STIG A button (top)
        load_a_btn = NSButton.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 28)))
        load_a_btn.setTitle_("Load STIG A")
        load_a_btn.setButtonType_(0)  # NSMomentaryLightButton
        load_a_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        load_a_btn.setAutoresizingMask_(0x08 | 0x02)  # NSViewMinYMargin | NSViewWidthSizable - pin to top, stretch width
        load_a_btn.setTarget_(self)
        load_a_btn.setAction_("loadStigA:")
        content.addSubview_(load_a_btn)
        print(f"CompareView._create_loader_pane: Added Load A button at y={y_pos}")  # Debug
        y_pos -= 33
        
        # STIG A filename text field
        stig_a_field = NSTextField.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 22)))
        stig_a_field.setStringValue_("(No file selected)")
        stig_a_field.setBezeled_(True)
        stig_a_field.setDrawsBackground_(True)
        stig_a_field.setEditable_(False)
        stig_a_field.setSelectable_(False)
        stig_a_field.setTextColor_(NSColor.grayColor())
        stig_a_field.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, stretch width
        content.addSubview_(stig_a_field)
        print(f"CompareView._create_loader_pane: Added STIG A field at y={y_pos}")  # Debug
        y_pos -= 40
        
        # Load STIG B button
        load_b_btn = NSButton.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 28)))
        load_b_btn.setTitle_("Load STIG B")
        load_b_btn.setButtonType_(0)  # NSMomentaryLightButton
        load_b_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        load_b_btn.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, stretch width
        load_b_btn.setTarget_(self)
        load_b_btn.setAction_("loadStigB:")
        content.addSubview_(load_b_btn)
        print(f"CompareView._create_loader_pane: Added Load B button at y={y_pos}")  # Debug
        y_pos -= 33
        
        # STIG B filename text field
        stig_b_field = NSTextField.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 22)))
        stig_b_field.setStringValue_("(No file selected)")
        stig_b_field.setBezeled_(True)
        stig_b_field.setDrawsBackground_(True)
        stig_b_field.setEditable_(False)
        stig_b_field.setSelectable_(False)
        stig_b_field.setTextColor_(NSColor.grayColor())
        stig_b_field.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, stretch width
        content.addSubview_(stig_b_field)
        print(f"CompareView._create_loader_pane: Added STIG B field at y={y_pos}")  # Debug
        y_pos -= 50
        
        # Compare STIGs button
        compare_btn = NSButton.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 28)))
        compare_btn.setTitle_("Compare STIGs")
        compare_btn.setButtonType_(0)  # NSMomentaryLightButton
        compare_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        compare_btn.setEnabled_(False)  # Disabled until both files loaded
        compare_btn.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, stretch width
        compare_btn.setTarget_(self)
        compare_btn.setAction_("compareStigs:")
        content.addSubview_(compare_btn)
        print(f"CompareView._create_loader_pane: Added Compare button at y={y_pos}")  # Debug
        
        # Store references on both the pane and the view itself for easy access
        attrs = get_view_attrs(pane)
        attrs['load_a_btn'] = load_a_btn
        attrs['load_b_btn'] = load_b_btn
        attrs['stig_a_field'] = stig_a_field
        attrs['stig_b_field'] = stig_b_field
        attrs['compare_btn'] = compare_btn
        
        # Also store on the CompareView itself for access from action methods
        self_attrs = get_view_attrs(self)
        self_attrs['stig_a_field'] = stig_a_field
        self_attrs['stig_b_field'] = stig_b_field
        self_attrs['compare_btn'] = compare_btn
        
        return pane
    
    def _create_search_pane(self, frame):
        """Create search pane with close button."""
        from AppKit import NSColor, NSBox
        width, height = get_bounds_size(frame)
        
        print(f"CompareView._create_search_pane: frame size = {width}x{height}")  # Debug
        
        # Use NSBox for border
        pane = NSBox.alloc().initWithFrame_(frame)
        pane.setBoxType_(3)  # NSBoxCustom
        pane.setBorderType_(1)  # NSLineBorder
        pane.setTitlePosition_(0)  # NSNoTitle
        pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Content view inside the box
        content = pane.contentView()
        content_bounds = content.bounds()
        content_width, content_height = get_bounds_size(content_bounds)
        
        print(f"CompareView._create_search_pane: content size = {content_width}x{content_height}")  # Debug
        
        # Position elements from top
        y_pos = content_height - 35
        
        # Title label at top
        label = NSTextField.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 24)))
        label.setStringValue_("Severity Filters")
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(NSColor.whiteColor())
        label.setAutoresizingMask_(0x08 | 0x02)  # NSViewMinYMargin | NSViewWidthSizable - pin to top
        content.addSubview_(label)
        print(f"CompareView._create_search_pane: Added label at y={y_pos}")  # Debug
        y_pos -= 40
        
        # High severity checkbox
        high_cb = NSButton.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 22)))
        high_cb.setTitle_("High")
        high_cb.setButtonType_(3)  # NSSwitchButton (checkbox)
        high_cb.setState_(1)  # Checked by default
        high_cb.setTarget_(self)
        high_cb.setAction_("highSeverityFilterChanged:")
        high_cb.setAutoresizingMask_(0x08 | 0x02)  # Pin to top
        content.addSubview_(high_cb)
        y_pos -= 25
        
        # Medium severity checkbox
        medium_cb = NSButton.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 22)))
        medium_cb.setTitle_("Medium")
        medium_cb.setButtonType_(3)  # NSSwitchButton (checkbox)
        medium_cb.setState_(1)  # Checked by default
        medium_cb.setTarget_(self)
        medium_cb.setAction_("mediumSeverityFilterChanged:")
        medium_cb.setAutoresizingMask_(0x08 | 0x02)  # Pin to top
        content.addSubview_(medium_cb)
        y_pos -= 25
        
        # Low/Other severity checkbox
        low_cb = NSButton.alloc().initWithFrame_(NSRect((10, y_pos), (content_width - 20, 22)))
        low_cb.setTitle_("Low/Other")
        low_cb.setButtonType_(3)  # NSSwitchButton (checkbox)
        low_cb.setState_(1)  # Checked by default
        low_cb.setTarget_(self)
        low_cb.setAction_("lowOtherSeverityFilterChanged:")
        low_cb.setAutoresizingMask_(0x08 | 0x02)  # Pin to top
        content.addSubview_(low_cb)
        
        # Store checkbox references
        attrs = get_view_attrs(self)
        attrs['high_severity_cb'] = high_cb
        attrs['medium_severity_cb'] = medium_cb
        attrs['low_other_severity_cb'] = low_cb
        
        # Close Compare Tab button at bottom
        close_btn = NSButton.alloc().initWithFrame_(NSRect((10, 10), (content_width - 20, 28)))
        close_btn.setTitle_("Close Compare Tab")
        close_btn.setButtonType_(0)  # NSMomentaryLightButton
        close_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        close_btn.setTarget_(self)
        close_btn.setAction_("closeCompareTab:")
        close_btn.setAutoresizingMask_(0x02)  # NSViewWidthSizable - stays at bottom, stretches width
        content.addSubview_(close_btn)
        print(f"CompareView._create_search_pane: Added Close button at y=10")  # Debug
        
        # Store reference
        attrs = get_view_attrs(pane)
        attrs['close_btn'] = close_btn
        
        return pane
    
    def _create_column2(self, frame):
        """Create Column 2: Three comparison lists."""
        width, height = get_bounds_size(frame)
        
        col2_split = NSSplitView.alloc().initWithFrame_(frame)
        col2_split.setVertical_(False)  # Horizontal divider (stacks vertically)
        col2_split.setDividerStyle_(1)  # NSSplitViewDividerStyleThin - thin visible divider
        col2_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        third_height = height / 3
        
        # Top: V-codes in B but not in A (list_index=0)
        list1_frame = NSRect((0, 0), (width, third_height))
        list1 = self._create_list_pane(list1_frame, "In B, Not in A", 0)
        list1.setToolTip_("V-codes that exist in STIG B but not in STIG A (new requirements added to newer STIG)")
        col2_split.addSubview_(list1)
        
        # Middle: V-codes in A but not in B (list_index=1)
        list2_frame = NSRect((0, 0), (width, third_height))
        list2 = self._create_list_pane(list2_frame, "In A, Not in B", 1)
        list2.setToolTip_("V-codes that exist in STIG A but not in STIG B (requirements removed or deprecated in newer STIG)")
        col2_split.addSubview_(list2)
        
        # Bottom: V-codes in both but different (list_index=2)
        list3_frame = NSRect((0, 0), (width, third_height))
        list3 = self._create_list_pane(list3_frame, "In Both (Different)", 2)
        list3.setToolTip_("V-codes that exist in both STIGs but have differences in content (severity, title, discussion, check, or fix text)")
        col2_split.addSubview_(list3)
        
        # Let split view handle layout naturally
        col2_split.adjustSubviews()
        
        return col2_split
    
    def _create_list_pane(self, frame, title, list_index):
        """Create a list pane with a table view."""
        from AppKit import NSColor
        width, height = get_bounds_size(frame)
        
        print(f"CompareView._create_list_pane: '{title}' frame size = {width}x{height}")  # Debug
        
        # Create scroll view for the table - return this directly as the pane
        scroll_view = NSScrollView.alloc().initWithFrame_(frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)  # NSBezelBorder
        
        # Create table view
        table_frame = NSRect((0, 0), (width, height))
        table_view = NSTableView.alloc().initWithFrame_(table_frame)
        table_view.setUsesAlternatingRowBackgroundColors_(True)  # Enable alternating stripes
        table_view.setRowHeight_(20.0)
        table_view.setHeaderView_(None)  # No column headers
        
        # Create single column for V-code
        column = NSTableColumn.alloc().initWithIdentifier_("vcode")
        column.setWidth_(width - 20)
        column.setResizingMask_(1)  # NSTableColumnAutoresizingMask
        table_view.addTableColumn_(column)
        
        # Create and set data source
        data_source = CompareListDataSource.alloc().init()
        table_view.setDataSource_(data_source)
        
        # Create and set delegate for selection handling
        delegate = CompareListDelegate.alloc().init()
        delegate.set_compare_view(self)
        delegate.set_list_index(list_index)
        table_view.setDelegate_(delegate)
        
        # Store references
        attrs = get_view_attrs(self)
        attrs['table_data_sources'].append(data_source)
        attrs['table_views'].append(table_view)
        attrs['table_delegates'].append(delegate)
        
        scroll_view.setDocumentView_(table_view)
        
        print(f"CompareView._create_list_pane: Created table view for '{title}'")  # Debug
        
        return scroll_view
    
    def _create_column3(self, frame):
        """Create Column 3: Four detail panes."""
        width, height = get_bounds_size(frame)
        
        col3_split = NSSplitView.alloc().initWithFrame_(frame)
        col3_split.setVertical_(False)  # Horizontal divider (stacks vertically)
        col3_split.setDividerStyle_(1)
        col3_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        quarter_height = height / 4
        
        attrs = get_view_attrs(self)
        
        # Pane 1: STIG A General Info
        pane1_frame = NSRect((0, 0), (width, quarter_height))
        scroll1, text1 = self._create_detail_pane(pane1_frame, "STIG A - General")
        col3_split.addSubview_(scroll1)
        attrs['detail_text_views'].append(text1)
        
        # Pane 2: STIG A Details
        pane2_frame = NSRect((0, 0), (width, quarter_height))
        scroll2, text2 = self._create_detail_pane(pane2_frame, "STIG A - Details")
        col3_split.addSubview_(scroll2)
        attrs['detail_text_views'].append(text2)
        
        # Pane 3: STIG B General Info
        pane3_frame = NSRect((0, 0), (width, quarter_height))
        scroll3, text3 = self._create_detail_pane(pane3_frame, "STIG B - General")
        col3_split.addSubview_(scroll3)
        attrs['detail_text_views'].append(text3)
        
        # Pane 4: STIG B Details
        pane4_frame = NSRect((0, 0), (width, quarter_height))
        scroll4, text4 = self._create_detail_pane(pane4_frame, "STIG B - Details")
        col3_split.addSubview_(scroll4)
        attrs['detail_text_views'].append(text4)
        
        col3_split.adjustSubviews()
        
        return col3_split
    
    def _create_detail_pane(self, frame, title):
        """Create a detail pane with a title. Returns (scroll_view, text_view)."""
        from AppKit import NSColor, NSFont
        
        scroll_view = NSScrollView.alloc().initWithFrame_(frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)
        
        text_view = NSTextView.alloc().initWithFrame_(frame)
        text_view.setEditable_(False)
        text_view.setSelectable_(True)
        text_view.setRichText_(False)  # Use plain text only
        text_view.setImportsGraphics_(False)  # Don't import graphics
        text_view.setAllowsUndo_(False)  # Disable undo for read-only
        text_view.setFieldEditor_(False)  # Not a field editor
        text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_view.setString_(f"{title}\n\n(Details will appear here)")
        text_view.setTextColor_(NSColor.whiteColor())
        text_view.setBackgroundColor_(NSColor.blackColor())
        text_view.setFont_(NSFont.systemFontOfSize_(12))
        scroll_view.setDocumentView_(text_view)
        
        return (scroll_view, text_view)

