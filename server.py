import argparse
import json
import logging
from contextlib import suppress
from functools import partial

import trio
from trio_websocket import ConnectionClosed, serve_websocket

from models import Bus, BusEncoder, WindowBounds

# noinspection PyArgumentList
logging.basicConfig(
    level=logging.INFO,
    format='{asctime} - {levelname} - {message} - {filename}:{lineno}',
    style='{',
)
logger = logging.getLogger(__file__)


class EmptyMessageError(Exception):
    ...


def parse_args():
    parser = argparse.ArgumentParser(description='Options for websocket proxy')
    parser.add_argument(
        '--bus-port',
        type=int,
        help='port to receive fake data',
        default=8080,
    )
    parser.add_argument(
        '--browser-port',
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


async def check_message(encoded_message):
    message = None
    error_msg = None
    try:
        message = json.loads(encoded_message)
        if message is None:
            raise EmptyMessageError
        if (
            isinstance(message, dict)
            and not {'busId', 'msgType'} & set(message.keys())
        ):
            raise KeyError
    except json.JSONDecodeError:
        error_msg = 'Requires valid JSON'
    except KeyError:
        error_msg = 'Requires msgType or busId specified'
    except EmptyMessageError:
        error_msg = 'Message is null'

    return message, error_msg


async def send_error(ws, error_message, source_message):
    error = json.dumps({
        'errors': [error_message],
        'msgType': 'Errors',
        'source_msg': source_message,
    })
    await ws.send_message(error)


async def listen_to_browser(ws, bounds):
    while True:
        try:
            encoded_message = await ws.get_message()
            logger.debug(encoded_message)
            message, error_message = await check_message(encoded_message)
            if error_message:
                await send_error(ws, error_message, encoded_message)
                continue
            if message['msgType'] == WindowBounds.msg_type:
                bounds.update(message['data'])
        except ConnectionClosed:
            logger.debug('listen_to_browser: connection closed')
            break


async def send_to_browser(ws, buses: dict, bounds):
    while True:
        with suppress(ConnectionClosed):
            inbound_buses = [
                bus for bus in buses.values() if bounds.is_inside(bus)
            ]
            if inbound_buses:
                await ws.send_message(json.dumps({
                    'msgType': 'Buses',
                    'buses': inbound_buses,
                }, cls=BusEncoder))
            await trio.sleep(0)


async def interact_with_browser(request, buses, bounds):
    ws = await request.accept()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_to_browser, ws, buses, bounds)
        nursery.start_soon(listen_to_browser, ws, bounds)


async def listen_fake_events(request, buses):
    ws = await request.accept()
    while True:
        try:
            encoded_message = await ws.get_message()
            logger.debug(encoded_message)
            message, error_message = await check_message(encoded_message)
            if error_message:
                await send_error(ws, error_message, encoded_message)
                continue
            bus = Bus(**message)
            buses[bus.busId] = bus
        except ConnectionClosed:
            logger.debug('listen_fake_events: connection closed')
            break


async def main():
    buses = {}
    bounds = WindowBounds()
    args = parse_args()
    logger.setLevel(args.verbose)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(
            partial(
                serve_websocket,
                partial(interact_with_browser, buses=buses, bounds=bounds),
                '127.0.0.1',
                args.browser_port,
                ssl_context=None,
            ),
        )
        nursery.start_soon(
            partial(
                serve_websocket,
                partial(listen_fake_events, buses=buses),
                '127.0.0.1',
                args.bus_port,
                ssl_context=None,
            ),
        )


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
