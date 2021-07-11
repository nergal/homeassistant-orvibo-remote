""" taken from https://gist.github.com/vxgmichel/e47bff34b68adb3cf6bd4845c4bed448
Provide high-level UDP endpoints for asyncio.
Example:
async def main():
    # Create a local UDP enpoint
    local = await open_local_endpoint('localhost', 8888)
    # Create a remote UDP enpoint, pointing to the first one
    remote = await open_remote_endpoint(*local.address)
    # The remote endpoint sends a datagram
    remote.send(b'Hey Hey, My My')
    # The local endpoint receives the datagram, along with the address
    data, address = await local.receive()
    # This prints: Got 'Hey Hey, My My' from 127.0.0.1 port 8888
    print(f"Got {data!r} from {address[0]} port {address[1]}")
"""

import asyncio
import time

from . import _LOGGER
from .const import (
    CD_ABORT_AND_RETRY,
    CD_ADD_AND_CONTINUE_WAITING,
    CD_RETURN_IMMEDIATELY,
)


class DatagramEndpointProtocol(asyncio.DatagramProtocol):
    """Datagram protocol for the endpoint high-level interface."""

    def __init__(self, endpoint):
        self._endpoint = endpoint

    # Protocol methods

    def connection_made(self, transport):
        self._endpoint._transport = transport

    def connection_lost(self, exc):
        if exc is not None:  # pragma: no cover
            msg = "Endpoint lost the connection: {!r}"
            _LOGGER.warning(msg.format(exc))
        self._endpoint.close()

    # Datagram protocol methods

    def datagram_received(self, data, addr):
        self._endpoint.feed_datagram(data, addr)

    def error_received(self, exc):
        msg = "Endpoint received an error: {!r}"
        _LOGGER.warning(msg.format(exc))


# Enpoint classes


class Endpoint:
    """High-level interface for UDP enpoints.
    Can either be local or remote.
    It is initialized with an optional queue size for the incoming datagrams.
    """

    def __init__(self, queue_size=None):
        if queue_size is None:
            queue_size = 0
        self._queue = dict()
        self._closed = False
        self._transport = None
        self._broadcast = False
        self._queue_size = queue_size

    # Protocol callbacks

    def feed_datagram(self, data, addr):
        try:
            key = self._init_queue(addr)
            self._queue[key].put_nowait((data, addr))
        except asyncio.QueueFull:
            _LOGGER.warning("Endpoint[%s:%d] queue is full", *addr)

    def close(self):
        # Manage flag
        if self._closed:
            return
        self._closed = True
        # Wake up
        for a, q in self._queue.items():
            if q.empty():
                self.feed_datagram(None, a)
        # Close transport
        if self._transport:
            self._transport.close()

    # User methods
    async def protocol(
        self, data, addr, check_data_fun, timeout, retry=3, is_broadcast=False
    ):
        lstdata = []
        if is_broadcast:
            self.broadcast = True
        for _ in range(retry):
            if data:
                self.send(data, addr, True)
            starttime = time.time()
            passed = 0
            while passed < timeout:
                try:
                    (rec_data, rec_addr) = await asyncio.wait_for(
                        self.receive(addr), timeout - passed
                    )
                    rv = check_data_fun(rec_data, rec_addr)
                    if isinstance(rv, tuple):
                        rec_data = rv[1]
                        rv = rv[0]
                    if rv == CD_RETURN_IMMEDIATELY:
                        self.broadcast = False
                        return rec_data, rec_addr
                    elif rv == CD_ABORT_AND_RETRY:
                        break
                    elif rv == CD_ADD_AND_CONTINUE_WAITING:
                        lstdata.append((rec_data, rec_addr))
                except asyncio.TimeoutError:
                    _LOGGER.warning("Protocol[%s:%d] timeout", *addr)
                    break
                passed = time.time() - starttime
            if lstdata:
                self.broadcast = False
                return lstdata
            elif not data:
                break
        self.broadcast = False
        return None

    @property
    def broadcast(self):
        return self._broadcast

    @broadcast.setter
    def broadcast(self, v):
        self._broadcast = v

    def _init_queue(self, addr):
        if self._broadcast:
            key = "*"
        else:
            key = addr[0]
        if key not in self._queue:
            self._queue[key] = asyncio.Queue(self._queue_size)
        return key

    def send(self, data, addr, expect_response):
        """Send a datagram to the given address."""
        if self._closed:
            raise IOError("Enpoint is closed")
        if expect_response:
            self._init_queue(addr)
        self._transport.sendto(data, addr)

    async def receive(self, expected_sender=("*", 0)):
        """Wait for an incoming datagram and return it with
        the corresponding address.
        This method is a coroutine.
        """
        key = self._init_queue(expected_sender)
        if self._queue[key].empty() and self._closed:
            raise IOError("Enpoint is closed")
        data, addr = await self._queue[key].get()
        if data is None:
            raise IOError("Enpoint is closed")
        return data, addr

    def abort(self):
        """Close the transport immediately."""
        if self._closed:
            raise IOError("Enpoint is closed")
        self._transport.abort()
        self.close()

    # Properties

    @property
    def address(self):
        """The endpoint address as a (host, port) tuple."""
        return self._transport._sock.getsockname()

    @property
    def closed(self):
        """Indicates whether the endpoint is closed or not."""
        return self._closed


# High-level coroutines
async def open_datagram_endpoint(
    host, port, *, endpoint_factory=Endpoint, remote=False, **kwargs
):
    """Open and return a datagram endpoint.
    The default endpoint factory is the Endpoint class.
    The endpoint can be made local or remote using the remote argument.
    Extra keyword arguments are forwarded to `loop.create_datagram_endpoint`.
    """
    loop = asyncio.get_event_loop()
    endpoint = endpoint_factory()
    kwargs["remote_addr" if remote else "local_addr"] = host, port
    kwargs["protocol_factory"] = lambda: DatagramEndpointProtocol(endpoint)
    await loop.create_datagram_endpoint(**kwargs)
    return endpoint


async def open_local_endpoint(host="0.0.0.0", port=0, *, queue_size=None, **kwargs):
    """Open and return a local datagram endpoint.
    An optional queue size arguement can be provided.
    Extra keyword arguments are forwarded to `loop.create_datagram_endpoint`.
    """
    return await open_datagram_endpoint(
        host,
        port,
        remote=False,
        endpoint_factory=lambda: Endpoint(queue_size),
        **kwargs
    )


async def open_remote_endpoint(host, port, *, queue_size=None, **kwargs):
    """Open and return a remote datagram endpoint.
    An optional queue size arguement can be provided.
    Extra keyword arguments are forwarded to `loop.create_datagram_endpoint`.
    """
    return await open_datagram_endpoint(
        host, port, remote=True, endpoint_factory=lambda: Endpoint(queue_size), **kwargs
    )
