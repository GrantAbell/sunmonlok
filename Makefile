# Makefile for sunmonlok project

.PHONY: help install install-dev install-client clean test lint format run-server run-client build dist upload-test upload-prod

# Default target
help:
	@echo "Available commands:"
	@echo "  install         - Install the server package in development mode"
	@echo "  install-dev     - Install with development dependencies"
	@echo "  install-client  - Install client dependencies"
	@echo "  install-all     - Install everything (server + client + dev)"
	@echo "  clean           - Clean build artifacts"
	@echo "  test            - Run tests"
	@echo "  lint            - Run linting checks"
	@echo "  format          - Format code with black"
	@echo "  run-server      - Run the server"
	@echo "  run-client      - Run the client (specify HOST=ip)"
	@echo "  build           - Build distribution packages"
	@echo "  dist            - Same as build"
	@echo ""
	@echo "Quick start:"
	@echo "  make install-all    # Install everything"
	@echo "  make run-server     # Start the server"
	@echo "  HOST=192.168.1.100 make run-client  # Connect client to server"

# Installation commands
install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

install-client:
	pip install -e ".[client]"

install-all: install install-client install-dev

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Development commands
test:
	python -m pytest

lint:
	flake8 sunshine_mmlock/ client.py
	mypy sunshine_mmlock/ client.py

format:
	black sunshine_mmlock/ client.py test_*.py

# Run commands
run-server:
	python -m sunshine_mmlock

run-client:
	@if [ -z "$(HOST)" ]; then \
		echo "Usage: HOST=<server_ip> make run-client"; \
		echo "Example: HOST=192.168.1.100 make run-client"; \
		exit 1; \
	fi
	python client.py --host $(HOST)

# Build and distribution
build dist:
	python -m build

upload-test: build
	python -m twine upload --repository testpypi dist/*

upload-prod: build
	python -m twine upload dist/*

# Development shortcuts
dev-setup: clean install-all
	@echo "Development environment set up successfully!"
	@echo "Run 'make run-server' to start the server"
	@echo "Run 'HOST=<server-ip> make run-client' to start the client"