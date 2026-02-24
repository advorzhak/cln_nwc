#!/usr/bin/env python3

"""
Entry point for this plugin
"""

try:
    import json
    import os
    import threading

    from coincurve import PrivateKey
    from pyln.client import Millisatoshi, Plugin

    from lib.nip47 import NIP47URI, URIOptions
    from lib.utils import get_keypair
    from lib.wallet import Wallet
    from utilities.rpc_plugin import plugin
except ImportError as e:
    # TODO: if something isn't installed then disable the plugin
    print("BAD STUFF", f"{e}")


# NWC-optimized Nostr relays - focus on relays with strong NIP47 support
# In test environment with TEST_RELAY=1, use localhost mock relay instead
if os.environ.get("TEST_RELAY"):
    DEFAULT_RELAYS = ["ws://localhost:8001"]
else:
    DEFAULT_RELAYS = [
        "wss://relay.getalby.com/v1",  # Alby - NWC specialist, high reliability
        "wss://relay-nwc.rizful.com",  # Rizful - NIP47 specialized relay
        "wss://relay.coinos.io",  # Coinos - NWC support
    ]


@plugin.init()
def init(options, configuration, plugin: Plugin):
    """initialize the plugin"""
    # TODO: create a Main class that implements Keys, Wallet, Plugin

    privkey, pubkey = get_keypair(plugin)
    plugin.privkey = privkey
    plugin.node_pubkey = pubkey.hex()

    # Initialize the list of plugin pubkeys that the wallet will listen to
    plugin.plugin_pubkeys = set()

    # Load all existing NWC connections and add their pubkeys
    all_connections = NIP47URI.find_all()
    for nwc in all_connections:
        plugin.plugin_pubkeys.add(nwc.pubkey)

    plugin.log(f"Loaded {len(plugin.plugin_pubkeys)} existing NWC connections", "info")

    # create a Wallet instance to listen for incoming nip47 requests
    # Pass all relays for parallel connection and high availability
    wallet = Wallet(relays=DEFAULT_RELAYS)

    # Store wallet in plugin for access from other methods
    plugin.nwc_wallet = wallet

    # start a new thread to listen for nip47 requests
    wallet_thread = threading.Thread(target=wallet.listen_for_nip47_requests)
    wallet_thread.start()

    plugin.log(f"listening for NWC on {len(DEFAULT_RELAYS)} relays", "info")


# https://github.com/nostr-protocol/nips/blob/master/47.md#example-connection-string
@plugin.method("nwc-create")
def create_nwc_uri(plugin: Plugin, expiry_unix: int = None, budget_msat: int = None):
    """Create a new nostr wallet connection"""
    wallet_pubkey = plugin.node_pubkey
    relay_url = DEFAULT_RELAYS[0]  # Use first relay as primary

    # 32-byte hex encoded secret to sign/encrypt
    sk = PrivateKey()
    secret = sk.secret.hex()

    options = URIOptions(
        relay_url=relay_url,
        secret=secret,
        wallet_pubkey=wallet_pubkey,
        expiry_unix=expiry_unix or None,
        budget_msat=Millisatoshi(budget_msat) if budget_msat else None,
    )

    nwc = NIP47URI(options=options)

    data_string = json.dumps(
        {
            "secret": nwc.secret,
            "budget_msat": nwc.budget_msat,
            "expiry_unix": nwc.expiry_unix,
            "spent_msat": Millisatoshi(0),
        }
    )
    plugin.rpc.datastore(key=nwc.datastore_key, string=data_string)

    # Add the new plugin pubkey to the wallet's listening set
    plugin.plugin_pubkeys.add(nwc.pubkey)

    # Request immediate resubscription to ensure the relay picks up the new pubkey
    if hasattr(plugin, "nwc_wallet"):
        plugin.nwc_wallet.request_resubscribe()

    return {"url": nwc.url, "pubkey": nwc.pubkey}


@plugin.method("nwc-list")
def list_nwc_uris(plugin: Plugin):
    """List all nostr wallet connections"""

    all_connections = NIP47URI.find_all()

    rtn = []
    for nwc in all_connections:
        remaining_budget_msat = None

        if nwc.budget_msat:
            try:
                remaining_budget_msat = nwc.budget_msat - nwc.spent_msat
            except (TypeError, ValueError):
                remaining_budget_msat = Millisatoshi(0)

        data = {
            "url": nwc.url,
            "pubkey": nwc.pubkey,
            "expiry_unix": nwc.expiry_unix,
            "remaining_budget_msat": remaining_budget_msat,
        }
        rtn.append(data)

    return {"connections": rtn}


@plugin.method("nwc-revoke")
def revoke_nwc_uri(plugin: Plugin, pubkey: str):
    """Revoke a nostr wallet connection"""
    nwc = NIP47URI.find_unique(pubkey=pubkey)

    if not nwc:
        return {"error": f"No wallet connection found for pubkey {pubkey}"}

    nwc.delete()
    return True


plugin.run()
