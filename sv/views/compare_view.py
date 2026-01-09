"""Compare view for comparing two STIG files."""

from AppKit import (
    NSView, NSRect, NSSplitView, NSTextField, NSButton, NSScrollView, NSTextView,
    NSViewWidthSizable, NSViewHeightSizable
)
from Foundation import NSObject
import objc

from .view_helpers import get_view_attrs, get_bounds_size


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
    
    def loadStigA_(self, sender):
        """Load STIG A file."""
        print("CompareView.loadStigA_: Called")  # Debug
        from AppKit import NSOpenPanel, NSFileHandlingPanelOKButton
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
                # TODO: Load and parse STIG A
                attrs = get_view_attrs(self)
                attrs['stig_a_path'] = file_path
                # Update the text field to show filename
                # Need to find the field...
                print(f"CompareView.loadStigA_: TODO - Update field with filename")  # Debug
        else:
            print("CompareView.loadStigA_: User cancelled")  # Debug
    
    def loadStigB_(self, sender):
        """Load STIG B file."""
        print("CompareView.loadStigB_: Called")  # Debug
        from AppKit import NSOpenPanel, NSFileHandlingPanelOKButton
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
                # TODO: Load and parse STIG B
                attrs = get_view_attrs(self)
                attrs['stig_b_path'] = file_path
                # Update the text field to show filename
                print(f"CompareView.loadStigB_: TODO - Update field with filename")  # Debug
        else:
            print("CompareView.loadStigB_: User cancelled")  # Debug
    
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
        content.addSubview_(compare_btn)
        print(f"CompareView._create_loader_pane: Added Compare button at y={y_pos}")  # Debug
        
        # Store references
        attrs = get_view_attrs(pane)
        attrs['load_a_btn'] = load_a_btn
        attrs['load_b_btn'] = load_b_btn
        attrs['stig_a_field'] = stig_a_field
        attrs['stig_b_field'] = stig_b_field
        attrs['compare_btn'] = compare_btn
        
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
        
        # Placeholder label at top
        label = NSTextField.alloc().initWithFrame_(NSRect((10, content_height - 35), (content_width - 20, 24)))
        label.setStringValue_("Search/Filter Pane")
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(NSColor.whiteColor())
        label.setAutoresizingMask_(0x08 | 0x02)  # NSViewMinYMargin | NSViewWidthSizable - pin to top
        content.addSubview_(label)
        print(f"CompareView._create_search_pane: Added label at y={content_height - 35}")  # Debug
        
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
        col2_split.setDividerStyle_(2)  # NSSplitViewDividerStylePaneSplitter (no visible divider)
        col2_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        third_height = height / 3
        
        # Top: V-codes in B but not in A
        list1_frame = NSRect((0, 0), (width, third_height))
        list1 = self._create_list_pane(list1_frame, "In B, Not in A")
        col2_split.addSubview_(list1)
        
        # Middle: V-codes in A but not in B
        list2_frame = NSRect((0, 0), (width, third_height))
        list2 = self._create_list_pane(list2_frame, "In A, Not in B")
        col2_split.addSubview_(list2)
        
        # Bottom: V-codes in both but different
        list3_frame = NSRect((0, 0), (width, third_height))
        list3 = self._create_list_pane(list3_frame, "In Both (Different)")
        col2_split.addSubview_(list3)
        
        col2_split.adjustSubviews()
        
        return col2_split
    
    def _create_list_pane(self, frame, title):
        """Create a list pane with a title."""
        from AppKit import NSColor
        width, height = get_bounds_size(frame)
        
        print(f"CompareView._create_list_pane: '{title}' frame size = {width}x{height}")  # Debug
        
        pane = NSView.alloc().initWithFrame_(frame)
        pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Scroll view fills entire pane
        scroll_frame = NSRect((0, 0), (width, height))
        scroll_width, scroll_height = get_bounds_size(scroll_frame)
        print(f"CompareView._create_list_pane: scroll_frame = ({scroll_width}x{scroll_height})")  # Debug
        scroll_view = NSScrollView.alloc().initWithFrame_(scroll_frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)  # NSBezelBorder
        
        # Generate test data based on title
        test_data = []
        if "In B, Not in A" in title:
            test_data = [
                "V-230221 - New check in STIG B",
                "V-230222 - Additional requirement",
                "V-230223 - Security enhancement"
            ]
        elif "In A, Not in B" in title:
            test_data = [
                "V-220001 - Deprecated check",
                "V-220002 - Removed requirement",
                "V-220003 - Obsolete control"
            ]
        elif "In Both (Different)" in title:
            test_data = [
                "V-215000 - Rule title changed",
                "V-215001 - Severity increased to High",
                "V-215002 - Check text modified",
                "V-215003 - Fix text updated"
            ]
        
        # Build content string
        content_lines = [f"{title}\n"]
        if test_data:
            content_lines.append("")
            for item in test_data:
                content_lines.append(item)
        else:
            content_lines.append("\n(List will appear here)")
        
        text_content = "\n".join(content_lines)
        
        print(f"CompareView._create_list_pane: Title='{title}', test_data count={len(test_data)}")  # Debug
        print(f"CompareView._create_list_pane: Content length={len(text_content)} chars")  # Debug
        print(f"CompareView._create_list_pane: First 100 chars: {text_content[:100]}")  # Debug
        
        # Text view for content - simpler approach
        from AppKit import NSColor, NSFont
        
        # Create text view with proper frame
        text_frame = NSRect((0, 0), (scroll_width, scroll_height))
        text_view = NSTextView.alloc().initWithFrame_(text_frame)
        text_view.setEditable_(False)
        text_view.setRichText_(False)
        text_view.setString_(text_content)
        text_view.setTextColor_(NSColor.whiteColor())
        text_view.setDrawsBackground_(True)
        text_view.setBackgroundColor_(NSColor.blackColor())  # Black background for better contrast
        text_view.setFont_(NSFont.systemFontOfSize_(14))
        text_view.setSelectable_(True)  # Make it selectable so we can verify it's there
        
        # Make sure text container is sized properly
        text_view.setMinSize_((scroll_width, 0))
        text_view.setMaxSize_((scroll_width, 1.0e7))
        text_view.setVerticallyResizable_(True)
        text_view.setHorizontallyResizable_(False)
        if text_view.textContainer():
            text_view.textContainer().setContainerSize_((scroll_width, 1.0e7))
            text_view.textContainer().setWidthTracksTextView_(True)
        
        # Set as document view
        scroll_view.setDocumentView_(text_view)
        
        print(f"CompareView._create_list_pane: Text view frame set to {scroll_width}x{scroll_height}")  # Debug
        print(f"CompareView._create_list_pane: Text view string length: {len(text_view.string())}")  # Debug
        print(f"CompareView._create_list_pane: Text view configured and added to scroll view")  # Debug
        
        pane.addSubview_(scroll_view)
        
        print(f"CompareView._create_list_pane: Created scroll view for '{title}' with {len(test_data)} test items")  # Debug
        
        return pane
    
    def _create_column3(self, frame):
        """Create Column 3: Four detail panes."""
        width, height = get_bounds_size(frame)
        
        col3_split = NSSplitView.alloc().initWithFrame_(frame)
        col3_split.setVertical_(False)  # Horizontal divider (stacks vertically)
        col3_split.setDividerStyle_(1)
        col3_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        quarter_height = height / 4
        
        # Pane 1: STIG A General Info
        pane1_frame = NSRect((0, 0), (width, quarter_height))
        pane1 = self._create_detail_pane(pane1_frame, "STIG A - General")
        col3_split.addSubview_(pane1)
        
        # Pane 2: STIG A Details
        pane2_frame = NSRect((0, 0), (width, quarter_height))
        pane2 = self._create_detail_pane(pane2_frame, "STIG A - Details")
        col3_split.addSubview_(pane2)
        
        # Pane 3: STIG B General Info
        pane3_frame = NSRect((0, 0), (width, quarter_height))
        pane3 = self._create_detail_pane(pane3_frame, "STIG B - General")
        col3_split.addSubview_(pane3)
        
        # Pane 4: STIG B Details
        pane4_frame = NSRect((0, 0), (width, quarter_height))
        pane4 = self._create_detail_pane(pane4_frame, "STIG B - Details")
        col3_split.addSubview_(pane4)
        
        col3_split.adjustSubviews()
        
        return col3_split
    
    def _create_detail_pane(self, frame, title):
        """Create a detail pane with a title."""
        scroll_view = NSScrollView.alloc().initWithFrame_(frame)
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setHasHorizontalScroller_(False)
        scroll_view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        scroll_view.setBorderType_(1)
        
        text_view = NSTextView.alloc().initWithFrame_(frame)
        text_view.setEditable_(False)
        text_view.setString_(f"{title}\n\n(Details will appear here)")
        scroll_view.setDocumentView_(text_view)
        
        return scroll_view

