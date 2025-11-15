#!/bin/bash
set -e

echo "🚀 Setting up SunMonLok (Sunshine Monitor Lock)"
echo "=============================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip &> /dev/null && ! command -v pip3 &> /dev/null; then
    echo "❌ pip is required but not installed."
    exit 1
fi

# Use pip3 if pip is not available, otherwise use pip
PIP_CMD="pip"
if ! command -v pip &> /dev/null; then
    PIP_CMD="pip3"
fi

echo "✅ Using pip: $PIP_CMD"

# Install build dependencies
echo ""
echo "📦 Installing build dependencies..."
$PIP_CMD install --upgrade pip setuptools wheel build

# Install the package in development mode with all dependencies
echo ""
echo "📦 Installing SunMonLok with all dependencies..."
$PIP_CMD install -e ".[client,dev]"

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Usage:"
echo "  Server (on Sunshine host):  python -m sunshine_mmlock"
echo "  Client (on streaming device): python client.py --host <SERVER_IP>"
echo ""
echo "Or use the installed commands:"
echo "  Server: sunmonlok-server"
echo "  Client: sunmonlok-client --host <SERVER_IP>"
echo ""
echo "For development:"
echo "  make run-server                    # Start server"
echo "  HOST=192.168.1.100 make run-client # Start client"
echo ""
echo "📖 See README.md for detailed setup instructions."