#!/bin/bash
# Start script for OpenSn Doxygen Documentation Validator

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║         OpenSn Doxygen Documentation Validator                           ║"
echo "║                                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "⚠ Virtual environment not found. Running setup..."
    echo ""
    ./setup.sh
    echo ""
fi

# Check if .env exists and has API key
if [ ! -f ".env" ]; then
    echo "✗ Error: .env file not found"
    echo "  Please run: ./setup.sh"
    exit 1
fi

if grep -q "TAMU_API_KEY=your-api-key-here" .env || grep -q "TAMU_API_KEY=$" .env; then
    echo "✗ Error: TAMU API key not configured"
    echo "  Please edit .env and add your TAMU API key"
    exit 1
fi

# Start the app
echo "Starting Doxygen Validator..."
echo "================================"
echo ""
echo "The app will open in your browser at:"
echo "  http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

./venv/bin/streamlit run streamlit_app.py
