"""
Server component for monitor switch detection.

This server monitors mouse position and sends monitor ID updates to connected clients.
"""

import logging
import socket
import threading
import time
from typing import Set, Optional
from .protocol import send_monitor_switch, DEFAULT_PORT


logger = logging.getLogger(__name__)


class MonitorServer:
    """TCP server that broadcasts monitor switch notifications to connected clients."""
    
    def __init__(self, port: int = DEFAULT_PORT, bind_address: str = '0.0.0.0'):
        """Initialize the monitor server.
        
        Args:
            port: Port to listen on
            bind_address: Address to bind to (default: 0.0.0.0 for all interfaces)
        """
        self.port = port
        self.bind_address = bind_address
        self._server_socket: Optional[socket.socket] = None
        self._clients: Set[socket.socket] = set()
        self._clients_lock = threading.Lock()
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._current_monitor: Optional[int] = None
    
    def start(self):
        """Start the server and begin accepting connections."""
        if self._running:
            logger.warning("Server already running")
            return
        
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.bind_address, self.port))
            self._server_socket.listen(5)
            self._running = True
            
            logger.info("Server listening on %s:%d", self.bind_address, self.port)
            
            # Start accept thread
            self._accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self._accept_thread.start()
            
        except (socket.error, OSError) as e:
            logger.error("Failed to start server: %s", e)
            self._running = False
            if self._server_socket:
                self._server_socket.close()
                self._server_socket = None
            raise
    
    def stop(self):
        """Stop the server and close all connections."""
        logger.info("Stopping server...")
        self._running = False
        
        # Close server socket
        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None
        
        # Close all client connections
        with self._clients_lock:
            for client in list(self._clients):
                try:
                    client.close()
                except Exception:
                    pass
            self._clients.clear()
        
        # Wait for accept thread to finish
        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=2.0)
    
    def _accept_connections(self):
        """Accept incoming client connections (runs in separate thread)."""
        while self._running and self._server_socket:
            try:
                self._server_socket.settimeout(1.0)
                client_socket, address = self._server_socket.accept()
                
                logger.info("Client connected from %s:%d", address[0], address[1])
                
                with self._clients_lock:
                    self._clients.add(client_socket)
                
                # Send current monitor state immediately to new client
                if self._current_monitor is not None:
                    if not send_monitor_switch(client_socket, self._current_monitor):
                        logger.warning("Failed to send initial monitor state to new client")
                        client_socket.close()
                        with self._clients_lock:
                            self._clients.discard(client_socket)
                
            except socket.timeout:
                continue
            except (socket.error, OSError) as e:
                if self._running:
                    logger.error("Error accepting connection: %s", e)
                break
    
    def broadcast_monitor_switch(self, monitor_id: int):
        """Send a monitor switch notification to all connected clients.
        
        Args:
            monitor_id: Monitor ID (0-10)
        """
        self._current_monitor = monitor_id
        
        with self._clients_lock:
            disconnected = []
            
            for client in self._clients:
                if not send_monitor_switch(client, monitor_id):
                    disconnected.append(client)
            
            # Remove disconnected clients
            for client in disconnected:
                try:
                    client.close()
                except Exception:
                    pass
                self._clients.discard(client)
                logger.info("Client disconnected (send failed)")
        
        if disconnected:
            logger.debug("Removed %d disconnected clients", len(disconnected))
    
    def get_client_count(self) -> int:
        """Get the number of connected clients."""
        with self._clients_lock:
            return len(self._clients)
