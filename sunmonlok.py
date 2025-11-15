#!/usr/bin/env python3
"""
SunMonLok Launcher - Universal entry point for both server and client.

This script automatically detects whether to run the server or client
based on the command line arguments provided.

Usage:
    sunmonlok                    # Run server (default)
    sunmonlok server             # Run server explicitly  
    sunmonlok client --host IP   # Run client
    sunmonlok --help             # Show help
"""

import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(
        description="SunMonLok - Sunshine Monitor Lock System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Run server
  %(prog)s server                    # Run server explicitly
  %(prog)s client --host 192.168.1.100  # Run client
        """
    )
    
    subparsers = parser.add_subparsers(dest='mode', help='Run mode')
    
    # Server subcommand
    server_parser = subparsers.add_parser('server', help='Run the server (monitor detection)')
    
    # Client subcommand  
    client_parser = subparsers.add_parser('client', help='Run the client (keyboard shortcuts)')
    client_parser.add_argument('--host', required=True, help='Server IP address to connect to')
    client_parser.add_argument('--port', type=int, default=9876, help='Server port (default: 9876)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to server if no mode specified
    if args.mode is None:
        args.mode = 'server'
    
    try:
        if args.mode == 'server':
            print("🖥️  Starting SunMonLok Server...")
            # Run the server module
            subprocess.run([sys.executable, '-m', 'sunshine_mmlock'], check=True)
            
        elif args.mode == 'client':
            print(f"🖱️  Starting SunMonLok Client (connecting to {args.host}:{args.port})...")
            # Run the client script
            client_args = [sys.executable, 'client.py', '--host', args.host, '--port', str(args.port)]
            subprocess.run(client_args, check=True)
            
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: Command failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())