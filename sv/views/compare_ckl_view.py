"""Compare CKL view with three-column layout for comparing two CKL files."""

from AppKit import (
    NSView, NSRect, NSSplitView, NSScrollView, NSTextView, NSTextField, NSButton,
    NSBox, NSOpenPanel, NSColor, NSFont, NSTableView, NSTableColumn,
    NSViewWidthSizable, NSViewHeightSizable, NSViewMinYMargin
)
from Foundation import NSObject
import objc
from pathlib import Path

from ..parsers.ckl_parser import CklParser
from .view_helpers import get_view_attrs, get_bounds_size


class CompareCklListDataSource(NSObject):
    """Data source for Compare CKL table views."""
    
    def init(self):
        self = objc.super(CompareCklListDataSource, self).init()
        if self is None:
            return None
        self.data = []  # List of (vcode, rule_title, vuln_obj)
        return self
    
    def numberOfRowsInTableView_(self, table_view):
        return len(self.data)
    
    def tableView_objectValueForTableColumn_row_(self, table_view, column, row):
        if row < len(self.data):
            vcode, rule_title, vuln = self.data[row]
            return f"{vcode} - {rule_title}"
        return ""
    
    @objc.python_method
    def set_data(self, data_list):
        """Set data as list of (vcode, rule_title, vuln_obj) tuples."""
        self.data = data_list


class CompareCklListDelegate(NSObject):
    """Delegate for Compare CKL table views."""
    
    def init(self):
        self = objc.super(CompareCklListDelegate, self).init()
        if self is None:
            return None
        self.data_source = None
        self.compare_view = None
        self.list_index = 0
        return self
    
    def tableViewSelectionDidChange_(self, notification):
        """Handle selection change."""
        print(f"CompareCklListDelegate.tableViewSelectionDidChange_: Called for list {self.list_index}")  # Debug
        
        if not self.data_source or not self.compare_view:
            print(f"CompareCklListDelegate: Missing data_source or compare_view!")  # Debug
            return
        
        table_view = notification.object()
        selected_row = table_view.selectedRow()
        
        print(f"CompareCklListDelegate: Selected row {selected_row}, data length {len(self.data_source.data)}")  # Debug
        
        if selected_row >= 0 and selected_row < len(self.data_source.data):
            vcode, rule_title, vuln = self.data_source.data[selected_row]
            print(f"CompareCklListDelegate: Selected {vcode} from list {self.list_index}")  # Debug
            # Call python method directly on compare_view
            CompareCklView._show_vcode_details(self.compare_view, vcode, vuln, self.list_index)


class CompareCklView(NSView):
    """Compare CKLs tab view with three columns for CKL comparison."""
    
    def init(self):
        """Initialize the Compare CKL view."""
        self = objc.super(CompareCklView, self).init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['ckl_a'] = None
        attrs['ckl_b'] = None
        attrs['ckl_a_path'] = None
        attrs['ckl_b_path'] = None
        attrs['main_window'] = None
        
        CompareCklView.createLayout(self)
        return self
    
    def createLayout(self):
        """Create the three-column layout."""
        print("CompareCklView.createLayout: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 1200, 800
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"CompareCklView.createLayout: Set default frame {width}x{height}")  # Debug
        
        print(f"CompareCklView.createLayout: Creating layout with bounds {width}x{height}")  # Debug
        
        # Main horizontal split view (three columns)
        main_split = NSSplitView.alloc().initWithFrame_(bounds)
        main_split.setVertical_(True)
        main_split.setDividerStyle_(1)  # NSSplitViewDividerStyleThin
        main_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Column 1: CKL loader and filter pane (25% width)
        col1_frame = NSRect((0, 0), (width * 0.25, height))
        col1 = CompareCklView._create_column1(self, col1_frame)
        
        # Column 2: Comparison results (50% width)
        col2_frame = NSRect((0, 0), (width * 0.50, height))
        col2 = CompareCklView._create_column2(self, col2_frame)
        
        # Column 3: Detail panes (25% width)
        col3_frame = NSRect((0, 0), (width * 0.25, height))
        col3 = CompareCklView._create_column3(self, col3_frame)
        
        # Add columns to main split view
        main_split.addSubview_(col1)
        main_split.addSubview_(col2)
        main_split.addSubview_(col3)
        main_split.adjustSubviews()
        
        # Set initial divider positions
        if width > 0:
            main_split.setPosition_ofDividerAtIndex_(width * 0.25, 0)
            main_split.setPosition_ofDividerAtIndex_(width * 0.75, 1)
        
        self.addSubview_(main_split)
        
        attrs = get_view_attrs(self)
        attrs['main_split'] = main_split
        attrs['col1'] = col1
        attrs['col2'] = col2
        attrs['col3'] = col3
        
        print("CompareCklView.createLayout: Complete")  # Debug
    
    def _create_column1(self, frame):
        """Create Column 1: CKL loader pane and filter pane."""
        width, height = get_bounds_size(frame)
        
        # Create vertical split view
        col1_split = NSSplitView.alloc().initWithFrame_(frame)
        col1_split.setVertical_(False)  # Horizontal divider (stacks vertically)
        col1_split.setDividerStyle_(1)
        col1_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Top: Loader pane (40% of height)
        loader_pane = CompareCklView._create_loader_pane(self, NSRect((0, 0), (width, height * 0.4)))
        
        # Bottom: Filter/search pane (60% of height)
        filter_pane = CompareCklView._create_filter_pane(self, NSRect((0, 0), (width, height * 0.6)))
        
        col1_split.addSubview_(loader_pane)
        col1_split.addSubview_(filter_pane)
        col1_split.adjustSubviews()
        col1_split.setPosition_ofDividerAtIndex_(height * 0.4, 0)
        
        return col1_split
    
    def _create_loader_pane(self, frame):
        """Create the loader pane with CKL A/B selection."""
        width, height = get_bounds_size(frame)
        
        pane = NSBox.alloc().initWithFrame_(frame)
        pane.setTitlePosition_(2)  # NSAtTop
        pane.setTitle_("Load CKL Files")
        pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        content = pane.contentView()
        content_frame = content.frame()
        content_width, content_height = get_bounds_size(content_frame)
        
        # Position elements from the top down
        y_pos = content_height - 10 - 30  # Start 10px from top, 30px for button
        
        # Load CKL A button
        load_a_btn_frame = NSRect((10, y_pos), (content_width - 20, 30))
        load_a_btn = NSButton.alloc().initWithFrame_(load_a_btn_frame)
        load_a_btn.setTitle_("Load CKL A")
        load_a_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        load_a_btn.setTarget_(self)
        load_a_btn.setAction_("loadCklA:")
        load_a_btn.setAutoresizingMask_(0x08 | 0x02)  # NSViewMinYMargin | NSViewWidthSizable
        content.addSubview_(load_a_btn)
        
        y_pos -= 35  # Move down for text field
        
        # CKL A filename field
        ckl_a_field_frame = NSRect((10, y_pos), (content_width - 20, 20))
        ckl_a_field = NSTextField.alloc().initWithFrame_(ckl_a_field_frame)
        ckl_a_field.setStringValue_("(No file selected)")
        ckl_a_field.setBezeled_(True)
        ckl_a_field.setDrawsBackground_(True)
        ckl_a_field.setEditable_(False)
        ckl_a_field.setSelectable_(False)
        ckl_a_field.setTextColor_(NSColor.grayColor())
        ckl_a_field.setAutoresizingMask_(0x08 | 0x02)
        content.addSubview_(ckl_a_field)
        
        y_pos -= 40  # Extra space before next button
        
        # Load CKL B button
        load_b_btn_frame = NSRect((10, y_pos), (content_width - 20, 30))
        load_b_btn = NSButton.alloc().initWithFrame_(load_b_btn_frame)
        load_b_btn.setTitle_("Load CKL B")
        load_b_btn.setBezelStyle_(1)
        load_b_btn.setTarget_(self)
        load_b_btn.setAction_("loadCklB:")
        load_b_btn.setAutoresizingMask_(0x08 | 0x02)
        content.addSubview_(load_b_btn)
        
        y_pos -= 35
        
        # CKL B filename field
        ckl_b_field_frame = NSRect((10, y_pos), (content_width - 20, 20))
        ckl_b_field = NSTextField.alloc().initWithFrame_(ckl_b_field_frame)
        ckl_b_field.setStringValue_("(No file selected)")
        ckl_b_field.setBezeled_(True)
        ckl_b_field.setDrawsBackground_(True)
        ckl_b_field.setEditable_(False)
        ckl_b_field.setSelectable_(False)
        ckl_b_field.setTextColor_(NSColor.grayColor())
        ckl_b_field.setAutoresizingMask_(0x08 | 0x02)
        content.addSubview_(ckl_b_field)
        
        y_pos -= 40
        
        # Compare button
        compare_btn_frame = NSRect((10, y_pos), (content_width - 20, 30))
        compare_btn = NSButton.alloc().initWithFrame_(compare_btn_frame)
        compare_btn.setTitle_("Compare CKLs")
        compare_btn.setBezelStyle_(1)
        compare_btn.setEnabled_(False)  # Initially disabled
        compare_btn.setTarget_(self)
        compare_btn.setAction_("compareCkls:")
        compare_btn.setAutoresizingMask_(0x08 | 0x02)
        content.addSubview_(compare_btn)
        
        # Store references
        self.ckl_a_field = ckl_a_field
        self.ckl_b_field = ckl_b_field
        self.compare_btn = compare_btn
        
        return pane
    
    def _create_filter_pane(self, frame):
        """Create the filter pane with 2-column layout for filters."""
        width, height = get_bounds_size(frame)
        
        pane = NSBox.alloc().initWithFrame_(frame)
        pane.setTitlePosition_(2)  # NSAtTop
        pane.setTitle_("Filter")
        pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        content = pane.contentView()
        content_frame = content.frame()
        content_width, content_height = get_bounds_size(content_frame)
        
        print(f"CompareCklView._create_filter_pane: content size = {content_width}x{content_height}")  # Debug
        
        # Calculate column positions (2 columns)
        # Use fixed pixel positions so columns don't overlap when pane is resized
        left_x = 5
        right_x = 115  # Fixed position for right column
        
        # Start from top
        y_left = content_height - 30
        y_right = content_height - 30
        
        # Store references
        attrs = get_view_attrs(self)
        attrs['severity_checkboxes'] = {}
        attrs['ckl_a_status_checkboxes'] = {}
        attrs['ckl_b_status_checkboxes'] = {}
        attrs['enabled_severities'] = {'High', 'Medium', 'Low'}  # All enabled by default
        attrs['enabled_ckl_a_statuses'] = {'Open', 'NotAFinding', 'Not_Reviewed', 'Not_Applicable'}  # All enabled
        attrs['enabled_ckl_b_statuses'] = {'Open', 'NotAFinding', 'Not_Reviewed', 'Not_Applicable'}  # All enabled
        
        # LEFT COLUMN: V-code Counts (fixed width, pinned to left)
        counts_label = NSTextField.alloc().initWithFrame_(NSRect((left_x, y_left), (85, 20)))
        counts_label.setStringValue_("V-code")
        counts_label.setBordered_(False)
        counts_label.setDrawsBackground_(False)
        counts_label.setEditable_(False)
        counts_label.setTextColor_(NSColor.whiteColor())
        counts_label.setFont_(NSFont.boldSystemFontOfSize_(12))
        counts_label.setAutoresizingMask_(0x08)  # NSViewMinYMargin only - pin to top and left
        content.addSubview_(counts_label)
        
        y_left -= 25
        
        # CKL A count
        ckl_a_count_label = NSTextField.alloc().initWithFrame_(NSRect((left_x + 5, y_left), (80, 20)))
        ckl_a_count_label.setStringValue_("CKL A: 0")
        ckl_a_count_label.setBordered_(False)
        ckl_a_count_label.setDrawsBackground_(False)
        ckl_a_count_label.setEditable_(False)
        ckl_a_count_label.setTextColor_(NSColor.whiteColor())
        ckl_a_count_label.setFont_(NSFont.systemFontOfSize_(11))
        ckl_a_count_label.setAutoresizingMask_(0x08)  # Pin to top and left
        content.addSubview_(ckl_a_count_label)
        attrs['ckl_a_count_label'] = ckl_a_count_label
        
        y_left -= 20
        
        # CKL B count
        ckl_b_count_label = NSTextField.alloc().initWithFrame_(NSRect((left_x + 5, y_left), (80, 20)))
        ckl_b_count_label.setStringValue_("CKL B: 0")
        ckl_b_count_label.setBordered_(False)
        ckl_b_count_label.setDrawsBackground_(False)
        ckl_b_count_label.setEditable_(False)
        ckl_b_count_label.setTextColor_(NSColor.whiteColor())
        ckl_b_count_label.setFont_(NSFont.systemFontOfSize_(11))
        ckl_b_count_label.setAutoresizingMask_(0x08)  # Pin to top and left
        content.addSubview_(ckl_b_count_label)
        attrs['ckl_b_count_label'] = ckl_b_count_label
        
        y_left -= 30  # Extra space
        
        # LEFT COLUMN: Severity
        severity_label = NSTextField.alloc().initWithFrame_(NSRect((left_x, y_left), (85, 20)))
        severity_label.setStringValue_("Severity:")
        severity_label.setBordered_(False)
        severity_label.setDrawsBackground_(False)
        severity_label.setEditable_(False)
        severity_label.setTextColor_(NSColor.whiteColor())
        severity_label.setFont_(NSFont.boldSystemFontOfSize_(12))
        severity_label.setAutoresizingMask_(0x08)  # Pin to top and left
        content.addSubview_(severity_label)
        
        y_left -= 25
        
        # Severity checkboxes
        severities = ['High', 'Medium', 'Low/Other']
        for severity in severities:
            checkbox = NSButton.alloc().initWithFrame_(NSRect((left_x + 5, y_left), (80, 22)))
            checkbox.setButtonType_(3)  # NSSwitchButton
            checkbox.setTitle_(severity)
            checkbox.setState_(1)  # Checked by default
            checkbox.setTarget_(self)
            checkbox.setAction_("severityCheckboxChanged:")
            checkbox.setAutoresizingMask_(0x08)  # Pin to top and left
            content.addSubview_(checkbox)
            
            # Store reference using normalized key
            severity_key = 'Low' if severity == 'Low/Other' else severity
            attrs['severity_checkboxes'][severity_key] = checkbox
            
            y_left -= 25
        
        # RIGHT COLUMN: CKL A Status (starts at fixed position, width adjusts)
        ckl_a_label = NSTextField.alloc().initWithFrame_(NSRect((right_x, y_right), (content_width - right_x - 5, 20)))
        ckl_a_label.setStringValue_("CKL A")
        ckl_a_label.setBordered_(False)
        ckl_a_label.setDrawsBackground_(False)
        ckl_a_label.setEditable_(False)
        ckl_a_label.setTextColor_(NSColor.whiteColor())
        ckl_a_label.setFont_(NSFont.boldSystemFontOfSize_(12))
        ckl_a_label.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, width adjustable
        content.addSubview_(ckl_a_label)
        
        y_right -= 25
        
        # CKL A Status checkboxes
        statuses = [
            ('Open', 'Open'),
            ('Not a Finding', 'NotAFinding'),
            ('Not Reviewed', 'Not_Reviewed'),
            ('Not Applicable', 'Not_Applicable')
        ]
        
        for display_name, status_key in statuses:
            checkbox = NSButton.alloc().initWithFrame_(NSRect((right_x + 5, y_right), (content_width - right_x - 10, 22)))
            checkbox.setButtonType_(3)  # NSSwitchButton
            checkbox.setTitle_(display_name)
            checkbox.setState_(1)  # Checked by default
            checkbox.setTarget_(self)
            checkbox.setAction_("statusCheckboxChanged:")
            checkbox.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, width adjustable
            content.addSubview_(checkbox)
            
            attrs['ckl_a_status_checkboxes'][status_key] = checkbox
            
            y_right -= 25
        
        y_right -= 10  # Extra space
        
        # RIGHT COLUMN: CKL B Status
        ckl_b_label = NSTextField.alloc().initWithFrame_(NSRect((right_x, y_right), (content_width - right_x - 5, 20)))
        ckl_b_label.setStringValue_("CKL B")
        ckl_b_label.setBordered_(False)
        ckl_b_label.setDrawsBackground_(False)
        ckl_b_label.setEditable_(False)
        ckl_b_label.setTextColor_(NSColor.whiteColor())
        ckl_b_label.setFont_(NSFont.boldSystemFontOfSize_(12))
        ckl_b_label.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, width adjustable
        content.addSubview_(ckl_b_label)
        
        y_right -= 25
        
        # CKL B Status checkboxes
        for display_name, status_key in statuses:
            checkbox = NSButton.alloc().initWithFrame_(NSRect((right_x + 5, y_right), (content_width - right_x - 10, 22)))
            checkbox.setButtonType_(3)  # NSSwitchButton
            checkbox.setTitle_(display_name)
            checkbox.setState_(1)  # Checked by default
            checkbox.setTarget_(self)
            checkbox.setAction_("statusCheckboxChanged:")
            checkbox.setAutoresizingMask_(0x08 | 0x02)  # Pin to top, width adjustable
            content.addSubview_(checkbox)
            
            attrs['ckl_b_status_checkboxes'][status_key] = checkbox
            
            y_right -= 25
        
        # Add "Close Comparison" button at bottom (full width)
        btn_height = 28
        close_btn_frame = NSRect((10, 10), (content_width - 20, btn_height))
        close_btn = NSButton.alloc().initWithFrame_(close_btn_frame)
        close_btn.setTitle_("Close Comparison")
        close_btn.setButtonType_(0)  # NSMomentaryLightButton
        close_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        close_btn.setTarget_(self)
        close_btn.setAction_("closeCompareCklTab:")
        close_btn.setAutoresizingMask_(0x02)  # NSViewWidthSizable - stays at bottom, stretches width
        content.addSubview_(close_btn)
        
        return pane
    
    def severityCheckboxChanged_(self, sender):
        """Handle severity checkbox state change."""
        attrs = get_view_attrs(self)
        enabled_severities = set()
        
        # Check which severities are enabled
        severity_checkboxes = attrs.get('severity_checkboxes', {})
        for severity_key, checkbox in severity_checkboxes.items():
            if checkbox.state() == 1:  # Checked
                enabled_severities.add(severity_key)
        
        attrs['enabled_severities'] = enabled_severities
        print(f"CompareCklView.severityCheckboxChanged_: Enabled severities: {enabled_severities}")  # Debug
        
        # Update V-code counts
        CompareCklView._update_vcode_counts(self)
        
        # Refresh the display with current filters
        CompareCklView._apply_filters(self)
    
    def statusCheckboxChanged_(self, sender):
        """Handle status checkbox state change for CKL A and CKL B."""
        attrs = get_view_attrs(self)
        
        # Check which CKL A statuses are enabled
        enabled_ckl_a_statuses = set()
        ckl_a_status_checkboxes = attrs.get('ckl_a_status_checkboxes', {})
        for status_key, checkbox in ckl_a_status_checkboxes.items():
            if checkbox.state() == 1:  # Checked
                enabled_ckl_a_statuses.add(status_key)
        
        # Check which CKL B statuses are enabled
        enabled_ckl_b_statuses = set()
        ckl_b_status_checkboxes = attrs.get('ckl_b_status_checkboxes', {})
        for status_key, checkbox in ckl_b_status_checkboxes.items():
            if checkbox.state() == 1:  # Checked
                enabled_ckl_b_statuses.add(status_key)
        
        attrs['enabled_ckl_a_statuses'] = enabled_ckl_a_statuses
        attrs['enabled_ckl_b_statuses'] = enabled_ckl_b_statuses
        
        print(f"CompareCklView.statusCheckboxChanged_: CKL A statuses: {enabled_ckl_a_statuses}")  # Debug
        print(f"CompareCklView.statusCheckboxChanged_: CKL B statuses: {enabled_ckl_b_statuses}")  # Debug
        
        # Update V-code counts
        CompareCklView._update_vcode_counts(self)
        
        # Refresh the display with current filters
        CompareCklView._apply_filters(self)
    
    def _create_column2(self, frame):
        """Create Column 2: Three table views for comparison results."""
        width, height = get_bounds_size(frame)
        
        # Create split view for three lists
        col2_split = NSSplitView.alloc().initWithFrame_(frame)
        col2_split.setVertical_(False)  # Horizontal dividers (stacks vertically)
        col2_split.setDividerStyle_(1)
        col2_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        attrs = get_view_attrs(self)
        attrs['table_views'] = []
        attrs['data_sources'] = []
        attrs['delegates'] = []  # IMPORTANT: Store delegates to prevent garbage collection
        
        # Create three table views (equal height)
        titles = [
            "In CKL B but not in CKL A",
            "In CKL A but not in CKL B", 
            "In both but with different status"
        ]
        
        pane_height = height / 3  # 33% each
        
        for i, title in enumerate(titles):
            # Create container with title
            container = NSView.alloc().initWithFrame_(NSRect((0, 0), (width, pane_height)))
            container.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            
            # Title label
            title_label = NSTextField.alloc().initWithFrame_(NSRect((5, pane_height - 25), (width - 10, 20)))
            title_label.setStringValue_(title)
            title_label.setBordered_(False)
            title_label.setDrawsBackground_(False)
            title_label.setEditable_(False)
            title_label.setTextColor_(NSColor.whiteColor())
            title_label.setFont_(NSFont.boldSystemFontOfSize_(12))
            title_label.setAutoresizingMask_(NSViewWidthSizable | NSViewMinYMargin)
            container.addSubview_(title_label)
            
            # Scroll view with table
            scroll_view = NSScrollView.alloc().initWithFrame_(NSRect((0, 0), (width, pane_height - 30)))
            scroll_view.setHasVerticalScroller_(True)
            scroll_view.setHasHorizontalScroller_(False)
            scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            scroll_view.setBorderType_(1)
            
            # Table view
            table_view = NSTableView.alloc().initWithFrame_(scroll_view.bounds())
            table_view.setUsesAlternatingRowBackgroundColors_(True)
            table_view.setRowHeight_(20)
            table_view.setHeaderView_(None)
            
            # Single column
            column = NSTableColumn.alloc().initWithIdentifier_("vcode")
            column.setWidth_(width - 20)
            column.setMinWidth_(100)
            column.setResizingMask_(1)
            table_view.addTableColumn_(column)
            
            # Data source and delegate
            data_source = CompareCklListDataSource.alloc().init()
            delegate = CompareCklListDelegate.alloc().init()
            delegate.data_source = data_source
            delegate.compare_view = self
            delegate.list_index = i
            
            print(f"_create_column2: Created delegate {i} with compare_view={self}, list_index={i}")  # Debug
            
            table_view.setDataSource_(data_source)
            table_view.setDelegate_(delegate)
            
            scroll_view.setDocumentView_(table_view)
            container.addSubview_(scroll_view)
            
            col2_split.addSubview_(container)
            attrs['table_views'].append(table_view)
            attrs['data_sources'].append(data_source)
            attrs['delegates'].append(delegate)  # IMPORTANT: Keep reference to prevent garbage collection
        
        col2_split.adjustSubviews()
        
        print(f"_create_column2: Created {len(attrs['delegates'])} delegates")  # Debug
        
        return col2_split
    
    def _create_column3(self, frame):
        """Create Column 3: Four detail panes (General A, Details A, General B, Details B)."""
        width, height = get_bounds_size(frame)
        
        # Create split view for 4 panes
        col3_split = NSSplitView.alloc().initWithFrame_(frame)
        col3_split.setVertical_(False)  # Horizontal dividers (stacks vertically)
        col3_split.setDividerStyle_(1)
        col3_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        attrs = get_view_attrs(self)
        attrs['detail_text_views'] = []
        
        # Create 4 text views for details
        pane_height = height / 4  # 25% each
        
        for i in range(4):
            scroll_view = NSScrollView.alloc().initWithFrame_(NSRect((0, 0), (width, pane_height)))
            scroll_view.setHasVerticalScroller_(True)
            scroll_view.setHasHorizontalScroller_(False)
            scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            scroll_view.setBorderType_(1)
            
            text_frame = NSRect((0, 0), (width, pane_height))
            text_view = NSTextView.alloc().initWithFrame_(text_frame)
            text_view.setEditable_(False)
            text_view.setSelectable_(True)
            text_view.setRichText_(False)
            text_view.setImportsGraphics_(False)
            text_view.setAllowsUndo_(False)
            text_view.setFieldEditor_(False)
            text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            
            if i == 0:
                text_view.setString_("General Info (CKL A)\n\n(Select a V-code to view details)")
            elif i == 1:
                text_view.setString_("Details (CKL A)\n\n(Select a V-code to view details)")
            elif i == 2:
                text_view.setString_("General Info (CKL B)\n\n(Select a V-code to view details)")
            else:  # i == 3
                text_view.setString_("Status Discrepancies\n\n(Click Compare to see report)")
            
            text_view.setTextColor_(NSColor.whiteColor())
            text_view.setBackgroundColor_(NSColor.blackColor())
            text_view.setFont_(NSFont.systemFontOfSize_(12))
            scroll_view.setDocumentView_(text_view)
            
            col3_split.addSubview_(scroll_view)
            attrs['detail_text_views'].append(text_view)
        
        col3_split.adjustSubviews()
        
        return col3_split
    
    def loadCklA_(self, sender):
        """Load CKL A file."""
        print("CompareCklView.loadCklA_: Called")  # Debug
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setAllowedFileTypes_(['ckl'])
        panel.setTitle_("Select CKL A")
        panel.setMessage_("Select the first CKL file to compare")
        
        if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
            urls = panel.URLs()
            if urls and len(urls) > 0:
                path = Path(str(urls[0].path()))
                print(f"CompareCklView.loadCklA_: Selected {path}")  # Debug
                attrs = get_view_attrs(self)
                attrs['ckl_a_path'] = path
                self.ckl_a_field.setStringValue_(path.name)
                self.ckl_a_field.setTextColor_(NSColor.whiteColor())
                CompareCklView._update_compare_button_state(self)
    
    def loadCklB_(self, sender):
        """Load CKL B file."""
        print("CompareCklView.loadCklB_: Called")  # Debug
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setAllowedFileTypes_(['ckl'])
        panel.setTitle_("Select CKL B")
        panel.setMessage_("Select the second CKL file to compare")
        
        if panel.runModal() == 1:  # NSFileHandlingPanelOKButton
            urls = panel.URLs()
            if urls and len(urls) > 0:
                path = Path(str(urls[0].path()))
                print(f"CompareCklView.loadCklB_: Selected {path}")  # Debug
                attrs = get_view_attrs(self)
                attrs['ckl_b_path'] = path
                self.ckl_b_field.setStringValue_(path.name)
                self.ckl_b_field.setTextColor_(NSColor.whiteColor())
                CompareCklView._update_compare_button_state(self)
    
    @objc.python_method
    def _update_compare_button_state(self):
        """Enable/disable the Compare button based on whether both CKLs are loaded."""
        attrs = get_view_attrs(self)
        ckl_a_path = attrs.get('ckl_a_path')
        ckl_b_path = attrs.get('ckl_b_path')
        
        enabled = (ckl_a_path is not None and ckl_b_path is not None)
        self.compare_btn.setEnabled_(enabled)
        print(f"CompareCklView._update_compare_button_state: Compare button enabled={enabled}")  # Debug
    
    def compareCkls_(self, sender):
        """Compare the two CKL files."""
        print("CompareCklView.compareCkls_: Called")  # Debug
        attrs = get_view_attrs(self)
        ckl_a_path = attrs.get('ckl_a_path')
        ckl_b_path = attrs.get('ckl_b_path')
        
        if not ckl_a_path or not ckl_b_path:
            print("CompareCklView.compareCkls_: Missing CKL A or B")  # Debug
            return
        
        try:
            # Parse CKL files
            print(f"CompareCklView.compareCkls_: Parsing CKL A: {ckl_a_path}")  # Debug
            ckl_a = CklParser.parse(ckl_a_path)
            attrs['ckl_a'] = ckl_a
            
            print(f"CompareCklView.compareCkls_: Parsing CKL B: {ckl_b_path}")  # Debug
            ckl_b = CklParser.parse(ckl_b_path)
            attrs['ckl_b'] = ckl_b
            
            # Perform comparison
            print("CompareCklView.compareCkls_: Performing comparison...")  # Debug
            results = CompareCklView._compare_ckls(self, ckl_a, ckl_b)
            
            # Store raw results for filtering
            attrs['raw_results'] = results
            
            # Update V-code counts
            print("CompareCklView.compareCkls_: Updating V-code counts...")  # Debug
            CompareCklView._update_vcode_counts(self)
            
            # Display results (will apply current filters)
            print("CompareCklView.compareCkls_: Displaying results...")  # Debug
            CompareCklView._apply_filters(self)
            
        except Exception as e:
            import traceback
            print(f"CompareCklView.compareCkls_: ERROR - {e}")  # Debug
            traceback.print_exc()
            # Show error in results pane
            results_text_view = attrs.get('results_text_view')
            if results_text_view:
                results_text_view.setString_(f"Error comparing CKLs:\n\n{e}")
    
    @objc.python_method
    def _compare_ckls(self, ckl_a, ckl_b):
        """Compare two CKL files and return differences."""
        # Get V-code IDs from each CKL
        vcodes_a = set(v.v_code for v in ckl_a.vulns)
        vcodes_b = set(v.v_code for v in ckl_b.vulns)
        
        print(f"DEBUG: CKL A has {len(vcodes_a)} unique V-codes")  # Debug
        print(f"DEBUG: CKL B has {len(vcodes_b)} unique V-codes")  # Debug
        print(f"DEBUG: Sample from CKL A: {sorted(list(vcodes_a))[:5]}")  # Debug
        print(f"DEBUG: Sample from CKL B: {sorted(list(vcodes_b))[:5]}")  # Debug
        print(f"DEBUG: V-214277 in A: {'V-214277' in vcodes_a}")  # Debug
        print(f"DEBUG: V-214277 in B: {'V-214277' in vcodes_b}")  # Debug
        
        # Find differences
        in_b_not_a = vcodes_b - vcodes_a
        in_a_not_b = vcodes_a - vcodes_b
        in_both = vcodes_a & vcodes_b
        
        print(f"DEBUG: in_b_not_a count: {len(in_b_not_a)}")  # Debug
        print(f"DEBUG: in_a_not_b count: {len(in_a_not_b)}")  # Debug
        print(f"DEBUG: in_both count: {len(in_both)}")  # Debug
        
        # For V-codes in both, check for status differences
        different = []
        vcodes_a_map = {v.v_code: v for v in ckl_a.vulns}
        vcodes_b_map = {v.v_code: v for v in ckl_b.vulns}
        
        for vcode in in_both:
            vuln_a = vcodes_a_map.get(vcode)
            vuln_b = vcodes_b_map.get(vcode)
            
            if vuln_a and vuln_b and vuln_a.status != vuln_b.status:
                different.append((vcode, vuln_a.status, vuln_b.status))
        
        # Helper to sort V-codes numerically
        def vcode_sort_key(vc):
            try:
                return int(vc.replace('V-', '').replace('v-', ''))
            except:
                return 999999999
        
        return {
            'in_b_not_a': sorted(in_b_not_a, key=vcode_sort_key),
            'in_a_not_b': sorted(in_a_not_b, key=vcode_sort_key),
            'different': sorted(different, key=lambda x: vcode_sort_key(x[0])),
            'vcodes_a_map': vcodes_a_map,
            'vcodes_b_map': vcodes_b_map
        }
    
    @objc.python_method
    def _display_results(self, results):
        """Display comparison results in Column 2 table views and Status Discrepancies in Column 3 pane 4."""
        attrs = get_view_attrs(self)
        table_views = attrs.get('table_views', [])
        data_sources = attrs.get('data_sources', [])
        detail_text_views = attrs.get('detail_text_views', [])
        
        if len(table_views) != 3 or len(data_sources) != 3:
            print("CompareCklView._display_results: Table views not ready!")  # Debug
            return
        
        vcodes_a_map = results.get('vcodes_a_map', {})
        vcodes_b_map = results.get('vcodes_b_map', {})
        
        # List 0: In B not A
        list_0_data = []
        for vcode in results['in_b_not_a']:
            vuln = vcodes_b_map.get(vcode)
            rule_title = vuln.rule_title if vuln else ""
            list_0_data.append((vcode, rule_title, vuln))
        data_sources[0].set_data(list_0_data)
        table_views[0].reloadData()
        
        # List 1: In A not B
        list_1_data = []
        for vcode in results['in_a_not_b']:
            vuln = vcodes_a_map.get(vcode)
            rule_title = vuln.rule_title if vuln else ""
            list_1_data.append((vcode, rule_title, vuln))
        data_sources[1].set_data(list_1_data)
        table_views[1].reloadData()
        
        # List 2: Different statuses (only V-codes, not full discrepancy info)
        list_2_data = []
        for vcode, status_a, status_b in results['different']:
            vuln = vcodes_a_map.get(vcode)
            rule_title = vuln.rule_title if vuln else ""
            list_2_data.append((vcode, rule_title, vuln))
        data_sources[2].set_data(list_2_data)
        table_views[2].reloadData()
        
        # Populate Status Discrepancies in Column 3, Pane 4 (4th detail pane)
        if len(detail_text_views) >= 4:
            issues_lines = []
            
            # Header row (no banner)
            issues_lines.append(f"{'V-code':<15} {'CKL A':<8} {'CKL B':<8} Rule Title")
            
            for vcode, status_a, status_b in results['different']:
                vuln = vcodes_a_map.get(vcode)
                rule_title = vuln.rule_title if vuln else ""
                
                # Abbreviate status values
                status_a_abbr = self._abbreviate_status(status_a.value)
                status_b_abbr = self._abbreviate_status(status_b.value)
                
                # Format as table row
                issues_lines.append(f"{vcode:<15} {status_a_abbr:<8} {status_b_abbr:<8} {rule_title}")
            
            if len(results['different']) == 0:
                issues_lines.append("(No status discrepancies found)")
            
            detail_text_views[3].setString_("\n".join(issues_lines))
        
        print(f"CompareCklView._display_results: Populated tables with {len(list_0_data)}, {len(list_1_data)}, {len(list_2_data)} items")  # Debug
    
    @objc.python_method
    def _abbreviate_status(self, status_value):
        """Convert status value to abbreviation for display.
        
        Args:
            status_value: Full status string (e.g., "Not_Reviewed", "NotAFinding")
            
        Returns:
            Abbreviated status (e.g., "NR", "NaF", "N/A")
        """
        status_lower = status_value.lower()
        
        if 'not_reviewed' in status_lower or 'notreviewed' in status_lower:
            return "NR"
        elif 'notafinding' in status_lower or 'not_a_finding' in status_lower:
            return "NaF"
        elif 'open' in status_lower:
            return "Open"
        elif 'notapplicable' in status_lower or 'not_applicable' in status_lower:
            return "N/A"
        else:
            # Return first 3 characters for unknown statuses
            return status_value[:3] if len(status_value) >= 3 else status_value
    
    @objc.python_method
    def _apply_filters(self):
        """Apply severity and status filters to the current comparison results."""
        attrs = get_view_attrs(self)
        raw_results = attrs.get('raw_results')
        
        if not raw_results:
            print("CompareCklView._apply_filters: No results to filter")  # Debug
            return
        
        enabled_severities = attrs.get('enabled_severities', {'High', 'Medium', 'Low'})
        enabled_ckl_a_statuses = attrs.get('enabled_ckl_a_statuses', {'Open', 'NotAFinding', 'Not_Reviewed', 'Not_Applicable'})
        enabled_ckl_b_statuses = attrs.get('enabled_ckl_b_statuses', {'Open', 'NotAFinding', 'Not_Reviewed', 'Not_Applicable'})
        
        print(f"CompareCklView._apply_filters: Severities={enabled_severities}, CKL A statuses={enabled_ckl_a_statuses}, CKL B statuses={enabled_ckl_b_statuses}")  # Debug
        
        # Helper function to check if vuln severity matches enabled severities
        def severity_enabled(vuln):
            if not vuln:
                return False
            severity = vuln.severity.lower().strip() if vuln.severity else ""
            
            # Normalize severity (handle variations)
            # Low severity variations
            if any(s in severity for s in ['low', 'cat iii', 'cat3', 'cat-3', 'cat-iii']):
                return 'Low' in enabled_severities
            # Medium severity variations
            elif any(s in severity for s in ['medium', 'cat ii', 'cat2', 'cat-2', 'cat-ii']):
                return 'Medium' in enabled_severities
            # High severity variations
            elif any(s in severity for s in ['high', 'critical', 'cat i', 'cat1', 'cat-1', 'cat-i']):
                return 'High' in enabled_severities
            else:
                # Unknown/unrecognized severity - log it and include in Low by default
                print(f"DEBUG: Unknown severity '{vuln.severity}' for {vuln.v_code} - treating as Low")
                return 'Low' in enabled_severities
        
        # Helper function to check if vuln status matches enabled statuses
        def status_enabled(vuln, enabled_statuses):
            if not vuln:
                return False
            # vuln.status is a ChecklistStatus enum - get its value
            status_value = vuln.status.value if hasattr(vuln.status, 'value') else str(vuln.status)
            # Debug: print the actual status value
            if not hasattr(status_enabled, '_printed_statuses'):
                status_enabled._printed_statuses = set()
            if status_value not in status_enabled._printed_statuses:
                print(f"DEBUG: Status value: '{status_value}' from {vuln.status}, checking against {enabled_statuses}")
                status_enabled._printed_statuses.add(status_value)
            return status_value in enabled_statuses
        
        # Filter results
        vcodes_a_map = raw_results.get('vcodes_a_map', {})
        vcodes_b_map = raw_results.get('vcodes_b_map', {})
        
        filtered_results = {
            'in_b_not_a': [
                v for v in raw_results['in_b_not_a'] 
                if severity_enabled(vcodes_b_map.get(v)) and status_enabled(vcodes_b_map.get(v), enabled_ckl_b_statuses)
            ],
            'in_a_not_b': [
                v for v in raw_results['in_a_not_b'] 
                if severity_enabled(vcodes_a_map.get(v)) and status_enabled(vcodes_a_map.get(v), enabled_ckl_a_statuses)
            ],
            'different': [
                (v, sa, sb) for v, sa, sb in raw_results['different'] 
                if severity_enabled(vcodes_a_map.get(v)) 
                and status_enabled(vcodes_a_map.get(v), enabled_ckl_a_statuses)
                and status_enabled(vcodes_b_map.get(v), enabled_ckl_b_statuses)
            ],
            'vcodes_a_map': vcodes_a_map,
            'vcodes_b_map': vcodes_b_map,
        }
        
        print(f"CompareCklView._apply_filters: Filtered to {len(filtered_results['in_b_not_a'])}, {len(filtered_results['in_a_not_b'])}, {len(filtered_results['different'])} items")  # Debug
        
        # Update display with filtered results
        CompareCklView._display_results(self, filtered_results)
    
    @objc.python_method
    def _update_vcode_counts(self):
        """Update the V-code count labels based on current filters."""
        attrs = get_view_attrs(self)
        ckl_a = attrs.get('ckl_a')
        ckl_b = attrs.get('ckl_b')
        ckl_a_count_label = attrs.get('ckl_a_count_label')
        ckl_b_count_label = attrs.get('ckl_b_count_label')
        enabled_severities = attrs.get('enabled_severities', {'High', 'Medium', 'Low'})
        enabled_ckl_a_statuses = attrs.get('enabled_ckl_a_statuses', {'Open', 'NotAFinding', 'Not_Reviewed', 'Not_Applicable'})
        enabled_ckl_b_statuses = attrs.get('enabled_ckl_b_statuses', {'Open', 'NotAFinding', 'Not_Reviewed', 'Not_Applicable'})
        
        if not ckl_a_count_label or not ckl_b_count_label:
            return
        
        # Helper function to check if vuln severity matches enabled severities
        def severity_enabled(vuln):
            if not vuln:
                return False
            severity = vuln.severity.lower().strip() if vuln.severity else ""
            
            # Normalize severity
            if any(s in severity for s in ['low', 'cat iii', 'cat3', 'cat-3', 'cat-iii']):
                return 'Low' in enabled_severities
            elif any(s in severity for s in ['medium', 'cat ii', 'cat2', 'cat-2', 'cat-ii']):
                return 'Medium' in enabled_severities
            elif any(s in severity for s in ['high', 'critical', 'cat i', 'cat1', 'cat-1', 'cat-i']):
                return 'High' in enabled_severities
            else:
                return 'Low' in enabled_severities
        
        # Helper function to check if vuln status matches enabled statuses
        def status_enabled(vuln, enabled_statuses):
            if not vuln:
                return False
            # vuln.status is a ChecklistStatus enum - get its value
            status_value = vuln.status.value if hasattr(vuln.status, 'value') else str(vuln.status)
            return status_value in enabled_statuses
        
        # Count V-codes in CKL A (with both severity and status filters)
        count_a = 0
        if ckl_a and hasattr(ckl_a, 'vulns'):
            for vuln in ckl_a.vulns:
                if severity_enabled(vuln) and status_enabled(vuln, enabled_ckl_a_statuses):
                    count_a += 1
        
        # Count V-codes in CKL B (with both severity and status filters)
        count_b = 0
        if ckl_b and hasattr(ckl_b, 'vulns'):
            for vuln in ckl_b.vulns:
                if severity_enabled(vuln) and status_enabled(vuln, enabled_ckl_b_statuses):
                    count_b += 1
        
        # Update labels
        ckl_a_count_label.setStringValue_(f"CKL A: {count_a}")
        ckl_b_count_label.setStringValue_(f"CKL B: {count_b}")
        
        print(f"CompareCklView._update_vcode_counts: A={count_a}, B={count_b}")  # Debug
    
    @objc.python_method
    def _show_vcode_details(self, vcode, vuln, list_index):
        """Show details for selected V-code in Column 3 (panes 1-3)."""
        print(f"CompareCklView._show_vcode_details: {vcode} from list {list_index}")  # Debug
        
        if not vuln:
            print(f"CompareCklView._show_vcode_details: No vuln object!")  # Debug
            return
        
        attrs = get_view_attrs(self)
        detail_text_views = attrs.get('detail_text_views', [])
        
        if len(detail_text_views) < 3:
            print(f"CompareCklView._show_vcode_details: Not enough detail panes!")  # Debug
            return
        
        # Build general info (Pane 0 for CKL A, Pane 2 for CKL B)
        general_info = []
        general_info.append(f"V-code: {vuln.v_code}")
        general_info.append(f"Severity: {vuln.severity}")
        general_info.append(f"Rule ID: {vuln.rule_id}")
        general_info.append(f"Rule Title: {vuln.rule_title}")
        general_info.append("")
        
        # STIG information
        if vuln.stig_info:
            general_info.append(f"STIG: {vuln.stig_info.title}")
            general_info.append(f"STIG ID: {vuln.stig_info.stig_id}")
            general_info.append(f"Version: {vuln.stig_info.version}")
            general_info.append(f"Release: {vuln.stig_info.release_info}")
        
        general_text = "\n".join(general_info)
        
        # Build details (Pane 1 for CKL A, Pane 3 is Status Discrepancies)
        details = []
        details.append("Discussion:")
        details.append(vuln.discussion or "(None)")
        details.append("")
        details.append("Check Text:")
        details.append(vuln.check_text or "(None)")
        details.append("")
        details.append("Fix Text:")
        details.append(vuln.fix_text or "(None)")
        details.append("")
        details.append("References:")
        details.append(getattr(vuln, 'references', '') or "(None)")
        
        detail_text = "\n".join(details)
        
        # Determine which CKL this is from (list_index: 0=B only, 1=A only, 2=Both)
        if list_index == 0:
            # In B, not in A - show in CKL B panes (panes 2 and would be 3, but 3 is Status Discrepancies)
            detail_text_views[0].setString_("(V-code not in CKL A)")
            detail_text_views[1].setString_("(V-code not in CKL A)")
            detail_text_views[2].setString_("General Info (CKL B)\n\n" + general_text)
            # Pane 3 stays as Status Discrepancies
        elif list_index == 1:
            # In A, not in B - show in CKL A panes (panes 0 and 1)
            detail_text_views[0].setString_("General Info (CKL A)\n\n" + general_text)
            detail_text_views[1].setString_("Details (CKL A)\n\n" + detail_text)
            detail_text_views[2].setString_("(V-code not in CKL B)")
            # Pane 3 stays as Status Discrepancies
        elif list_index == 2:
            # In both - show in CKL A panes (panes 0 and 1), B info would go in pane 2
            detail_text_views[0].setString_("General Info (CKL A)\n\n" + general_text)
            detail_text_views[1].setString_("Details (CKL A)\n\n" + detail_text)
            
            # For "In both", also try to get CKL B version
            ckl_b = attrs.get('ckl_b')
            if ckl_b and hasattr(ckl_b, 'vulns'):
                vuln_b = None
                for v in ckl_b.vulns:
                    if v.v_code == vcode:
                        vuln_b = v
                        break
                
                if vuln_b:
                    general_info_b = []
                    general_info_b.append(f"V-code: {vuln_b.v_code}")
                    general_info_b.append(f"Severity: {vuln_b.severity}")
                    general_info_b.append(f"Rule ID: {vuln_b.rule_id}")
                    general_info_b.append(f"Rule Title: {vuln_b.rule_title}")
                    general_info_b.append("")
                    if vuln_b.stig_info:
                        general_info_b.append(f"STIG: {vuln_b.stig_info.title}")
                        general_info_b.append(f"STIG ID: {vuln_b.stig_info.stig_id}")
                        general_info_b.append(f"Version: {vuln_b.stig_info.version}")
                        general_info_b.append(f"Release: {vuln_b.stig_info.release_info}")
                    detail_text_views[2].setString_("General Info (CKL B)\n\n" + "\n".join(general_info_b))
                else:
                    detail_text_views[2].setString_("(V-code not found in CKL B)")
            else:
                detail_text_views[2].setString_("(CKL B not loaded)")
            # Pane 3 stays as Status Discrepancies
        
        print(f"CompareCklView._show_vcode_details: Updated detail panes")  # Debug
    
    def closeCompareCklTab_(self, sender):
        """Close the Compare CKLs tab."""
        print("CompareCklView.closeCompareCklTab_: Called")  # Debug
        attrs = get_view_attrs(self)
        main_window = attrs.get('main_window')
        if main_window:
            print("CompareCklView.closeCompareCklTab_: Calling main_window.remove_compare_ckl_tab")  # Debug
            main_window.remove_compare_ckl_tab()
        else:
            print("CompareCklView.closeCompareCklTab_: WARNING - No main_window reference!")  # Debug
