from typing import Optional, Dict
import logging
import time

logger = logging.getLogger(__name__)

# Global cache for Sunshine monitor mapping
_sunshine_monitor_map: Optional[Dict[str, int]] = None
_last_refresh_time: float = 0.0
_refresh_cooldown: float = 10.0  # Minimum seconds between refreshes


def initialize_sunshine_mapping() -> bool:
    """Initialize the Sunshine monitor mapping from logs.
    
    Should be called once at server startup.
    
    Returns:
        True if successfully initialized, False otherwise.
    """
    global _sunshine_monitor_map, _last_refresh_time
    
    try:
        from .sunshine_monitor import create_sunshine_monitor_map
        _sunshine_monitor_map = create_sunshine_monitor_map()
        _last_refresh_time = time.time()
        
        if _sunshine_monitor_map:
            logger.info("Sunshine monitor mapping initialized:")
            for name, idx in _sunshine_monitor_map.items():
                logger.info(f"  {name} → Sunshine Monitor {idx} (F{idx + 1})")
            return True
        else:
            logger.warning("No monitors found in Sunshine logs")
            return False
            
    except Exception as e:
        logger.error(f"Failed to initialize Sunshine mapping: {e}", exc_info=True)
        return False


def refresh_sunshine_mapping() -> bool:
    """Refresh the Sunshine monitor mapping from logs.
    
    Can be called when unknown monitors are detected. Has a cooldown to avoid
    excessive re-parsing.
    
    Returns:
        True if successfully refreshed, False otherwise.
    """
    global _sunshine_monitor_map, _last_refresh_time
    
    # Check cooldown
    now = time.time()
    if now - _last_refresh_time < _refresh_cooldown:
        logger.debug(f"Skipping refresh (cooldown: {_refresh_cooldown}s)")
        return False
    
    try:
        from .sunshine_monitor import create_sunshine_monitor_map
        old_map = _sunshine_monitor_map.copy() if _sunshine_monitor_map else {}
        _sunshine_monitor_map = create_sunshine_monitor_map()
        _last_refresh_time = now
        
        if _sunshine_monitor_map:
            # Check if anything changed
            if old_map != _sunshine_monitor_map:
                logger.info("Sunshine monitor mapping refreshed:")
                for name, idx in _sunshine_monitor_map.items():
                    if name not in old_map:
                        logger.info(f"  NEW: {name} → Sunshine Monitor {idx} (F{idx + 1})")
                    else:
                        logger.debug(f"  {name} → Sunshine Monitor {idx} (F{idx + 1})")
            else:
                logger.debug("Sunshine mapping unchanged after refresh")
            return True
        else:
            logger.warning("No monitors found in Sunshine logs after refresh")
            return False
            
    except Exception as e:
        logger.error(f"Failed to refresh Sunshine mapping: {e}", exc_info=True)
        return False


def get_monitor_from_xy_sunshine(x: int, y: int) -> Optional[int]:
    """
    Determines which monitor contains the given coordinates and returns Sunshine's monitor index.
    
    Uses Sunshine's monitor ordering (from logs) instead of position-based ordering.
    
    Args:
        x: The x-coordinate.
        y: The y-coordinate.

    Returns:
        The Sunshine monitor index (0-based), or None if not found.
    """
    global _sunshine_monitor_map
    
    # If no Sunshine mapping is available, fall back to position-based
    if _sunshine_monitor_map is None:
        logger.debug("Sunshine mapping not initialized, falling back to position-based")
        return get_monitor_from_xy(x, y)
    
    # Get the monitor name from Hyprland
    try:
        from .hyprland_monitor import get_hyprland_monitors
        monitors = get_hyprland_monitors()
        
        # Find which monitor contains this point
        for monitor in monitors:
            if monitor.contains_point(x, y):
                # Look up the Sunshine index for this monitor name
                sunshine_index = _sunshine_monitor_map.get(monitor.name)
                if sunshine_index is not None:
                    logger.debug(f"Coordinate ({x}, {y}) on {monitor.name} → Sunshine index {sunshine_index}")
                    return sunshine_index
                else:
                    # Monitor not in mapping - try refreshing once
                    logger.warning(f"Monitor {monitor.name} not found in Sunshine mapping, refreshing...")
                    if refresh_sunshine_mapping():
                        # Try lookup again after refresh
                        sunshine_index = _sunshine_monitor_map.get(monitor.name)
                        if sunshine_index is not None:
                            logger.info(f"Found {monitor.name} after refresh → Sunshine index {sunshine_index}")
                            return sunshine_index
                    
                    logger.warning(f"Monitor {monitor.name} still not found after refresh")
                    return None
        
        # Not on any monitor
        return None
        
    except Exception as e:
        logger.error(f"Failed to get monitor from coordinates: {e}", exc_info=True)
        return None


def get_monitor_from_xy(x: int, y: int) -> Optional[int]:
    """
    Determines which monitor contains the given (x, y) coordinates.
    
    Returns the monitor index sorted by x-coordinate (left to right):
    - Leftmost monitor = 0 (maps to F1)
    - Next monitor = 1 (maps to F2)
    - Rightmost monitor = 2 (maps to F3)
    
    Prefers Hyprland native monitor info if available, falls back to screeninfo.

    Args:
        x: The x-coordinate.
        y: The y-coordinate.

    Returns:
        The index of the monitor (sorted by x position), or None if not found.
    """
    # Try Hyprland first (most accurate on Hyprland/Wayland)
    try:
        from .hyprland_monitor import get_monitor_index_from_xy_hyprland
        return get_monitor_index_from_xy_hyprland(x, y)
    except Exception as e_hyprland:
        # Fall back to screeninfo for X11 or other display servers
        try:
            # Import screeninfo lazily so the module can still import on systems
            # where screeninfo is not installed; callers will get None if we
            # can't detect monitors.
            import screeninfo

            # Sort monitors by their x-coordinate to ensure a consistent order (0, 1, 2, etc.)
            monitors = sorted(screeninfo.get_monitors(), key=lambda m: m.x)
            for i, monitor in enumerate(monitors):
                if monitor.x <= x < monitor.x + monitor.width and \
                   monitor.y <= y < monitor.y + monitor.height:
                    return i
        except Exception as e_screeninfo:
            # Any failure to query monitors results in returning None. The
            # caller should handle this gracefully (e.g., by falling back to
            # another input method).
            logger.debug("Monitor detection failed - hyprland: %s, screeninfo: %s", e_hyprland, e_screeninfo)
            return None
    return None

if __name__ == '__main__':
    # Example usage for testing
    # Note: This requires a running display server to work.
    try:
        from pynput import mouse

        def on_move(x, y):
            monitor_index = get_monitor_from_xy(x, y)
            if monitor_index is not None:
                print(f"Mouse is at ({x}, {y}) on monitor {monitor_index}", end='\r')

        print("Testing monitor detection. Move your mouse. Press Ctrl+C to exit.")
        with mouse.Listener(on_move=on_move) as listener:
            listener.join()
    except ImportError:
        print("pynput is not installed. Run 'pip install pynput' for this test.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")