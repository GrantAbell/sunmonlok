#!/usr/bin/env python3
"""Quick script to debug monitor detection."""

import screeninfo

monitors = screeninfo.get_monitors()
print(f"Total monitors detected: {len(monitors)}\n")

for i, m in enumerate(monitors):
    print(f"Monitor {i} (unsorted): {m.name}")
    print(f"  Position: ({m.x}, {m.y})")
    print(f"  Size: {m.width}x{m.height}")
    print(f"  Bounds: x=[{m.x}, {m.x + m.width}), y=[{m.y}, {m.y + m.height})")
    print()

# Now show sorted order (how mapper.py sees them)
monitors_sorted = sorted(monitors, key=lambda m: m.x)
print("\n=== After sorting by x-coordinate (mapper.py order) ===\n")
for i, m in enumerate(monitors_sorted):
    print(f"Monitor {i}: {m.name}")
    print(f"  Position: ({m.x}, {m.y})")
    print(f"  Size: {m.width}x{m.height}")
    print(f"  Bounds: x=[{m.x}, {m.x + m.width}), y=[{m.y}, {m.y + m.height})")
    print()

# Test some coordinates
test_coords = [(1280, 720), (2686, 508), (6438, 866)]
print("\n=== Testing coordinate mappings ===")
for x, y in test_coords:
    for i, m in enumerate(monitors_sorted):
        if m.x <= x < m.x + m.width and m.y <= y < m.y + m.height:
            print(f"({x}, {y}) -> Monitor {i}")
            break
    else:
        print(f"({x}, {y}) -> NOT FOUND")
