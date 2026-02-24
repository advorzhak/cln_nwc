# Core Lightning (CLN) Installation Guide

This guide provides instructions for installing Core Lightning on different platforms to run the integration tests.

## Quick Install Script (Ubuntu/macOS)

For a quick automated installation on Ubuntu or macOS:

```bash
# Make the script executable (if not already)
chmod +x scripts/install_cln.sh

# Run the installer
./scripts/install_cln.sh

# Or specify a version
CLN_VERSION=v24.11 ./scripts/install_cln.sh
```

This script will:

- Detect your OS and version
- Download and install Core Lightning binaries
- Verify the installation
- Provide next steps

## Quick Check

To check if Core Lightning is already installed:

```bash
lightning-cli --version
```

If the command is found, you're ready to run integration tests!

## Installation Methods

### Option 1: Ubuntu/Debian (Recommended for CI/Testing)

#### Using Pre-built Binaries (Fastest)

```bash
# Get the latest release URL
CLN_VERSION="v24.11"
url=$(curl -s https://api.github.com/repos/ElementsProject/lightning/releases/tags/${CLN_VERSION} \
  | jq '.assets[] | select(.name | contains("22.04")) | .browser_download_url' \
  | tr -d '"')

# Download and install
wget $url
sudo tar -xvf ${url##*/} -C /usr/local --strip-components=2

# Verify installation
lightning-cli --version
```

#### Using APT (Ubuntu 22.04+)

```bash
# Add Core Lightning repository
sudo apt-get install -y software-properties-common
sudo add-apt-repository ppa:lightningnetwork/ppa
sudo apt-get update

# Install Core Lightning
sudo apt-get install -y lightningd

# Verify installation
lightning-cli --version
```

### Option 2: macOS

#### Using Homebrew

```bash
brew install lightning
```

#### Build from Source

```bash
# Install dependencies
brew install autoconf automake libtool gnu-sed gettext libsodium sqlite

# Clone repository
git clone https://github.com/ElementsProject/lightning.git
cd lightning
git checkout v24.11

# Build and install
./configure
make
sudo make install

# Verify installation
lightning-cli --version
```

### Option 3: Building from Source (Any Linux Distribution)

```bash
# Install build dependencies
# For Ubuntu/Debian:
sudo apt-get update
sudo apt-get install -y \
  autoconf automake build-essential git libtool libgmp-dev libsqlite3-dev \
  python3 python3-pip net-tools zlib1g-dev libsodium-dev gettext

# For Fedora/RHEL:
sudo dnf install -y \
  autoconf automake gcc git libtool gmp-devel sqlite-devel \
  python3 python3-pip net-tools zlib-devel libsodium-devel gettext

# Clone and build
git clone https://github.com/ElementsProject/lightning.git
cd lightning
git checkout v24.11
git submodule update --init --recursive

# Configure and build
./configure
make

# Install (optional - or just use from the build directory)
sudo make install

# Verify installation
lightning-cli --version
```

### Option 4: Using Nix (For NixOS users)

If you're using the `flake.nix` in this repository:

```bash
# Enter development shell with all dependencies
nix develop

# Or build directly
nix build
```

### Option 5: Docker (For Testing Only)

```bash
# Pull the official Core Lightning image
docker pull elementsproject/lightningd:latest

# Run in a container
docker run --rm -it elementsproject/lightningd:latest lightning-cli --version
```

## Verifying Installation

After installation, verify that all required binaries are available:

```bash
# Check lightning-cli
which lightning-cli
lightning-cli --version

# Check lightningd (daemon)
which lightningd
lightningd --version
```

## Setting Up for Tests

The integration tests require a running Bitcoin regtest network and Core Lightning nodes. The tests use this path structure:

```bash
.lightning_nodes/
├── l1/  # First Lightning node
└── l2/  # Second Lightning node
```

### Starting Test Environment

The repository includes scripts to help set up the test environment:

```bash
# Start nodes in regtest mode
cd contrib
./startup_regtest.sh
```

## Running Tests with Core Lightning

Once Core Lightning is installed and verified:

```bash
# Set environment variable (if needed)
export CLN_PATH=/path/to/lightning

# Install Python dependencies
source .venv/bin/activate
pip install -r requirements.txt

# Install JavaScript dependencies
cd tests
npm install

# Run Python unit tests (no CLN required)
pytest test_nwc_units.py -v

# Run integration tests (requires CLN)
npm test
```

## Troubleshooting

### Command Not Found: lightning-cli

If `lightning-cli` is not found after installation:

1. **Check installation path:**

   ```bash
   find /usr/local -name lightning-cli 2>/dev/null
   ```

2. **Add to PATH if necessary:**

   ```bash
   export PATH="/usr/local/bin:$PATH"
   # Add to ~/.bashrc or ~/.zshrc to make permanent
   ```

3. **Verify permissions:**
   ```bash
   ls -la $(which lightning-cli)
   # Should be executable
   ```

### Tests Still Failing

The tests will gracefully skip if Core Lightning is not available:

```
⚠️  Core Lightning (lightning-cli) not found. Skipping RPC tests.
   Install Core Lightning to run these tests: https://github.com/ElementsProject/lightning
```

This is expected behavior when CLN is not installed. The Python unit tests will still run successfully.

## CI/CD

The GitHub Actions workflow (`.github/workflows/ci.yml`) automatically:

- Downloads and installs Core Lightning
- Sets up Bitcoin regtest
- Runs both Python unit tests and JavaScript integration tests

The CI tests against:

- Python 3.8 and 3.12
- Node.js 18 and 20
- Core Lightning v24.11
- Bitcoin Core 26.1

## Additional Resources

- [Core Lightning Documentation](https://docs.corelightning.org/)
- [GitHub Repository](https://github.com/ElementsProject/lightning)
- [Installation Guide](https://docs.corelightning.org/docs/installation)
- [Getting Started](https://docs.corelightning.org/docs/getting-started)

## Version Compatibility

This project is tested with:

- **Core Lightning**: v24.11
- **Python**: 3.8, 3.12
- **Node.js**: 18, 20

Check `.github/workflows/main.yml` for the exact versions used in CI.
