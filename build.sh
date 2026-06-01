#!/bin/bash
set -e

echo "Creating virtual environment..."
python3.11 -m venv /opt/render/project/venv

echo "Installing dependencies..."
/opt/render/project/venv/bin/pip install --upgrade pip setuptools wheel
/opt/render/project/venv/bin/pip install --no-cache-dir -r requirements.txt

echo "✓ Dependencies installed successfully"
