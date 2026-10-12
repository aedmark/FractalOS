#!/usr/bin/env python3
"""FractalOS signaling relay: routes WebRTC offers/answers/presence between mesh nodes.

Usage: signaling_server.py [--port 8080] [--bind 0.0.0.0]

Needs the `websockets` package (Debian/Ubuntu: apt install python3-websockets). There is no authentication:
run it on a trusted LAN only.
"""
import argparse
import asyncio
import json
import logging
import websockets

logging.basicConfig(level=logging.INFO)

# Map of instance_id -> websocket
connected_clients = {}

async def register(websocket):
    pass

async def unregister(websocket):
    # Remove from connected_clients
    to_remove = []
    for instance_id, ws in connected_clients.items():
        if ws == websocket:
            to_remove.append(instance_id)
    for instance_id in to_remove:
        del connected_clients[instance_id]
        logging.info(f"Unregistered instance {instance_id}. Total clients: {len(connected_clients)}")

async def signaling_handler(websocket, path=None):
    # `path` exists in websockets < 13 only; newer releases call the handler with the connection alone.
    await register(websocket)
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except ValueError:
                logging.warning("Received invalid JSON")
                continue
            
            source_id = data.get('sourceId')
            target_id = data.get('targetId')
            msg_type = data.get('type')
            
            # Register the source_id if we haven't already
            if source_id and source_id not in connected_clients:
                connected_clients[source_id] = websocket
                logging.info(f"Registered new instance: {source_id}. Total clients: {len(connected_clients)}")
                
            logging.info(f"Routing {msg_type} from {source_id} to {target_id if target_id and target_id != 'broadcast' else 'BROADCAST'}")
            
            # Route the message
            # The client addresses a broadcast as targetId 'broadcast', not as a missing target.
            if target_id and target_id != 'broadcast':
                target_ws = connected_clients.get(target_id)
                if target_ws:
                    await target_ws.send(message)
                else:
                    logging.warning(f"Target {target_id} not found for direct message")
            else:
                # Broadcast to all except sender
                for client_id, client_ws in connected_clients.items():
                    if client_id != source_id:
                        try:
                            await client_ws.send(message)
                        except Exception as e:
                            logging.error(f"Error broadcasting to {client_id}: {e}")
                            
    except websockets.exceptions.ConnectionClosed:
        logging.info("Connection closed")
    finally:
        await unregister(websocket)

async def main(bind, port):
    logging.info(f"Starting signaling server on ws://{bind}:{port}")
    async with websockets.serve(signaling_handler, bind, port):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FractalOS signaling relay")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--bind", default="0.0.0.0")
    args = parser.parse_args()
    asyncio.run(main(args.bind, args.port))
