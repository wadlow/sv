"""Search criteria pane."""

from AppKit import (
    NSView, NSRect, NSTextField, NSButton, NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
import objc

from .view_helpers import get_view_attrs, get_bounds_size


class SearchPane(NSView):
    """Pane for entering search criteria."""
    
    def init(self):
        """Initialize the search pane."""
        self = objc.super(SearchPane, self).init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['search_field'] = None
        attrs['on_search_changed'] = None
        attrs['severity_filters'] = {
            'high': True,
            'medium': True,
            'low': True,
        }
        attrs['severity_checkboxes'] = {}
        attrs['rule_title_mismatch_filter'] = False  # Initially unchecked
        attrs['rule_title_checkbox'] = None
        attrs['count_label'] = None
        SearchPane.createUI(self)
        return self
    
    def createUI(self):
        """Create the UI with severity filter checkboxes."""
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            from AppKit import NSRect
            width, height = 300, 120
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
        
        attrs = get_view_attrs(self)
        
        # Title label (left side)
        title_frame = NSRect((10, height - 25), (width // 2 - 10, 20))
        title_label = NSTextField.alloc().initWithFrame_(title_frame)
        title_label.setStringValue_("Severity Filter:")
        title_label.setBordered_(False)
        title_label.setDrawsBackground_(False)
        title_label.setEditable_(False)
        title_label.setAutoresizingMask_(NSViewWidthSizable | 0x08)  # Width sizable + NSViewMinYMargin (stays at top)
        self.addSubview_(title_label)
        
        # V-code count label (right side, same row as title)
        from AppKit import NSColor, NSRightTextAlignment
        count_frame = NSRect((width // 2, height - 25), (width // 2 - 10, 20))
        count_label = NSTextField.alloc().initWithFrame_(count_frame)
        count_label.setStringValue_("V-codes: 0")
        count_label.setBordered_(False)
        count_label.setDrawsBackground_(False)
        count_label.setEditable_(False)
        count_label.setTextColor_(NSColor.whiteColor())
        count_label.setAlignment_(NSRightTextAlignment)  # Right-align the text
        count_label.setAutoresizingMask_(NSViewWidthSizable | 0x08)  # Width sizable + NSViewMinYMargin
        self.addSubview_(count_label)
        attrs['count_label'] = count_label
        
        # Create severity checkboxes
        severity_checkboxes = {}
        severities = [
            ('high', "High"),
            ('medium', "Medium"),
            ('low', "Low/Other"),
        ]
        
        y_pos = height - 50
        for sev_key, label in severities:
            checkbox_frame = NSRect((10, y_pos), (width - 20, 20))
            checkbox = NSButton.alloc().initWithFrame_(checkbox_frame)
            checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
            checkbox.setTitle_(label)
            checkbox.setState_(1)  # Initially checked
            checkbox.setTarget_(self)
            checkbox.setAction_("severityCheckboxChanged:")
            checkbox.setAutoresizingMask_(NSViewWidthSizable | 0x08)  # Width sizable + NSViewMinYMargin
            self.addSubview_(checkbox)
            
            severity_checkboxes[sev_key] = checkbox
            y_pos -= 25
        
        attrs['severity_checkboxes'] = severity_checkboxes
        
        # Add "STIG/Checklist Rule Title" checkbox after severity filters
        rule_title_checkbox_frame = NSRect((10, y_pos), (width - 20, 20))
        rule_title_checkbox = NSButton.alloc().initWithFrame_(rule_title_checkbox_frame)
        rule_title_checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
        rule_title_checkbox.setTitle_("STIG/Checklist Rule Title")
        rule_title_checkbox.setState_(0)  # Initially unchecked
        rule_title_checkbox.setTarget_(self)
        rule_title_checkbox.setAction_("ruleTitleCheckboxChanged:")
        rule_title_checkbox.setAutoresizingMask_(NSViewWidthSizable | 0x08)  # Width sizable + NSViewMinYMargin
        self.addSubview_(rule_title_checkbox)
        attrs['rule_title_checkbox'] = rule_title_checkbox
        
        # Add Delete Selected STIG button at the bottom right corner (small)
        btn_width = 130
        btn_height = 24
        delete_btn_frame = NSRect((width - btn_width - 10, 10), (btn_width, btn_height))
        delete_btn = NSButton.alloc().initWithFrame_(delete_btn_frame)
        delete_btn.setTitle_("Delete Selected STIG")
        delete_btn.setButtonType_(0)  # NSMomentaryPushInButton
        delete_btn.setBezelStyle_(4)  # NSRoundedBezelStyle (4 = small rounded)
        from AppKit import NSFont
        small_font = NSFont.systemFontOfSize_(11)  # Smaller font
        delete_btn.setFont_(small_font)
        delete_btn.setTarget_(self)
        delete_btn.setAction_("deleteStigClicked:")
        delete_btn.setEnabled_(False)  # Initially disabled
        self.addSubview_(delete_btn)
        attrs['delete_btn'] = delete_btn
        
        print(f"SearchPane.createUI: Created {len(severity_checkboxes)} severity checkboxes + delete button")  # Debug
    
    @objc.python_method
    def get_search_text(self) -> str:
        """Get the current search text (deprecated - now using severity filters)."""
        # Search text field was replaced with severity checkboxes
        return ""
    
    def severityCheckboxChanged_(self, sender):
        """Handle severity checkbox state change."""
        print(f"SearchPane.severityCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        severity_checkboxes = attrs.get('severity_checkboxes', {})
        severity_filters = attrs.get('severity_filters', {})
        
        # Update all severity filter states
        for sev_key, checkbox in severity_checkboxes.items():
            severity_filters[sev_key] = (checkbox.state() == 1)
        
        print(f"SearchPane: Severity filters = {severity_filters}")  # Debug
        
        # Call the filter changed callback
        on_search_changed = attrs.get('on_search_changed')
        if on_search_changed:
            print("SearchPane: Calling filter changed callback")  # Debug
            on_search_changed()
        else:
            print("SearchPane: WARNING - No filter changed callback set!")  # Debug
    
    def ruleTitleCheckboxChanged_(self, sender):
        """Handle Rule Title checkbox state change."""
        print(f"SearchPane.ruleTitleCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        rule_title_checkbox = attrs.get('rule_title_checkbox')
        
        # Update rule title filter state
        if rule_title_checkbox:
            attrs['rule_title_mismatch_filter'] = (rule_title_checkbox.state() == 1)
            print(f"SearchPane: Rule Title mismatch filter = {attrs['rule_title_mismatch_filter']}")  # Debug
        
        # Call the filter changed callback
        on_search_changed = attrs.get('on_search_changed')
        if on_search_changed:
            print("SearchPane: Calling filter changed callback")  # Debug
            on_search_changed()
        else:
            print("SearchPane: WARNING - No filter changed callback set!")  # Debug
    
    def deleteStigClicked_(self, sender):
        """Handle Delete STIG button click."""
        print("SearchPane.deleteStigClicked_: Called")  # Debug
        attrs = get_view_attrs(self)
        on_delete_stig = attrs.get('on_delete_stig')
        if on_delete_stig:
            print("SearchPane: Calling delete STIG callback")  # Debug
            on_delete_stig()
        else:
            print("SearchPane: WARNING - No delete STIG callback set!")  # Debug
    
    @objc.python_method
    def update_delete_button_state(self, has_selection):
        """Update the delete button enabled state based on selection."""
        print(f"SearchPane.update_delete_button_state: Called with has_selection={has_selection}")  # Debug
        attrs = get_view_attrs(self)
        delete_btn = attrs.get('delete_btn')
        print(f"SearchPane.update_delete_button_state: delete_btn={delete_btn}")  # Debug
        if delete_btn:
            delete_btn.setEnabled_(has_selection)
            print(f"SearchPane.update_delete_button_state: Button enabled set to {has_selection}")  # Debug
        else:
            print("SearchPane.update_delete_button_state: WARNING - No delete button!")  # Debug
    
    @objc.python_method
    def get_enabled_severities(self):
        """Get the list of enabled severity values."""
        attrs = get_view_attrs(self)
        severity_filters = attrs.get('severity_filters', {})
        enabled = [sev for sev, enabled in severity_filters.items() if enabled]
        print(f"SearchPane.get_enabled_severities: Returning {len(enabled)} enabled severities")  # Debug
        return enabled
    
    @objc.python_method
    def get_rule_title_mismatch_filter(self):
        """Get the state of the Rule Title mismatch filter."""
        attrs = get_view_attrs(self)
        return attrs.get('rule_title_mismatch_filter', False)
    
    @objc.python_method
    def update_vcode_count(self, count):
        """Update the V-code count display.
        
        Args:
            count: Number of V-codes currently visible
        """
        attrs = get_view_attrs(self)
        count_label = attrs.get('count_label')
        if count_label:
            count_label.setStringValue_(f"V-codes: {count}")
            print(f"SearchPane.update_vcode_count: Updated count to {count}")  # Debug
        else:
            print("SearchPane.update_vcode_count: WARNING - No count label!")  # Debug

