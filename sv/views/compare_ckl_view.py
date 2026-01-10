"""Compare CKL view with three-column layout for comparing two CKL files."""

from AppKit import (
    NSView, NSRect, NSSplitView, NSScrollView, NSTextView, NSTextField, NSButton,
    NSBox, NSOpenPanel, NSColor, NSFont,
    NSViewWidthSizable, NSViewHeightSizable, NSViewMinYMargin
)
from Foundation import NSObject
import objc
from pathlib import Path

from ..parsers.ckl_parser import CklParser
from .view_helpers import get_view_attrs, get_bounds_size


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
        
        # Top: Loader pane (70% of height)
        loader_pane = CompareCklView._create_loader_pane(self, NSRect((0, 0), (width, height * 0.7)))
        
        # Bottom: Filter/search pane (30% of height)
        filter_pane = CompareCklView._create_filter_pane(self, NSRect((0, 0), (width, height * 0.3)))
        
        col1_split.addSubview_(loader_pane)
        col1_split.addSubview_(filter_pane)
        col1_split.adjustSubviews()
        col1_split.setPosition_ofDividerAtIndex_(height * 0.7, 0)
        
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
        """Create the filter pane."""
        width, height = get_bounds_size(frame)
        
        pane = NSBox.alloc().initWithFrame_(frame)
        pane.setTitlePosition_(2)  # NSAtTop
        pane.setTitle_("Filter Pane")
        pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        content = pane.contentView()
        content_frame = content.frame()
        content_width, content_height = get_bounds_size(content_frame)
        
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
        
        print(f"DEBUG: Filter pane - Button created at y=10, width={content_width - 20}")  # Debug
        
        return pane
    
    def _create_column2(self, frame):
        """Create Column 2: Comparison results placeholder."""
        width, height = get_bounds_size(frame)
        
        scroll_view = NSScrollView.alloc().initWithFrame_(frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)
        
        text_frame = NSRect((0, 0), (width, height))
        text_view = NSTextView.alloc().initWithFrame_(text_frame)
        text_view.setEditable_(False)
        text_view.setSelectable_(True)
        text_view.setRichText_(False)
        text_view.setImportsGraphics_(False)
        text_view.setAllowsUndo_(False)
        text_view.setFieldEditor_(False)
        text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_view.setString_("Comparison Results\n\n(Select CKL A and CKL B, then click Compare)")
        text_view.setTextColor_(NSColor.whiteColor())
        text_view.setBackgroundColor_(NSColor.blackColor())
        text_view.setFont_(NSFont.systemFontOfSize_(12))
        scroll_view.setDocumentView_(text_view)
        
        attrs = get_view_attrs(self)
        attrs['results_text_view'] = text_view
        
        return scroll_view
    
    def _create_column3(self, frame):
        """Create Column 3: Detail panes placeholder."""
        width, height = get_bounds_size(frame)
        
        scroll_view = NSScrollView.alloc().initWithFrame_(frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)
        
        text_frame = NSRect((0, 0), (width, height))
        text_view = NSTextView.alloc().initWithFrame_(text_frame)
        text_view.setEditable_(False)
        text_view.setSelectable_(True)
        text_view.setRichText_(False)
        text_view.setImportsGraphics_(False)
        text_view.setAllowsUndo_(False)
        text_view.setFieldEditor_(False)
        text_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        text_view.setString_("Detail Pane\n\n(Details will appear here)")
        text_view.setTextColor_(NSColor.whiteColor())
        text_view.setBackgroundColor_(NSColor.blackColor())
        text_view.setFont_(NSFont.systemFontOfSize_(12))
        scroll_view.setDocumentView_(text_view)
        
        attrs = get_view_attrs(self)
        attrs['detail_text_view'] = text_view
        
        return scroll_view
    
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
            
            # Display results
            print("CompareCklView.compareCkls_: Displaying results...")  # Debug
            CompareCklView._display_results(self, results)
            
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
        for vcode in in_both:
            vuln_a = next(v for v in ckl_a.vulns if v.v_code == vcode)
            vuln_b = next(v for v in ckl_b.vulns if v.v_code == vcode)
            
            if vuln_a.status != vuln_b.status:
                different.append((vcode, vuln_a.status, vuln_b.status))
        
        return {
            'in_b_not_a': sorted(in_b_not_a),
            'in_a_not_b': sorted(in_a_not_b),
            'different': sorted(different, key=lambda x: x[0])
        }
    
    @objc.python_method
    def _display_results(self, results):
        """Display comparison results in Column 2."""
        attrs = get_view_attrs(self)
        results_text_view = attrs.get('results_text_view')
        
        if not results_text_view:
            print("CompareCklView._display_results: No results text view!")  # Debug
            return
        
        # Build results text
        lines = ["CKL Comparison Results", "=" * 80, ""]
        
        lines.append(f"In CKL B but not in CKL A ({len(results['in_b_not_a'])} V-codes):")
        lines.append("-" * 80)
        for vcode in results['in_b_not_a']:
            lines.append(f"  {vcode}")
        lines.append("")
        
        lines.append(f"In CKL A but not in CKL B ({len(results['in_a_not_b'])} V-codes):")
        lines.append("-" * 80)
        for vcode in results['in_a_not_b']:
            lines.append(f"  {vcode}")
        lines.append("")
        
        lines.append(f"In both but with different status ({len(results['different'])} V-codes):")
        lines.append("-" * 80)
        for vcode, status_a, status_b in results['different']:
            lines.append(f"  {vcode}: A={status_a.name}, B={status_b.name}")
        
        results_text = "\n".join(lines)
        results_text_view.setString_(results_text)
        print(f"CompareCklView._display_results: Displayed {len(lines)} lines")  # Debug
    
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
