# Test Infrastructure Guide

## Test Types

This project has two distinct types of tests:

### 1. Python Unit Tests (✅ Completed - Python 3.8 & 3.12 Compatible)

- **Location**: `tests/test_nwc_units.py`
- **Purpose**: Unit tests for Python cryptography, NIP47 handling, and utility functions
- **Requirements**: None (all dependencies in `requirements.txt`)
- **Status**: ✅ Compatible with Python 3.8 and 3.12+

**Run Python tests:**

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/test_nwc_units.py -v
```

### 2. JavaScript Integration Tests (⚠️ Infrastructure Dependencies)

- **Location**: `tests/nwc.test.js`, `tests/rpc.test.js`
- **Purpose**: Integration tests with actual Core Lightning and Nostr relay
- **Requirements**:
  - Core Lightning installed and running
  - Nostr relay accessible at `wss://relay.getalby.com/v1` (or configured relay)
  - `npm install` in `tests/` directory

**Run JavaScript tests:**

```bash
cd tests
npm install
npm test
```

## Infrastructure Requirements for JavaScript Tests

The JavaScript integration tests require a full regtest environment with Bitcoin and Lightning nodes running.

### Automated Setup (CI and Local Testing)

For CI environments or quick local testing, use the automated setup scripts:

```bash
# Setup regtest environment (starts bitcoind and 2 CLN nodes)
bash contrib/ci_setup_regtest.sh

# Run tests
cd tests
npm test

# Cleanup when done
bash contrib/ci_cleanup_regtest.sh
```

**What the setup script does:**

1. Starts bitcoind in regtest mode
2. Creates a default wallet and mines 101 blocks
3. Starts 2 Core Lightning nodes (l1 and l2) with NWC plugin loaded
4. Uses a wrapper script to ensure plugin has access to Python virtual environment
5. Exports environment variables for test configuration

**Note:** The NWC plugin is loaded by default using `contrib/plugin_wrapper.sh` which activates the Python virtual environment. To skip loading the plugin, set `LOAD_NWC_PLUGIN=false` before running the setup script.

### Manual Setup (Development)

For development and debugging, you can use the interactive startup script:

```bash
# Source the startup script to get helper functions
source contrib/startup_regtest.sh

# Start regtest environment with 2 nodes
start_ln 2

# Helper commands are now available:
# l1-cli getinfo
# l2-cli getinfo
# bt-cli getblockchaininfo
```

### 1. Core Lightning

The RPC tests require Core Lightning to be installed and running:

```bash
# Install Core Lightning (check documentation for your OS)
# Then ensure lightning-cli is in PATH
which lightning-cli  # Should find the executable
```

### 2. Nostr Relay

The NWC provider tests require a working Nostr relay. The configured relay is `wss://relay.getalby.com/v1`.

If the relay is unavailable, tests will timeout. The tests will:

- Attempt connection with a 5-second timeout (15 seconds if `SLOW_MACHINE=1`)
- Log a warning if connection fails
- Continue with available tests

### 3. Environment Configuration

For local testing, you can configure the test environment with these environment variables:

```bash
# Optional: Set Core Lightning path (for building from source)
export CLN_PATH=/path/to/your/core/lightning

# Optional: Set lightning directories for test nodes
export LIGHTNING_DIR_L1=/path/to/.lightning_nodes/l1
export LIGHTNING_DIR_L2=/path/to/.lightning_nodes/l2

# Optional: Enable extended timeouts for slow machines
export SLOW_MACHINE=1
```

**Default Behavior:**

- If `LIGHTNING_DIR_L1` or `LIGHTNING_DIR_L2` are not set, tests will use `.lightning_nodes/l1` and `.lightning_nodes/l2` respectively
- If `SLOW_MACHINE=1` is set, all test timeouts are tripled (useful for CI environments or slower hardware)
- Tests will automatically detect `lightning-cli` from your system PATH

## CI/CD Testing

The GitHub Actions CI workflow automatically:

1. **Builds dependencies**: Installs Bitcoin, Core Lightning, Python, and Node.js
2. **Runs Python unit tests**: These always run and must pass
3. **Sets up regtest environment**: Uses `contrib/ci_setup_regtest.sh` to start Bitcoin and Lightning nodes
4. **Runs JavaScript integration tests**: Tests against the live regtest environment
5. **Cleans up**: Uses `contrib/ci_cleanup_regtest.sh` to stop all services

**CI Environment Variables:**

- `SLOW_MACHINE=1`: Enables extended timeouts (90s instead of 30s)
- `TEST_DEBUG=1`: Enables verbose test output
- `LIGHTNING_DIR_L1` / `LIGHTNING_DIR_L2`: Set by setup script to point to test nodes

The CI setup ensures a clean, reproducible environment for each test run.

## Test Results Summary

### Python Tests Status

- ✅ `TestUtils` - All passing
- ✅ `TestNIP04Encryption` - All passing
- ✅ `TestNIP47URI` - All passing
- ✅ `TestNWCErrors` - All passing

**Python Compatibility**: Both 3.8 and 3.12+

### JavaScript Tests Status

- ⚠️ Require Core Lightning and Nostr relay infrastructure
- ✅ WebSocket import fixed (using `ws` package)
- ✅ Jest cleanup improved to prevent hanging processes
- ✅ Connection timeout handling added (5-second timeout)

## Key Changes for Compatibility

### Python 3.8 & 3.12 Compatibility

1. Added `from __future__ import annotations` to all module files
2. Used `Optional[Type]` notation instead of `Type | None`
3. Created `pyproject.toml` with `requires-python = ">=3.8,<4"`
4. Fixed type hints in dataclasses and function signatures

### JavaScript Test Improvements

1. Replaced non-existent `websocket-polyfill` with standard `ws` package

## Mock Relay Infrastructure

For reliable, deterministic testing without external relay dependencies, the test suite includes a **mock Nostr relay** written in Python.

### How the Mock Relay Works

**File:** `tests/mock_relay.py`

- Listens on `localhost:8001` (WebSocket server)
- Implements minimal NIP-01 protocol (events, subscriptions, filters)
- Stores events in memory (not persistent)
- Handles multiple concurrent client connections
- Provides detailed logging for debugging

**Activated by:** Setting `TEST_RELAY=1` environment variable

When enabled:

```bash
TEST_RELAY=1 lightning-cli plugin start /path/to/nwc.py
```

The plugin automatically uses `ws://localhost:8001` instead of real Nostr relays.

### Benefits of Mock Relay

✅ **Deterministic** - Same test inputs always produce same outputs
✅ **Fast** - No network latency (localhost connections)
✅ **Offline** - Tests run without internet access
✅ **Isolated** - Test events don't leak to public relays
✅ **Reproducible** - CI/CD consistency across all environments
✅ **Debuggable** - Detailed logging for test troubleshooting

### Mock Relay Startup (Jest Setup)

**File:** `tests/jest.setup.js`

Before integration tests run:

1. Detects Python executable (from venv, virtualenv, GitHub Actions, system paths)
2. Spawns mock relay server as child process
3. Waits for relay to listen on port 8001
4. Passes connection info to test environment
5. Stops relay after tests complete

This ensures:

- Relay is always available when tests start
- Tests don't interfere with each other
- Cleanup happens automatically

2. Added `jest.config.js` for proper configuration
3. Added `jest.setup.js` for graceful cleanup
4. Added timeout handling for NWC provider connection
5. Improved error handling in utility functions

## Continuous Integration

For CI/CD pipelines:

**Python Tests** (should always pass):

```bash
cd /home/advorzha/dev/advorzhak/cln_nwc
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_nwc_units.py -v
```

**JavaScript Tests** (optional - requires infrastructure):

```bash
cd /home/advorzha/dev/advorzhak/cln_nwc/tests
npm install
npm test  # Will timeout gracefully if infrastructure unavailable
```

## Troubleshooting

### Python Tests Fail

- Ensure Python >= 3.8
- Check all dependencies: `pip install -r requirements.txt`
- Verify syntax: `python -m py_compile tests/test_nwc_units.py`

### JavaScript Tests Timeout

- **Check Nostr relay**: Test connection to `wss://relay.getalby.com/v1`
- **Check Core Lightning**: Verify `lightning-cli` is installed: `which lightning-cli`
- **Network issues**: May need firewall/proxy configuration for WebSocket connections
- **Tests will continue**: Connection timeout is gracefully handled (5-second timeout)

### Jest Process Won't Exit

- Added `forceExit: true` in `jest.config.js` to force process exit after tests
- Improved cleanup in `jest.setup.js` to close WebSocket connections

## Future Improvements

1. **Mock Infrastructure Tests**: Create unit tests that don't require external services
2. **Docker Compose**: Set up Docker Compose for complete test environment
3. **Separate Test Suites**: Split unit and integration tests into different configurations
4. **Speed Improvements**: Cache dependencies and reduce test timeout where safe
