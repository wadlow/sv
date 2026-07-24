"""Application delegate for the STIG Viewer."""

from AppKit import NSApplication, NSObject, NSMenuItem
from PyObjCTools import AppHelper

from .controllers.app_controller import AppController


class AppDelegate(NSObject):
    """Application delegate."""
    
    def applicationDidFinishLaunching_(self, notification):
        """Called when the application finishes launching."""
        try:
            # Initialize the app controller
            self.app_controller = AppController()
            self.app_controller.setup_application()
        except Exception as e:
            import traceback
            print(f"Error during application setup: {e}")
            traceback.print_exc()
            from AppKit import NSAlert
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Application Error")
            alert.setInformativeText_(f"Error starting application: {e}")
            alert.setAlertStyle_(2)  # NSAlertStyleCritical
            alert.runModal()
    
    def applicationShouldTerminate_(self, sender):
        """Called when the application is about to terminate."""
        # Let the app controller handle termination
        if hasattr(self, 'app_controller'):
            return self.app_controller.should_terminate()
        return True
    
    def applicationWillTerminate_(self, notification):
        """Called when the application is terminating."""
        if hasattr(self, 'app_controller'):
            self.app_controller.will_terminate()
    
    def windowShouldClose_(self, sender):
        """Called when the user clicks the window close button."""
        print("Window close button clicked - terminating application")
        app = NSApplication.sharedApplication()
        app.terminate_(None)
        return True
    
    # Menu validation - enable menu items if app controller exists
    def validateMenuItem_(self, menu_item):
        """Validate menu items - enable them if app controller is available."""
        if not hasattr(self, 'app_controller') or not self.app_controller:
            return False
        
        action = menu_item.action()
        if action == 'importStig:' or action == 'compareStigs:' or action == 'checkForStigs:' or \
           action == 'openChecklist:' or action == 'compareCkls:' or action == 'showPreferences:':
            return True
        
        if action == 'compareLoadedStigs:':
            return self.app_controller.has_comparable_stigs()
        
        # Create CKL file is only enabled when on Explorer tab AND STIGs are loaded
        if action == 'createCklFile:':
            return (self.app_controller.is_explorer_tab_active() and 
                    self.app_controller.has_stigs_loaded())
        
        return False
    
    # Menu action handlers
    def importStig_(self, sender):
        """Handle Import STIG menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.import_stig_files()
    
    def compareStigs_(self, sender):
        """Handle Compare STIGs menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.compare_stigs()
    
    def compareLoadedStigs_(self, sender):
        """Handle Compare Loaded STIGs menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.compare_loaded_stigs()
    
    def checkForStigs_(self, sender):
        """Handle Check for STIGs menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.check_for_stigs()
    
    def openChecklist_(self, sender):
        """Handle Open Checklist menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.open_checklist_files()
    
    def createCklFile_(self, sender):
        """Handle Create CKL file menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.create_ckl_file()
    
    def compareCkls_(self, sender):
        """Handle Compare CKLs menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.compare_ckls()
    
    def showPreferences_(self, sender):
        """Handle Preferences menu action."""
        if hasattr(self, 'app_controller') and self.app_controller:
            self.app_controller.show_preferences()

