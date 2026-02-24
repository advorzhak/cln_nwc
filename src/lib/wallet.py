"""Main wallet functionality"""

import asyncio
import concurrent.futures
import json
import uuid

import websockets

from utilities.rpc_plugin import plugin

from .nip47 import InfoEvent, NIP47Request, NIP47Response


class Wallet:
    """Connect to multiple relays in parallel, subscribe to filters, and handle events"""  # noqa: E501

    def __init__(self, relays: list):
        self.relays = relays
        self.connections = {}  # Map of relay_url -> websocket
        self.subscriptions = {}  # Map of sub_id -> filter
        self._first_time_connected = True
        self._listen = None
        self._running = False
        self._loop = None  # Store event loop for cross-thread communication
        self._pending_resubscribe = False  # Flag to trigger immediate resubscription

    def listen_for_nip47_requests(self):
        """start the asyncio event loop"""
        asyncio.run(self.run())

    async def run(self):
        """Connect to all relays, subscribe, listen for incoming events."""
        self._listen = True
        self._loop = asyncio.get_event_loop()  # Store loop for cross-thread access
        reconnect_delay = 5  # seconds
        while self._listen:
            try:
                # Connect to all relays in parallel
                await self.connect_all()
                if self._first_time_connected:
                    await self.send_info_event()  # publish kind 13194 info event
                    self._first_time_connected = False
                # Subscribe to nwc requests for all plugin pubkeys on all relays
                await self._do_subscribe()
                # Start subscription monitor task and listen concurrently
                monitor_task = asyncio.create_task(self._monitor_subscriptions())
                try:
                    await self.listen_all()
                finally:
                    monitor_task.cancel()
                    try:
                        await monitor_task
                    except asyncio.CancelledError:
                        pass
            except websockets.exceptions.ConnectionClosedError as e:
                msg = (
                    f"NWC relay connection closed: {e}. "
                    f"Reconnecting in {reconnect_delay}s..."
                )
                plugin.log(msg, "debug")
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                plugin.log(f"An unexpected error occurred: {e}", "error")
                self._listen = False
            finally:
                self._running = False

    async def connect_all(self):
        """Connect to all relays in parallel with timeout for each"""
        self._running = False
        tasks = []
        for relay_url in self.relays:
            tasks.append(self._connect_relay(relay_url))
        # Connect to all relays, don't fail if some are unavailable
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Track how many connected successfully
        connected_count = sum(1 for r in results if r is True)
        if connected_count == 0:
            raise ConnectionError("Failed to connect to any relay")
        self._running = True
        plugin.log(f"Connected to {connected_count}/{len(self.relays)} relays", "info")

    async def _connect_relay(self, relay_url: str):
        """Connect to a single relay with timeout"""
        try:
            ws = await asyncio.wait_for(websockets.connect(relay_url), timeout=10)
            self.connections[relay_url] = ws
            plugin.log(f"Connected to relay: {relay_url}", "info")
            return True
        except asyncio.TimeoutError:
            plugin.log(f"Timeout connecting to relay: {relay_url}", "debug")
            return False
        except Exception as e:
            plugin.log(f"Failed to connect to relay {relay_url}: {e}", "debug")
            return False

    async def disconnect_all(self):
        """Close all websocket connections"""
        for relay_url, ws in list(self.connections.items()):
            try:
                await ws.close()
            except Exception as e:
                plugin.log(f"Error closing {relay_url}: {e}", "debug")
            finally:
                del self.connections[relay_url]
        self._running = False

    async def listen_all(self):
        """Listen on all relay connections concurrently"""
        tasks = []
        for relay_url, ws in self.connections.items():
            tasks.append(self._listen_relay(relay_url, ws))
        # Wait for any relay to close (error handling in _listen_relay)
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _listen_relay(self, relay_url: str, ws):
        """Listen for messages from a single relay"""
        plugin.log(f"Starting listener for {relay_url}", "debug")
        try:
            async for message in ws:
                data = json.loads(message)
                if data[0] == "EVENT":
                    plugin.log(
                        f"Received EVENT from {relay_url}: "
                        f"kind={data[2].get('kind')}, "
                        f"tags={data[2].get('tags', [])}",
                        "debug",
                    )
                    await self.on_event(data=data[2])
                elif data[0] == "OK":
                    plugin.log(f"OK from {relay_url}: {data[1]}", "debug")
                elif data[0] == "CLOSED":
                    plugin.log(f"CLOSED from {relay_url}: {data}", "debug")
        except websockets.exceptions.ConnectionClosedError:
            plugin.log(f"Relay disconnected: {relay_url}", "info")
        except Exception as e:
            plugin.log(f"Error listening to {relay_url}: {e}", "debug")
        finally:
            if relay_url in self.connections:
                del self.connections[relay_url]
            if len(self.connections) == 0:
                # If all relays disconnected, stop listening
                self._listen = False

    async def subscribe_all(self, filter):
        """Subscribe to filter on all connected relays"""
        plugin.log(f"nwc subscription: {filter}", "info")
        plugin.log(f"Connected relays: {list(self.connections.keys())}", "debug")
        sub_id = str(uuid.uuid4())[:64]
        tasks = []
        for relay_url, ws in self.connections.items():
            tasks.append(self._subscribe_relay(relay_url, ws, sub_id, filter))
        await asyncio.gather(*tasks, return_exceptions=True)
        self.subscriptions[sub_id] = filter
        plugin.log(f"Subscription complete for sub_id {sub_id}", "debug")
        return sub_id

    async def _subscribe_relay(self, relay_url: str, ws, sub_id: str, filter):
        """Subscribe to filter on a single relay"""
        try:
            plugin.log(
                f"Sending subscription to {relay_url}: sub_id={sub_id}, "
                f"filter={filter}",
                "debug",
            )
            await ws.send(json.dumps(["REQ", sub_id, filter]))
            # Give relay a moment to process the subscription before returning
            await asyncio.sleep(0.5)
            plugin.log(
                f"Subscription sent to {relay_url} (sub_id={sub_id[:8]}...)",
                "info",
            )
        except Exception as e:
            plugin.log(f"Failed to subscribe to {relay_url}: {e}", "error")

    async def _do_subscribe(self):
        """Subscribe to events for all current plugin pubkeys"""
        wallet_pubkey = plugin.node_pubkey
        if wallet_pubkey:
            # Listen for kind 23194 (NWC requests) mentioning the wallet
            await self.subscribe_all(filter={"kinds": [23194], "#p": [wallet_pubkey]})
            plugin.log("Subscribed to requests for wallet pubkey", "info")
        else:
            plugin.log("No wallet pubkey available for subscription", "warning")

    async def _monitor_subscriptions(self):
        """Monitor for explicit resubscription requests"""
        plugin.log("Subscription monitor started", "debug")
        while True:
            try:
                await asyncio.sleep(0.1)  # Check every 100ms for fast response
                # Check if resubscription was explicitly requested
                if self._pending_resubscribe:
                    self._pending_resubscribe = False
                    plugin.log(
                        "Immediate resubscription requested, executing now", "info"
                    )
                    await self._do_subscribe()
            except asyncio.CancelledError:
                plugin.log("Subscription monitor cancelled", "debug")
                break
            except Exception as e:
                plugin.log(f"Error in subscription monitor: {e}", "error")

    def request_resubscribe(self):
        """Signal to immediately resubscribe (can be called from RPC handlers)"""
        if self._loop is None:
            plugin.log(
                "Event loop not ready yet, will resubscribe on next monitor cycle",
                "warning",
            )
            self._pending_resubscribe = True
            return

        # Schedule the subscription immediately on the event loop
        plugin.log("Scheduling immediate resubscription on event loop", "info")
        try:
            future = asyncio.run_coroutine_threadsafe(self._do_subscribe(), self._loop)
            # Wait up to 5 seconds for the subscription to complete
            plugin.log("Waiting for subscription to complete...", "debug")
            result = future.result(timeout=5)
            plugin.log(f"Subscription completed successfully: {result}", "info")
        except concurrent.futures.TimeoutError:
            plugin.log(
                "Subscription took too long, will try again later",
                "warning",
            )
            self._pending_resubscribe = True
        except RuntimeError as e:
            plugin.log(
                f"Failed to schedule resubscription: {e}. "
                f"Using fallback flag method.",
                "warning",
            )
            self._pending_resubscribe = True
        except Exception as e:
            plugin.log(
                f"Unexpected error in resubscription: {e}",
                "error",
            )
            self._pending_resubscribe = True

    async def send_info_event(self):
        supported_methods = [
            "pay_invoice",
            "make_invoice",
            "get_info",
            "pay_keysend",
            "lookup_invoice",
            "get_balance",
            "list_transactions",
        ]
        nip47_info_event = InfoEvent(supported_methods)

        nip47_info_event.sign(privkey=plugin.privkey.hex())

        plugin.log(
            f"sending info event. Supported methods: {supported_methods}", "info"
        )

        await self.send_event(nip47_info_event.event_data())

    async def send_event(self, event_data):
        """Broadcast an event to all connected relays"""
        event_json = json.dumps(["EVENT", event_data])
        plugin.log(
            f"Sending event to {len(self.connections)} relays: "
            f"kind={event_data.get('kind')}, "
            f"tags={event_data.get('tags', [])}",
            "debug",
        )
        tasks = []
        for relay_url, ws in self.connections.items():
            tasks.append(self._send_relay(relay_url, ws, event_json))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if r is True)
        if successful > 0:
            plugin.log(
                f"Event sent to {successful}/{len(self.connections)} relays", "debug"
            )
        else:
            plugin.log("Failed to send event to any relay", "error")

    async def _send_relay(self, relay_url: str, ws, event_json: str):
        """Send event to a single relay"""
        try:
            await ws.send(event_json)
            return True
        except websockets.exceptions.WebSocketException as e:
            plugin.log(f"Error sending to {relay_url}: {e}", "debug")
            return False

    async def on_event(self, data: str):
        """handle incoming NIP47 request events"""
        try:
            pubkey_short = data.get("pubkey", "unknown")[:8]
            plugin.log(
                f"Processing NIP47 event: pubkey={pubkey_short}...",
                "debug",
            )
            request = NIP47Request.from_JSON(evt_json=data)
            plugin.log(f"Parsed request from {request._pubkey[:8]}...", "debug")

            response_content = await request.process_request(
                dh_privkey_hex=plugin.privkey.hex()
            )

            plugin.log(f"nwc request executed: {response_content}", "debug")

            response_event = NIP47Response(
                content=json.dumps(response_content),
                nip04_pubkey=request._pubkey,
                referenced_event_id=request._id,
                privkey=plugin.privkey.hex(),
            )

            response_event.sign()
            plugin.log(
                f"Sending response to {request._pubkey[:8]}...",
                "debug",
            )
            await self.send_event(response_event.event_data())
        except Exception as e:
            plugin.log(f"Error processing NIP47 event: {e}", "error")
