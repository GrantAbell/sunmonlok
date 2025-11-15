#!/usr/bin/env python3
"""Test mouse position providers to see which actually works."""

print("Testing mouse position providers...\n")

# Test 1: mouseinfo
print("1. Testing mouseinfo...")
try:
    import mouseinfo
    pos = mouseinfo.position()
    print(f"   ✓ mouseinfo works: {pos}\n")
    mouseinfo_works = True
except Exception as e:
    print(f"   ✗ mouseinfo failed: {e}\n")
    mouseinfo_works = False

# Test 2: pynput
print("2. Testing pynput...")
try:
    from pynput.mouse import Controller
    c = Controller()
    pos = c.position
    print(f"   ✓ pynput works: {pos}\n")
    pynput_works = True
except Exception as e:
    print(f"   ✗ pynput failed: {e}\n")
    pynput_works = False

# Test 3: Check display environment
print("3. Display environment:")
import os
print(f"   DISPLAY={os.environ.get('DISPLAY', 'not set')}")
print(f"   WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', 'not set')}")
print(f"   XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE', 'not set')}")

print("\n" + "="*50)
if mouseinfo_works or pynput_works:
    print("✓ At least one reliable method available!")
    print("  The app should NOT be using EvdevMouseReader.")
else:
    print("✗ No high-level mouse position API available.")
    print("  App will use EvdevMouseReader (which has drift issues).")
