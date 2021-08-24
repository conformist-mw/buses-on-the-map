import argparse
import json
import logging
from contextlib import suppress
from functools import wraps
from itertools import cycle
from random import choice, randint

import trio
from trio_websocket import ConnectionClosed, HandshakeError, open_websocket_url

from utils import load_routes

# noinspection PyArgumentList
logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__file__)


def parse_args():
    parser = argparse.ArgumentParser(description='Options for load testing')
    parser.add_argument(
        '--server',
        help='websocket server address',
        default='ws://localhost:8080',
    )
    parser.add_argument(
        '--routes-number',
        type=int,
        default=10,
        choices=range(1, 100),
        help='how many routes will be loaded',
    )
    parser.add_argument(
        '--buses-per-route',
        type=int,
        default=5,
        help='generate routes with offset',
    )
    parser.add_argument(
        '--websockets-count',
        type=int,
        default=10,
        choices=range(1, 50),
        help='how many websockets will be opened',
    )
    parser.add_argument(
        '--emulator-id',
        default='1',
        help='busId prefix if multiple fake_bus instances running',
    )
    parser.add_argument(
        '--refresh-timeout',
        type=float,
        default=1.0,
        help='timeout between sending new coordinates',
    )
    parser.add_argument(
        '-v', '--verbose',
        type=int,
        choices=[x * 10 for x in range(1, 6)],
        default=logging.INFO,
        help='set logging level (10, 20, 30, 40, 50)',
    )
    return parser.parse_args()


def relaunch_on_disconnect(async_function):
    @wraps(async_function)
    async def wrapped(*args, **kwargs):
        while True:
            try:
                await async_function(*args, **kwargs)
            except (ConnectionClosed, HandshakeError):
                logger.debug('send_updates reconnect')
                await trio.sleep(3)
    return wrapped


async def run_bus(sender, bus_id, route, refresh_timeout):
    coordinates = route['coordinates']
    rand_offset = randint(0, len(coordinates) - 1)
    route_with_offset = cycle(
        coordinates[rand_offset:] + coordinates[:rand_offset],
    )
    for lat, lng in route_with_offset:
        await sender.send(json.dumps({
            'busId': bus_id,
            'lat': lat,
            'lng': lng,
            'route': bus_id,
        }, ensure_ascii=False))
        await trio.sleep(refresh_timeout)


@relaunch_on_disconnect
async def send_updates(server_url, receiver):
    async with open_websocket_url(server_url) as ws:
        while True:
            msg = await receiver.receive()
            await ws.send_message(msg)


async def main():
    args = parse_args()
    logger.setLevel(args.verbose)
    async with trio.open_nursery() as nursery:
        senders = []
        for _ in range(args.websockets_count):
            sender, receiver = trio.open_memory_channel(0)
            nursery.start_soon(send_updates, args.server, receiver)
            senders.append(sender)
        for routes_index, route in enumerate(load_routes('routes')):
            if routes_index >= args.routes_number:
                break
            for index in range(args.buses_per_route):
                sender = choice(senders)
                nursery.start_soon(
                    run_bus,
                    sender,
                    f"{args.emulator_id}-{route['name']}-{index}",
                    route,
                    args.refresh_timeout,
                )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
