"""Helper functions for NSView attribute storage."""

# Module-level storage for view attributes
_view_attrs = {}


def get_view_attrs(view):
    """Get attributes dictionary for a view."""
    if view not in _view_attrs:
        _view_attrs[view] = {}
    return _view_attrs[view]


def get_bounds_size(bounds):
    """Safely extract width and height from NSRect bounds."""
    try:
        # Try accessing as struct
        if hasattr(bounds, 'size'):
            return bounds.size.width, bounds.size.height
        # Try accessing as tuple/list
        elif isinstance(bounds, (tuple, list)) and len(bounds) >= 2:
            size = bounds[1]
            if hasattr(size, 'width') and hasattr(size, 'height'):
                return size.width, size.height
            elif isinstance(size, (tuple, list)) and len(size) >= 2:
                return float(size[0]), float(size[1])
        # Try direct attribute access
        elif hasattr(bounds, 'width') and hasattr(bounds, 'height'):
            return bounds.width, bounds.height
    except (AttributeError, TypeError, IndexError):
        pass
    # Default fallback
    return 800.0, 600.0

