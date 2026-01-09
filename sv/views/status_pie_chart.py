"""Status pie chart view using Core Graphics."""

from AppKit import NSView, NSRect, NSColor, NSViewWidthSizable, NSViewHeightSizable
from Foundation import NSObject
from typing import List
from collections import Counter
import objc
import os

from ..models.ckl_file import CklVuln
from ..models.checklist_status import ChecklistStatus
from .view_helpers import get_view_attrs, get_bounds_size

# Check if verbose CKL debug logging is enabled
_CKL_DEBUG = os.environ.get('SV_CKL_DEBUG') == '1'


class StatusPieChart(NSView):
    """Custom view that draws a pie chart of vulnerability statuses."""
    
    def init(self):
        """Initialize the pie chart view."""
        self = objc.super(StatusPieChart, self).init()
        if self is None:
            return None
        
        print("StatusPieChart.init: Initializing")  # Debug
        
        # Initialize with empty data
        attrs = get_view_attrs(self)
        attrs['vulns'] = []
        attrs['status_counts'] = {}
        StatusPieChart.updateCounts(self)
        
        # Mark as needing display
        self.setNeedsDisplay_(True)
        
        print("StatusPieChart.init: Complete")  # Debug
        return self
    
    def isOpaque(self):
        """Return YES to indicate the view is opaque (improves performance and ensures drawing)."""
        return True
    
    @objc.python_method
    def set_vulns(self, vulns: List[CklVuln]):
        """Set the vulnerabilities to display."""
        if _CKL_DEBUG:
            print(f"StatusPieChart.set_vulns: Setting {len(vulns)} vulns")  # Debug
        attrs = get_view_attrs(self)
        attrs['vulns'] = vulns
        StatusPieChart.updateCounts(self)
        
        status_counts = attrs.get('status_counts', {})
        if _CKL_DEBUG:
            print(f"StatusPieChart.set_vulns: status_counts={status_counts}")  # Debug
        
        # Check bounds - always show for debugging
        bounds = self.bounds()
        print(f"StatusPieChart.set_vulns: bounds={bounds.size.width}x{bounds.size.height}")
        
        # Force redraw
        self.setNeedsDisplay_(True)
        self.display()  # Force immediate display
        if _CKL_DEBUG:
            print("StatusPieChart.set_vulns: setNeedsDisplay and display called")  # Debug
    
    @objc.python_method
    def updateCounts(self):
        """Update the status counts."""
        attrs = get_view_attrs(self)
        vulns = attrs.get('vulns', [])
        counts = Counter()
        for vuln in vulns:
            counts[vuln.status] += 1
        attrs['status_counts'] = dict(counts)
    
    def drawRect_(self, rect):
        """Draw the pie chart."""
        # Always show drawRect calls - critical for debugging why pie chart doesn't appear
        print("StatusPieChart.drawRect_: Drawing")
        try:
            attrs = get_view_attrs(self)
            status_counts = attrs.get('status_counts', {})
            print(f"StatusPieChart.drawRect_: Got status_counts, count={len(status_counts)}")
            
            if not status_counts or sum(status_counts.values()) == 0:
                # Draw empty state - just fill with white to show the pane exists
                print("StatusPieChart.drawRect_: Drawing empty state")
                from AppKit import NSColor
                NSColor.whiteColor().setFill()
                from AppKit import NSBezierPath
                NSBezierPath.fillRect_(rect)
                print("StatusPieChart.drawRect_: Drew empty state (white fill)")
                return
        except Exception as e:
            print(f"StatusPieChart.drawRect_: ERROR in empty state check: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Get graphics context
        try:
            print("StatusPieChart.drawRect_: Getting graphics context")
            from AppKit import NSGraphicsContext
            context = NSGraphicsContext.currentContext()
            if context is None:
                print("StatusPieChart.drawRect_: No graphics context")
                return
            print("StatusPieChart.drawRect_: Got graphics context")
        except Exception as e:
            print(f"StatusPieChart.drawRect_: ERROR getting context: {e}")
            return
        
        try:
            print("StatusPieChart.drawRect_: Getting bounds")
            bounds = self.bounds()
            center_x = bounds.size.width / 2
            center_y = bounds.size.height / 2
            radius = min(bounds.size.width, bounds.size.height) / 2 - 20
            print(f"StatusPieChart.drawRect_: Bounds OK, radius={radius}")
            
            if radius <= 0:
                print("StatusPieChart.drawRect_: Radius too small")
                return
            
            # Color mapping for statuses (using basic colors)
            print("StatusPieChart.drawRect_: Creating color map")
            from AppKit import NSColor
            colors = {
                ChecklistStatus.OPEN: NSColor.redColor(),
                ChecklistStatus.NOT_A_FINDING: NSColor.greenColor(),
                ChecklistStatus.NOT_REVIEWED: NSColor.grayColor(),
                ChecklistStatus.NOT_APPLICABLE: NSColor.blueColor(),
            }
            print("StatusPieChart.drawRect_: Color map created")
            
            # Calculate angles
            total = sum(status_counts.values())
            current_angle = -90  # Start at top
            print(f"StatusPieChart.drawRect_: Starting to draw {len(status_counts)} segments")
            
            # Draw each segment
            for status, count in status_counts.items():
                if count == 0:
                    continue
                
                angle = (count / total) * 360
                color = colors.get(status, NSColor.grayColor())
                print(f"StatusPieChart.drawRect_: Drawing segment for {status}, angle={angle}")
                
                # Draw pie segment
                StatusPieChart._draw_pie_segment(
                    center_x, center_y, radius,
                    current_angle, current_angle + angle,
                    color
                )
                
                current_angle += angle
            
            print("StatusPieChart.drawRect_: All segments drawn successfully")
            
            # Draw legend
            self._draw_legend(bounds, status_counts, colors)
            
        except Exception as e:
            print(f"StatusPieChart.drawRect_: ERROR during drawing: {e}")
            import traceback
            traceback.print_exc()
    
    def _draw_legend(self, bounds, status_counts, colors):
        """Draw a legend for the pie chart in 2 columns below the chart."""
        try:
            from AppKit import NSColor, NSBezierPath, NSFont, NSFontAttributeName, NSForegroundColorAttributeName
            from Foundation import NSString, NSDictionary
            
            # Legend configuration
            box_size = 14
            text_spacing = 5
            row_spacing = 5
            font_size = 11
            
            # Calculate center position for pie chart
            center_y = bounds.size.height / 2
            radius = min(bounds.size.width, bounds.size.height) / 2 - 20
            
            # Legend is at the bottom, right-justified for right column
            legend_start_y = 10
            legend_x_left = 10
            legend_x_right = bounds.size.width - 140  # Right-justify
            
            # Status names and display order (always show all statuses)
            status_order = [
                (ChecklistStatus.OPEN, "Open"),
                (ChecklistStatus.NOT_A_FINDING, "Not a Finding"),
                (ChecklistStatus.NOT_REVIEWED, "Not Reviewed"),
                (ChecklistStatus.NOT_APPLICABLE, "Not Applicable"),
            ]
            
            # Draw in 2x2 grid
            for idx, (status, name) in enumerate(status_order):
                count = status_counts.get(status, 0)
                color = colors.get(status, NSColor.grayColor())
                
                # Calculate position (2 columns)
                row = idx // 2
                col = idx % 2
                
                x_pos = legend_x_left if col == 0 else legend_x_right
                y_pos = legend_start_y + (row * (box_size + row_spacing))
                
                # Draw color box
                box_rect = ((x_pos, y_pos), (box_size, box_size))
                color.setFill()
                NSBezierPath.fillRect_(box_rect)
                
                # Draw black border around box
                NSColor.blackColor().setStroke()
                path = NSBezierPath.bezierPathWithRect_(box_rect)
                path.stroke()
                
                # Draw label with white text
                label_text = f"{name}: {count}"
                label_point = (x_pos + box_size + text_spacing, y_pos + 2)
                
                # Create attributes dictionary
                font = NSFont.systemFontOfSize_(font_size)
                attrs = {
                    NSFontAttributeName: font,
                    NSForegroundColorAttributeName: NSColor.whiteColor()
                }
                
                # Convert Python string to NSString and draw
                ns_label = NSString.stringWithString_(label_text)
                ns_label.drawAtPoint_withAttributes_(label_point, attrs)
            
        except Exception as e:
            print(f"StatusPieChart._draw_legend: ERROR: {e}")
    
    @staticmethod
    def _draw_pie_segment(center_x, center_y, radius, start_angle, end_angle, color):
        """Draw a pie chart segment."""
        # Create path
        from AppKit import NSBezierPath
        path = NSBezierPath.bezierPath()
        
        # Move to center
        path.moveToPoint_((center_x, center_y))
        
        # Add arc
        path.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
            (center_x, center_y),
            radius,
            start_angle,
            end_angle,
            False
        )
        
        # Close path
        path.closePath()
        
        # Fill with color
        color.setFill()
        path.fill()
        
        # Draw border
        NSColor.blackColor().setStroke()
        path.setLineWidth_(1.0)
        path.stroke()

