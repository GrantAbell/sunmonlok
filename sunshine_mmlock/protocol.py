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
