# SunMonLok - Client/Server Architecture

Automatic monitor switching for Sunshine game streaming based on mouse position using **Sunshine's native monitor ordering**.

## Overview

This system uses a **client-server model** to detect mouse position on the host and trigger keyboard shortcuts on the streaming client:

- **Server (Host)**: Runs on the Sunshine streaming host (Linux/Hyprland), detects which monitor the mouse is on
- **Client**: Runs on the device receiving the Sunshine stream (any OS), presses keyboard shortcuts

### Key Features

- **Sunshine-native monitor mapping**: Parses Sunshine's logs to use its exact monitor ordering (HDMI-A-1, DP-1, SUNSHINE virtual display)
- **Auto-refresh mapping**: Detects when Sunshine adds/removes virtual displays during streaming sessions
- **Hyprland-native**: Uses `hyprctl` for accurate mouse and monitor detection with scale factor support
- **Low latency**: ~50-200ms from mouse movement to monitor switch
- **Network-based**: TCP protocol for reliable client-server communication
- **Minimal dependencies**: Only 1 package for server (screeninfo), 1 for client (pynput)

### Why Client/Server?

Sunshine streaming requires keyboard shortcuts to be pressed **on the client side** to switch which monitor is being streamed. The server detects mouse position but cannot directly affect the stream - the client must press the keys.

## Quick Start

### Server (Sunshine Host)
```bash
# Ensure Sunshine has run at least once (creates logs)
systemctl status sunshine

# Start the server
python -m sunshine_mmlock

# Server will parse Sunshine logs and show mapping:
# INFO - HDMI-A-1 → Sunshine Monitor 0 (F1)
# INFO - DP-1 → Sunshine Monitor 1 (F2)
```

### Client (Streaming Device)
```bash
python client.py --host <SUNSHINE_HOST_IP>
# Connected to server
# Received monitor switch to monitor 0
```

### Verify Mapping
```bash
# Test the Sunshine mapping
python test_mapping.py

# Check your actual Sunshine monitor order
journalctl -xe --no-pager -n 1000 | grep -A 10 "Start of Wayland monitor list"
```

## One-Command Installation

### 🚀 Quick Setup (Recommended)

```bash
# Clone and auto-install everything
git clone https://github.com/GrantAbell/sunmonlok.git
cd sunmonlok
./setup.sh
```

This installs the package with all dependencies and creates convenient commands.

### 🎮 Running

**Server (Sunshine Host)**:
```bash
sunmonlok                    # Universal launcher (runs server by default)
# or
sunmonlok server            # Explicit server mode  
# or
python -m sunshine_mmlock             # Direct module execution
```

**Client (Streaming Device)**:
```bash
sunmonlok client --host 192.168.1.100    # Universal launcher
# or  
sunmonlok-client --host 192.168.1.100    # Direct client command
# or
python client.py --host 192.168.1.100    # Direct script execution
```

### 🛠️ Development

```bash
# Development commands via Makefile
make install-all            # Install everything for development
make run-server             # Start server
HOST=192.168.1.100 make run-client  # Start client

# Or install manually
pip install -e ".[client,dev]"
```

### 📋 Requirements

**Server (Sunshine Host)**:
- Linux with Hyprland compositor
- Sunshine streaming server running
- `hyprctl` command available (comes with Hyprland)
- Python 3.8+

**Client (Streaming Device)**:
- Python 3.8+
- Any OS (macOS/Windows/Linux)

**macOS Client Setup**: Grant Accessibility permissions:
1. System Preferences → Security & Privacy → Privacy → Accessibility
2. Add Terminal or Python to the allowed apps

### 🔧 Manual Installation (Advanced)

If you prefer manual control:

```bash
# Server dependencies only
pip install -r requirements.txt

# Client dependencies only  
pip install -r requirements-client.txt

# Development dependencies
pip install -r requirements-dev.txt
```

## Configuration

### Server Configuration (`config.json`)

```json
{
    "hotkey": {
        "modifiers": ["ctrl", "alt", "shift"],
        "base_keys": ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11"]
    },
    "debounce_seconds": 0.5,
    "poll_interval": 0.2,
    "poll_move_threshold": 1.0,
    "debug": false,
    "server_port": 9876,
    "server_bind": "0.0.0.0"
}
```

**Settings:**
- `debounce_seconds`: Prevents rapid monitor switching when mouse hovers near boundaries (seconds)
- `poll_interval`: How frequently to check mouse position (seconds) - lower = more responsive but more CPU
- `poll_move_threshold`: Minimum mouse movement in pixels to process - reduces CPU when mouse is idle
- `server_port`: Network port for client connections (default: 9876)
- `server_bind`: Interface to bind to (`0.0.0.0` = all interfaces, `127.0.0.1` = localhost only)
- `debug`: Enable verbose logging
- `hotkey`: **(Legacy)** Only used if running server in standalone mode without client

**Recommended values:**
- Low latency: `poll_interval: 0.1`, `debounce_seconds: 0.3`
- Balanced (default): `poll_interval: 0.2`, `debounce_seconds: 0.5`
- Low CPU: `poll_interval: 0.5`, `debounce_seconds: 1.0`

### Client Configuration

The client uses command-line arguments:

```bash
python client.py --host 192.168.1.100 --port 9876 --debug
```

**Arguments:**
- `--host`: Server IP address (required)
- `--port`: Server port (default: 9876)
- `--debug`: Enable debug logging

## Usage

### 1. Start the Server (on Sunshine host)

```bash
# Run the server
python -m sunshine_mmlock

# The server output (yours will likely vary):
# INFO - Starting Monitor Mouse Lock Server...
# INFO - Initializing Sunshine monitor mapping...
# INFO - Parsed 2 monitor(s) from Sunshine (journalctl)
# INFO - Sunshine monitor mapping initialized:
# INFO -   HDMI-A-1 → Sunshine Monitor 0 (F1)
# INFO -   DP-1 → Sunshine Monitor 1 (F2)
# INFO - Detected 3 Hyprland monitor(s):
# INFO -   DP-1 (ID=0) x=[866-3426) scale=1.00
# INFO -   HDMI-A-1 (ID=1) x=[3426-5026) scale=1.60
# INFO - Server listening on 0.0.0.0:9876
# INFO - Hyprland mouse reader initialized successfully
# INFO - Starting mouse poller with a 0.200 second poll interval...
```

The server will:
- Parse Sunshine logs to get monitor ordering
- Detect your monitor layout using Hyprland (with scale factors)
- Listen for client connections on port 9876
- Send Sunshine monitor IDs (0-10) when the mouse moves between monitors

### 2. Start the Client (on streaming device)

```bash
python client.py --host <SUNSHINE_HOST_IP>

# Output:
# INFO - Connecting to server at <SUNSHINE_HOST_IP>:9876...
# INFO - Connected to server
# INFO - Received monitor switch to monitor 0
```

The client will:
- Connect to the server
- Press `Ctrl+Option+Command+Shift+F[1-11]` when receiving monitor IDs
- Automatically reconnect if connection is lost

### 3. Configure Sunshine Hotkeys

In Sunshine's web interface (typically `https://localhost:47990`), configure hotkeys to match the client output.

**Important**: The monitor indices sent by the server match **Sunshine's monitor order** from its logs, not physical position.

Check your Sunshine monitor order:
```bash
journalctl -xe --no-pager -n 1000 | grep -A 10 "Start of Wayland monitor list"
```

Example output:
```
Monitor 0 is HDMI-A-1: XXX Projector (HDMI-A-1)
Monitor 1 is DP-1: ASUS Monitor (DP-1)
```

Default Sunshine hotkeys:
- Monitor 0  → `Ctrl+Option+Shift+F1`
- Monitor 1  → `Ctrl+Option+Shift+F2`
- ...and so on

The server will automatically parse these logs and map coordinates to the correct Sunshine indices.

## Architecture

### Components

```
┌────────────────────────────────────────────────────┐
│  Sunshine Host (Linux/Hyprland)                    │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  Server (python -m sunshine_mmlock)          │ │
│  │                                              │ │
│  │  1. Parse Sunshine logs (journalctl)        │ │
│  │     → Get monitor order: HDMI-A-1=0, DP-1=1 │ │
│  │                                              │ │
│  │  2. Query Hyprland (hyprctl monitors -j)    │ │
│  │     → Get monitor layout with scale factors │ │
│  │                                              │ │
│  │  3. Create mapping: monitor name → index    │ │
│  │                                              │ │
│  │  4. Poll mouse position (hyprctl cursorpos) │ │      TCP Socket
│  │     → Detect monitor changes                │◄├─────────────────┐
│  │                                              │ │                 │
│  │  5. Broadcast monitor ID (0-10)             │ │                 │
│  │     → Send to all connected clients         │ │                 │
│  └──────────────────────────────────────────────┘ │                 │
└────────────────────────────────────────────────────┘                 │
                                                                       │
┌──────────────────────────────────────────────────┐                   │
│  Streaming Device (macOS/Windows/Linux)          │                   │
│                                                  │                   │
│  ┌────────────────────────────────────────────┐ │                   │
│  │  Client (python client.py)                 │ │                   │
│  │                                            │ │                   │
│  │  1. Connect to server (192.168.x.x:9876)  │─┼───────────────────┘
│  │                                            │ │
│  │  2. Receive monitor ID byte                │ │
│  │                                            │ │
│  │  3. Press Ctrl+Alt+Shift+Cmd+F[1-11]       │ │
│  │     → Triggers Sunshine monitor switch     │ │
│  │                                            │ │
│  │  4. Auto-reconnect on disconnect           │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### File Structure

```
sunmonlok/
├── sunshine_mmlock/             # Server package (renamed from 'mlock')
│   ├── __main__.py              # Server entry point
│   ├── config.py                # Configuration loader
│   ├── mapper.py                # Coordinate-to-monitor mapping (Sunshine + position-based)
│   ├── sunshine_monitor.py      # Sunshine log parser (NEW)
│   ├── listener.py              # Mouse position polling
│   ├── hyprland_mouse.py        # Hyprland mouse position reader
│   ├── hyprland_monitor.py      # Hyprland monitor detection (scale-aware)
│   ├── protocol.py              # Network protocol (single-byte monitor ID)
│   ├── server.py                # TCP server with client management
│   ├── executor.py              # (Legacy) Keystroke execution fallback
│   └── input_reader.py          # (Legacy) Evdev mouse reader fallback
├── client.py                    # Standalone client
├── config.json                  # Server configuration
├── requirements.txt             # Server dependencies (1 package)
├── requirements-client.txt      # Client dependencies (1 package)
├── requirements-dev.txt         # Development dependencies
├── test_mapping.py              # Test Sunshine mapping
├── test_monitors.py             # Test monitor detection
├── test_mouse_provider.py       # Test mouse readers
└── test_client.py               # Test client functionality
```

**Legacy components** (kept for non-Hyprland fallback):
- `executor.py`: Direct keystroke execution (unused in client-server mode)
- `input_reader.py`: Evdev-based mouse reading (unused on Hyprland)

### How It Works

1. **Server startup**: 
   - Parses Sunshine logs to get monitor ordering (`journalctl` → `~/.config/sunshine/sunshine.log`)
   - Detects Hyprland monitors with scale factors using `hyprctl monitors -j`
   - Creates mapping: Hyprland monitor name → Sunshine index
   - Starts TCP server on port 9876

2. **Mouse polling**: 
   - Every 0.2s (configurable), reads mouse position using `hyprctl cursorpos`
   - Checks if movement exceeds threshold (1.0px)

3. **Monitor detection**: 
   - Finds which Hyprland monitor contains the (x,y) coordinates
   - Uses scale-aware bounds (effective_width = width/scale)
   - Looks up Sunshine index for that monitor name

4. **Change detection**: 
   - Compares to last known monitor
   - Applies debounce timer (0.5s default)
   - Handles unknown monitors by auto-refreshing Sunshine mapping (10s cooldown)

5. **Broadcasting**: 
   - Sends single-byte monitor ID (0-10) to all connected clients
   - TCP socket ensures reliable delivery

6. **Client reception**: 
   - Receives monitor ID
   - Presses `Ctrl+Option+Command+Shift+F[1-11]` (monitor_id + 1)

7. **Sunshine response**: 
   - Receives hotkey
   - Switches stream to the target monitor

### Protocol

Simple TCP protocol on port 9876:
- **Message format**: Single byte (0-10)
- **Message meaning**: Monitor ID (Sunshine's index, not position-based)
- **Direction**: Server → Client (one-way)
- **Connection**: Persistent, auto-reconnect on failure

Example packet: `0x02` = Switch to monitor 2 (press Ctrl+Option+Command+Shift+F3)

### Sunshine Monitor Mapping

The server automatically parses Sunshine's logs to determine monitor ordering:

**How it works:**
1. **Startup**: Parses `journalctl` or `~/.config/sunshine/sunshine.log`
2. **Extracts monitor list**: Finds section between markers:
   ```
   -------- Start of Wayland monitor list --------
   Monitor 0 is HDMI-A-1: XXX Projector (HDMI-A-1)
   Monitor 1 is DP-1: ASUS Monitor (DP-1)
   Monitor 2 is SUNSHINE:
   --------- End of Wayland monitor list ---------
   ```
3. **Creates mapping**: `{"HDMI-A-1": 0, "DP-1": 1, "SUNSHINE": 2}`
4. **Coordinate lookup**: Mouse at (4000, 500) → Hyprland monitor "HDMI-A-1" → Sunshine index 0 → Sends byte `0x00`

**Auto-refresh:**
- When an unknown monitor is detected (e.g., SUNSHINE virtual display appears)
- Automatically re-parses Sunshine logs
- 10-second cooldown to prevent excessive re-parsing
- Logs new monitors: `NEW: SUNSHINE → Sunshine Monitor 2 (F3)`

**Fallback:**
- If Sunshine logs unavailable, uses position-based mapping (left-to-right)
- Leftmost monitor = 0, next = 1, etc.

**Scale factor awareness:**
- Hyprland monitors can have different scale factors (e.g., 1.0, 1.5, 1.6 for HiDPI)
- Monitor bounds use **effective dimensions** (width/scale) not pixel dimensions
- Example: 2560px wide monitor at 1.6 scale = 1600 effective units in coordinate space
- This prevents monitor overlap in bounds checking

**Testing your mapping:**
```bash
python test_mapping.py
```

Example output:
```
=== Sunshine Monitor Mapping ===
Sunshine Index 0 (F1): HDMI-A-1
Sunshine Index 1 (F2): DP-1
Sunshine Index 2 (F3): SUNSHINE

=== Hyprland Monitor Layout ===
DP-1 (Hyprland ID=0)
  Position: x=[866, 3426), y=0
  Pixel Size: 2560x1440, Scale: 1.00
  Effective Size: 2560x1440
  → Maps to Sunshine Index 1 (F2)

HDMI-A-1 (Hyprland ID=1)
  Position: x=[3426, 5026), y=0
  Pixel Size: 2560x1440, Scale: 1.60
  Effective Size: 1600x900
  → Maps to Sunshine Index 0 (F1)

=== Testing Coordinate Mappings ===
(1500, 720) -> DP-1 → Sunshine Index 1 = F2
(4000, 720) -> HDMI-A-1 → Sunshine Index 0 = F1
(6000, 945) -> SUNSHINE → Sunshine Index 2 = F3
```

## Troubleshooting

### Server Issues

**"Hyprland not detected"**
- Ensure you're running on Hyprland (not X11, Sway, etc.)
- Check `hyprctl monitors -j` works in terminal
- Verify `HYPRLAND_INSTANCE_SIGNATURE` environment variable is set

**"No monitors detected"**
- Run `hyprctl monitors -j` to see monitor layout
- Check Sunshine is running: `systemctl status sunshine`

**"Sunshine mapping not available"**
- Check Sunshine logs: `journalctl -xe --no-pager -n 1000 | grep "Start of Wayland monitor list"`
- Ensure Sunshine has started at least once (creates logs)
- Verify `~/.config/sunshine/sunshine.log` exists
- Server will fall back to position-based mapping (left-to-right)

**"Server won't start / port in use"**
```bash
# Check if port 9876 is in use
sudo netstat -tulpn | grep 9876

# Kill existing process
sudo kill -9 <PID>

# Or change port in config.json
```

### Client Issues

**"Connection refused"**
- Verify server is running
- Check firewall allows port 9876
- Test connectivity: `telnet <SERVER_IP> 9876`

**"Keys not working on macOS"**
- Grant Accessibility permissions in System Preferences
- Restart Terminal/Python after granting permissions

**"Wrong monitor switching"**
- Check Sunshine hotkey configuration matches client output
- Monitor IDs start at 0 (not 1)
- Ensure Sunshine is using same modifier keys

### Network Issues

**"Clients disconnecting frequently"**
- Check network stability
- Consider setting `server_bind` to specific interface IP
- Verify firewall isn't dropping idle connections

**"High latency"**
- Adjust `poll_interval` in `config.json` (lower = faster but more CPU)
- Check network bandwidth/quality
- Consider reducing `debounce_seconds`

## Performance

- **Server CPU usage**: <1% (polls every 0.2s by default)
- **Network bandwidth**: ~1 byte per monitor switch (minimal)
- **Latency**: ~50-200ms from mouse movement to keystroke
- **Memory**: ~25MB for server, ~15MB for client
- **Monitor detection**: <1ms per poll (native Hyprland IPC)
- **Sunshine log parsing**: ~5-10ms at startup, 10s cooldown for refreshes

## Requirements

### Server
- **Python 3.8+**
- **Linux with Hyprland compositor**
- **Sunshine streaming server** (for log-based monitor mapping)
- **`hyprctl`** available in PATH (comes with Hyprland)
- **Network connectivity** to accept client connections

**Install with**: `pip install -r requirements.txt`

**Installed packages** (server):
```
screeninfo==0.8.1  # Only used for non-Hyprland fallback
```

**Total packages installed**: 4 (`screeninfo`, `pynput`, `evdev`, `pip`)

### Client
- **Python 3.8+** (any OS: macOS, Windows, Linux)
- **`pynput`** Python package for cross-platform keyboard control
- **Network access** to server
- **Accessibility permissions** to send keystrokes:
  - **macOS**: System Preferences → Security & Privacy → Privacy → Accessibility
  - **Windows**: Run as administrator (optional, depends on app)
  - **Linux**: No special permissions usually needed

**Install with**: `pip install -r requirements-client.txt`

**Installed packages** (client):
```
pynput==1.8.1
```

### Development/Testing
Additional packages for testing fallback mouse readers and debugging:

**Install with**: `pip install -r requirements-dev.txt`

**Installed packages** (dev):
```
mouseinfo
pynput
evdev
```

**Note**: PyAutoGUI and its 11 dependencies were removed as unnecessary. The server uses native Hyprland commands exclusively.

## Security Considerations

- Protocol is unencrypted - use on trusted networks only
- Consider using SSH tunnel or VPN for internet connections
- Server binds to all interfaces by default - change `server_bind` to `127.0.0.1` for localhost only
- No authentication currently - clients can connect without credentials

## Future Enhancements

- [ ] Add TLS/SSL encryption for network protocol
- [ ] Add authentication/password protection
- [ ] Systemd service files for auto-start
- [ ] Client launchd plist for macOS auto-start
- [ ] Web-based configuration interface
- [ ] Support for X11 (currently Hyprland-only)
- [ ] Windows/macOS server support (detect Sunshine differently)
- [ ] Event-based detection using Hyprland IPC sockets (lower latency)
- [ ] Configuration option to prefer position-based vs Sunshine-based mapping
- [ ] Handle Sunshine log rotation without restart

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

[Your License Here]

## Summary

This tool solves the problem of **manually switching Sunshine streaming monitors** by automatically detecting which monitor your mouse is on and pressing the corresponding hotkey on the client device.

**What makes it unique:**
- Uses Sunshine's own monitor ordering from logs (not position-based guessing)
- Scale-factor aware for HiDPI monitors
- Auto-refreshes when Sunshine creates/removes virtual displays
- Minimal dependencies (1 package for server, 1 for client)
- Low latency (<200ms) and low CPU (<1%)

**Perfect for:**
- Multi-monitor Sunshine streaming setups
- Gaming across different displays
- Seamless monitor switching without touching keyboard
- Hyprland users who want automation

## Credits

Created for automatic monitor switching with Sunshine game streaming on Hyprland.

**Technologies used:**
- Hyprland IPC (`hyprctl`) for mouse/monitor detection
- Sunshine log parsing for monitor ordering
- TCP sockets for client-server communication
- pynput for cross-platform keyboard control
