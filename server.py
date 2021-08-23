import argparse
import json
import logging
from contextlib import suppress
from functools import partial
from time import monotonic

import trio
from trio_websocket import ConnectionClosed, serve_websocket

from models import Bus, BusEncoder, WindowBounds

# noinspection PyArgumentList
logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__file__)

sender, receiver = trio.open_memory_channel(0)
bounds_sender, bounds_receiver = trio.open_memory_channel(0)


def parse_args():
    parser = argparse.ArgumentParser(description='Options for websocket proxy')
    parser.add_argument(
        '--bus_port',
        type=int,
        help='port to receive fake data',
        default=8080,
    )
    parser.add_argument(
        '--browser_port',
        type=int,
        default=8000,
        help='port to communicate with browser',
    )
    parser.add_argument(
        '-v', '--verbose',
        type=int,
        choices=[x * 10 for x in range(1, 6)],
        default=logging.INFO,
        help='set logging level (10, 20, 30, 40, 50)',
    )
    return parser.parse_args()


async def listen_browser(ws):
    while True:
        msg = json.loads(await ws.get_message())
        logger.info(msg)
        if msg['msgType'] == WindowBounds.msg_type:
            await bounds_sender.send(msg['data'])


async def send_to_browser(ws):
    start, buses, bounds = monotonic(), [], WindowBounds()
    while True:
        with suppress(ConnectionClosed):
            with suppress(trio.WouldBlock):
                bounds_coords = bounds_receiver.receive_nowait()
                bounds.update(bounds_coords)
            bus = await receiver.receive()
            if bounds.is_inside(bus):
                buses.append(bus)
            if (monotonic() - start) > 1:
                await ws.send_message(json.dumps({
                    'msgType': 'Buses',
                    'buses': buses,
                }, cls=BusEncoder))
                start, buses = monotonic(), []


async def interact_with_browser(request):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_to_browser, ws)
        nursery.start_soon(listen_browser, ws)


async def listen_fake_events(request):
    ws = await request.accept()
    while True:
        try:
            message = await ws.get_message()
            await sender.send(Bus.from_json(message))
        except ConnectionClosed:
            break


async def main():
    args = parse_args()
    logger.setLevel(args.verbose)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(
                serve_websocket,
                interact_with_browser,
                '127.0.0.1',
                args.browser_port,
                ssl_context=None,
            ),
        )
        nursery.start_soon(
            partial(
                serve_websocket,
                listen_fake_events,
                '127.0.0.1',
                args.bus_port,
                ssl_context=None,
            ),
        )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
