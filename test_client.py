#!/usr/bin/env python3
"""
Quick test to verify the client/server communication works.

This simulates a client connecting and receiving monitor IDs.
"""

import socket
import time
from mlock.protocol import receive_monitor_switch

def test_client(host='localhost', port=9876):
    """Test connecting to server and receiving monitor IDs."""
    print(f"Connecting to {host}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        print("✓ Connected to server")
        
        print("Waiting for monitor ID updates (move your mouse between monitors)...")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                monitor_id = receive_monitor_switch(sock, timeout=5.0)
                print(f"Received: Monitor {monitor_id} → Would press Ctrl+Option+Command+Shift+F{monitor_id + 1}")
            except TimeoutError:
                print(".", end="", flush=True)
            except ConnectionError as e:
                print(f"\n✗ Connection lost: {e}")
                break
                
    except KeyboardInterrupt:
        print("\n\nStopping test...")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        try:
            sock.close()
        except:
            pass

if __name__ == '__main__':
    import sys
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    test_client(host)
