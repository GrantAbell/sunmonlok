#!/usr/bin/env python3
"""Test script to verify monitor ID mapping."""

from sunshine_mmlock.hyprland_monitor import get_hyprland_monitors
from sunshine_mmlock.sunshine_monitor import parse_sunshine_monitors, create_sunshine_monitor_map
from sunshine_mmlock.mapper import get_monitor_from_xy_sunshine, initialize_sunshine_mapping

def main():
    print("=== Sunshine Monitor Mapping ===\n")
    
    # Initialize Sunshine mapping
    initialize_sunshine_mapping()
    sunshine_monitors = parse_sunshine_monitors()
    sunshine_map = create_sunshine_monitor_map()
    
    if sunshine_monitors:
        print(f"Found {len(sunshine_monitors)} monitor(s) in Sunshine logs:\n")
        for mon in sunshine_monitors:
            print(f"  Sunshine Index {mon.index} (F{mon.index + 1}): {mon.name}")
            print(f"    Description: {mon.description}")
        print()
    else:
        print("WARNING: No Sunshine monitors found!\n")
    
    print("=== Hyprland Monitor Layout ===\n")
    monitors = get_hyprland_monitors()
    
    for monitor in monitors:
        sunshine_idx = sunshine_map.get(monitor.name, "?")
        x_end = monitor.x + monitor.effective_width
        print(f"{monitor.name} (Hyprland ID={monitor.id})")
        print(f"  Position: x=[{monitor.x}, {x_end}), y={monitor.y}")
        print(f"  Pixel Size: {monitor.width}x{monitor.height}, Scale: {monitor.scale}")
        print(f"  Effective Size: {monitor.effective_width}x{monitor.effective_height}")
        print(f"  → Maps to Sunshine Index {sunshine_idx} (F{sunshine_idx + 1 if isinstance(sunshine_idx, int) else '?'})")
        print()
    
    # Test some coordinates
    print("=== Testing Coordinate Mappings (Sunshine-based) ===\n")
    test_points = [
        (1500, 720),   # Should be in DP-1
        (4000, 720),   # Should be in HDMI-A-1
        (6000, 945),   # Should be in SUNSHINE (if present)
    ]
    
    for x, y in test_points:
        sunshine_index = get_monitor_from_xy_sunshine(x, y)
        if sunshine_index is not None:
            # Find which monitor this is
            monitor = None
            for m in monitors:
                if m.contains_point(x, y):
                    monitor = m
                    break
            
            if monitor:
                print(f"({x}, {y}) -> {monitor.name} → Sunshine Index {sunshine_index} = F{sunshine_index + 1}")
            else:
                print(f"({x}, {y}) -> Sunshine Index {sunshine_index} = F{sunshine_index + 1}")
        else:
            print(f"({x}, {y}) -> No monitor found")

if __name__ == "__main__":
    main()
