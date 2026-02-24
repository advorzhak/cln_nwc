# Development Guide

This guide covers setting up a development environment for the CLN NWC plugin.

## Quick Start

### Prerequisites

- Nix with experimental features enabled (recommended)
- Python 3.8+
- Node.js 18+
- Bitcoin Core 26.1+
- Core Lightning v24.11+ (see [INSTALL_CLN.md](INSTALL_CLN.md) for installation instructions)

### Setup with Nix

```bash
# Clone and enter the dev environment
git clone https://github.com/advorzha/cln_nwc
cd cln_nwc
nix develop
```

This provides all dependencies including Bitcoin, CLN, and Python packages.

### Setup without Nix

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node dependencies for tests
cd tests
npm install
cd ..

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

## Code Quality

### Pre-commit Hooks

Pre-commit hooks automatically check code before commits. Install them:

```bash
pre-commit install
```

Hooks run automatically on `git commit`. To run manually:

```bash
# All hooks on all files
pre-commit run --all-files

# Specific hook
pre-commit run black --all-files

# Skip hooks on commit
git commit --no-verify
```

Configured checks:

- **black**: Python formatting (88 char line limit)
- **isort**: Python import organization
- **flake8**: Python linting
- **bandit**: Python security scanning
- **prettier**: JavaScript/YAML/JSON formatting
- **nixpkgs-fmt**: Nix file formatting
- **yamllint**: YAML validation
- **markdownlint**: Markdown linting
- **trailing-whitespace**: Remove trailing whitespace
- **detect-private-key**: Scan for secrets

### Running Tests Locally

#### Python Unit Tests

```bash
# From project root
pytest tests/test_nwc_units.py -v

# With coverage
pytest tests/test_nwc_units.py --cov=src/lib
```

Test coverage:

- ✅ Utility functions (pubkey derivation, keypair generation)
- ✅ NIP04 encryption/decryption (ECDH, AES)
- ✅ NIP47 URI parsing and validation
- ✅ Budget and expiry calculations
- ✅ Error handling and exceptions

#### Integration Tests

Setup regtest environment:

```bash
source ./contrib/startup_regtest.sh
start_ln  # Start 2 test nodes

# In another terminal
./contrib/restart_plugin.sh 1  # Start plugin on node 1
```

Run integration tests:

```bash
cd tests
npm test
```

Tests check:

- ✅ NIP47 method implementations
- ✅ Invoice payment (pay_invoice, pay_keysend)
- ✅ Invoice creation (make_invoice)
- ✅ Node info (get_info)
- ✅ Balance queries (get_balance)

## Project Structure

```
cln_nwc/
├── .github/workflows/          # GitHub Actions CI
│   ├── ci.yml                  # Reusable test workflow
│   └── main.yml                # Main branch workflow
├── .pre-commit-config.yaml     # Pre-commit hooks config
├── src/
│   ├── nwc.py                  # Plugin entry point
│   ├── lib/
│   │   ├── event.py            # Nostr event classes
│   │   ├── nip04.py            # NIP04 encryption
│   │   ├── nip47.py            # NIP47 NWC protocol
│   │   ├── utils.py            # Utility functions
│   │   └── wallet.py           # Relay connection & event handling
│   └── utilities/
│       └── rpc_plugin.py       # CLN RPC interface
├── tests/
│   ├── nwc.test.js            # Integration tests
│   ├── test_nwc_units.py      # Unit tests
│   ├── utils.js               # Test utilities
│   ├── rpc.test.js            # RPC tests
│   ├── mock_relay.py          # Mock Nostr relay for testing
│   ├── jest.config.js         # Jest configuration
│   ├── jest.setup.js          # Jest setup with Python relay
│   ├── package.json           # NPM dependencies
│   └── .test_env              # Test environment variables
├── contrib/
│   ├── startup_regtest.sh     # Regtest setup (interactive)
│   ├── ci_setup_regtest.sh    # Regtest setup (automated CI)
│   ├── ci_cleanup_regtest.sh  # Regtest cleanup
│   ├── plugin_wrapper.sh      # Plugin startup wrapper
│   └── restart_plugin.sh      # Plugin restart script
├── scripts/
│   └── install_cln.sh         # Core Lightning installer
├── flake.nix                   # Nix dev environment
├── pyproject.toml              # Python project config
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
└── README.md                   # Main documentation
```

## Making Changes

### Development Workflow

1. **Create a branch**

   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes**

   - Edit files in `src/lib/` for core logic
   - Update `tests/` with new tests
   - Follow code style (pre-commit will help)

3. **Run tests locally**

   ```bash
   # Unit tests
   pytest tests/test_nwc_units.py -v

   # Integration tests (with regtest running)
   cd tests && npm test
   ```

4. **Commit with pre-commit checks**

   ```bash
   git add .
   git commit -m "feat: description of change"
   # Pre-commit hooks run automatically
   ```

5. **Push and create PR**

   ```bash
   git push origin feature/my-feature
   ```

### Code Style

Code style is enforced by pre-commit hooks:

- **Python**: PEP 8 via black, isort, flake8
- **JavaScript**: Prettier defaults
- **YAML/Markdown**: Standard formatting

Run formatting before committing:

```bash
black src/
isort src/
prettier --write tests/
```

## Key Modules

### `src/lib/utils.py`

Utility functions for keypair management:

- `get_hex_pubkey()` - Derive x-only pubkey from private key
- `get_keypair()` - Get or generate plugin keypair

### `src/lib/nip04.py`

NIP04 encryption implementation:

- `encrypt()` - Encrypt data to a recipient's pubkey
- `decrypt()` - Decrypt data with your private key
- `get_ecdh_key()` - ECDH key exchange
- `process_aes()` - AES-256-CBC encryption/decryption

### `src/lib/nip47.py`

NIP47 NWC protocol:

- `NIP47URI` - Wallet connection URI (creation, parsing, validation)
- `NIP47Request` - Incoming NWC requests
- `NIP47Response` - NWC responses
- Error classes for request validation

### `src/lib/wallet.py`

Relay connection and event handling:

- `Wallet` - Connects to relay, subscribes to events, processes requests
- `listen_for_nip47_requests()` - Async event loop
- `on_event()` - Request processing

## Common Tasks

### Adding a New NWC Method

1. Add parameter schema to `NIP47RequestHandler.method_params_schema` in `src/lib/nip47.py`
2. Implement handler in `NIP47RequestHandler`
3. Add test in `tests/nwc.test.js`
4. Add error handling for edge cases

### Adding Unit Tests

1. Tests go in `tests/test_nwc_units.py`
2. Use pytest fixtures and assertions
3. Test both success and error cases
4. Run: `pytest tests/test_nwc_units.py -v`

### Debugging

Enable debug logging in CLN:

```bash
lightningd --log-level=debug
```

Check plugin logs:

```bash
lightning-cli plugin_list
```

## Continuous Integration

GitHub Actions runs on:

- Push to main
- Pull requests
- Scheduled (can be configured)

CI runs:

1. Python unit tests (pytest)
2. Integration tests (Node.js with real CLN + relay)
3. Multiple Python versions (3.8, 3.12)
4. Multiple Node.js versions (18, 20)

See `.github/workflows/` for configuration.

## Release Checklist

- [ ] All tests passing
- [ ] Code reviewed
- [ ] CHANGELOG updated
- [ ] Version bumped in setup files
- [ ] Git tag created
- [ ] GitHub release created

## Resources

- [NIP47 Specification](https://github.com/nostr-protocol/nips/blob/master/47.md)
- [NIP04 Encryption](https://github.com/nostr-protocol/nips/blob/master/04.md)
- [Core Lightning Plugin API](https://docs.corelightning.org/docs/plugins/)
- [Pre-commit Framework](https://pre-commit.com/)

## Getting Help

- Check existing issues/PRs
- Review NIP specifications
- Check CLN plugin documentation
- Ask in Lightning Dev Kit community

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass and code is formatted
5. Submit a pull request with a clear description
