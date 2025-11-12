#!/usr/bin/env python3
"""
Client application for receiving monitor switch notifications and pressing hotkeys.

This client connects to the monitor detection server and presses the appropriate
keyboard shortcuts when receiving monitor change notifications.

Usage:
    python client.py --host <server_ip> [--port 9876]
"""

import argparse
import socket
import logging
import socket
import sys
import time
from typing import Optional

# Try to import pynput for cross-platform keyboard support
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("WARNING: pynput not available. Install with: pip install pynput")

logger = logging.getLogger(__name__)

from mlock.protocol import receive_monitor_switch, DEFAULT_PORT
"""
Network protocol for monitor switch notifications.

Simple TCP-based protocol where:
- Server sends a single byte (0-10) representing the monitor ID
- Client receives and triggers the corresponding keystroke
- Connection is persistent with reconnection logic
"""

import socket
import struct
import logging

logger = logging.getLogger(__name__)


# Protocol constants
PROTOCOL_VERSION = 1
DEFAULT_PORT = 9876
MAX_MONITOR_ID = 10  # Support F1-F11


class MonitorProtocol:
    """Handles encoding/decoding of monitor switch messages."""
    
    @staticmethod
    def encode_monitor_switch(monitor_id: int) -> bytes:
        """Encode a monitor ID into a network message.
        
        Args:
            monitor_id: Monitor index (0-10)
            
        Returns:
            Bytes ready to send over the network
        """
        if not (0 <= monitor_id <= MAX_MONITOR_ID):
            raise ValueError(f"Monitor ID must be 0-{MAX_MONITOR_ID}, got {monitor_id}")
        
        # Simple protocol: single byte for monitor ID
        return struct.pack('B', monitor_id)
    
    @staticmethod
    def decode_monitor_switch(data: bytes) -> int:
        """Decode a monitor switch message.
        
        Args:
            data: Raw bytes from network
            
        Returns:
            Monitor ID (0-10)
        """
        if len(data) != 1:
            raise ValueError(f"Expected 1 byte, got {len(data)}")
        
        monitor_id = struct.unpack('B', data)[0]
        
        if not (0 <= monitor_id <= MAX_MONITOR_ID):
            raise ValueError(f"Invalid monitor ID: {monitor_id}")
        
        return monitor_id


def send_monitor_switch(sock: socket.socket, monitor_id: int) -> bool:
    """Send a monitor switch notification over a socket.
    
    Args:
        sock: Connected socket
        monitor_id: Monitor ID to send
        
    Returns:
        True if successful, False if connection error
    """
    try:
        message = MonitorProtocol.encode_monitor_switch(monitor_id)
        sock.sendall(message)
        logger.debug("Sent monitor ID %d", monitor_id)
        return True
    except (socket.error, OSError) as e:
        logger.error("Failed to send monitor switch: %s", e)
        return False


def receive_monitor_switch(sock: socket.socket, timeout: float = None) -> int:
    """Receive a monitor switch notification from a socket.
    
    Args:
        sock: Connected socket
        timeout: Optional timeout in seconds
        
    Returns:
        Monitor ID (0-10)
        
    Raises:
        ConnectionError: If connection is closed
        ValueError: If invalid data received
    """
    if timeout is not None:
        sock.settimeout(timeout)
    
    try:
        data = sock.recv(1)
        if not data:
            raise ConnectionError("Connection closed by peer")
        
        monitor_id = MonitorProtocol.decode_monitor_switch(data)
        logger.debug("Received monitor ID %d", monitor_id)
        return monitor_id
    except socket.timeout:
        raise TimeoutError("Receive timeout")
    except (socket.error, OSError) as e:
        raise ConnectionError(f"Socket error: {e}")

def receive_monitor_switch(sock: socket.socket, timeout: float = None) -> int:
    """Receive a monitor switch notification from a socket.
    
    Args:
        sock: Connected socket
        timeout: Optional timeout in seconds
        
    Returns:
        Monitor ID (0-10)
        
    Raises:
        ConnectionError: If connection is closed
        ValueError: If invalid data received
    """
    if timeout is not None:
        sock.settimeout(timeout)
    
    try:
        data = sock.recv(1)
        if not data:
            raise ConnectionError("Connection closed by peer")
        
        monitor_id = MonitorProtocol.decode_monitor_switch(data)
        logger.debug("Received monitor ID %d", monitor_id)
        return monitor_id
    except socket.timeout:
        raise TimeoutError("Receive timeout")
    except (socket.error, OSError) as e:
        raise ConnectionError(f"Socket error: {e}")


class KeystrokeClient:
    """Client that receives monitor IDs and presses corresponding hotkeys."""
    
    def __init__(self, modifiers: list = None):
        """Initialize the keystroke client.
        
        Args:
            modifiers: List of modifier keys (default: ['ctrl', 'alt', 'shift', 'cmd'])
        """
        self.logger = logging.getLogger(__name__)
        
        if not PYNPUT_AVAILABLE:
            raise RuntimeError("pynput is required for keystroke client. Install with: pip install pynput")
        
        self._keyboard = keyboard.Controller()
        
        # Default modifiers for macOS: Ctrl+Option+Fn+Shift
        # On macOS: ctrl=control, alt=option, cmd=command
        if modifiers is None:
            modifiers = ['ctrl', 'alt', 'shift', 'cmd']
        
        # Map modifier names to pynput keys
        MODIFIER_MAP = {
            'ctrl': keyboard.Key.ctrl,
            'control': keyboard.Key.ctrl,
            'alt': keyboard.Key.alt,
            'option': keyboard.Key.alt,
            'shift': keyboard.Key.shift,
            'cmd': keyboard.Key.cmd,
            'command': keyboard.Key.cmd,
            'super': keyboard.Key.cmd,
        }
        
        self._modifiers = [MODIFIER_MAP[mod.lower()] for mod in modifiers if mod.lower() in MODIFIER_MAP]
        self.logger.info("Initialized keystroke client with modifiers: %s", modifiers)
    
    def press_hotkey(self, monitor_id: int):
        """Press the hotkey combination for the given monitor.
        
        Args:
            monitor_id: Monitor ID (0-10) corresponding to F1-F11
        """
        # Map monitor ID to function key (0->F1, 1->F2, ..., 10->F11)
        function_keys = [
            keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3, keyboard.Key.f4,
            keyboard.Key.f5, keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8,
            keyboard.Key.f9, keyboard.Key.f10, keyboard.Key.f11
        ]
        
        if not (0 <= monitor_id <= 10):
            self.logger.error("Invalid monitor ID: %d", monitor_id)
            return
        
        target_key = function_keys[monitor_id]
        
        try:
            # Press all modifiers
            for mod in self._modifiers:
                self._keyboard.press(mod)
            
            # Tap the function key
            self._keyboard.tap(target_key)
            
            # Release all modifiers
            for mod in reversed(self._modifiers):
                self._keyboard.release(mod)
            
            modifier_names = '+'.join([str(mod).split('.')[-1] for mod in self._modifiers])
            self.logger.info("Pressed hotkey for monitor ID %d: %s+F%d", 
                           monitor_id, modifier_names, monitor_id + 1)
        except Exception as e:
            self.logger.error("Failed to press hotkey: %s", e, exc_info=True)


class MonitorClient:
    """Network client that connects to monitor server and handles monitor switches."""
    
    def __init__(self, host: str, port: int = DEFAULT_PORT, reconnect_delay: float = 5.0):
        """Initialize the monitor client.
        
        Args:
            host: Server hostname or IP
            port: Server port
            reconnect_delay: Seconds to wait between reconnection attempts
        """
        self.host = host
        self.port = port
        self.reconnect_delay = reconnect_delay
        self.logger = logging.getLogger(__name__)
        self._socket: Optional[socket.socket] = None
        self._running = False
        self.keystroke_client = KeystrokeClient()
    
    def connect(self) -> bool:
        """Connect to the server.
        
        Returns:
            True if connected successfully
        """
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.connect((self.host, self.port))
            self.logger.info("Connected to server %s:%d", self.host, self.port)
            return True
        except (socket.error, OSError) as e:
            self.logger.error("Connection failed: %s", e)
            if self._socket:
                self._socket.close()
                self._socket = None
            return False
    
    def run(self):
        """Main client loop - connect and handle monitor switches."""
        self._running = True
        self.logger.info("Starting monitor client...")
        
        while self._running:
            # Connect if not connected
            if not self._socket:
                if not self.connect():
                    self.logger.info("Reconnecting in %.1f seconds...", self.reconnect_delay)
                    time.sleep(self.reconnect_delay)
                    continue
            
            # Receive and handle monitor switches
            try:
                monitor_id = receive_monitor_switch(self._socket, timeout=1.0)
                self.keystroke_client.press_hotkey(monitor_id)
            except TimeoutError:
                # Timeout is normal, just continue
                continue
            except (ConnectionError, ValueError) as e:
                self.logger.error("Connection error: %s", e)
                if self._socket:
                    self._socket.close()
                    self._socket = None
                time.sleep(self.reconnect_delay)
    
    def stop(self):
        """Stop the client."""
        self.logger.info("Stopping client...")
        self._running = False
        if self._socket:
            self._socket.close()
            self._socket = None


def main():
    """Main entry point for the client application."""
    parser = argparse.ArgumentParser(
        description="Monitor switch client - receives monitor IDs and presses hotkeys"
    )
    parser.add_argument(
        '--host',
        required=True,
        help='Server hostname or IP address'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=DEFAULT_PORT,
        help=f'Server port (default: {DEFAULT_PORT})'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if not PYNPUT_AVAILABLE:
        print("ERROR: pynput is required. Install with: pip install pynput")
        return 1
    
    # Create and run client
    client = MonitorClient(args.host, args.port)
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        client.stop()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
