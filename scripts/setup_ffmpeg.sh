#!/bin/bash
# Setup script to install FFmpeg on development machines

set -e

echo "Checking for FFmpeg installation..."

if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is already installed:"
    ffmpeg -version | head -1
    exit 0
fi

echo "FFmpeg not found. Installing..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if command -v brew &> /dev/null; then
        echo "Installing FFmpeg via Homebrew..."
        brew install ffmpeg
    else
        echo "Error: Homebrew not found. Please install Homebrew first:"
        echo "  /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        echo "Installing FFmpeg via apt-get..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        echo "Installing FFmpeg via yum..."
        sudo yum install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        echo "Installing FFmpeg via dnf..."
        sudo dnf install -y ffmpeg
    else
        echo "Error: Package manager not found. Please install FFmpeg manually."
        exit 1
    fi
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "Windows detected. Please install FFmpeg manually:"
    echo "1. Download from https://ffmpeg.org/download.html"
    echo "2. Extract and add to PATH"
    echo "Or use chocolatey: choco install ffmpeg"
    exit 1
else
    echo "Unknown OS: $OSTYPE"
    echo "Please install FFmpeg manually from https://ffmpeg.org/download.html"
    exit 1
fi

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "FFmpeg successfully installed:"
    ffmpeg -version | head -1
else
    echo "Error: FFmpeg installation failed or not found in PATH"
    exit 1
fi
