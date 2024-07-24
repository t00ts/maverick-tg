import asyncio
import websockets
import threading
import aioconsole

import datetime
import json
import uuid
import sys
import re
import os

from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import TerminalFormatter

from telethon.sync import TelegramClient
from telethon.tl.types import InputMessagesFilterPhotos
from telethon.utils import get_display_name
from telethon import events


# Telegram auth
tg_api_id = "YOUR API ID" # The API ID you obtained from https://my.telegram.org
tg_api_hash = "YOUR API Hash" # The API hash you obtained from https://my.telegram.org

# The entity of the telegram group you want to listen to
tg_group_entity = "https://t.me/+abcde12345"


# -- WS Server ----------------------------------------------------------------

# Global variable to store the WebSocket server
server = None

# Create a queue for inter-thread communication
message_queue = asyncio.Queue()

class WebSocketServer:

    def __init__(self, host="0.0.0.0", port=5999):
        self.server = None
        self.host = host
        self.port = port

    async def start_server(self):
        self.server = await websockets.serve(
            self.client_handler, self.host, self.port
        )
        await self.server.wait_closed()
        print("Server stopped!", file=sys.stderr)

    def shutdown(self):
        self.server.close()
        print("Server shutdown!", file=sys.stderr)
        asyncio.get_event_loop().stop()

    async def client_handler(self, websocket, path):
        try:
            print(f"Client connected: {websocket.remote_address}", file=sys.stderr)
            # Tasks to concurrently handle sending and receiving messages
            receive_task = asyncio.ensure_future(self.receive_handler(websocket))
            send_task = asyncio.ensure_future(self.send_handler(websocket))
            # Wait for either task to finish
            await asyncio.wait([receive_task, send_task], return_when=asyncio.FIRST_COMPLETED)
        except websockets.ConnectionClosedError:
            print(f"Connection with {websocket.remote_address} closed (1)", file=sys.stderr)
            return

    async def receive_handler(self, websocket):
        while True:
            try:
                message = await websocket.recv()
                if not message:
                    break
                print(highlight(pretty(message), JsonLexer(), TerminalFormatter()), file=sys.stderr, flush=False)
                print("---", file=sys.stderr, flush=False)
            except websockets.ConnectionClosedError:
                print(f"Connection with {websocket.remote_address} closed (2)", file=sys.stderr)
                return

    async def send_handler(self, websocket):
        global message_queue
        while True:
            try:
                #print(f"Ready to send messages to {websocket.remote_address}", file=sys.stderr)
                message = await message_queue.get()
                await websocket.send(message)
                #print(f"Sent a new message to {websocket.remote_address}: {message}", file=sys.stderr)
            except websockets.ConnectionClosedError:
                print(f"Connection with {websocket.remote_address} closed (3)", file=sys.stderr)
                return

def pretty(string):
    """
    Pretty-prints a JSON string
    """
    try:
        json_data = json.loads(string)
        pretty_json = json.dumps(json_data, indent=2)
        return pretty_json

    except json.JSONDecodeError as e:
        return string


# -- Telegram -----------------------------------------------------------------

# Telegram client
tg_client = TelegramClient('maverick', tg_api_id, tg_api_hash)

async def telegram_feed():
    """
    Subscribes to incoming Telegram messages from the given entity
    and sends them to the processing queue.
    """

    await tg_client.start()
    entity = await tg_client.get_entity(tg_group_entity)

    # Now subscribe to new messages
    tg_client.add_event_handler(process_msg, events.NewMessage())
    await tg_client.run_until_disconnected()

def regex_match(regex, text):
    """
    Gets the first regex match
    """

    matches = re.finditer(regex, text, re.MULTILINE)
    for matchNum, match in enumerate(matches, start=1):
        for groupNum in range(0, len(match.groups())):
            return match.group(groupNum+1)
    return None

async def process_msg(msg):
    """
    Process incoming Telegram messages and create the Maverick-compatible
    BetRequest object.
    """

    # Message filter
    if not msg.text.startswith("⚽️"):
        return

    print("Processing new Telegram message: {id}".format(id=msg.id), file=sys.stderr)
    print(msg.text, file=sys.stderr)

    # Extract url
    regex_url = r"(https:\/\/[^\s]+)"
    url = regex_match(regex_url, msg.text)

    # Extract over/under
    regex_ou = r"(Over|Under)"
    ou = regex_match(regex_ou, msg.text)

    # Extract goals
    regex_goals = r"(?:(?:Over)|(?:Under))\s(\d+(?:\.\d+)?)"
    goals = regex_match(regex_goals, msg.text)

    # Extract odds
    regex_odds = r"Odds: (\d+(?:\.\d+)?)"
    odds = regex_match(regex_odds, msg.text)

    bet = {}
    if ou == "Over":
        bet = {"Goals":{"Over": float(goals)}}
    elif ou == "Under":
        bet = {"Goals":{"Under": float(goals)}}

    # Construct the bet request for Maverick
    betReq = {
        "PlaceBet":{
            "id": str(uuid.uuid4()),
            "match":{
                "Url": url,
            },
            "tf": "FullTime",
            "bet": bet,
            "odds": { "base": float(odds) },
            "stake": 0.05
        }
    }

    json_command = json.dumps(betReq)
    json_string = json.dumps(betReq, indent=2)
    print(highlight(json_string, JsonLexer(), TerminalFormatter()), file=sys.stderr)

    await message_queue.put(json_command)  # Put the message in the queue


# -- Stdin --------------------------------------------------------------------

async def async_input(prompt: str) -> str:
    return 

async def stdin_feed():
    while True:
        message = await aioconsole.ainput("> ")
        if message == "quit":
            exit(0)
        await message_queue.put(message)  # Put the message in the queue

# -- Main ---------------------------------------------------------------------

async def main():

    # Create instances tasks (WebSocket server and data feed)
    websocket_server = WebSocketServer()

    # Run both tasks concurrently
    await asyncio.gather(
        websocket_server.start_server(),
        telegram_feed(),
        stdin_feed(),
    )

if __name__ == "__main__":
    # Run the asyncio event loop in a separate thread
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_until_complete, args=(main(),))
    loop_thread.start()

    try:
        # Wait for the asyncio event loop to finish
        loop_thread.join()
    except KeyboardInterrupt:
        print("\nCleaning up and exiting...", file=sys.stderr)
        exit()
