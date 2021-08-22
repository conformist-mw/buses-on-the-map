import json
import logging
from contextlib import suppress
from itertools import cycle
from random import choice, randint

import trio
from trio_websocket import open_websocket_url

from utils import load_routes

# noinspection PyArgumentList
logging.basicConfig(
    level=logging.DEBUG,
    format='{asctime} - {levelname} - {message}',
    style='{',
)
logger = logging.getLogger(__file__)


async def run_bus(sender, bus_id, route):
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
        await trio.sleep(1)


async def send_updates(server_url, receiver):
    try:
        async with open_websocket_url(server_url) as ws:
            while True:
                msg = await receiver.receive()
                await ws.send_message(msg)
    except OSError as ose:
        logger.warning('Connection attempt failed: %s' % ose)


async def main():
    async with trio.open_nursery() as nursery:
        senders = []
        for _ in range(10):
            sender, receiver = trio.open_memory_channel(0)
            nursery.start_soon(send_updates, 'ws://localhost:8080', receiver)
            senders.append(sender)
        for route in load_routes('routes'):
            for index in range(randint(100, 150)):
                sender = choice(senders)
                nursery.start_soon(
                    run_bus,
                    sender,
                    f"{route['name']}-{index}",
                    route,
                )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
