#!/bin/bash
set -e

echo "Installing dependencies with Python 3.11..."
python3.11 -m pip install --upgrade pip setuptools wheel --break-system-packages
python3.11 -m pip install --no-cache-dir -r requirements.txt --break-system-packages

echo "✓ Dependencies installed successfully"
