"""Main window with tabbed interface."""

from AppKit import (
    NSWindow, NSWindowStyleMask, NSRect, NSView, NSTabView, NSTabViewItem,
    NSApplication, NSBackingStoreBuffered, NSScreen
)
from PyObjCTools import AppHelper

from .explorer_view import ExplorerView


class MainWindow:
    """Main application window with tabbed interface."""
    
    def __init__(self):
        """Initialize the main window."""
        self.window = None
        self.tab_view = None
        self.explorer_tab = None
        self.ckl_tabs = {}  # Map of CKL file paths to tab items
        self.compare_tab = None  # Compare tab item
        self.compare_loaded_tab = None  # Compare Loaded STIGs tab item
        self.detailed_comparison_tabs = {}  # Map tab labels to tab items
        self.new_stig_evaluation_tab = None
        self.check_texts_explorer_tab = None
        self.check_for_stigs_tab = None  # Check for STIGs tab item
        self.createWindow()
    
    def createWindow(self):
        """Create the main window."""
        try:
            # Create window
            screen = NSScreen.mainScreen()
            if screen:
                screen_frame = screen.frame()
            window_frame = NSRect((100, 100), (1200, 800))
            
            # Window style mask constants
            style_mask = (
                1 |  # NSTitledWindowMask
                2 |  # NSClosableWindowMask
                4 |  # NSMiniaturizableWindowMask
                8    # NSResizableWindowMask
            )
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                window_frame,
                style_mask,
                2,  # NSBackingStoreBuffered
                False
            )
            self.window.setTitle_("STIG Viewer")
            self.window.setReleasedWhenClosed_(False)
            
            # Set window delegate to handle close button
            app = NSApplication.sharedApplication()
            app_delegate = app.delegate()
            if app_delegate:
                self.window.setDelegate_(app_delegate)
                print("MainWindow: Set window delegate to AppDelegate")  # Debug
            
            # Create tab view
            content_view = self.window.contentView()
            tab_frame = content_view.bounds()
            self.tab_view = NSTabView.alloc().initWithFrame_(tab_frame)
            self.tab_view.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
            content_view.addSubview_(self.tab_view)
            
            # Create Explorer tab
            self.createExplorerTab()
            
            # Center and show window
            self.window.center()
            self.window.makeKeyAndOrderFront_(None)
            self.window.orderFrontRegardless()
        except Exception as e:
            import traceback
            print(f"Error creating window: {e}")
            traceback.print_exc()
            raise
    
    def createExplorerTab(self):
        """Create the Explorer tab."""
        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_("Explorer")
        
        # Create explorer view
        explorer_view = ExplorerView.alloc().init()
        explorer_view.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
        tab_item.setView_(explorer_view)
        
        self.tab_view.addTabViewItem_(tab_item)
        self.explorer_tab = explorer_view
    
    def add_ckl_tab(self, ckl_file, ckl_view):
        """
        Add a new CKL tab.
        
        Args:
            ckl_file: CklFile object
            ckl_view: CklView object
        """
        # Set main_window reference in ckl_view
        from .view_helpers import get_view_attrs
        attrs = get_view_attrs(ckl_view)
        attrs['main_window'] = self
        
        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_(ckl_file.display_name)
        
        ckl_view.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
        tab_item.setView_(ckl_view)
        
        self.tab_view.addTabViewItem_(tab_item)
        self.ckl_tabs[str(ckl_file.file_path)] = tab_item
        
        # Switch to the new tab
        self.tab_view.selectTabViewItem_(tab_item)
        print(f"MainWindow.add_ckl_tab: Added and selected tab for {ckl_file.display_name}")  # Debug
    
    def add_compare_tab(self, compare_view):
        """
        Add a new Compare tab.
        
        Args:
            compare_view: CompareView object
        """
        print(f"MainWindow.add_compare_tab: Called with {compare_view}")  # Debug
        try:
            # Set main_window reference on compare_view
            from .view_helpers import get_view_attrs
            attrs = get_view_attrs(compare_view)
            attrs['main_window'] = self
            print("MainWindow.add_compare_tab: Set main_window reference")  # Debug
            
            tab_item = NSTabViewItem.alloc().init()
            tab_item.setLabel_("Compare")
            print("MainWindow.add_compare_tab: Created tab item")  # Debug
            
            compare_view.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
            tab_item.setView_(compare_view)
            print("MainWindow.add_compare_tab: Set view")  # Debug
            
            self.tab_view.addTabViewItem_(tab_item)
            print("MainWindow.add_compare_tab: Added tab item")  # Debug
            
            # Store reference to compare tab
            self.compare_tab = tab_item
            
            # Switch to the new tab
            self.tab_view.selectTabViewItem_(tab_item)
            print("MainWindow.add_compare_tab: Selected tab")  # Debug
        except Exception as e:
            import traceback
            print(f"MainWindow.add_compare_tab: ERROR - {e}")  # Debug
            traceback.print_exc()
    
    def remove_ckl_tab(self, ckl_file_path):
        """Remove a CKL tab."""
        if str(ckl_file_path) in self.ckl_tabs:
            tab_item = self.ckl_tabs[str(ckl_file_path)]
            self.tab_view.removeTabViewItem_(tab_item)
            del self.ckl_tabs[str(ckl_file_path)]
    
    def remove_compare_tab(self):
        """Remove the Compare tab."""
        print("MainWindow.remove_compare_tab: Called")  # Debug
        if hasattr(self, 'compare_tab') and self.compare_tab:
            print("MainWindow.remove_compare_tab: Removing tab")  # Debug
            self.tab_view.removeTabViewItem_(self.compare_tab)
            self.compare_tab = None
            # Switch to Explorer tab
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)
        else:
            print("MainWindow.remove_compare_tab: No compare tab to remove")  # Debug
    
    def add_compare_loaded_tab(self, compare_view):
        """
        Add a new Compare Loaded STIGs tab.
        
        Args:
            compare_view: CompareLoadedStigsView object
        """
        from .view_helpers import get_view_attrs
        attrs = get_view_attrs(compare_view)
        attrs['main_window'] = self
        
        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_("Compare Loaded STIGs")
        compare_view.setAutoresizingMask_(0x12)
        tab_item.setView_(compare_view)
        
        self.tab_view.addTabViewItem_(tab_item)
        self.compare_loaded_tab = tab_item
        self.tab_view.selectTabViewItem_(tab_item)
    
    def remove_compare_loaded_tab(self):
        """Remove the Compare Loaded STIGs tab."""
        if hasattr(self, 'compare_loaded_tab') and self.compare_loaded_tab:
            self.tab_view.removeTabViewItem_(self.compare_loaded_tab)
            self.compare_loaded_tab = None
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)
    
    def add_detailed_comparison_tab(self, stig_name, detailed_view):
        """Add or refresh a Detailed Comparison tab for a newer STIG."""
        from .view_helpers import get_view_attrs
        label = f"Detailed Comparison: {stig_name}"
        attrs = get_view_attrs(detailed_view)
        attrs['main_window'] = self
        attrs['tab_label'] = label

        if label in self.detailed_comparison_tabs:
            tab_item = self.detailed_comparison_tabs[label]
            detailed_view.setAutoresizingMask_(0x12)
            tab_item.setView_(detailed_view)
            self.tab_view.selectTabViewItem_(tab_item)
            return

        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_(label)
        detailed_view.setAutoresizingMask_(0x12)
        tab_item.setView_(detailed_view)
        self.tab_view.addTabViewItem_(tab_item)
        self.detailed_comparison_tabs[label] = tab_item
        self.tab_view.selectTabViewItem_(tab_item)

    def remove_detailed_comparison_tab(self, tab_label):
        """Remove a Detailed Comparison tab."""
        if tab_label in self.detailed_comparison_tabs:
            tab_item = self.detailed_comparison_tabs[tab_label]
            self.tab_view.removeTabViewItem_(tab_item)
            del self.detailed_comparison_tabs[tab_label]
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)

    def add_new_stig_evaluation_tab(self, evaluation_view):
        """Add or refresh the New STIG Evaluation tab."""
        from .new_stig_evaluation_view import TAB_LABEL
        from .view_helpers import get_view_attrs

        attrs = get_view_attrs(evaluation_view)
        attrs['main_window'] = self

        if self.new_stig_evaluation_tab:
            tab_item = self.new_stig_evaluation_tab
            evaluation_view.setAutoresizingMask_(0x12)
            tab_item.setView_(evaluation_view)
            self.tab_view.selectTabViewItem_(tab_item)
            return

        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_(TAB_LABEL)
        evaluation_view.setAutoresizingMask_(0x12)
        tab_item.setView_(evaluation_view)
        self.tab_view.addTabViewItem_(tab_item)
        self.new_stig_evaluation_tab = tab_item
        self.tab_view.selectTabViewItem_(tab_item)

    def remove_new_stig_evaluation_tab(self):
        """Remove the New STIG Evaluation tab."""
        if self.new_stig_evaluation_tab:
            self.tab_view.removeTabViewItem_(self.new_stig_evaluation_tab)
            self.new_stig_evaluation_tab = None
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)

    def add_check_texts_explorer_tab(self, explorer_view):
        """Add or refresh the Check Texts Explorer tab."""
        from .check_texts_explorer_view import TAB_LABEL
        from .view_helpers import get_view_attrs

        attrs = get_view_attrs(explorer_view)
        attrs['main_window'] = self

        if self.check_texts_explorer_tab:
            tab_item = self.check_texts_explorer_tab
            explorer_view.setAutoresizingMask_(0x12)
            tab_item.setView_(explorer_view)
            self.tab_view.selectTabViewItem_(tab_item)
            return

        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_(TAB_LABEL)
        explorer_view.setAutoresizingMask_(0x12)
        tab_item.setView_(explorer_view)
        self.tab_view.addTabViewItem_(tab_item)
        self.check_texts_explorer_tab = tab_item
        self.tab_view.selectTabViewItem_(tab_item)

    def remove_check_texts_explorer_tab(self):
        """Remove the Check Texts Explorer tab."""
        if self.check_texts_explorer_tab:
            self.tab_view.removeTabViewItem_(self.check_texts_explorer_tab)
            self.check_texts_explorer_tab = None
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)
    
    def add_compare_ckl_tab(self, compare_ckl_view):
        """
        Add a new Compare CKLs tab.
        
        Args:
            compare_ckl_view: CompareCklView object
        """
        print(f"MainWindow.add_compare_ckl_tab: Called with {compare_ckl_view}")  # Debug
        try:
            # Set main_window reference on compare_ckl_view
            from .view_helpers import get_view_attrs
            attrs = get_view_attrs(compare_ckl_view)
            attrs['main_window'] = self
            print("MainWindow.add_compare_ckl_tab: Set main_window reference")  # Debug
            
            tab_item = NSTabViewItem.alloc().init()
            tab_item.setLabel_("Compare CKLs")
            print("MainWindow.add_compare_ckl_tab: Created tab item")  # Debug
            
            compare_ckl_view.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
            tab_item.setView_(compare_ckl_view)
            print("MainWindow.add_compare_ckl_tab: Set view")  # Debug
            
            self.tab_view.addTabViewItem_(tab_item)
            print("MainWindow.add_compare_ckl_tab: Added tab item")  # Debug
            
            # Store reference to compare CKL tab
            self.compare_ckl_tab = tab_item
            
            # Switch to the new tab
            self.tab_view.selectTabViewItem_(tab_item)
            print("MainWindow.add_compare_ckl_tab: Selected tab")  # Debug
        except Exception as e:
            import traceback
            print(f"MainWindow.add_compare_ckl_tab: ERROR - {e}")  # Debug
            traceback.print_exc()
    
    def add_check_for_stigs_tab(self, check_view):
        """Add the Check for STIGs tab."""
        from .view_helpers import get_view_attrs
        attrs = get_view_attrs(check_view)
        attrs['main_window'] = self
        tab_item = NSTabViewItem.alloc().init()
        tab_item.setLabel_("Check for STIGs")
        check_view.setAutoresizingMask_(0x12)
        tab_item.setView_(check_view)
        self.tab_view.addTabViewItem_(tab_item)
        self.check_for_stigs_tab = tab_item
        self.tab_view.selectTabViewItem_(tab_item)
    
    def remove_check_for_stigs_tab(self):
        """Remove the Check for STIGs tab."""
        if hasattr(self, 'check_for_stigs_tab') and self.check_for_stigs_tab:
            self.tab_view.removeTabViewItem_(self.check_for_stigs_tab)
            self.check_for_stigs_tab = None
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)
    
    def remove_compare_ckl_tab(self):
        """Remove the Compare CKLs tab."""
        print("MainWindow.remove_compare_ckl_tab: Called")  # Debug
        if hasattr(self, 'compare_ckl_tab') and self.compare_ckl_tab:
            print("MainWindow.remove_compare_ckl_tab: Removing tab")  # Debug
            self.tab_view.removeTabViewItem_(self.compare_ckl_tab)
            self.compare_ckl_tab = None
            # Switch to Explorer tab
            if self.tab_view.numberOfTabViewItems() > 0:
                self.tab_view.selectTabViewItemAtIndex_(0)
        else:
            print("MainWindow.remove_compare_ckl_tab: No compare_ckl_tab to remove")  # Debug
    
    def get_explorer_view(self):
        """Get the Explorer view."""
        return self.explorer_tab
    
    def is_explorer_tab_active(self):
        """Check if the Explorer tab is currently active."""
        if not self.tab_view:
            return False
        selected_item = self.tab_view.selectedTabViewItem()
        if not selected_item:
            return False
        # The Explorer tab is the first tab (index 0)
        return self.tab_view.indexOfTabViewItem_(selected_item) == 0
    
    def show(self):
        """Show the window and bring it to the front."""
        if self.window:
            app = NSApplication.sharedApplication()
            app.activateIgnoringOtherApps_(True)
            self.window.makeKeyAndOrderFront_(None)
            # Defer a second activation pass so the window reliably comes to front when launched from terminal
            def bring_to_front():
                app.activateIgnoringOtherApps_(True)
                self.window.orderFrontRegardless()
            AppHelper.callLater(0.1, bring_to_front)
    
    def close(self):
        """Close the window."""
        if self.window:
            self.window.close()

