# Maverick Test Server

Boilerplate Python server for [Maverick](https://github.com/t00ts/maverick).

Demonstrates two simple ways of sending instructions:
1. Manually, using the stdin to send commands to Maverick.
2. Fetching messages from a Telegram entity _(e.g. a group)_, parsing them into `BetRequest`s, and forwarding them to Maverick.


### Basic project setup

1. Clone the repo
   * `git clone https://github.com/t00ts/maverick-tg`
   * `cd maverick-tg`
2. Set up a Python virtual environment
   * `python -m venv venv`
   * `source venv/bin/activate`
3. Install dependencies
   * `pip install -r requirements.txt`

## Initial setup

If you just want to send commands to Maverick using your terminal, skip to [disable Telegram](#disable-telegram-just-manual-input)

### Setting up Telegram

You'll want to set your Telegram credentials in `server.py`:

```python
tg_api_id = "YOUR API ID" # The API ID you obtained from https://my.telegram.org
tg_api_hash = "YOUR API Hash" # The API hash you obtained from https://my.telegram.org
```

And set the [entity](https://docs.telethon.dev/en/stable/concepts/entities.html#getting-entities) for the Telegram group you want to listen from.

```python
tg_group_entity = "https://t.me/+abcde12345"
```

If you want to change the default server address/port, feel free to do so in the `main()` when instantiating the `WebSocketServer`:

```python
websocket_server = WebSocketServer(port=54321)
```

### Parsing incoming Telegram messages

All incoming messages will be sent to the `process_msg` function. This is where you filter and parse messages, and **construct the `BetRequest` object that will be sent to Maverick**.

> 💡 To understand how to construct a valid `BetRequest` object, **run the `betreq` binary** that is **included in your Maverick bundle**. You will be able to create `BetRequest` objects interactively and gain detailed insights into how to build your own.


### Disable Telegram (Just manual input)
Comment out the `telegram_feed()` task in the `main()` function and you'll just have basic stdin functionality:

```python
async def main():

    # Create instances tasks (WebSocket server and data feed)
    websocket_server = WebSocketServer()

    # Run both tasks concurrently
    await asyncio.gather(
        websocket_server.start_server(),
        #telegram_feed(), <- Disable Telegram
        stdin_feed(),
    )

```

## Running the server

Launch two side-by-side terminal sessions:

| **Terminal 1**             | **Terminal 2**       |
|----------------------------|----------------------|
| `source venv/bin/activate` |                      |
| `./run_server.sh`          | `./server_output.sh` |


## Connecting Maverick to your server

In Maverick's `config.toml`, set the `addr` of your `[server]` block to point to your running websocket server:

```toml
[server]
addr = "ws://localhost:5999"
max_retries = 10
```

[Run Maverick](https://github.com/t00ts/maverick?tab=readme-ov-file#running-mavierick), and you should see the connection has been established successfully:

```
INFO maverick::server: Connecting to server (ws://localhost:5999/)
INFO maverick::server: Connection established successfully.
```