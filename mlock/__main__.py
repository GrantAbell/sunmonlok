import signal
import sys
import logging
from .listener import MousePoller
from .server import MonitorServer
from .config import config

def setup_logging():
    """Configures the root logger."""
    level = logging.DEBUG if config.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout,
        force=True 
    )

# Global server instance for signal handler
_server_instance = None
_poller_instance = None

def handle_shutdown_signal(signum, frame):
    """Gracefully handle termination signals."""
    logging.info(f"Received signal {signum}. Shutting down gracefully.")
    if _poller_instance:
        _poller_instance.stop()
    if _server_instance:
        _server_instance.stop()
    sys.exit(0)

def main():
    """
    Main entry point for the monitor-mouse-lock server daemon.
    
    This server detects mouse monitor changes and broadcasts monitor IDs
    to connected clients over the network.
    """
    global _server_instance, _poller_instance
    
    setup_logging()
    logging.info("Starting Monitor Mouse Lock Server...")

    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    try:
        # Get server configuration
        server_port = config.__dict__.get('server_port', 9876)
        server_bind = config.__dict__.get('server_bind', '0.0.0.0')
        
        # Initialize Sunshine monitor mapping
        logging.info("Initializing Sunshine monitor mapping...")
        from .mapper import initialize_sunshine_mapping
        sunshine_available = initialize_sunshine_mapping()
        
        if not sunshine_available:
            logging.warning("Sunshine mapping not available, falling back to position-based mapping")
        
        # Log monitor layout
        try:
            from .hyprland_monitor import get_hyprland_monitors
            monitors = get_hyprland_monitors()
            logging.info("Detected %d Hyprland monitor(s):", len(monitors))
            for monitor in monitors:
                x_end = monitor.x + monitor.effective_width
                logging.info("  %s (ID=%d) x=[%d-%d) scale=%.2f", 
                           monitor.name, monitor.id, 
                           monitor.x, x_end, monitor.scale)
        except Exception as e:
            logging.warning("Could not log monitor layout: %s", e)
        
        # Start network server
        server = MonitorServer(port=server_port, bind_address=server_bind)
        server.start()
        _server_instance = server
        
        logging.info("Network server started on %s:%d", server_bind, server_port)
        
        # Create a simple broadcaster that sends monitor IDs to the server
        class ServerBroadcaster:
            """Adapter that broadcasts monitor changes to network clients."""
            def __init__(self, server: MonitorServer):
                self._server = server
            
            def execute_for_monitor(self, monitor_index: int):
                """Called when monitor changes - broadcast to clients."""
                client_count = self._server.get_client_count()
                if client_count > 0:
                    logging.info("Broadcasting monitor %d to %d client(s)", monitor_index, client_count)
                    self._server.broadcast_monitor_switch(monitor_index)
                else:
                    logging.debug("No clients connected, monitor %d not broadcast", monitor_index)
        
        broadcaster = ServerBroadcaster(server)
        
        # Start mouse poller with broadcaster
        # Use Sunshine mapping if available, otherwise fall back to position-based
        poller = MousePoller(executor=broadcaster, use_sunshine_mapping=sunshine_available)
        _poller_instance = poller
        poller.start()
        
    except Exception as e:
        logging.error("An unexpected error occurred: %s", e, exc_info=True)
        if _server_instance:
            _server_instance.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()