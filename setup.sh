#!/bin/bash
# Setup script for OpenSn Doxygen Documentation Validator

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                          ║"
echo "║         OpenSn Doxygen Documentation Validator - Setup                  ║"
echo "║                                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "1. Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo "   ✓ Python $PYTHON_VERSION found"
else
    echo "   ✗ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

# Create virtual environment
echo ""
echo "2. Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   ℹ Virtual environment already exists"
else
    python3 -m venv venv
    echo "   ✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "3. Activating virtual environment..."
source venv/bin/activate
echo "   ✓ Virtual environment activated"

# Upgrade pip
echo ""
echo "4. Upgrading pip..."
pip install --upgrade pip -q
echo "   ✓ Pip upgraded"

# Install dependencies
echo ""
echo "5. Installing dependencies..."
pip install -r requirements.txt -q
echo "   ✓ Dependencies installed"

# Check for .env file
echo ""
echo "6. Checking configuration..."
if [ -f ".env" ]; then
    if grep -q "TAMU_API_KEY=your-api-key-here" .env || grep -q "TAMU_API_KEY=$" .env; then
        echo "   ⚠ WARNING: Please add your TAMU API key to .env file"
        echo "   Edit .env and set: TAMU_API_KEY=your-actual-key"
    else
        echo "   ✓ Configuration file found"
    fi
else
    echo "   ℹ Creating .env file..."
    cat > .env << 'EOF'
# TAMU AI Chat API Key
TAMU_API_KEY=your-api-key-here
TAMU_CHAT_API_KEY=your-api-key-here

# Optional: Groq API Key (fallback)
# GROQ_API_KEY=your-groq-key-here

# Optional: OpenAI API Key (fallback)
# OPENAI_API_KEY=your-openai-key-here
EOF
    echo "   ✓ .env file created"
    echo "   ⚠ Please edit .env and add your TAMU API key"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                         Setup Complete!                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your TAMU API key (if not done already)"
echo "  2. Run: ./start.sh"
echo ""
