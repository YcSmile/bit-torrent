import asyncio
import logging
from typing import Callable, TypeVar

from control_manager import ControlManager
from control_server import ControlServer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


T = TypeVar('T')


class ControlClient:
    def __init__(self):
        self._reader = None  # type: asyncio.StreamReader
        self._writer = None  # type: asyncio.StreamWriter

    async def connect(self):
        for port in ControlServer.PORT_RANGE:
            try:
                self._reader, self._writer = await asyncio.open_connection(host=ControlServer.HOST, port=port)

                message = await self._reader.readexactly(len(ControlServer.HANDSHAKE_MESSAGE))
                if message != ControlServer.HANDSHAKE_MESSAGE:
                    raise RuntimeError('Unknown control server protocol')
            except Exception as e:
                self.close()
                self._reader = None
                self._writer = None
                logger.debug('failed to connect to port %s: %s', port, repr(e))
            else:
                break
        else:
            raise RuntimeError('Failed to connect to a control server')

    async def execute(self, action: Callable[[ControlManager], T]) -> T:
        ControlServer.send_object(action, self._writer)
        result = await ControlServer.receive_object(self._reader)

        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        if self._writer is not None:
            self._writer.close()

    async def __aenter__(self) -> 'ControlClient':
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
