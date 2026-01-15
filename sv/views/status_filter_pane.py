"""Status filter pane with checkboxes for CKL views."""

from AppKit import (
    NSView, NSRect, NSButton, NSTextField,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
import objc

from ..models.checklist_status import ChecklistStatus
from .view_helpers import get_view_attrs, get_bounds_size


class StatusFilterPane(NSView):
    """Pane showing status filter checkboxes."""
    
    def init(self):
        """Initialize the status filter pane."""
        self = objc.super(StatusFilterPane, self).init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['status_filters'] = {
            ChecklistStatus.OPEN: True,
            ChecklistStatus.NOT_A_FINDING: True,
            ChecklistStatus.NOT_REVIEWED: True,
            ChecklistStatus.NOT_APPLICABLE: True,
        }
        attrs['severity_filters'] = {
            'high': True,
            'medium': True,
            'low': True,
        }
        attrs['mtf_filter'] = False  # Default OFF - when ON, hides MTF/risk-accepted items
        attrs['invalid_arg_filter'] = False  # Default OFF - when ON, shows ONLY Invalid Argument items
        attrs['rule_title_mismatch_filter'] = False  # Default OFF - when ON, shows ONLY V-codes with Rule Title mismatches
        attrs['no_info_filter'] = False  # Default OFF - when ON, hides V-codes with "no info" Finding Details
        attrs['on_filter_changed'] = None
        attrs['status_checkboxes'] = {}
        attrs['severity_checkboxes'] = {}
        attrs['mtf_checkbox'] = None
        attrs['invalid_arg_checkbox'] = None
        attrs['rule_title_checkbox'] = None
        attrs['no_info_checkbox'] = None
        attrs['vcode_count_label'] = None
        StatusFilterPane.createUI(self)
        return self
    
    def createUI(self):
        """Create the UI with status, severity, and MTF checkboxes in three columns."""
        from AppKit import NSViewMinYMargin
        print("StatusFilterPane.createUI: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 300, 120
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"StatusFilterPane.createUI: Set default frame {width}x{height}")  # Debug
        
        attrs = get_view_attrs(self)
        third_width = width / 3
        
        # Position controls from top down with margin
        # Note: When inside NSBox, use the actual content view height
        top_margin = 15  # Margin from content area top
        row_spacing = 22  # Space between rows
        
        # Add V-code count label at the top left
        from AppKit import NSColor
        count_frame = NSRect((10, height - top_margin - 20), (150, 20))
        vcode_count_label = NSTextField.alloc().initWithFrame_(count_frame)
        vcode_count_label.setStringValue_("V-codes: 0")
        vcode_count_label.setBordered_(False)
        vcode_count_label.setDrawsBackground_(False)
        vcode_count_label.setEditable_(False)
        vcode_count_label.setTextColor_(NSColor.whiteColor())
        vcode_count_label.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(vcode_count_label)
        attrs['vcode_count_label'] = vcode_count_label
        
        # Adjust starting position for column titles to be below the count
        column_start_margin = top_margin + 25  # Add space for the count label
        
        # LEFT COLUMN: Status Filter
        # Title label
        y_pos = height - column_start_margin - 20 if height > 0 else 155
        status_title_frame = NSRect((10, y_pos), (third_width - 15, 20))
        status_title = NSTextField.alloc().initWithFrame_(status_title_frame)
        status_title.setStringValue_("Status Filter:")
        status_title.setBordered_(False)
        status_title.setDrawsBackground_(False)
        status_title.setEditable_(False)
        status_title.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(status_title)
        
        # Create status checkboxes
        status_checkboxes = {}
        statuses = [
            (ChecklistStatus.OPEN, "Open"),
            (ChecklistStatus.NOT_A_FINDING, "Not a Fi..."),
            (ChecklistStatus.NOT_REVIEWED, "Not Revi..."),
            (ChecklistStatus.NOT_APPLICABLE, "Not App..."),
        ]
        
        y_pos -= row_spacing
        for status, label in statuses:
            checkbox_frame = NSRect((10, y_pos), (third_width - 15, 20))
            checkbox = NSButton.alloc().initWithFrame_(checkbox_frame)
            checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
            checkbox.setTitle_(label)
            checkbox.setState_(1)  # Initially checked
            checkbox.setTarget_(self)
            checkbox.setAction_("statusCheckboxChanged:")
            checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
            self.addSubview_(checkbox)
            
            status_checkboxes[status] = checkbox
            y_pos -= row_spacing
        
        # MIDDLE COLUMN: Severity Filter
        # Title label
        y_pos = height - column_start_margin - 20 if height > 0 else 155
        severity_title_frame = NSRect((third_width + 5, y_pos), (third_width - 15, 20))
        severity_title = NSTextField.alloc().initWithFrame_(severity_title_frame)
        severity_title.setStringValue_("Severity:")
        severity_title.setBordered_(False)
        severity_title.setDrawsBackground_(False)
        severity_title.setEditable_(False)
        severity_title.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(severity_title)
        
        # Create severity checkboxes
        severity_checkboxes = {}
        severities = [
            ('high', "High"),
            ('medium', "Medium"),
            ('low', "Low/Other"),
        ]
        
        y_pos -= row_spacing
        for sev_key, label in severities:
            checkbox_frame = NSRect((third_width + 5, y_pos), (third_width - 15, 20))
            checkbox = NSButton.alloc().initWithFrame_(checkbox_frame)
            checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
            checkbox.setTitle_(label)
            checkbox.setState_(1)  # Initially checked
            checkbox.setTarget_(self)
            checkbox.setAction_("severityCheckboxChanged:")
            checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
            self.addSubview_(checkbox)
            
            severity_checkboxes[sev_key] = checkbox
            y_pos -= row_spacing
        
        # RIGHT COLUMN: Other filters
        # Title label
        y_pos = height - column_start_margin - 20 if height > 0 else 155
        mtf_title_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        mtf_title = NSTextField.alloc().initWithFrame_(mtf_title_frame)
        mtf_title.setStringValue_("Other:")
        mtf_title.setBordered_(False)
        mtf_title.setDrawsBackground_(False)
        mtf_title.setEditable_(False)
        mtf_title.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(mtf_title)
        
        # Create MTF checkbox
        y_pos -= row_spacing
        mtf_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        mtf_checkbox = NSButton.alloc().initWithFrame_(mtf_checkbox_frame)
        mtf_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        mtf_checkbox.setTitle_("Hide MTF")
        mtf_checkbox.setState_(0)  # Initially UNchecked (show MTF items)
        mtf_checkbox.setTarget_(self)
        mtf_checkbox.setAction_("mtfCheckboxChanged:")
        mtf_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(mtf_checkbox)
        
        # Create Invalid Arg checkbox
        y_pos -= row_spacing
        invalid_arg_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        invalid_arg_checkbox = NSButton.alloc().initWithFrame_(invalid_arg_checkbox_frame)
        invalid_arg_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        invalid_arg_checkbox.setTitle_("Invalid A...")
        invalid_arg_checkbox.setState_(0)  # Initially UNchecked
        invalid_arg_checkbox.setTarget_(self)
        invalid_arg_checkbox.setAction_("invalidArgCheckboxChanged:")
        invalid_arg_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(invalid_arg_checkbox)
        
        # Create STIG/Checklist Rule Title checkbox
        y_pos -= row_spacing
        rule_title_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        rule_title_checkbox = NSButton.alloc().initWithFrame_(rule_title_checkbox_frame)
        rule_title_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        rule_title_checkbox.setTitle_("STIG/Chec...")
        rule_title_checkbox.setState_(0)  # Initially UNchecked
        rule_title_checkbox.setTarget_(self)
        rule_title_checkbox.setAction_("ruleTitleCheckboxChanged:")
        rule_title_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(rule_title_checkbox)
        
        # Create No info checkbox
        y_pos -= row_spacing
        no_info_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        no_info_checkbox = NSButton.alloc().initWithFrame_(no_info_checkbox_frame)
        no_info_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        no_info_checkbox.setTitle_("No info")
        no_info_checkbox.setState_(0)  # Initially UNchecked
        no_info_checkbox.setTarget_(self)
        no_info_checkbox.setAction_("noInfoCheckboxChanged:")
        no_info_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        self.addSubview_(no_info_checkbox)
        
        # Add "Close Checklist" button at bottom right corner
        btn_width = 130
        btn_height = 28
        close_btn_frame = NSRect((width - btn_width - 5, 5), (btn_width, btn_height))
        close_btn = NSButton.alloc().initWithFrame_(close_btn_frame)
        close_btn.setTitle_("Close Checklist")
        close_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        close_btn.setTarget_(self)
        close_btn.setAction_("closeChecklist:")
        from AppKit import NSViewMinXMargin
        close_btn.setAutoresizingMask_(NSViewMinXMargin)  # Keep on right side
        self.addSubview_(close_btn)
        attrs['close_btn'] = close_btn
        
        attrs['status_checkboxes'] = status_checkboxes
        attrs['severity_checkboxes'] = severity_checkboxes
        attrs['mtf_checkbox'] = mtf_checkbox
        attrs['invalid_arg_checkbox'] = invalid_arg_checkbox
        attrs['rule_title_checkbox'] = rule_title_checkbox
        attrs['no_info_checkbox'] = no_info_checkbox
        print(f"StatusFilterPane.createUI: Created {len(status_checkboxes)} status + {len(severity_checkboxes)} severity + 4 other checkboxes")  # Debug
        print("StatusFilterPane.createUI: Complete")  # Debug
    
    def statusCheckboxChanged_(self, sender):
        """Handle status checkbox state change."""
        print(f"StatusFilterPane.statusCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        status_checkboxes = attrs.get('status_checkboxes', {})
        status_filters = attrs.get('status_filters', {})
        
        # Update all status filter states
        for status, checkbox in status_checkboxes.items():
            status_filters[status] = (checkbox.state() == 1)
        
        print(f"StatusFilterPane: Status filters = {status_filters}")  # Debug
        self._trigger_callback()
    
    def severityCheckboxChanged_(self, sender):
        """Handle severity checkbox state change."""
        print(f"StatusFilterPane.severityCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        severity_checkboxes = attrs.get('severity_checkboxes', {})
        severity_filters = attrs.get('severity_filters', {})
        
        # Update all severity filter states
        for sev_key, checkbox in severity_checkboxes.items():
            severity_filters[sev_key] = (checkbox.state() == 1)
        
        print(f"StatusFilterPane: Severity filters = {severity_filters}")  # Debug
        self._trigger_callback()
    
    def mtfCheckboxChanged_(self, sender):
        """Handle MTF checkbox state change."""
        print(f"StatusFilterPane.mtfCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        mtf_checkbox = attrs.get('mtf_checkbox')
        
        # Update MTF filter state (when checked, hide MTF items)
        if mtf_checkbox:
            attrs['mtf_filter'] = (mtf_checkbox.state() == 1)
            print(f"StatusFilterPane: MTF filter = {attrs['mtf_filter']}")  # Debug
        
        self._trigger_callback()
    
    def invalidArgCheckboxChanged_(self, sender):
        """Handle Invalid Arg checkbox state change."""
        print(f"StatusFilterPane.invalidArgCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        invalid_arg_checkbox = attrs.get('invalid_arg_checkbox')
        
        # Update Invalid Arg filter state (when checked, show ONLY Invalid Argument items)
        if invalid_arg_checkbox:
            attrs['invalid_arg_filter'] = (invalid_arg_checkbox.state() == 1)
            print(f"StatusFilterPane: Invalid Arg filter = {attrs['invalid_arg_filter']}")  # Debug
        
        self._trigger_callback()
    
    def ruleTitleCheckboxChanged_(self, sender):
        """Handle STIG/Checklist Rule Title checkbox state change."""
        print(f"StatusFilterPane.ruleTitleCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        rule_title_checkbox = attrs.get('rule_title_checkbox')
        
        # Update Rule Title filter state (when checked, show ONLY items with Rule Title mismatches)
        if rule_title_checkbox:
            attrs['rule_title_mismatch_filter'] = (rule_title_checkbox.state() == 1)
            print(f"StatusFilterPane: Rule Title mismatch filter = {attrs['rule_title_mismatch_filter']}")  # Debug
        
        self._trigger_callback()
    
    def noInfoCheckboxChanged_(self, sender):
        """Handle No info checkbox state change."""
        print(f"StatusFilterPane.noInfoCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        no_info_checkbox = attrs.get('no_info_checkbox')
        
        # Update No info filter state (when checked, hide V-codes with "no info" Finding Details)
        if no_info_checkbox:
            attrs['no_info_filter'] = (no_info_checkbox.state() == 1)
            print(f"StatusFilterPane: No info filter = {attrs['no_info_filter']}")  # Debug
        
        self._trigger_callback()
    
    @objc.python_method
    def _trigger_callback(self):
        """Trigger the filter changed callback."""
        attrs = get_view_attrs(self)
        on_filter_changed = attrs.get('on_filter_changed')
        if on_filter_changed:
            print("StatusFilterPane: Calling filter changed callback")  # Debug
            on_filter_changed()
        else:
            print("StatusFilterPane: WARNING - No filter changed callback set!")  # Debug
    
    @objc.python_method
    def get_enabled_statuses(self):
        """Get the list of enabled status values."""
        attrs = get_view_attrs(self)
        status_filters = attrs.get('status_filters', {})
        enabled = [status for status, enabled in status_filters.items() if enabled]
        print(f"StatusFilterPane.get_enabled_statuses: Returning {len(enabled)} enabled statuses")  # Debug
        return enabled
    
    @objc.python_method
    def get_enabled_severities(self):
        """Get the list of enabled severity values."""
        attrs = get_view_attrs(self)
        severity_filters = attrs.get('severity_filters', {})
        enabled = [sev for sev, enabled in severity_filters.items() if enabled]
        print(f"StatusFilterPane.get_enabled_severities: Returning {len(enabled)} enabled severities")  # Debug
        return enabled
    
    @objc.python_method
    def is_mtf_filter_enabled(self):
        """Check if MTF filter is enabled (hide MTF/risk-accepted items)."""
        attrs = get_view_attrs(self)
        mtf_enabled = attrs.get('mtf_filter', False)
        print(f"StatusFilterPane.is_mtf_filter_enabled: {mtf_enabled}")  # Debug
        return mtf_enabled
    
    @objc.python_method
    def is_invalid_arg_filter_enabled(self):
        """Check if Invalid Arg filter is enabled (show ONLY Invalid Argument items in finding details)."""
        attrs = get_view_attrs(self)
        invalid_arg_enabled = attrs.get('invalid_arg_filter', False)
        print(f"StatusFilterPane.is_invalid_arg_filter_enabled: {invalid_arg_enabled}")  # Debug
        return invalid_arg_enabled
    
    @objc.python_method
    def is_rule_title_mismatch_filter_enabled(self):
        """Check if Rule Title mismatch filter is enabled (show ONLY items with STIG vs Checklist Rule Title differences)."""
        attrs = get_view_attrs(self)
        rule_title_enabled = attrs.get('rule_title_mismatch_filter', False)
        print(f"StatusFilterPane.is_rule_title_mismatch_filter_enabled: {rule_title_enabled}")  # Debug
        return rule_title_enabled
    
    @objc.python_method
    def is_no_info_filter_enabled(self):
        """Check if No info filter is enabled (hide V-codes with 'no info' Finding Details pattern)."""
        attrs = get_view_attrs(self)
        no_info_enabled = attrs.get('no_info_filter', False)
        print(f"StatusFilterPane.is_no_info_filter_enabled: {no_info_enabled}")  # Debug
        return no_info_enabled
    
    def closeChecklist_(self, sender):
        """Handle Close Checklist button click."""
        print("StatusFilterPane.closeChecklist_: Button clicked")  # Debug
        attrs = get_view_attrs(self)
        on_close_callback = attrs.get('on_close_callback')
        if on_close_callback:
            print("StatusFilterPane.closeChecklist_: Calling close callback")  # Debug
            on_close_callback()
        else:
            print("StatusFilterPane.closeChecklist_: WARNING - No close callback set!")  # Debug
    
    @objc.python_method
    def set_on_filter_changed(self, callback):
        """Set the callback for filter changes."""
        attrs = get_view_attrs(self)
        attrs['on_filter_changed'] = callback
        print("StatusFilterPane.set_on_filter_changed: Callback set")  # Debug
    
    @objc.python_method
    def set_on_close_callback(self, callback):
        """Set the callback for close button."""
        attrs = get_view_attrs(self)
        attrs['on_close_callback'] = callback
        print("StatusFilterPane.set_on_close_callback: Callback set")  # Debug
    
    @objc.python_method
    def update_vcode_count(self, count):
        """Update the V-code count display.
        
        Args:
            count: Number of V-codes currently visible after filtering
        """
        attrs = get_view_attrs(self)
        vcode_count_label = attrs.get('vcode_count_label')
        if vcode_count_label:
            vcode_count_label.setStringValue_(f"V-codes: {count}")
            print(f"StatusFilterPane.update_vcode_count: Updated count to {count}")  # Debug
        else:
            print("StatusFilterPane.update_vcode_count: WARNING - No count label!")  # Debug

