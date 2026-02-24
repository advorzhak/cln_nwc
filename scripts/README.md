# Scripts Directory

This directory contains helper scripts for development and testing.

## Available Scripts

### `install_cln.sh`

Automated Core Lightning installation script for Ubuntu and macOS.

**Usage:**

```bash
./scripts/install_cln.sh
```

**Options:**

- `CLN_VERSION`: Version to install (default: v24.11)
- `INSTALL_DIR`: Installation directory (default: /usr/local)

**Examples:**

```bash
# Install default version
./scripts/install_cln.sh

# Install specific version
CLN_VERSION=v24.08 ./scripts/install_cln.sh

# Install to custom directory
INSTALL_DIR=/opt/cln ./scripts/install_cln.sh
```

**What it does:**

- Detects your operating system
- Downloads pre-built binaries (Ubuntu) or installs via Homebrew (macOS)
- Verifies the installation
- Provides usage instructions

**Requirements:**

- Ubuntu 20.04+ or macOS
- `jq` and `wget` (installed automatically on Ubuntu)
- `brew` (for macOS)
- Sudo privileges for system-wide installation

See [INSTALL_CLN.md](../INSTALL_CLN.md) for more installation options and troubleshooting.
