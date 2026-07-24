"""Menu bar controller."""

from AppKit import (
    NSMenu, NSMenuItem, NSApplication, NSObject
)
from Foundation import NSObject
from objc import selector

# Module-level storage for app controller
_app_controller_ref = None


def _import_stig_handler(self, sender):
    """Handle Import STIG menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.import_stig_files()


def _compare_stigs_handler(self, sender):
    """Handle Compare STIGs menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.compare_stigs()


def _compare_loaded_stigs_handler(self, sender):
    """Handle Compare Loaded STIGs menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.compare_loaded_stigs()


def _open_checklist_handler(self, sender):
    """Handle Open Checklist menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.open_checklist_files()


def _create_ckl_file_handler(self, sender):
    """Handle Create CKL file menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.create_ckl_file()


def _show_preferences_handler(self, sender):
    """Handle Preferences menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.show_preferences()


def _compare_ckls_handler(self, sender):
    """Handle Compare CKLs menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.compare_ckls()


def _check_for_stigs_handler(self, sender):
    """Handle Check for STIGs menu action."""
    global _app_controller_ref
    if _app_controller_ref:
        _app_controller_ref.check_for_stigs()


class MenuController(NSObject):
    """Controller for menu bar actions."""
    
    # Register methods as Objective-C selectors
    importStig_ = selector(_import_stig_handler, signature=b'v@:@')
    compareStigs_ = selector(_compare_stigs_handler, signature=b'v@:@')
    compareLoadedStigs_ = selector(_compare_loaded_stigs_handler, signature=b'v@:@')
    openChecklist_ = selector(_open_checklist_handler, signature=b'v@:@')
    createCklFile_ = selector(_create_ckl_file_handler, signature=b'v@:@')
    compareCkls_ = selector(_compare_ckls_handler, signature=b'v@:@')
    checkForStigs_ = selector(_check_for_stigs_handler, signature=b'v@:@')
    showPreferences_ = selector(_show_preferences_handler, signature=b'v@:@')
    
    def init(self):
        """Initialize the menu controller."""
        self = NSObject.alloc().init()
        if self is None:
            return None
        return self
    
    def set_app_controller(self, app_controller):
        """Set the app controller for callbacks."""
        global _app_controller_ref
        _app_controller_ref = app_controller
        # Create menu bar after controller is set
        _create_menu_bar(self)
    
def _create_menu_bar(menu_controller):
    """Create the menu bar."""
    app = NSApplication.sharedApplication()
    app_delegate = app.delegate()
    main_menu = NSMenu.alloc().init()
    
    # App menu (required for macOS)
    app_menu_item = NSMenuItem.alloc().init()
    app_menu = NSMenu.alloc().init()
    
    # About
    about_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "About STIG Viewer", "orderFrontStandardAboutPanel:", ""
    )
    app_menu.addItem_(about_item)
    
    app_menu.addItem_(NSMenuItem.separatorItem())
    
    # Quit
    quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Quit STIG Viewer", "terminate:", "q"
    )
    app_menu.addItem_(quit_item)
    
    app_menu_item.setSubmenu_(app_menu)
    main_menu.addItem_(app_menu_item)
    
    # File menu
    file_menu_item = NSMenuItem.alloc().init()
    file_menu = NSMenu.alloc().init()
    
    import_stig_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Import STIG", "importStig:", ""
    )
    file_menu.addItem_(import_stig_item)
    
    compare_stigs_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Compare STIGs", "compareStigs:", ""
    )
    file_menu.addItem_(compare_stigs_item)
    
    compare_loaded_stigs_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Compare Loaded STIGs", "compareLoadedStigs:", ""
    )
    file_menu.addItem_(compare_loaded_stigs_item)
    
    check_for_stigs_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Check for STIGs", "checkForStigs:", ""
    )
    file_menu.addItem_(check_for_stigs_item)
    
    file_menu.addItem_(NSMenuItem.separatorItem())
    
    create_ckl_file_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Create CKL file", "createCklFile:", ""
    )
    file_menu.addItem_(create_ckl_file_item)
    
    file_menu_item.setSubmenu_(file_menu)
    file_menu_item.setTitle_("File")
    main_menu.addItem_(file_menu_item)
    
    # Edit menu (required for Copy, Paste, etc.)
    edit_menu_item = NSMenuItem.alloc().init()
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    
    # Cut
    cut_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Cut", "cut:", "x"
    )
    edit_menu.addItem_(cut_item)
    
    # Copy
    copy_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Copy", "copy:", "c"
    )
    edit_menu.addItem_(copy_item)
    
    # Paste
    paste_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Paste", "paste:", "v"
    )
    edit_menu.addItem_(paste_item)
    
    edit_menu.addItem_(NSMenuItem.separatorItem())
    
    # Select All
    select_all_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Select All", "selectAll:", "a"
    )
    edit_menu.addItem_(select_all_item)
    
    edit_menu_item.setSubmenu_(edit_menu)
    edit_menu_item.setTitle_("Edit")
    main_menu.addItem_(edit_menu_item)
    
    # Checklist menu
    checklist_menu_item = NSMenuItem.alloc().init()
    checklist_menu = NSMenu.alloc().init()
    
    open_checklist_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Open Checklist from File", "openChecklist:", ""
    )
    checklist_menu.addItem_(open_checklist_item)
    
    compare_ckls_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Compare CKLs", "compareCkls:", ""
    )
    checklist_menu.addItem_(compare_ckls_item)
    
    checklist_menu_item.setSubmenu_(checklist_menu)
    checklist_menu_item.setTitle_("Checklist")
    main_menu.addItem_(checklist_menu_item)
    
    # Options menu
    options_menu_item = NSMenuItem.alloc().init()
    options_menu = NSMenu.alloc().init()
    
    preferences_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        "Preferences", "showPreferences:", ","
    )
    options_menu.addItem_(preferences_item)
    
    options_menu_item.setSubmenu_(options_menu)
    options_menu_item.setTitle_("Options")
    main_menu.addItem_(options_menu_item)
    
    app.setMainMenu_(main_menu)
    
    # Set targets to the app delegate (which handles menu validation)
    app_delegate = app.delegate()
    
    # Set targets for menu items to the app delegate
    import_stig_item.setTarget_(app_delegate)
    import_stig_item.setAction_("importStig:")
    
    compare_stigs_item.setTarget_(app_delegate)
    compare_stigs_item.setAction_("compareStigs:")
    
    compare_loaded_stigs_item.setTarget_(app_delegate)
    compare_loaded_stigs_item.setAction_("compareLoadedStigs:")
    
    check_for_stigs_item.setTarget_(app_delegate)
    check_for_stigs_item.setAction_("checkForStigs:")
    
    create_ckl_file_item.setTarget_(app_delegate)
    create_ckl_file_item.setAction_("createCklFile:")
    
    open_checklist_item.setTarget_(app_delegate)
    open_checklist_item.setAction_("openChecklist:")
    
    compare_ckls_item.setTarget_(app_delegate)
    compare_ckls_item.setAction_("compareCkls:")
    
    preferences_item.setTarget_(app_delegate)
    preferences_item.setAction_("showPreferences:")
    

