"""Hyprland-specific mouse position provider using hyprctl."""
import subprocess
import logging
from typing import Tuple, Optional


logger = logging.getLogger(__name__)


class HyprlandMouseReader:
    """Reads mouse position directly from Hyprland compositor via hyprctl.
    
    This provides accurate absolute mouse coordinates on Hyprland without
    needing X11 or accumulating relative movements.
    """
    
    def __init__(self):
        """Initialize and verify hyprctl is available."""
        try:
            result = subprocess.run(
                ['hyprctl', 'cursorpos'],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=True
            )
            # Test that we can parse the output (format: "X, Y")
            parts = result.stdout.strip().split(',')
            if len(parts) != 2:
                raise ValueError(f"Unexpected cursorpos format: {result.stdout}")
            logger.info("Hyprland mouse reader initialized successfully")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"hyprctl not available or not working: {e}")
    
    def position(self) -> Tuple[int, int]:
        """Get current mouse position from Hyprland.
        
        Returns:
            Tuple of (x, y) coordinates.
        
        Raises:
            RuntimeError: If hyprctl fails or returns unexpected format.
        """
        try:
            result = subprocess.run(
                ['hyprctl', 'cursorpos'],
                capture_output=True,
                text=True,
                timeout=2.0,  # Increased from 0.5s to avoid spurious timeouts during high system load
                check=True
            )
            # Parse "X, Y" format
            parts = result.stdout.strip().split(',')
            x = int(parts[0].strip())
            y = int(parts[1].strip())
            return (x, y)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, IndexError) as e:
            logger.error("Failed to get cursor position from hyprctl: %s", e)
            raise RuntimeError(f"hyprctl cursor position query failed: {e}")


def is_hyprland_available() -> bool:
    """Check if we're running under Hyprland compositor.
    
    Returns:
        True if Hyprland is available and hyprctl works.
    """
    try:
        result = subprocess.run(
            ['hyprctl', 'version'],
            capture_output=True,
            timeout=1.0,
            check=True
        )
        return True
    except Exception:
        return False
