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
        attrs['low_confidence_filter'] = False  # Default OFF - when ON, shows ONLY V-codes with low confidence Check Text analysis
        attrs['not_met_filter'] = False  # Default OFF - when ON, shows ONLY V-codes where Check Text criteria are not met
        attrs['hide_manual_filter'] = False  # Default OFF - when ON, hides V-codes with "MANUAL TEST REQUIRED" in Finding Details
        attrs['hide_audit_filter'] = False  # Default OFF - when ON, hides V-codes with "audit" in their title
        attrs['on_filter_changed'] = None
        attrs['on_compare_to_check_text'] = None
        attrs['status_checkboxes'] = {}
        attrs['severity_checkboxes'] = {}
        attrs['mtf_checkbox'] = None
        attrs['invalid_arg_checkbox'] = None
        attrs['rule_title_checkbox'] = None
        attrs['no_info_checkbox'] = None
        attrs['low_confidence_checkbox'] = None
        attrs['not_met_checkbox'] = None
        attrs['hide_manual_checkbox'] = None
        attrs['hide_audit_checkbox'] = None
        attrs['vcode_count_label'] = None
        attrs['compare_button'] = None
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
        
        # Create status checkboxes with tooltips
        status_checkboxes = {}
        statuses = [
            (ChecklistStatus.OPEN, "Open", "Show V-codes with status: Open"),
            (ChecklistStatus.NOT_A_FINDING, "Not a Fi...", "Show V-codes with status: Not a Finding"),
            (ChecklistStatus.NOT_REVIEWED, "Not Revi...", "Show V-codes with status: Not Reviewed"),
            (ChecklistStatus.NOT_APPLICABLE, "Not App...", "Show V-codes with status: Not Applicable"),
        ]
        
        y_pos -= row_spacing
        for status, label, tooltip in statuses:
            checkbox_frame = NSRect((10, y_pos), (third_width - 15, 20))
            checkbox = NSButton.alloc().initWithFrame_(checkbox_frame)
            checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
            checkbox.setTitle_(label)
            checkbox.setState_(1)  # Initially checked
            checkbox.setTarget_(self)
            checkbox.setAction_("statusCheckboxChanged:")
            checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
            checkbox.setToolTip_(tooltip)
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
        
        # Create severity checkboxes with tooltips
        severity_checkboxes = {}
        severities = [
            ('high', "High", "Show V-codes with CAT I (high) severity"),
            ('medium', "Medium", "Show V-codes with CAT II (medium) severity"),
            ('low', "Low/Other", "Show V-codes with CAT III (low) severity and other severities"),
        ]
        
        y_pos -= row_spacing
        for sev_key, label, tooltip in severities:
            checkbox_frame = NSRect((third_width + 5, y_pos), (third_width - 15, 20))
            checkbox = NSButton.alloc().initWithFrame_(checkbox_frame)
            checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
            checkbox.setTitle_(label)
            checkbox.setState_(1)  # Initially checked
            checkbox.setTarget_(self)
            checkbox.setAction_("severityCheckboxChanged:")
            checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
            checkbox.setToolTip_(tooltip)
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
        mtf_checkbox.setToolTip_("Hide V-codes marked as MTF (Mitigated by Technical Fix) or risk-accepted in Finding Details")
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
        invalid_arg_checkbox.setToolTip_("Show ONLY V-codes with 'Invalid Argument' in Finding Details")
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
        rule_title_checkbox.setToolTip_("Show ONLY V-codes where STIG Rule Title differs from Checklist Rule Title")
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
        no_info_checkbox.setToolTip_("Hide V-codes with 'no info' or placeholder text in Finding Details")
        self.addSubview_(no_info_checkbox)
        
        # Create Low Confidence checkbox
        y_pos -= row_spacing
        low_confidence_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        low_confidence_checkbox = NSButton.alloc().initWithFrame_(low_confidence_checkbox_frame)
        low_confidence_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        low_confidence_checkbox.setTitle_("Low Confid...")
        low_confidence_checkbox.setState_(0)  # Initially UNchecked
        low_confidence_checkbox.setTarget_(self)
        low_confidence_checkbox.setAction_("lowConfidenceCheckboxChanged:")
        low_confidence_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        low_confidence_checkbox.setToolTip_("Show ONLY V-codes with low confidence Check Text analysis results")
        self.addSubview_(low_confidence_checkbox)
        
        # Create Not Met checkbox
        y_pos -= row_spacing
        not_met_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        not_met_checkbox = NSButton.alloc().initWithFrame_(not_met_checkbox_frame)
        not_met_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        not_met_checkbox.setTitle_("Not Met")
        not_met_checkbox.setState_(0)  # Initially UNchecked
        not_met_checkbox.setTarget_(self)
        not_met_checkbox.setAction_("notMetCheckboxChanged:")
        not_met_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        not_met_checkbox.setToolTip_("Show ONLY V-codes where Check Text criteria are not met based on Finding Details")
        self.addSubview_(not_met_checkbox)
        
        # Create Hide MANUAL checkbox
        y_pos -= row_spacing
        hide_manual_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        hide_manual_checkbox = NSButton.alloc().initWithFrame_(hide_manual_checkbox_frame)
        hide_manual_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        hide_manual_checkbox.setTitle_("Hide MANUAL")
        hide_manual_checkbox.setState_(0)  # Initially UNchecked
        hide_manual_checkbox.setTarget_(self)
        hide_manual_checkbox.setAction_("hideManualCheckboxChanged:")
        hide_manual_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        hide_manual_checkbox.setToolTip_("Hide V-codes with 'MANUAL TEST REQUIRED' in Finding Details")
        self.addSubview_(hide_manual_checkbox)
        
        # Create Hide Audit checkbox
        y_pos -= row_spacing
        hide_audit_checkbox_frame = NSRect((third_width * 2 + 5, y_pos), (third_width - 15, 20))
        hide_audit_checkbox = NSButton.alloc().initWithFrame_(hide_audit_checkbox_frame)
        hide_audit_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        hide_audit_checkbox.setTitle_("Hide Audit")
        hide_audit_checkbox.setState_(0)  # Initially UNchecked
        hide_audit_checkbox.setTarget_(self)
        hide_audit_checkbox.setAction_("hideAuditCheckboxChanged:")
        hide_audit_checkbox.setAutoresizingMask_(NSViewMinYMargin)  # Pin to top
        hide_audit_checkbox.setToolTip_("Hide V-codes with 'audit' in their title (e.g., auditing, audited)")
        self.addSubview_(hide_audit_checkbox)
        
        # Add "Compare to Check Text" button at bottom (left of Close button)
        compare_btn_width = 180
        btn_height = 28
        compare_btn_frame = NSRect((5, 5), (compare_btn_width, btn_height))
        compare_btn = NSButton.alloc().initWithFrame_(compare_btn_frame)
        compare_btn.setTitle_("Compare to Check Text")
        compare_btn.setBezelStyle_(1)  # NSRoundedBezelStyle
        compare_btn.setTarget_(self)
        compare_btn.setAction_("compareToCheckText:")
        compare_btn.setEnabled_(False)  # Initially disabled until V-code is selected
        self.addSubview_(compare_btn)
        attrs['compare_button'] = compare_btn
        
        # Add "Close Checklist" button at bottom right corner
        btn_width = 130
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
        attrs['low_confidence_checkbox'] = low_confidence_checkbox
        attrs['not_met_checkbox'] = not_met_checkbox
        attrs['hide_manual_checkbox'] = hide_manual_checkbox
        attrs['hide_audit_checkbox'] = hide_audit_checkbox
        print(f"StatusFilterPane.createUI: Created {len(status_checkboxes)} status + {len(severity_checkboxes)} severity + 8 other checkboxes")  # Debug
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
    
    def lowConfidenceCheckboxChanged_(self, sender):
        """Handle Low Confidence checkbox state change."""
        print(f"StatusFilterPane.lowConfidenceCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        low_confidence_checkbox = attrs.get('low_confidence_checkbox')
        
        # Update Low Confidence filter state (when checked, show ONLY V-codes with low confidence Check Text analysis)
        if low_confidence_checkbox:
            attrs['low_confidence_filter'] = (low_confidence_checkbox.state() == 1)
            print(f"StatusFilterPane: Low confidence filter = {attrs['low_confidence_filter']}")  # Debug
        
        self._trigger_callback()
    
    def notMetCheckboxChanged_(self, sender):
        """Handle Not Met checkbox state change."""
        print(f"StatusFilterPane.notMetCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        not_met_checkbox = attrs.get('not_met_checkbox')
        
        # Update Not Met filter state (when checked, show ONLY V-codes where Check Text criteria are not met)
        if not_met_checkbox:
            attrs['not_met_filter'] = (not_met_checkbox.state() == 1)
            print(f"StatusFilterPane: Not met filter = {attrs['not_met_filter']}")  # Debug
        
        self._trigger_callback()
    
    def hideManualCheckboxChanged_(self, sender):
        """Handle Hide MANUAL checkbox state change."""
        print(f"StatusFilterPane.hideManualCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        hide_manual_checkbox = attrs.get('hide_manual_checkbox')
        
        # Update Hide MANUAL filter state (when checked, hide V-codes with "MANUAL TEST REQUIRED" in Finding Details)
        if hide_manual_checkbox:
            attrs['hide_manual_filter'] = (hide_manual_checkbox.state() == 1)
            print(f"StatusFilterPane: Hide MANUAL filter = {attrs['hide_manual_filter']}")  # Debug
        
        self._trigger_callback()
    
    def hideAuditCheckboxChanged_(self, sender):
        """Handle Hide Audit checkbox state change."""
        print(f"StatusFilterPane.hideAuditCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        hide_audit_checkbox = attrs.get('hide_audit_checkbox')
        
        # Update Hide Audit filter state (when checked, hide V-codes with "audit" in their title)
        if hide_audit_checkbox:
            attrs['hide_audit_filter'] = (hide_audit_checkbox.state() == 1)
            print(f"StatusFilterPane: Hide Audit filter = {attrs['hide_audit_filter']}")  # Debug
        
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
    
    @objc.python_method
    def is_low_confidence_filter_enabled(self):
        """Check if Low Confidence filter is enabled (show ONLY V-codes with low confidence Check Text analysis)."""
        attrs = get_view_attrs(self)
        low_confidence_enabled = attrs.get('low_confidence_filter', False)
        print(f"StatusFilterPane.is_low_confidence_filter_enabled: {low_confidence_enabled}")  # Debug
        return low_confidence_enabled
    
    @objc.python_method
    def is_not_met_filter_enabled(self):
        """Check if Not Met filter is enabled (show ONLY V-codes where Check Text criteria are not met)."""
        attrs = get_view_attrs(self)
        not_met_enabled = attrs.get('not_met_filter', False)
        print(f"StatusFilterPane.is_not_met_filter_enabled: {not_met_enabled}")  # Debug
        return not_met_enabled
    
    @objc.python_method
    def is_hide_manual_filter_enabled(self):
        """Check if Hide MANUAL filter is enabled (hide V-codes with 'MANUAL TEST REQUIRED' in Finding Details)."""
        attrs = get_view_attrs(self)
        hide_manual_enabled = attrs.get('hide_manual_filter', False)
        print(f"StatusFilterPane.is_hide_manual_filter_enabled: {hide_manual_enabled}")  # Debug
        return hide_manual_enabled
    
    @objc.python_method
    def is_hide_audit_filter_enabled(self):
        """Check if Hide Audit filter is enabled (hide V-codes with 'audit' in their title)."""
        attrs = get_view_attrs(self)
        hide_audit_enabled = attrs.get('hide_audit_filter', False)
        print(f"StatusFilterPane.is_hide_audit_filter_enabled: {hide_audit_enabled}")  # Debug
        return hide_audit_enabled
    
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
    
    def compareToCheckText_(self, sender):
        """Handle Compare to Check Text button click."""
        print("StatusFilterPane.compareToCheckText_: Button clicked")  # Debug
        attrs = get_view_attrs(self)
        on_compare_callback = attrs.get('on_compare_to_check_text')
        if on_compare_callback:
            print("StatusFilterPane.compareToCheckText_: Calling compare callback")  # Debug
            on_compare_callback()
        else:
            print("StatusFilterPane.compareToCheckText_: WARNING - No compare callback set!")  # Debug
    
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
    
    @objc.python_method
    def set_on_compare_to_check_text(self, callback):
        """Set the callback for Compare to Check Text button."""
        attrs = get_view_attrs(self)
        attrs['on_compare_to_check_text'] = callback
        print("StatusFilterPane.set_on_compare_to_check_text: Callback set")  # Debug
    
    @objc.python_method
    def set_compare_button_enabled(self, enabled):
        """Enable or disable the Compare to Check Text button."""
        attrs = get_view_attrs(self)
        compare_button = attrs.get('compare_button')
        if compare_button:
            compare_button.setEnabled_(enabled)
            print(f"StatusFilterPane.set_compare_button_enabled: Set to {enabled}")  # Debug
        else:
            print("StatusFilterPane.set_compare_button_enabled: WARNING - No compare button!")  # Debug

