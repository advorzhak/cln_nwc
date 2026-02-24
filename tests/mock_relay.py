#!/usr/bin/env python3
"""
Mock Nostr Relay for NWC Testing

A simple WebSocket relay that handles NWC (Nostr Wallet Connect) testing.
Supports REQ (subscription), EVENT (publishing), and echoes back events
to matching subscriptions.
"""

import asyncio
import json
import logging
import sys
from typing import Dict, List

import websockets

logging.basicConfig(
    level=logging.DEBUG,
    format="[MockRelay] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


class MockRelay:
    """A simple Nostr relay for testing"""

    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.clients: Dict = {}  # client_id -> websocket
        self.subscriptions: Dict = {}  # client_id -> {sub_id -> filter}
        self.client_counter = 0

    async def handle_client(self, websocket, path=None):
        """Handle a client connection"""
        client_id = self.client_counter
        self.client_counter += 1
        self.clients[client_id] = websocket
        self.subscriptions[client_id] = {}

        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        sys.stdout.flush()

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data[0] if data else "empty"
                    logger.debug(
                        f"Client {client_id}: Received message type: {msg_type}"
                    )
                    await self.handle_message(client_id, websocket, data)
                except json.JSONDecodeError as e:
                    logger.error(f"Client {client_id}: Invalid JSON: {message} - {e}")
                except Exception as e:
                    logger.error(
                        f"Client {client_id}: Error handling message: {e}",
                        exc_info=True,
                    )
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Client {client_id} disconnected: {e}")
        except Exception as e:
            logger.error(f"Client {client_id}: Unexpected error: {e}", exc_info=True)
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.subscriptions:
                del self.subscriptions[client_id]

    async def handle_message(self, client_id: int, websocket, data: List):
        """Handle incoming Nostr protocol messages"""
        if not isinstance(data, list) or len(data) == 0:
            logger.warning(f"Client {client_id}: Invalid message format: {data}")
            return

        msg_type = data[0]
        logger.info(f"Client {client_id}: Handling message type '{msg_type}'")

        if msg_type == "REQ":
            # Subscription request: ["REQ", <subscription_id>, <filters>...]
            if len(data) < 3:
                logger.warning(f"Client {client_id}: Invalid REQ message (too short)")
                return

            sub_id = data[1]
            filters = data[2:]

            logger.info(
                f"Client {client_id}: Subscribing {sub_id[:8]}... "
                f"to {len(filters)} filter(s): {filters}"
            )
            sys.stdout.flush()
            sys.stderr.flush()
            self.subscriptions[client_id][sub_id] = filters

            # Send EOSE (End Of Stored Events) for subscription
            eose_response = ["EOSE", sub_id]
            await websocket.send(json.dumps(eose_response))
            logger.info(f"Client {client_id}: Sent EOSE for {sub_id[:8]}...")

        elif msg_type == "EVENT":
            # Publishing event: ["EVENT", <event_object>]
            if len(data) < 2:
                logger.warning(f"Client {client_id}: Invalid EVENT message")
                return

            event = data[1]
            event_id = event.get("id", "unknown")[:8]
            event_kind = event.get("kind")

            logger.info(
                f"Client {client_id}: Publishing event {event_id}... "
                f"(kind {event_kind})"
            )

            # Broadcast to all subscribed clients
            await self.broadcast_event(client_id, event)

            # Send OK response
            ok_response = ["OK", event.get("id"), True, ""]
            await websocket.send(json.dumps(ok_response))

        elif msg_type == "CLOSE":
            # Close subscription: ["CLOSE", <subscription_id>]
            if len(data) < 2:
                logger.warning(f"Client {client_id}: Invalid CLOSE message")
                return

            sub_id = data[1]
            if client_id in self.subscriptions:
                self.subscriptions[client_id].pop(sub_id, None)
                logger.info(f"Client {client_id}: Closed subscription {sub_id[:8]}...")

        else:
            logger.warning(f"Client {client_id}: Unknown message type: {msg_type}")

    async def broadcast_event(self, sender_id: int, event: Dict):
        """Broadcast event to all subscribed clients"""
        event_id = event.get("id", "unknown")[:8]
        event_kind = event.get("kind")
        event_pubkey = event.get("pubkey", "unknown")[:8]

        logger.info(
            f"Broadcasting event {event_id}... (kind {event_kind}, "
            f"pubkey {event_pubkey}) from client {sender_id}"
        )

        sent_count = 0
        # Check each client's subscriptions
        for client_id, subs in self.subscriptions.items():
            # Don't send back to sender
            if client_id == sender_id:
                logger.debug(f"Skipping sender client {client_id}")
                continue

            logger.debug(
                f"Checking client {client_id} with {len(subs)} subscription(s)"
            )
            for sub_id, filters in subs.items():
                # Check if event matches any filter
                if self.event_matches_filters(event, filters):
                    # Get the client's websocket
                    if client_id in self.clients:
                        ws = self.clients[client_id]
                        try:
                            event_message = ["EVENT", sub_id, event]
                            await ws.send(json.dumps(event_message))
                            sent_count += 1
                            logger.info(
                                f"Sent event {event_id}... (kind {event_kind}) "
                                f"to client {client_id} on subscription {sub_id[:8]}"
                            )
                        except Exception as e:
                            logger.error(f"Error sending to client {client_id}: {e}")
                else:
                    logger.debug(
                        f"Event {event_id}... did not match subscription "
                        f"{sub_id[:8]} for client {client_id}"
                    )

        if sent_count == 0:
            logger.warning(
                f"Event {event_id}... (kind {event_kind}) was not sent "
                f"to any clients (total clients: {len(self.clients)}, "
                f"sender: {sender_id})"
            )
        sys.stdout.flush()
        sys.stderr.flush()

    def event_matches_filters(self, event: Dict, filters: List[Dict]) -> bool:
        """Check if event matches any of the filters"""
        for filter_item in filters:
            if self.event_matches_filter(event, filter_item):
                return True
        return False

    def event_matches_filter(self, event: Dict, filter_item: Dict) -> bool:
        """Check if event matches a single filter"""
        event_id = event.get("id", "unknown")[:8]
        event_kind = event.get("kind")
        event_pubkey = event.get("pubkey", "")[:8]

        # Check kinds
        if "kinds" in filter_item:
            if event_kind not in filter_item["kinds"]:
                logger.debug(
                    f"Event {event_id} kind {event_kind} not in filter kinds "
                    f"{filter_item['kinds']}"
                )
                return False

        # Check p tag (p tag in event points to these pubkeys)
        if "#p" in filter_item:
            event_p_tags = [tag[1] for tag in event.get("tags", []) if tag[0] == "p"]
            if not any(p in filter_item["#p"] for p in event_p_tags):
                logger.debug(
                    f"Event {event_id} p tags {[t[:8] for t in event_p_tags]} "
                    f"not in filter #p {[p[:8] for p in filter_item['#p']]}"
                )
                return False

        # Check e tag
        if "#e" in filter_item:
            event_e_tags = [tag[1] for tag in event.get("tags", []) if tag[0] == "e"]
            if not any(e in filter_item["#e"] for e in event_e_tags):
                logger.debug(
                    f"Event {event_id} e tags {[t[:8] for t in event_e_tags]} "
                    f"not in filter #e {[e[:8] for e in filter_item['#e']]}"
                )
                return False

        # Check authors
        if "authors" in filter_item:
            if event.get("pubkey") not in filter_item["authors"]:
                logger.debug(
                    f"Event {event_id} author {event_pubkey} not in filter "
                    f"authors {[a[:8] for a in filter_item['authors']]}"
                )
                return False

        # Check since/until timestamps
        created_at = event.get("created_at", 0)
        if "since" in filter_item and created_at < filter_item["since"]:
            logger.debug(f"Event {event_id} too old (before 'since')")
            return False
        if "until" in filter_item and created_at > filter_item["until"]:
            logger.debug(f"Event {event_id} too new (after 'until')")
            return False

        logger.debug(f"Event {event_id} matches filter!")
        return True

    async def start(self):
        """Start the relay server"""
        try:
            logger.info(f"Starting mock relay on ws://{self.host}:{self.port}")
            sys.stdout.flush()

            async with websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                # Use default settings for compatibility
            ):
                logger.info(f"Mock relay listening on ws://{self.host}:{self.port}")
                sys.stdout.flush()
                sys.stderr.flush()
                # Keep running until interrupted
                await asyncio.Future()
        except OSError as e:
            logger.error(f"Failed to bind to {self.host}:{self.port}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in relay server: {e}", exc_info=True)
            raise


async def main():
    """Run the mock relay"""
    relay = MockRelay()
    try:
        logger.info(f"Main: Starting relay on ws://{relay.host}:{relay.port}")
        sys.stdout.flush()
        sys.stderr.flush()
        await relay.start()
    except KeyboardInterrupt:
        logger.info("Shutting down mock relay")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Failed to run main: {e}", exc_info=True)
        sys.exit(1)
