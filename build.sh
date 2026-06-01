#!/bin/bash
set -e

echo "Installing dependencies with Python 3.11..."
python3.11 -m pip install --upgrade pip setuptools wheel
python3.11 -m pip install --no-cache-dir -r requirements.txt

echo "✓ Dependencies installed successfully"
