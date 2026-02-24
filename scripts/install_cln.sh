#!/bin/bash
# Quick Core Lightning installation script for Ubuntu/Debian
# This script installs Core Lightning v24.11 using pre-built binaries

set -e

CLN_VERSION="${CLN_VERSION:-v24.11}"
INSTALL_DIR="${INSTALL_DIR:-/usr/local}"

echo "🚀 Core Lightning Quick Installer"
echo "=================================="
echo "Version: $CLN_VERSION"
echo "Install directory: $INSTALL_DIR"
echo ""

# Check if already installed
if command -v lightning-cli &> /dev/null; then
    CURRENT_VERSION=$(lightning-cli --version 2>&1 | head -n 1 || echo "unknown")
    echo "✅ Core Lightning is already installed: $CURRENT_VERSION"
    read -p "Do you want to reinstall/upgrade? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
fi

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Check Ubuntu version
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$ID" == "ubuntu" ]]; then
            echo "📦 Detected Ubuntu $VERSION_ID"

            # Check for jq
            if ! command -v jq &> /dev/null; then
                echo "Installing jq..."
                sudo apt-get update -qq
                sudo apt-get install -y jq wget
            fi

            echo "🔍 Finding download URL for Ubuntu binaries..."
            url=$(curl -s https://api.github.com/repos/ElementsProject/lightning/releases/tags/${CLN_VERSION} \
              | jq -r '.assets[] | select(.name | contains("Ubuntu")) | select(.name | contains("22.04") or contains("20.04")) | .browser_download_url' \
              | head -n 1)

            if [ -z "$url" ]; then
                echo "❌ Could not find pre-built binaries for your Ubuntu version."
                echo "Please build from source. See INSTALL_CLN.md for instructions."
                exit 1
            fi

            echo "📥 Downloading $url..."
            TEMP_FILE=$(mktemp)
            wget -q --show-progress "$url" -O "$TEMP_FILE"

            echo "📦 Installing to $INSTALL_DIR..."
            sudo tar -xzf "$TEMP_FILE" -C "$INSTALL_DIR" --strip-components=2

            rm "$TEMP_FILE"

            echo "✅ Core Lightning installed successfully!"

        else
            echo "⚠️  Not Ubuntu. Please install manually. See INSTALL_CLN.md"
            exit 1
        fi
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Detected macOS"
    if command -v brew &> /dev/null; then
        echo "📦 Installing via Homebrew..."
        brew install lightning
        echo "✅ Core Lightning installed successfully!"
    else
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
else
    echo "❌ Unsupported OS: $OSTYPE"
    echo "Please install manually. See INSTALL_CLN.md for instructions."
    exit 1
fi

# Verify installation
echo ""
echo "🔍 Verifying installation..."
if command -v lightning-cli &> /dev/null; then
    INSTALLED_VERSION=$(lightning-cli --version 2>&1 | head -n 1)
    echo "✅ Core Lightning is installed: $INSTALLED_VERSION"
    echo ""
    echo "🎉 Installation complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Run tests: cd tests && npm test"
    echo "  2. Read the docs: https://docs.corelightning.org/"
    echo ""
else
    echo "❌ Installation verification failed. Please check for errors above."
    exit 1
fi
