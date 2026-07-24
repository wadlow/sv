"""Search criteria pane."""

from AppKit import (
    NSView, NSRect, NSTextField, NSButton, NSViewWidthSizable, NSViewHeightSizable,
    NSViewMinXMargin, NSViewMaxXMargin, NSColor, NSFont, NSRightTextAlignment,
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
        attrs['hide_audit_filter'] = False  # Initially unchecked
        attrs['hide_audit_checkbox'] = None
        attrs['count_label'] = None
        attrs['check_texts_btn'] = None
        attrs['on_check_texts'] = None
        attrs['title_label'] = None
        SearchPane.createUI(self)
        return self

    FOOTER_HEIGHT = 36
    CHECKBOX_ROW_HEIGHT = 25
    TOP_MARGIN = 5
    TITLE_HEIGHT = 20

    def resizeSubviewsWithOldSize_(self, old_size):
        objc.super(SearchPane, self).resizeSubviewsWithOldSize_(old_size)
        SearchPane._layout_content(self)

    def viewDidMoveToWindow(self):
        SearchPane._layout_content(self)
    
    def createUI(self):
        """Create the UI with severity filter checkboxes."""
        self.setFlipped_(True)
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 300, 220
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
        
        attrs = get_view_attrs(self)
        
        title_label = NSTextField.alloc().initWithFrame_(NSRect((10, self.TOP_MARGIN), (width // 2 - 10, self.TITLE_HEIGHT)))
        title_label.setStringValue_("Severity Filter:")
        title_label.setBordered_(False)
        title_label.setDrawsBackground_(False)
        title_label.setEditable_(False)
        title_label.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        self.addSubview_(title_label)
        attrs['title_label'] = title_label
        
        count_label = NSTextField.alloc().initWithFrame_(NSRect((width // 2, self.TOP_MARGIN), (width // 2 - 10, self.TITLE_HEIGHT)))
        count_label.setStringValue_("V-codes: 0")
        count_label.setBordered_(False)
        count_label.setDrawsBackground_(False)
        count_label.setEditable_(False)
        count_label.setTextColor_(NSColor.whiteColor())
        count_label.setAlignment_(NSRightTextAlignment)
        count_label.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        self.addSubview_(count_label)
        attrs['count_label'] = count_label
        
        severity_checkboxes = {}
        severities = [
            ('high', "High", "Show V-codes with CAT I (high) severity"),
            ('medium', "Medium", "Show V-codes with CAT II (medium) severity"),
            ('low', "Low/Other", "Show V-codes with CAT III (low) severity and other severities"),
        ]
        
        for sev_key, label, tooltip in severities:
            checkbox = NSButton.alloc().initWithFrame_(NSRect((10, 0), (width - 20, 20)))
            checkbox.setButtonType_(3)  # NSSwitchButton (checkbox)
            checkbox.setTitle_(label)
            checkbox.setState_(1)  # Initially checked
            checkbox.setTarget_(self)
            checkbox.setAction_("severityCheckboxChanged:")
            checkbox.setAutoresizingMask_(NSViewWidthSizable)
            checkbox.setToolTip_(tooltip)
            self.addSubview_(checkbox)
            severity_checkboxes[sev_key] = checkbox
        
        attrs['severity_checkboxes'] = severity_checkboxes
        
        rule_title_checkbox = NSButton.alloc().initWithFrame_(NSRect((10, 0), (width - 20, 20)))
        rule_title_checkbox.setButtonType_(3)
        rule_title_checkbox.setTitle_("STIG/Checklist Rule Title")
        rule_title_checkbox.setState_(0)
        rule_title_checkbox.setTarget_(self)
        rule_title_checkbox.setAction_("ruleTitleCheckboxChanged:")
        rule_title_checkbox.setAutoresizingMask_(NSViewWidthSizable)
        rule_title_checkbox.setToolTip_("Show ONLY V-codes where STIG Rule Title differs from Checklist Rule Title")
        self.addSubview_(rule_title_checkbox)
        attrs['rule_title_checkbox'] = rule_title_checkbox
        
        hide_audit_checkbox = NSButton.alloc().initWithFrame_(NSRect((10, 0), (width - 20, 20)))
        hide_audit_checkbox.setButtonType_(3)
        hide_audit_checkbox.setTitle_("Hide Audit")
        hide_audit_checkbox.setState_(0)
        hide_audit_checkbox.setTarget_(self)
        hide_audit_checkbox.setAction_("hideAuditCheckboxChanged:")
        hide_audit_checkbox.setAutoresizingMask_(NSViewWidthSizable)
        hide_audit_checkbox.setToolTip_("Hide V-codes with 'audit' in their title (e.g., auditing, audited)")
        self.addSubview_(hide_audit_checkbox)
        attrs['hide_audit_checkbox'] = hide_audit_checkbox

        small_font = NSFont.systemFontOfSize_(11)
        delete_btn = NSButton.alloc().initWithFrame_(NSRect((0, 0), (130, 24)))
        delete_btn.setTitle_("Delete Selected STIG")
        delete_btn.setButtonType_(0)
        delete_btn.setBezelStyle_(4)
        delete_btn.setFont_(small_font)
        delete_btn.setTarget_(self)
        delete_btn.setAction_("deleteStigClicked:")
        delete_btn.setEnabled_(False)
        delete_btn.setAutoresizingMask_(NSViewMinXMargin | NSViewMaxXMargin)
        self.addSubview_(delete_btn)
        attrs['delete_btn'] = delete_btn

        check_texts_btn = NSButton.alloc().initWithFrame_(NSRect((0, 0), (100, 24)))
        check_texts_btn.setTitle_("Check Texts")
        check_texts_btn.setButtonType_(0)
        check_texts_btn.setBezelStyle_(4)
        check_texts_btn.setFont_(small_font)
        check_texts_btn.setTarget_(self)
        check_texts_btn.setAction_("checkTextsClicked:")
        check_texts_btn.setAutoresizingMask_(NSViewMinXMargin | NSViewMaxXMargin)
        self.addSubview_(check_texts_btn)
        attrs['check_texts_btn'] = check_texts_btn

        SearchPane._layout_content(self)
        
        print(f"SearchPane.createUI: Created {len(severity_checkboxes)} severity checkboxes + footer buttons")  # Debug

    @objc.python_method
    def _layout_content(self):
        """Lay out filter controls with buttons pinned to the bottom."""
        width, height = get_bounds_size(self.bounds())
        if width == 0 or height == 0:
            return

        attrs = get_view_attrs(self)
        title_label = attrs.get('title_label')
        count_label = attrs.get('count_label')
        if title_label:
            title_label.setFrame_(NSRect((10, self.TOP_MARGIN), (max(80, width // 2 - 10), self.TITLE_HEIGHT)))
        if count_label:
            count_label.setFrame_(NSRect((width // 2, self.TOP_MARGIN), (max(80, width // 2 - 10), self.TITLE_HEIGHT)))

        checkbox_y = self.TOP_MARGIN + self.TITLE_HEIGHT + 8
        for checkbox in attrs.get('severity_checkboxes', {}).values():
            checkbox.setFrame_(NSRect((10, checkbox_y), (max(100, width - 20), 20)))
            checkbox_y += self.CHECKBOX_ROW_HEIGHT

        rule_title_checkbox = attrs.get('rule_title_checkbox')
        if rule_title_checkbox:
            rule_title_checkbox.setFrame_(NSRect((10, checkbox_y), (max(100, width - 20), 20)))
            checkbox_y += self.CHECKBOX_ROW_HEIGHT

        hide_audit_checkbox = attrs.get('hide_audit_checkbox')
        if hide_audit_checkbox:
            hide_audit_checkbox.setFrame_(NSRect((10, checkbox_y), (max(100, width - 20), 20)))

        btn_height = 24
        btn_y = height - btn_height - 8
        btn_right = width - 10
        delete_btn = attrs.get('delete_btn')
        check_texts_btn = attrs.get('check_texts_btn')
        delete_width = 130
        check_texts_width = 100
        btn_gap = 10

        if delete_btn:
            delete_btn.setFrame_(NSRect((btn_right - delete_width, btn_y), (delete_width, btn_height)))
        if check_texts_btn:
            check_texts_btn.setFrame_(
                NSRect(
                    (btn_right - delete_width - btn_gap - check_texts_width, btn_y),
                    (check_texts_width, btn_height),
                )
            )
    
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
    
    def hideAuditCheckboxChanged_(self, sender):
        """Handle Hide Audit checkbox state change."""
        print(f"SearchPane.hideAuditCheckboxChanged_: Checkbox changed")  # Debug
        attrs = get_view_attrs(self)
        hide_audit_checkbox = attrs.get('hide_audit_checkbox')
        
        # Update hide audit filter state
        if hide_audit_checkbox:
            attrs['hide_audit_filter'] = (hide_audit_checkbox.state() == 1)
            print(f"SearchPane: Hide Audit filter = {attrs['hide_audit_filter']}")  # Debug
        
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

    def checkTextsClicked_(self, sender):
        """Handle Check Texts button click."""
        attrs = get_view_attrs(self)
        on_check_texts = attrs.get('on_check_texts')
        if on_check_texts:
            on_check_texts()
    
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
    def get_hide_audit_filter(self):
        """Get the state of the Hide Audit filter."""
        attrs = get_view_attrs(self)
        return attrs.get('hide_audit_filter', False)
    
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

