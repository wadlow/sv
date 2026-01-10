"""CKL detail pane with four vertically stacked panes."""

from AppKit import (
    NSView, NSRect, NSSplitView, NSScrollView, NSTextView,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
from typing import Optional
import objc

from ..models.vuln_code import VulnCode
from ..models.ckl_file import CklVuln
from .view_helpers import get_view_attrs, get_bounds_size


class CklDetailPane(NSView):
    """Pane showing detailed information about a CKL vulnerability with 4 panes."""
    
    def init(self):
        """Initialize the CKL detail pane."""
        self = NSView.alloc().init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['general_info_text'] = None
        attrs['specific_details_text'] = None
        attrs['finding_details_text'] = None
        attrs['comments_text'] = None
        attrs['current_vuln_code'] = None
        CklDetailPane.createUI(self)
        return self
    
    def createUI(self):
        """Create the UI with four vertically stacked scroll views using NSSplitView."""
        print("CklDetailPane.createUI: Starting...")  # Debug
        bounds = self.bounds()
        width, height = get_bounds_size(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 400, 800
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
            print(f"CklDetailPane.createUI: Set default frame {width}x{height}")  # Debug
        
        print(f"CklDetailPane.createUI: bounds={width}x{height}")  # Debug
        
        # Create vertical split view that fills the entire pane
        split_view = NSSplitView.alloc().initWithFrame_(bounds)
        split_view.setVertical_(False)  # Horizontal divider (stacks vertically)
        split_view.setDividerStyle_(1)  # NSSplitViewDividerStyleThin
        split_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Pane heights: Pane 1 reduced by 30%, remaining space distributed to other panes
        # Pane 1: 17.5% (70% of 25%), Panes 2-4: 27.5% each
        pane1_height = height * 0.175
        pane2_height = height * 0.275
        pane3_height = height * 0.275
        pane4_height = height * 0.275
        
        # Pane 1: General Information (17.5% - reduced by 30%)
        pane1_scroll_frame = NSRect((0, 0), (width, pane1_height))
        pane1_scroll = NSScrollView.alloc().initWithFrame_(pane1_scroll_frame)
        pane1_scroll.setHasVerticalScroller_(True)
        pane1_scroll.setHasHorizontalScroller_(False)
        pane1_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane1_scroll.setBorderType_(1)  # NSBezelBorder
        
        attrs = get_view_attrs(self)
        # Create text view with proper frame initialization
        text_frame = NSRect((0, 0), (width, pane1_height))
        general_info_text = NSTextView.alloc().initWithFrame_(text_frame)
        general_info_text.setEditable_(False)
        general_info_text.setSelectable_(True)
        general_info_text.setRichText_(False)  # Use plain text only
        general_info_text.setImportsGraphics_(False)  # Don't import graphics
        general_info_text.setAllowsUndo_(False)  # Disable undo for read-only
        general_info_text.setFieldEditor_(False)  # Not a field editor
        general_info_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane1_scroll.setDocumentView_(general_info_text)
        attrs['general_info_text'] = general_info_text
        
        # Pane 2: Specific Details (27.5%)
        pane2_scroll_frame = NSRect((0, 0), (width, pane2_height))
        pane2_scroll = NSScrollView.alloc().initWithFrame_(pane2_scroll_frame)
        pane2_scroll.setHasVerticalScroller_(True)
        pane2_scroll.setHasHorizontalScroller_(False)
        pane2_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane2_scroll.setBorderType_(1)  # NSBezelBorder
        
        # Create text view with proper frame initialization
        text_frame = NSRect((0, 0), (width, pane2_height))
        specific_details_text = NSTextView.alloc().initWithFrame_(text_frame)
        specific_details_text.setEditable_(False)
        specific_details_text.setSelectable_(True)
        specific_details_text.setRichText_(False)  # Use plain text only
        specific_details_text.setImportsGraphics_(False)  # Don't import graphics
        specific_details_text.setAllowsUndo_(False)  # Disable undo for read-only
        specific_details_text.setFieldEditor_(False)  # Not a field editor
        specific_details_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane2_scroll.setDocumentView_(specific_details_text)
        attrs['specific_details_text'] = specific_details_text
        
        # Pane 3: Finding Details (27.5%, editable, Courier font)
        pane3_scroll_frame = NSRect((0, 0), (width, pane3_height))
        pane3_scroll = NSScrollView.alloc().initWithFrame_(pane3_scroll_frame)
        pane3_scroll.setHasVerticalScroller_(True)
        pane3_scroll.setHasHorizontalScroller_(False)
        pane3_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane3_scroll.setBorderType_(1)  # NSBezelBorder
        
        # Create text view with proper frame initialization
        text_frame = NSRect((0, 0), (width, pane3_height))
        finding_details_text = NSTextView.alloc().initWithFrame_(text_frame)
        finding_details_text.setEditable_(True)  # Editable for CKL
        finding_details_text.setSelectable_(True)  # Explicitly enable selection
        finding_details_text.setRichText_(False)  # Use plain text only
        finding_details_text.setImportsGraphics_(False)  # Don't import graphics
        finding_details_text.setUsesFontPanel_(False)  # Don't use font panel
        finding_details_text.setFieldEditor_(False)  # Not a field editor
        finding_details_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        # Set Courier font for Finding Details
        from AppKit import NSFont
        courier_font = NSFont.fontWithName_size_("Courier", 12)
        if courier_font:
            finding_details_text.setFont_(courier_font)
        pane3_scroll.setDocumentView_(finding_details_text)
        attrs['finding_details_text'] = finding_details_text
        
        # Pane 4: Comments (27.5%, editable)
        pane4_scroll_frame = NSRect((0, 0), (width, pane4_height))
        pane4_scroll = NSScrollView.alloc().initWithFrame_(pane4_scroll_frame)
        pane4_scroll.setHasVerticalScroller_(True)
        pane4_scroll.setHasHorizontalScroller_(False)
        pane4_scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane4_scroll.setBorderType_(1)  # NSBezelBorder
        
        # Create text view with proper frame initialization
        text_frame = NSRect((0, 0), (width, pane4_height))
        comments_text = NSTextView.alloc().initWithFrame_(text_frame)
        comments_text.setEditable_(True)  # Editable for CKL
        comments_text.setSelectable_(True)  # Explicitly enable selection
        comments_text.setRichText_(False)  # Use plain text only
        comments_text.setImportsGraphics_(False)  # Don't import graphics
        comments_text.setUsesFontPanel_(False)  # Don't use font panel
        comments_text.setFieldEditor_(False)  # Not a field editor
        comments_text.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        pane4_scroll.setDocumentView_(comments_text)
        attrs['comments_text'] = comments_text
        
        # Add scroll views directly to split view
        split_view.addSubview_(pane1_scroll)
        split_view.addSubview_(pane2_scroll)
        split_view.addSubview_(pane3_scroll)
        split_view.addSubview_(pane4_scroll)
        split_view.adjustSubviews()
        
        # Set divider positions
        split_view.setPosition_ofDividerAtIndex_(pane1_height, 0)
        split_view.setPosition_ofDividerAtIndex_(pane1_height + pane2_height, 1)
        split_view.setPosition_ofDividerAtIndex_(pane1_height + pane2_height + pane3_height, 2)
        
        # Add split view to self
        self.addSubview_(split_view)
        attrs['split_view'] = split_view
        
        print(f"CklDetailPane.createUI: Created split view with four scroll views")  # Debug
        print("CklDetailPane.createUI: Complete")  # Debug
    
    @objc.python_method
    def set_vuln_code(self, vuln_code: Optional[VulnCode], finding_details: str = "", comments: str = ""):
        """Set the V-code to display with CKL-specific fields."""
        print(f"CklDetailPane.set_vuln_code: Called with {vuln_code.v_code if vuln_code else 'None'}")  # Debug
        attrs = get_view_attrs(self)
        attrs['current_vuln_code'] = vuln_code
        
        general_info_text = attrs.get('general_info_text')
        specific_details_text = attrs.get('specific_details_text')
        finding_details_text = attrs.get('finding_details_text')
        comments_text = attrs.get('comments_text')
        
        if vuln_code is None:
            print("CklDetailPane.set_vuln_code: Clearing text views")  # Debug
            if general_info_text:
                general_info_text.setString_("")
            if specific_details_text:
                specific_details_text.setString_("")
            if finding_details_text:
                finding_details_text.setString_("")
            if comments_text:
                comments_text.setString_("")
            return
        
        # Build general info text without banner
        general_lines = [
            f"STIG: {vuln_code.stig_name}",
            f"Version: {vuln_code.stig_version}",
            f"Release: {vuln_code.stig_release}",
            "",
            f"V-code: {vuln_code.v_code}",
            f"Rule ID: {vuln_code.rule_id}",
            f"Severity: {vuln_code.severity.upper()}",
            "",
            f"Rule Title:",
            f"{vuln_code.rule_title}",
        ]
        general_info = "\n".join(general_lines)
        
        if general_info_text:
            general_info_text.setString_(general_info)
        
        # Build specific details text without banner
        details_lines = [
            "Discussion:",
            "-" * 80,
            vuln_code.discussion,
            "",
            "",
            "Check Text:",
            "-" * 80,
            vuln_code.check_text,
            "",
            "",
            "Fix Text:",
            "-" * 80,
            vuln_code.fix_text,
        ]
        specific_details = "\n".join(details_lines)
        
        if specific_details_text:
            specific_details_text.setString_(specific_details)
        
        # Set finding details without banner
        if finding_details_text:
            finding_details_text.setString_(finding_details)
        
        # Set comments without banner
        if comments_text:
            comments_text.setString_(comments)
        
        print("CklDetailPane.set_vuln_code: Complete")  # Debug

