"""Hyprland-specific monitor mapper using hyprctl."""
import subprocess
import json
import logging
from typing import Optional, List, Dict, Any


logger = logging.getLogger(__name__)


class HyprlandMonitor:
    """Represents a monitor as reported by Hyprland."""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id', -1)
        self.name = data.get('name', 'unknown')
        self.x = data.get('x', 0)
        self.y = data.get('y', 0)
        self.width = data.get('width', 0)
        self.height = data.get('height', 0)
        self.scale = data.get('scale', 1.0)
        self.active_workspace = data.get('activeWorkspace', {}).get('id', -1)
        
        # Calculate effective dimensions (scaled dimensions used in coordinate space)
        self.effective_width = int(self.width / self.scale)
        self.effective_height = int(self.height / self.scale)
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if the given point is within this monitor's bounds.
        
        Uses effective (scaled) dimensions for bounds checking since Hyprland's
        coordinate system uses scaled coordinates.
        """
        return (self.x <= x < self.x + self.effective_width and 
                self.y <= y < self.y + self.effective_height)
    
    def __repr__(self):
        return f"HyprlandMonitor(id={self.id}, name={self.name}, x={self.x}, y={self.y}, {self.width}x{self.height}, scale={self.scale}, effective={self.effective_width}x{self.effective_height})"


def get_hyprland_monitors() -> List[HyprlandMonitor]:
    """Get list of monitors from Hyprland.
    
    Returns:
        List of HyprlandMonitor objects, sorted by x-coordinate for display.
    
    Raises:
        RuntimeError: If hyprctl fails or returns unexpected format.
    """
    try:
        result = subprocess.run(
            ['hyprctl', 'monitors', '-j'],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True
        )
        monitors_data = json.loads(result.stdout)
        monitors = [HyprlandMonitor(m) for m in monitors_data]
        # Sort by x-coordinate for consistent display ordering
        monitors.sort(key=lambda m: m.x)
        return monitors
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, 
            json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to get monitors from hyprctl: %s", e)
        raise RuntimeError(f"hyprctl monitors query failed: {e}")


def get_monitor_index_from_xy_hyprland(x: int, y: int) -> Optional[int]:
    """Determine which monitor contains the given coordinates using Hyprland.
    
    Returns the sorted index (by x-coordinate) which is used for function key mapping:
    - Leftmost monitor = index 0 = F1
    - Middle monitor = index 1 = F2
    - Rightmost monitor = index 2 = F3
    
    Args:
        x: The x-coordinate.
        y: The y-coordinate.
    
    Returns:
        The monitor index (sorted by x position, 0-based), or None if not found.
    """
    try:
        monitors = get_hyprland_monitors()
        for index, monitor in enumerate(monitors):
            if monitor.contains_point(x, y):
                logger.debug("Coordinate (%d, %d) is on monitor index %d (ID=%d, name=%s, x=%d)", 
                           x, y, index, monitor.id, monitor.name, monitor.x)
                return index
        return None
    except Exception as e:
        logger.error("Failed to determine monitor from coordinates: %s", e)
        return None


