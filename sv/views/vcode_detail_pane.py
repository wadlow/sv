"""V-code detail pane."""

from AppKit import (
    NSView, NSRect, NSSplitView, NSScrollView, NSTextView, NSTextField,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
from typing import Optional

from ..models.vuln_code import VulnCode, Severity
from .view_helpers import get_view_attrs, get_bounds_size


class VCodeDetailPane(NSView):
    """Pane showing detailed information about a V-code."""
    
    def init(self):
        """Initialize the V-code detail pane."""
        self = NSView.alloc().init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['description_text'] = None
        attrs['details_text'] = None
        VCodeDetailPane.createUI(self)
        return self
    
    def createUI(self):
        """Create the UI with two vertically stacked scroll views using NSSplitView."""
        print("VCodeDetailPane.createUI: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 400, 600
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"VCodeDetailPane.createUI: Set default frame {width}x{height}")  # Debug
        
        print(f"VCodeDetailPane.createUI: bounds={width}x{height}")  # Debug
        
        # Create vertical split view that fills the entire pane
        split_view = NSSplitView.alloc().initWithFrame_(bounds)
        split_view.setVertical_(False)  # Horizontal divider (stacks vertically)
        split_view.setDividerStyle_(1)  # NSSplitViewDividerStyleThin
        split_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Top scroll view: General Information (35% - reduced by 30% from 50%)
        top_height = height * 0.35
        top_scroll_frame = NSRect((0, 0), (width, top_height))
        top_scroll = NSScrollView.alloc().initWithFrame_(top_scroll_frame)
        top_scroll.setHasVerticalScroller_(True)
        top_scroll.setHasHorizontalScroller_(False)
        top_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        top_scroll.setBorderType_(1)  # NSBezelBorder
        top_scroll.setToolTip_("General information about the selected vulnerability (V-code, Rule ID, Severity, Rule Title)")
        
        attrs = get_view_attrs(self)
        # Create text view with proper frame initialization
        text_frame = NSRect((0, 0), (width, top_height))
        description_text = NSTextView.alloc().initWithFrame_(text_frame)
        description_text.setEditable_(False)
        description_text.setSelectable_(True)
        description_text.setRichText_(False)  # Use plain text only
        description_text.setImportsGraphics_(False)  # Don't import graphics
        description_text.setAllowsUndo_(False)  # Disable undo for read-only
        description_text.setFieldEditor_(False)  # Not a field editor
        description_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        top_scroll.setDocumentView_(description_text)
        attrs['description_text'] = description_text
        
        # Bottom scroll view: Specific Details (65% - gets the remaining space)
        bottom_height = height * 0.65
        bottom_scroll_frame = NSRect((0, 0), (width, bottom_height))
        bottom_scroll = NSScrollView.alloc().initWithFrame_(bottom_scroll_frame)
        bottom_scroll.setHasVerticalScroller_(True)
        bottom_scroll.setHasHorizontalScroller_(False)
        bottom_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        bottom_scroll.setBorderType_(1)  # NSBezelBorder
        bottom_scroll.setToolTip_("Detailed information: Discussion, Check Text, and Fix Text for the selected vulnerability")
        
        # Create text view with proper frame initialization
        text_frame = NSRect((0, 0), (width, bottom_height))
        details_text = NSTextView.alloc().initWithFrame_(text_frame)
        details_text.setEditable_(False)
        details_text.setSelectable_(True)
        details_text.setRichText_(False)  # Use plain text only
        details_text.setImportsGraphics_(False)  # Don't import graphics
        details_text.setAllowsUndo_(False)  # Disable undo for read-only
        details_text.setFieldEditor_(False)  # Not a field editor
        details_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        bottom_scroll.setDocumentView_(details_text)
        attrs['details_text'] = details_text
        
        # Add scroll views directly to split view
        split_view.addSubview_(top_scroll)
        split_view.addSubview_(bottom_scroll)
        split_view.adjustSubviews()
        
        # Set divider position (35% for top pane)
        split_view.setPosition_ofDividerAtIndex_(height * 0.35, 0)
        
        # Add split view to self
        self.addSubview_(split_view)
        attrs['split_view'] = split_view
        
        print(f"VCodeDetailPane.createUI: Created split view with two scroll views")  # Debug
        print("VCodeDetailPane.createUI: Complete")  # Debug
    
    def set_vuln_code(self, vuln_code: Optional[VulnCode]):
        """Set the V-code to display."""
        print(f"VCodeDetailPane.set_vuln_code: Called with {vuln_code.v_code if vuln_code else 'None'}")  # Debug
        attrs = get_view_attrs(self)
        description_text = attrs.get('description_text')
        details_text = attrs.get('details_text')
        
        print(f"VCodeDetailPane.set_vuln_code: description_text = {description_text}")  # Debug
        print(f"VCodeDetailPane.set_vuln_code: details_text = {details_text}")  # Debug
        
        if vuln_code is None:
            print("VCodeDetailPane.set_vuln_code: Clearing text views")  # Debug
            if description_text:
                description_text.setString_("")
            if details_text:
                details_text.setString_("")
            return
        
        # Debug: Log what we have
        print(f"VCodeDetailPane.set_vuln_code: vuln_code.discussion = {vuln_code.discussion[:50] if vuln_code.discussion else 'None'}...")  # Debug
        print(f"VCodeDetailPane.set_vuln_code: vuln_code.check_text = {vuln_code.check_text[:50] if vuln_code.check_text else 'None'}...")  # Debug
        print(f"VCodeDetailPane.set_vuln_code: vuln_code.fix_text = {vuln_code.fix_text[:50] if vuln_code.fix_text else 'None'}...")  # Debug
        
        # Build description text - use CAT severity format to match official STIGViewer
        cat_severity = Severity.to_cat_format(vuln_code.severity)
        desc_lines = [
            f"STIG: {vuln_code.stig_name}",
            f"Version: {vuln_code.stig_version}",
            f"Release: {vuln_code.stig_release}",
            "",
            f"Vul ID: {vuln_code.v_code}",
            f"Rule ID: {vuln_code.rule_id}",
            f"Severity: {cat_severity}",
            "",
            f"Rule Title:",
            f"{vuln_code.rule_title}",
        ]
        description = "\n".join(desc_lines)
        
        print(f"VCodeDetailPane.set_vuln_code: Setting description text ({len(description)} chars)")  # Debug
        if description_text:
            description_text.setString_(description)
            print("VCodeDetailPane.set_vuln_code: Description text set")  # Debug
        else:
            print("VCodeDetailPane.set_vuln_code: WARNING - No description_text view!")  # Debug
        
        # Build details text without header banner (Discussion, Check Text, Fix Text, References)
        details_lines = [
            "Discussion:",
            "-" * 80,
            vuln_code.discussion or "(No discussion available)",
            "",
            "",
            "Check Text:",
            "-" * 80,
            vuln_code.check_text or "(No check text available)",
            "",
            "",
            "Fix Text:",
            "-" * 80,
            vuln_code.fix_text or "(No fix text available)",
        ]
        references = getattr(vuln_code, 'references', '') or ""
        details_lines.extend([
            "",
            "",
            "References",
            "-" * 80,
            references or "(None)",
        ])
        details = "\n".join(details_lines)
        print(f"VCodeDetailPane.set_vuln_code: discussion={len(vuln_code.discussion or '')} chars, check_text={len(vuln_code.check_text or '')} chars, fix_text={len(vuln_code.fix_text or '')} chars")  # Debug
        
        print(f"VCodeDetailPane.set_vuln_code: Setting details text ({len(details)} chars)")  # Debug
        if details_text:
            details_text.setString_(details)
            print("VCodeDetailPane.set_vuln_code: Details text set")  # Debug
        else:
            print("VCodeDetailPane.set_vuln_code: WARNING - No details_text view!")  # Debug
        
        print("VCodeDetailPane.set_vuln_code: Complete")  # Debug

