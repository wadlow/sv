"""Explorer view with three-column layout."""

from AppKit import NSView, NSRect, NSSplitView, NSViewWidthSizable, NSViewHeightSizable
from Foundation import NSObject
import objc

from .stigs_pane import StigsPane
from .search_pane import SearchPane
from .vcode_list_pane import VCodeListPane
from .vcode_detail_pane import VCodeDetailPane

from .view_helpers import get_view_attrs


class ExplorerView(NSView):
    """Explorer tab view with three columns."""
    
    def init(self):
        """Initialize the explorer view."""
        self = NSView.alloc().init()
        if self is None:
            return None
        
        attrs = get_view_attrs(self)
        attrs['stigs_pane'] = None
        attrs['search_pane'] = None
        attrs['vcode_list_pane'] = None
        attrs['vcode_detail_pane'] = None
        # Call createLayout as class method, passing self
        ExplorerView.createLayout(self)
        return self
    
    def createLayout(self):
        """Create the three-column layout."""
        bounds = self.bounds()
        
        # Access NSRect size - bounds is an NSRect struct
        # In PyObjC, NSRect has origin and size attributes
        try:
            width = bounds.size.width
            height = bounds.size.height
        except (AttributeError, TypeError):
            # If bounds is a tuple or different format, use default
            width, height = 800, 600
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
        
        # If bounds are zero, use default size
        if width == 0 or height == 0:
            width, height = 800, 600
            bounds = NSRect((0, 0), (width, height))
            self.setFrame_(bounds)
        
        # Get width and height from bounds
        try:
            width = bounds.size.width
            height = bounds.size.height
        except (AttributeError, TypeError):
            width, height = 800, 600
        
        # Main horizontal split view (three columns)
        main_split = NSSplitView.alloc().initWithFrame_(bounds)
        main_split.setVertical_(True)
        main_split.setDividerStyle_(1)  # NSSplitViewDividerStyleThin
        main_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # Column 1: STIGS + SEARCH (40% width)
        col1_frame = NSRect((0, 0), (width * 0.4, height))
        col1_split = NSSplitView.alloc().initWithFrame_(col1_frame)
        col1_split.setVertical_(False)
        col1_split.setDividerStyle_(1)
        col1_split.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        
        # STIGS pane (top 50%)
        attrs = get_view_attrs(self)
        stigs_pane = StigsPane.alloc().init()
        stigs_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['stigs_pane'] = stigs_pane
        
        # SEARCH pane (bottom 50%)
        search_pane = SearchPane.alloc().init()
        search_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['search_pane'] = search_pane
        
        col1_split.addSubview_(stigs_pane)
        col1_split.addSubview_(search_pane)
        col1_split.adjustSubviews()
        
        # Column 2: V-code list (20% width)
        col2_frame = NSRect((0, 0), (width * 0.2, height))
        vcode_list_pane = VCodeListPane.alloc().init()
        vcode_list_pane.setFrame_(col2_frame)
        vcode_list_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['vcode_list_pane'] = vcode_list_pane
        
        # Column 3: V-code detail (40% width)
        col3_frame = NSRect((0, 0), (width * 0.4, height))
        vcode_detail_pane = VCodeDetailPane.alloc().init()
        vcode_detail_pane.setFrame_(col3_frame)
        vcode_detail_pane.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        attrs['vcode_detail_pane'] = vcode_detail_pane
        
        # Add columns to main split view
        main_split.addSubview_(col1_split)
        main_split.addSubview_(vcode_list_pane)
        main_split.addSubview_(vcode_detail_pane)
        main_split.adjustSubviews()
        
        # Set initial divider positions (40%, 20%, 40%)
        main_split.setPosition_ofDividerAtIndex_(width * 0.4, 0)
        main_split.setPosition_ofDividerAtIndex_(width * 0.6, 1)
        
        self.addSubview_(main_split)
        
        # Wire up search change callback and delete STIG callback
        attrs = get_view_attrs(self)
        search_pane = attrs.get('search_pane')
        if search_pane:
            search_pane_attrs = get_view_attrs(search_pane)
            # Store method reference in attributes - use class method pattern
            search_pane_attrs['on_search_changed'] = lambda: ExplorerView.onSearchChanged(self)
            search_pane_attrs['on_delete_stig'] = lambda: ExplorerView.onDeleteStig(self)
    
    def set_stig_files(self, stig_files):
        """Set the STIG files to display."""
        print(f"ExplorerView.set_stig_files: Called with {len(stig_files)} files")  # Debug
        attrs = get_view_attrs(self)
        stigs_pane = attrs.get('stigs_pane')
        print(f"ExplorerView.set_stig_files: stigs_pane = {stigs_pane}")  # Debug
        if stigs_pane:
            # Wire up callbacks FIRST (before calling set_stig_files)
            stigs_attrs = get_view_attrs(stigs_pane)
            # Checkbox callback - triggers V-code list update
            stigs_attrs['on_selection_changed'] = lambda: ExplorerView.onStigSelectionChanged(self)
            print(f"ExplorerView.set_stig_files: Set checkbox callback on stigs_pane: {stigs_attrs['on_selection_changed']}")  # Debug
            # Row selection callback - triggers delete button state update
            stigs_attrs['on_row_selection_changed'] = lambda: ExplorerView._update_delete_button_state(self)
            print(f"ExplorerView.set_stig_files: Set row selection callback on stigs_pane: {stigs_attrs['on_row_selection_changed']}")  # Debug
            
            # Now call set_stig_files, which will read the callbacks from attrs
            from .stigs_pane import StigsPane
            print("ExplorerView.set_stig_files: Calling StigsPane.set_stig_files...")  # Debug
            StigsPane.set_stig_files(stigs_pane, stig_files)
            print("ExplorerView.set_stig_files: StigsPane.set_stig_files complete")  # Debug
            print("ExplorerView.set_stig_files: Complete")  # Debug
            
            # Update delete button state initially
            ExplorerView._update_delete_button_state(self)
    
    def set_vcode_list(self, vuln_codes):
        """Set the V-code list to display."""
        print(f"ExplorerView.set_vcode_list: Called with {len(vuln_codes)} codes")  # Debug
        attrs = get_view_attrs(self)
        vcode_list_pane = attrs.get('vcode_list_pane')
        print(f"ExplorerView.set_vcode_list: vcode_list_pane = {vcode_list_pane}")  # Debug
        if vcode_list_pane:
            # Call method on VCodeListPane class, passing instance
            from .vcode_list_pane import VCodeListPane
            print("ExplorerView.set_vcode_list: Calling VCodeListPane.set_vuln_codes...")  # Debug
            VCodeListPane.set_vuln_codes(vcode_list_pane, vuln_codes)
            print("ExplorerView.set_vcode_list: Complete")  # Debug
    
    def set_selected_vcode(self, vuln_code):
        """Set the selected V-code for detail display."""
        print(f"ExplorerView.set_selected_vcode: Called with {vuln_code.v_code if vuln_code else 'None'}")  # Debug
        attrs = get_view_attrs(self)
        vcode_detail_pane = attrs.get('vcode_detail_pane')
        print(f"ExplorerView.set_selected_vcode: vcode_detail_pane = {vcode_detail_pane}")  # Debug
        if vcode_detail_pane:
            # Call method on VCodeDetailPane class, passing instance
            from .vcode_detail_pane import VCodeDetailPane
            print(f"ExplorerView.set_selected_vcode: Setting vuln_code in detail pane")  # Debug
            VCodeDetailPane.set_vuln_code(vcode_detail_pane, vuln_code)
            print(f"ExplorerView.set_selected_vcode: Complete")  # Debug
        else:
            print("ExplorerView.set_selected_vcode: WARNING - No detail pane!")  # Debug
    
    def get_search_pane(self):
        """Get the search pane."""
        attrs = get_view_attrs(self)
        return attrs.get('search_pane')
    
    def get_search_text(self):
        """Get the current search text."""
        attrs = get_view_attrs(self)
        search_pane = attrs.get('search_pane')
        if search_pane:
            # Call method on SearchPane class, passing instance
            from .search_pane import SearchPane
            return SearchPane.get_search_text(search_pane)
        return ""
    
    def get_checked_stigs(self):
        """Get the list of checked STIG files (for V-code display)."""
        attrs = get_view_attrs(self)
        stigs_pane = attrs.get('stigs_pane')
        if stigs_pane:
            # Call method on StigsPane class, passing instance
            from .stigs_pane import StigsPane
            return StigsPane.get_checked_stigs(stigs_pane)
        return []
    
    def get_selected_stigs(self):
        """Get the list of selected (highlighted) STIG files (for deletion)."""
        attrs = get_view_attrs(self)
        stigs_pane = attrs.get('stigs_pane')
        if stigs_pane:
            from .stigs_pane import StigsPane
            return StigsPane.get_selected_stigs(stigs_pane)
        return []
    
    @objc.python_method
    def onStigSelectionChanged(self):
        """Handle STIG checkbox change."""
        print("ExplorerView.onStigSelectionChanged: Called (checkbox changed)")  # Debug
        
        # Trigger update of V-code list based on checked STIGs
        attrs = get_view_attrs(self)
        on_stig_selection_changed = attrs.get('on_stig_selection_changed')
        print(f"ExplorerView.onStigSelectionChanged: Callback = {on_stig_selection_changed}")  # Debug
        if on_stig_selection_changed:
            print("ExplorerView.onStigSelectionChanged: Calling callback...")  # Debug
            on_stig_selection_changed()
            print("ExplorerView.onStigSelectionChanged: Callback complete")  # Debug
        else:
            print("ExplorerView.onStigSelectionChanged: WARNING - No callback set!")  # Debug
    
    @objc.python_method
    def onSearchChanged(self):
        """Handle search text change."""
        # Trigger update of V-code list
        attrs = get_view_attrs(self)
        on_stig_selection_changed = attrs.get('on_stig_selection_changed')
        if on_stig_selection_changed:
            on_stig_selection_changed()
    
    @objc.python_method
    def onDeleteStig(self):
        """Handle delete STIG button click."""
        print("ExplorerView.onDeleteStig: Called")  # Debug
        attrs = get_view_attrs(self)
        on_delete_stig = attrs.get('on_delete_stig')
        if on_delete_stig:
            print("ExplorerView: Calling delete STIG callback")  # Debug
            on_delete_stig()
        else:
            print("ExplorerView: WARNING - No delete STIG callback set!")  # Debug
    
    def _update_delete_button_state(self):
        """Update the delete button enabled state based on row selection."""
        print("ExplorerView._update_delete_button_state: Called (row selection changed)")  # Debug
        attrs = get_view_attrs(self)
        stigs_pane = attrs.get('stigs_pane')
        
        # Check if any row is selected (highlighted), not if it's checked
        has_selection = False
        if stigs_pane:
            from .stigs_pane import StigsPane
            has_selection = StigsPane.has_selected_row(stigs_pane)
        print(f"ExplorerView._update_delete_button_state: has_row_selection={has_selection}")  # Debug
        
        # Update button state in search pane
        search_pane = attrs.get('search_pane')
        if search_pane:
            from .search_pane import SearchPane
            print(f"ExplorerView._update_delete_button_state: Updating button state to {has_selection}")  # Debug
            SearchPane.update_delete_button_state(search_pane, has_selection)
        else:
            print("ExplorerView._update_delete_button_state: WARNING - No search pane!")  # Debug

