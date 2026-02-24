[![main on CLN v24.11](https://github.com/advorzha/cln-nwc/actions/workflows/main.yml/badge.svg?branch=main)](https://github.com/advorzha/cln-nwc/actions/workflows/main.yml)

# Nostr Wallet Connect (NWC) Plugin for Core Lightning

A [Core Lightning](https://github.com/ElementsProject/lightning) plugin
implementing [NIP-47](https://github.com/nostr-protocol/nips/blob/master/47.md)
to enable remote payments via Nostr relays using permissioned connections.

> **⚠️ WARNING:** This is beta software. Use at your own risk. Test thoroughly
> on regtest or testnet before mainnet deployment.

## Features

- 🔐 **Permissioned wallet connections** - Create multiple connections with
  individual budgets and expiry times
- 🔗 **Nostr relay-based** - Communication via Nostr relays, device-agnostic
- 💳 **NIP-47 compliant** - Support for Lightning payments, invoices, and info
- 🏠 **Remote-friendly** - Control your node from anywhere via relays
- ⚡ **Budget controls** - Limit spending per connection
- 🔄 **NIP-04 encryption** - End-to-end encrypted communication

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Mobile App / Web Wallet (NWC Client)                         │
└──────────────────────┬───────────────────────────────────────┘
                       │ (NWC Request - NIP-47, NIP-04 encrypted)
                       ▼
    Multiple Nostr Relays (Parallel connections for HA):
    ┌─────────────────────────────────────────────────────┐
    │ ┌──────────────────┐  ┌──────────────────┐         │
    │ │ relay.getalby   │  │ nos.lol          │  ...    │
    │ │ .com/v1         │  │                  │         │
    │ └────────┬─────────┘  └────────┬─────────┘         │
    │          │                     │                   │
    └──────────┼─────────────────────┼───────────────────┘
               │ (Listens on all)    │
               │ (Publishes to all)  │
               ▼                     ▼
    ┌──────────────────────────────────────────┐
    │  CLN NWC Plugin (Multi-Relay Wallet)     │
    │  ├─ Parallel relay connections           │
    │  ├─ Validates connection & budget        │
    │  ├─ Decrypts request (NIP-04)            │
    │  ├─ Executes payment (lightning-cli)     │
    │  └─ Encrypts response to all relays      │
    └─────────┬──────────────────────────────┘
              │
              ▼
     ┌────────────────────┐
     │ Core Lightning     │
     │ (lightning-rpc)    │
     └────────────────────┘
```

**Key improvements over single relay:**

- Connects to **3 relays simultaneously** for high availability
- Works even if some relays are down
- Client reaches plugin via fastest available relay
- Harder to censor (distributed across relays)

## Installation

### Prerequisites

- Core Lightning v24.02+
- Python 3.8+
- Dependencies: `pyln-client`, `coincurve`, `cryptography`, `websockets`

### Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/advorzha/cln_nwc
   cd cln_nwc
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Update Python path** in [src/nwc.py](./src/nwc.py):

   ```bash
   which python  # Get your Python path
   ```

   Edit the shebang on line 1 to point to your Python executable.

4. **Start the plugin** (choose one method)

   **Option A: Config file** (persistent, recommended)

   ```bash
   # Add to ~/.lightning/config (or your CLN config)
   plugin=/path/to/cln_nwc/src/nwc.py
   ```

   **Option B: Manual start**

   ```bash
   lightning-cli plugin start /path/to/cln_nwc/src/nwc.py
   ```

   **Option C: With lightningd**

   ```bash
   lightningd --plugin=/path/to/cln_nwc/src/nwc.py
   ```

## Using the Plugin

### Creating a Connection

Create a new Nostr Wallet Connect URI with optional budget and expiry:

```bash
# Basic (no limits)
lightning-cli nwc-create

# With budget limit (1M sats = 1,000,000 msats)
lightning-cli nwc-create budget_msat=1000000

# With expiry (Unix timestamp)
lightning-cli nwc-create budget_msat=1000000 expiry_unix=1735689600

# With both
lightning-cli nwc-create budget_msat=500000 expiry_unix=1735689600
```

**Response example:**

```json
{
  "url": "nostr+walletconnect://2f4a1...?relay=wss://relay.getalby.com/v1&secret=abc123...",
  "pubkey": "npub1...2f4a1c65d..."
}
```

Scan the `url` with your mobile wallet or share it with the app you want to
connect.

### Listing Connections

View all active NWC connections:

```bash
lightning-cli nwc-list
```

**Response example:**

```json
{
  "connections": [
    {
      "url": "nostr+walletconnect://...",
      "pubkey": "2f4a1c65d...",
      "expiry_unix": 1735689600,
      "remaining_budget_msat": "950000msat"
    },
    {
      "url": "nostr+walletconnect://...",
      "pubkey": "e3b0c44298...",
      "expiry_unix": null,
      "remaining_budget_msat": null
    }
  ]
}
```

### Revoking a Connection

Revoke and delete a connection:

```bash
lightning-cli nwc-revoke pubkey=2f4a1c65d...
```

Returns `true` on success.

### Understanding Connection Parameters

**URL Structure:**

```
nostr+walletconnect://[WALLET_PUBKEY]?relay=[RELAY_URL]&secret=[SECRET]
```

| Parameter       | Meaning                                   | Example                      |
| --------------- | ----------------------------------------- | ---------------------------- |
| `WALLET_PUBKEY` | Node's Nostr pubkey (from plugin keypair) | `2f4a1c65...`                |
| `RELAY_URL`     | Nostr relay for event routing             | `wss://relay.getalby.com/v1` |
| `SECRET`        | Shared secret for encryption/auth         | `abc123def456...`            |

**Budget Management:**

- Amounts in **millisatoshis (msat)** - 1 sat = 1000 msat
- Budget checked **per request**
- Leftover budget after connection expiry is **lost**
- `remaining_budget_msat` reflects current available funds

**Expiry:**

- Unix timestamp (seconds since epoch)
- Connection becomes invalid after this time
- `null` = no expiry
- Generate: `date +%s` (current) + X seconds (duration)

## Security Considerations

### Connection Security

1. **Budget limits** - Always set conservative budgets per connection
2. **Short expiry** - Use 24h-7d expiration for app keys
3. **One app per key** - Create separate connections for each application
4. **Revoke unused** - Delete connections when no longer needed

### Relay Selection & High Availability

The plugin connects to **multiple relays in parallel** for high availability:

**Default relays (production):**

- `wss://relay.getalby.com/v1` - Alby operated, high reliability
- `wss://relay-nwc.rizful.com` - NIP47-specialized relay
- `wss://relay.coinos.io` - NWC-focused relay

**Test environment:**

When `TEST_RELAY=1` environment variable is set, plugin uses:

- `ws://localhost:8001` - Local mock relay for deterministic testing

**How it works:**

- Plugin connects to **all relays simultaneously** (not just one)
- Listens for requests on **all connections**
- Broadcasts responses to **all available relays**
- Continues operating even if some relays are down
- Better privacy and reliability (don't depend on single relay)

**Benefits:**

- ✅ **High availability** - Works even if some relays are down
- ✅ **Faster** - Client can reach you via fastest relay
- ✅ **Redundancy** - Not a single point of failure
- ✅ **Privacy** - Harder to censor (you're on many relays)

**Customizing relays:**
Edit `DEFAULT_RELAYS` in [src/nwc.py](./src/nwc.py) to use different relays:

```python
DEFAULT_RELAYS = [
    "wss://your-relay.com",
    "wss://backup-relay.com",
]
```

**Test environment:**

For local testing with a mock Nostr relay (no real relay needed):

```bash
export TEST_RELAY=1
lightning-cli plugin start /path/to/cln_nwc/src/nwc.py
```

This uses a mock relay at `localhost:8001` for deterministic testing without relay dependencies.

**Considerations:**

- **Privacy** - Relays can see connection metadata (not payments)
- **Trust** - Only add relays you trust
- **Performance** - More relays = slightly more bandwidth
- **Public relays** - Most relays are public, anyone can host one

### Encryption

- **NIP-04 encryption** - All requests/responses encrypted with
  [libsecp256k1](https://github.com/bitcoin-core/secp256k1)
- **No plaintext** - Sensitive data never sent unencrypted over relay
- **Replay protection** - Each connection has unique secret

### Best Practices

```bash
# ✅ Good
lightning-cli nwc-create budget_msat=100000 expiry_unix=$(date +%s)+86400
# Creates 1000 sat limit, expires in 24 hours

# ✅ Good - one connection per app
lightning-cli nwc-create  # For mobile wallet app
lightning-cli nwc-create  # For different app

# ❌ Bad - unlimited budget
lightning-cli nwc-create

# ❌ Bad - very long expiry
lightning-cli nwc-create expiry_unix=9999999999

# ❌ Bad - sharing one connection across apps
# Share same URI to multiple apps (cross-linked spending)
```

## Running Tests

### Python Unit Tests

```bash
# All tests
pytest tests/test_nwc_units.py -v

# Specific test class
pytest tests/test_nwc_units.py::TestUtils -v

# With coverage
pytest tests/test_nwc_units.py --cov=src/lib --cov-report=html
```

Test coverage includes:

- ✅ Utility functions (keypair generation)
- ✅ NIP04 encryption/decryption
- ✅ NIP47 URI parsing and validation
- ✅ Budget and expiry calculations
- ✅ Error handling and edge cases

### Integration Tests

**Setup:**

```bash
# Terminal 1: Start regtest environment
source ./contrib/startup_regtest.sh
start_ln

# Terminal 2: Start plugin
./contrib/restart_plugin.sh 1

# Terminal 3: Run tests
cd tests
npm install
npm test
```

Tests validate:

- ✅ Pay invoice (BOLT11)
- ✅ Pay keysend
- ✅ Create invoice
- ✅ Get node info
- ✅ Get balance
- ✅ Look up invoices
- ✅ List transactions

### Code Quality

All commits are checked with pre-commit hooks:

```bash
# Install hooks
pre-commit install

# Run all checks
pre-commit run --all-files

# Specific check
pre-commit run flake8 --all-files
```

Checks include:

- **Python:** black, isort, flake8
- **JavaScript:** prettier
- **YAML:** yamllint
- **General:** trailing whitespace, merge conflicts

## Troubleshooting

### Plugin won't start

**Issue:** `Error: Plugin exited before initialization`

**Solutions:**

- Check Python path: `head -1 src/nwc.py`
- Verify dependencies: `pip list | grep -E 'pyln|coincurve|cryptography|websockets'`
- Check CLN logs: `lightning-cli getlog info`
- Validate syntax: `python -m py_compile src/nwc.py`

### Connection not working

**Issue:** App can't send payments

**Solutions:**

- Verify relay is accessible: `curl https://relay.getalby.com/v1`
- Check connection active: `lightning-cli nwc-list`
- Verify not expired: `date +%s` vs `expiry_unix`
- Check budget: `remaining_budget_msat` > 0
- Check logs: `lightning-cli getlog debug | grep nwc`

### Relay issues

**Issue:** "Relay connection closed" errors or slow transactions

**Solutions:**

- Plugin automatically connects to 6 popular relays for redundancy
- If one relay is down, others keep working
- Check relay status on [nostr.watch](https://nostr.watch)
- Try running your own relay: [strfry](https://github.com/hoytech/strfry)
- Add faster/more reliable relays by editing `DEFAULT_RELAYS` in
  [src/nwc.py](./src/nwc.py)
- Monitor plugin logs: `lightning-cli getlog debug | grep nwc`
- Plugin auto-reconnects on failures

### High fees

**Issue:** Payments being rejected for fee reasons

**Solutions:**

- Budget includes routing fees (not just payment amount)
- Use larger budget for high-fee conditions
- Monitor fee rate: `lightning-cli feerates perkb`
- Consider off-chain solutions (HTLCs, etc.)

## Connection Architecture

The plugin uses a **per-connection pubkey model** for improved security and flexibility:

### Plugin Pubkeys vs Node Pubkey

- **Node pubkey** (`plugin.node_pubkey`): The Lightning node's Nostr identity, derived from HSM secret
- **Plugin pubkeys** (`plugin.plugin_pubkeys`): Set of pubkeys for each NWC connection, derived from connection secrets
- **Dynamic subscriptions**: Plugin subscribes to all active connection pubkeys on relays

### Connection Lifecycle

1. **Create** - `lightning-cli nwc-create` generates new secret → unique plugin pubkey
2. **Subscribe** - Plugin adds pubkey to listening set, resubscribes to relays
3. **Handle requests** - Relay sends events to plugin pubkey → plugin validates → executes payment
4. **Revoke** - `lightning-cli nwc-revoke` removes pubkey from listening set

Each connection is isolated with its own budget, expiry, and pubkey.

## Development

See [DEVELOPMENT.md](./DEVELOPMENT.md) for:

- Local development setup (with/without Nix)
- Contributing workflow
- Code style and linting
- Debugging techniques
- Project architecture

## API Reference

### Commands

#### `nwc-create [budget_msat] [expiry_unix]`

Create new NWC connection.

**Parameters:**

- `budget_msat` (optional): Max spending in millisatoshis
- `expiry_unix` (optional): Unix timestamp expiration

**Returns:**

```json
{
  "url": "nostr+walletconnect://...",
  "pubkey": "2f4a1c65d..."
}
```

#### `nwc-list`

List all active connections.

**Returns:**

```json
{
  "connections": [
    {
      "url": "nostr+walletconnect://...",
      "pubkey": "2f4a1c65d...",
      "expiry_unix": 1735689600,
      "remaining_budget_msat": "950000msat"
    }
  ]
}
```

#### `nwc-revoke pubkey=<pubkey>`

Revoke/delete a connection.

**Parameters:**

- `pubkey`: Connection pubkey to revoke

**Returns:**

```json
true
```

## Performance

### Scalability

- **Connections:** Tested with 100+ concurrent connections
- **Throughput:** Up to 1 request/sec per connection
- **Latency:** Relay-dependent (typically 1-5 seconds)

### Optimization Tips

1. **Batching** - Group multiple payments if possible
2. **Relay choice** - Use fast, reliable relay
3. **Network** - Ensure low-latency connection to relay
4. **Budget size** - Smaller budgets = faster validation

## Known Limitations

See [NIP-47 Supported Methods](#nip-47-supported-methods) for
implementation status.

**Major limitations:**

- ❌ `multi_pay_invoice` - Batch payments not implemented
- ❌ `multi_pay_keysend` - Batch keysend not implemented
- ⚠️ Description hash - `make_invoice` doesn't set hash
- ⚠️ Preimage verification - Request preimage field ignored

## Related Projects

- [Alby](https://getalby.com/) - Mobile NWC client
- [Primal](https://primal.net/) - Web-based Bitcoin nostr apps
- [Minibits](https://minibits.cash/) - Mobile Cashu wallet
- [cln-nip47](https://github.com/daywalker90/cln-nip47) - Alternative
  implementation (now preferred by Core Lightning)

## References

- [NIP-47 Spec](https://github.com/nostr-protocol/nips/blob/master/47.md) -
  Wallet Connect specification
- [NIP-04 Spec](https://github.com/nostr-protocol/nips/blob/master/04.md) -
  Encryption specification
- [Core Lightning Plugins](https://docs.corelightning.org/docs/plugins/) - CLN
  plugin documentation
- [Nostr Protocol](https://nostr.com/) - Decentralized protocol

## Contributing

Contributions welcome! See [DEVELOPMENT.md](./DEVELOPMENT.md) for setup and
guidelines.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/xyz`)
3. Add tests for new functionality
4. Ensure all tests pass (`pytest` + `npm test`)
5. Run code quality checks (`pre-commit run --all-files`)
6. Submit pull request with clear description

## License

MIT License - see [LICENSE](./LICENSE) for details

## Disclaimer

This software is provided **as-is** without warranty. Use on mainnet at your
own risk. Always test on regtest/testnet first.

Don't expose your node to the internet unnecessarily. Use proper network
security measures (firewall, VPN, etc.).

## NIP-47 Supported Methods

| Method                | Status       | Notes                              |
| --------------------- | ------------ | ---------------------------------- |
| **get_info**          | ✅ Full      | `block_hash` not supported         |
| **pay_invoice**       | ✅ Full      | Pay BOLT11 invoices                |
| **pay_keysend**       | ⚠️ Partial   | Preimage/TLV records unsupported   |
| **make_invoice**      | ⚠️ Partial   | Description hash unsupported       |
| **get_balance**       | ✅ Full      | Returns on-chain + channel balance |
| **lookup_invoice**    | ✅ Full      | Query invoice status               |
| **list_transactions** | ✅ Full      | List past transactions             |
| **multi_pay_invoice** | ❌ Not impl. | Batch payments not supported       |
| **multi_pay_keysend** | ❌ Not impl. | Batch keysend not supported        |
| **Info event**        | ✅ Full      | NIP-47 capability advertisement    |
| **Expiration tag**    | ❌ Not impl. | Request expiry not validated       |

**Response metadata limitations:**

- `make_invoice`: Missing description, description_hash, preimage, fees_paid, metadata
- No confirmation numbers in responses
- Limited payment metadata returned
