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
bounds_sender, bounds_receiver = trio.open_memory_channel(0)


def is_inside(bounds, lat, lng):
    if bounds is None:  # have not yet received data from the browser
        return True
    return (
        (bounds['south_lat'] < lat < bounds['north_lat'])
        and (bounds['west_lng'] < lng < bounds['east_lng'])
    )


async def listen_browser(ws):
    while True:
        msg = json.loads(await ws.get_message())
        logger.info(msg)
        if msg['msgType'] == 'newBounds':
            await bounds_sender.send(msg['data'])


async def send_to_browser(ws):
    start, buses, bounds = monotonic(), [], None
    while True:
        try:
            try:
                bounds = bounds_receiver.receive_nowait()
            except trio.WouldBlock:
                pass
            bus = await receiver.receive()
            if is_inside(bounds, bus['lat'], bus['lng']):
                buses.append(bus)
            if (monotonic() - start) > 1:
                await ws.send_message(json.dumps({
                    'msgType': 'Buses',
                    'buses': buses,
                }))
                start, buses = monotonic(), []
        except ConnectionClosed:
            break


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
            await sender.send(json.loads(message))
        except ConnectionClosed:
            break


async def main():
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(
                serve_websocket,
                interact_with_browser,
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
