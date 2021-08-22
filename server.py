import json
import logging
from contextlib import suppress
from functools import partial
from time import monotonic

import trio
from trio_websocket import ConnectionClosed, serve_websocket

# noinspection PyArgumentList
logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__file__)

sender, receiver = trio.open_memory_channel(0)


async def send_to_browser(request):
    ws = await request.accept()
    start, buses = monotonic(), []
    while True:
        try:
            bus = await receiver.receive()
            buses.append(bus)
            if (monotonic() - start) > 3 and buses:
                await ws.send_message(json.dumps({
                    'msgType': 'Buses',
                    'buses': buses,
                }))
                start, buses = monotonic(), []
        except ConnectionClosed:
            break


async def listen_fake_events(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            await sender.send(json.loads(message))
        except ConnectionClosed:
            break


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(
                serve_websocket,
                send_to_browser,
                '127.0.0.1',
                8000,
                ssl_context=None,
            ),
        )
        nursery.start_soon(
            partial(
                serve_websocket,
                listen_fake_events,
                '127.0.0.1',
                8080,
                ssl_context=None,
            ),
        )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
