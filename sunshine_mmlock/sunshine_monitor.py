"""Parse Sunshine logs to extract monitor mappings."""
import re
import logging
import subprocess
from typing import List, Dict, Optional
from pathlib import Path
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class SunshineMonitor:
    """Represents a monitor as reported by Sunshine."""
    def __init__(self, index: int, name: str, description: str):
        self.index = index  # Sunshine's monitor index (order in the list)
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f"SunshineMonitor(index={self.index}, name={self.name}, description={self.description})"


def find_sunshine_log_file() -> Optional[Path]:
    """Find Sunshine's log file.
    
    Checks common locations for Sunshine logs.
    
    Returns:
        Path to the log file, or None if not found.
    """
    possible_locations = [
        Path.home() / ".local" / "share" / "sunshine" / "sunshine.log",
        Path.home() / ".config" / "sunshine" / "sunshine.log",
        Path("/var") / "log" / "sunshine" / "sunshine.log",
        Path("/tmp") / "sunshine.log",
    ]
    
    for path in possible_locations:
        if path.exists():
            logger.debug(f"Found Sunshine log at: {path}")
            return path
    
    logger.warning("Could not find Sunshine log file in common locations")
    return None


def parse_sunshine_monitors_from_journalctl() -> List[SunshineMonitor]:
    """Parse Sunshine's monitor list from journalctl output.
    
    Looks for the most recent section between:
    -------- Start of Wayland monitor list --------
    and
    --------- End of Wayland monitor list ---------
    
    Returns:
        List of SunshineMonitor objects in the order Sunshine reports them.
    """
    try:
        # Get recent journal entries
        result = subprocess.run(
            ['journalctl', '-xe', '--no-pager', '-n', '1000'],
            capture_output=True,
            text=True,
            timeout=5.0
        )
        
        if result.returncode != 0:
            logger.error("Failed to run journalctl")
            return []
        
        content = result.stdout
        
        # Find all monitor list sections and take the most recent one
        # Split by the start marker
        sections = content.split('-------- Start of Wayland monitor list --------')
        
        if len(sections) < 2:
            logger.warning("No Wayland monitor list found in journalctl output")
            return []
        
        # Get the last section and find the end marker
        last_section = sections[-1]
        if '--------- End of Wayland monitor list ---------' not in last_section:
            logger.warning("Monitor list end marker not found")
            return []
        
        # Extract just the monitor list content
        monitor_section = last_section.split('--------- End of Wayland monitor list ---------')[0]
        print(monitor_section)
        # Parse monitor lines
        # Expected formats:
        # "Monitor 0 is HDMI-A-1: XXX Projector (HDMI-A-1)"
        # "Monitor 2 is SUNSHINE:"  (virtual display with no description)
        monitors = []
        monitor_pattern = r'Monitor (\d+) is (.*):(.*)$'
        
        for line in monitor_section.split('\n'):
            match = re.search(monitor_pattern, line)
            print(match)
            if match:
                index = int(match.group(1))
                name = match.group(2).strip()
                description = match.group(3).strip() if match.group(3) else name
                
                monitors.append(SunshineMonitor(
                    index=index,
                    name=name,
                    description=description
                ))
                logger.debug(f"Parsed Sunshine monitor {index}: {name} - {description}")
        
        # Sort by index to ensure correct order
        monitors.sort(key=lambda m: m.index)
        
        logger.info(f"Parsed {len(monitors)} monitor(s) from Sunshine (journalctl)")
        return monitors
        
    except subprocess.TimeoutExpired:
        logger.error("journalctl command timed out")
        return []
    except Exception as e:
        logger.error(f"Failed to parse Sunshine monitors from journalctl: {e}", exc_info=True)
        return []


def parse_sunshine_monitors(log_path: Optional[Path] = None) -> List[SunshineMonitor]:
    """Parse Sunshine's monitor list.
    
    First tries journalctl (most reliable), then falls back to log file.
    
    Args:
        log_path: Path to Sunshine log file. If None, will try journalctl first.
    
    Returns:
        List of SunshineMonitor objects in the order Sunshine reports them.
    """
    # Try journalctl first (most up-to-date)
    monitors = parse_sunshine_monitors_from_journalctl()
    if monitors:
        return monitors
    
    # Fallback to log file if provided
    if log_path is None:
        log_path = find_sunshine_log_file()
    
    if log_path is None:
        logger.error("Cannot parse Sunshine monitors: journalctl failed and no log file found")
        return []
    
    try:
        with open(log_path, 'r') as f:
            content = f.read()
        
        # Find the most recent monitor list section
        pattern = r'-------- Start of Wayland monitor list --------\s*(.*?)\s*--------- End of Wayland monitor list ---------'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            logger.warning("No Wayland monitor list found in Sunshine log file")
            return []
        
        # Use the last (most recent) match
        monitor_section = matches[-1]
        
        # Parse monitor lines with the same pattern
        monitors = []
        monitor_pattern = r'Monitor (\d+) is ([A-Z]+-?[A-Z]*-?\d*|[A-Z]+):(.*)$'
        
        for line in monitor_section.split('\n'):
            match = re.search(monitor_pattern, line)
            if match:
                index = int(match.group(1))
                name = match.group(2).strip()
                description = match.group(3).strip() if match.group(3) else name
                
                monitors.append(SunshineMonitor(
                    index=index,
                    name=name,
                    description=description
                ))
                logger.debug(f"Parsed Sunshine monitor {index}: {name}")
        
        monitors.sort(key=lambda m: m.index)
        logger.info(f"Parsed {len(monitors)} monitor(s) from Sunshine log file")
        return monitors
        
    except Exception as e:
        logger.error(f"Failed to parse Sunshine log file: {e}", exc_info=True)
        return []


def create_sunshine_monitor_map() -> Dict[str, int]:
    """Create a mapping from monitor name to Sunshine index.
    
    Returns:
        Dict mapping monitor name (e.g., "DP-1") to Sunshine monitor index (0, 1, 2...).
    """
    monitors = parse_sunshine_monitors()
    return {mon.name: mon.index for mon in monitors}


def get_sunshine_monitor_index(monitor_name: str, sunshine_map: Optional[Dict[str, int]] = None) -> Optional[int]:
    """Get Sunshine's monitor index for a given monitor name.
    
    Args:
        monitor_name: Monitor name from Hyprland (e.g., "DP-1")
        sunshine_map: Pre-built mapping dict. If None, will parse logs.
    
    Returns:
        Sunshine monitor index (0-based), or None if not found.
    """
    if sunshine_map is None:
        sunshine_map = create_sunshine_monitor_map()
    
    return sunshine_map.get(monitor_name)


if __name__ == "__main__":
    # Test the parser
    logging.basicConfig(level=logging.DEBUG)
    
    print("=== Sunshine Monitor Parser Test ===\n")
    
    log_file = find_sunshine_log_file()
    if log_file:
        print(f"Found log file: {log_file}\n")
        
        monitors = parse_sunshine_monitors(log_file)
        print(f"Detected {len(monitors)} monitor(s):\n")
        
        for mon in monitors:
            print(f"  Sunshine Index {mon.index}: {mon.name}")
            print(f"    Full description: {mon.description}")
            print()
        
        # Show the mapping
        mapping = create_sunshine_monitor_map()
        print("Monitor Name → Sunshine Index mapping:")
        for name, idx in mapping.items():
            print(f"  {name} → {idx} (F{idx + 1})")
    else:
        print("ERROR: Could not find Sunshine log file")
        print("\nPlease provide the log file path manually:")
        print("  python -c 'from src.sunshine_monitor import parse_sunshine_monitors; "
              "parse_sunshine_monitors(Path(\"/path/to/sunshine.log\"))'")
