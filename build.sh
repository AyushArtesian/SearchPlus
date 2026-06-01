#!/bin/bash
set -e

echo "Installing Python 3.11 venv..."
apt-get update
apt-get install -y python3.11-venv

echo "Creating virtual environment..."
python3.11 -m venv /opt/render/project/venv

echo "Installing dependencies..."
/opt/render/project/venv/bin/pip install --upgrade pip setuptools wheel
/opt/render/project/venv/bin/pip install --no-cache-dir -r requirements.txt

echo "✓ Dependencies installed successfully"
