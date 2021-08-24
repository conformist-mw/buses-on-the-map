import json
import logging
from contextlib import suppress

import trio
from trio_websocket import open_websocket_url

# noinspection PyArgumentList
logging.basicConfig(
    level=logging.DEBUG,
    format='{asctime} - {levelname} - {message}',
    style='{',
)
logger = logging.getLogger('harmful_client')


async def send_harmful_messages(server_url):
    async with open_websocket_url(server_url) as ws:
        for msg in ('', '{}', 'null'):  # noqa: P103
            await ws.send_message(msg)
            response = json.loads(await ws.get_message())
            logger.debug(response)
            assert response['msgType'] == 'Errors'  # noqa: AST100


async def main():
    async with trio.open_nursery() as nursery:
        for port in (8080, 8000):
            nursery.start_soon(send_harmful_messages, f'ws://localhost:{port}')


if __name__ == '__main__':
    with suppress(KeyboardInterrupt):
        trio.run(main)
