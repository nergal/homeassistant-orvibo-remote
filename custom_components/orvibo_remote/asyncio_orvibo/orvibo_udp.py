"""
Created on 25 apr 2019

@author: Matteo
"""
import binascii
import struct
import time

from . import _LOGGER
from .asyncio_udp import open_local_endpoint
from .const import (
    CD_ADD_AND_CONTINUE_WAITING,
    CD_CONTINUE_WAITING,
    CD_RETURN_IMMEDIATELY,
)

PORT = 10000
DISCOVERY_ALLONE = b"\x49\x52\x44"
DISCOVERY_S20 = b"\x53\x4f\x43"
MAC_START = b"\xac\xcf"
MAGIC = b"\x68\x64"
DISCOVERY_LEN = b"\x00\x06"
DISCOVERY_ID = b"\x71\x61"
SUBSCRIBE_LEN = b"\x00\x1e"
SUBSCRIBE_ID = b"\x63\x6c"
PADDING_1 = b"\x20\x20\x20\x20\x20\x20"
PADDING_2 = b"\x00\x00\x00\x00"
SUBSCRIPTION_TIMEOUT = 60


class OrviboUDP:
    _local = None

    def __repr__(self):
        return "[%s:%d] %s %s" % (
            *self.hp,
            OrviboUDP.print_mac(self.mac),
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.mytime)),
        )

    def __init__(self, hp, mac, mytime=None, timeout=3, **kwargs):
        self.hp = hp
        if isinstance(mac, bytes):
            self.mac = mac
        else:
            mac = mac.replace(":", "").replace("-", "").replace(" ", "")
            self.mac = binascii.unhexlify(mac)
        ba = bytearray(self.mac)
        ba.reverse()
        self.mac_reversed = bytes(ba)
        self.time_subscribe = 0
        self.mytime = mytime - 2208988800 if mytime is not None else time.time()
        self.learning_time = 0
        self.timeout = timeout

    def use_subscribe_data(self, s_data):
        pass

    @staticmethod
    async def protocol(
        data, addr, check_data_fun, timeout, retry=3, is_broadcast=False, **kwargs
    ):
        out_data = None
        for _ in range(retry):
            try:
                if await OrviboUDP.init_local(**kwargs):
                    for _ in range(retry):
                        out_data = await OrviboUDP._local.protocol(
                            data, addr, check_data_fun, timeout, 1, is_broadcast
                        )
                        if out_data:
                            break
                    break
            except BaseException as ex:
                OrviboUDP.destroy_local()
                _LOGGER.error("Protocol[%s:%d] error: %s", *addr, str(ex))

        # =======================================================================
        # if not out_data:
        #     OrviboUDP.destroy_local()
        # =======================================================================
        return out_data

    @staticmethod
    async def init_local(**kwargs):
        if not OrviboUDP._local:
            try:
                OrviboUDP._local = await open_local_endpoint(
                    port=PORT, allow_broadcast=True, **kwargs
                )
            except BaseException as ex:
                _LOGGER.error("Open endpoint error %s", str(ex))
                OrviboUDP._local = None
        return OrviboUDP._local

    @staticmethod
    def destroy_local():
        if OrviboUDP._local:
            try:
                OrviboUDP._local.abort()
            except Exception:
                pass
            OrviboUDP._local = None

    @staticmethod
    def print_mac(mac_bytes):
        return binascii.hexlify(mac_bytes).decode("utf-8")

    @staticmethod
    def check_discovery_packet(data, addr):
        return (
            CD_CONTINUE_WAITING
            if len(data) < 41 or data[4:6] != (DISCOVERY_ID)
            else CD_ADD_AND_CONTINUE_WAITING
        )

    @staticmethod
    def mac_from_data(data):
        idx = data.find(MAC_START)
        if idx >= 0 and idx + 6 <= len(data):
            return data[idx : idx + 6]
        else:
            return None

    def is_my_mac(self, data):
        mac = OrviboUDP.mac_from_data(data)
        return False if not mac else mac == self.mac

    def check_subscription_packet(self, data, addr):
        return (
            CD_RETURN_IMMEDIATELY
            if len(data) >= 13 and data[4:6] == (SUBSCRIBE_ID) and self.is_my_mac(data)
            else CD_CONTINUE_WAITING
        )

    async def subscribe_if_necessary(self, timeout=-1, retry=3):
        now = time.time()
        if now - self.time_subscribe > SUBSCRIPTION_TIMEOUT:
            timeout = self.timeout if timeout <= 0 else timeout
            out_data = await OrviboUDP.protocol(
                MAGIC
                + SUBSCRIBE_LEN
                + SUBSCRIBE_ID
                + self.mac
                + PADDING_1
                + self.mac_reversed
                + PADDING_1,
                self.hp,
                self.check_subscription_packet,
                timeout,
                retry,
            )
            if out_data:
                self.time_subscribe = time.time()
                self.use_subscribe_data(out_data[0])
                return True
            return False
        else:
            return True

    @staticmethod
    async def discovery(broadcast_address="255.255.255.255", timeout=5, retry=3):
        out_data = await OrviboUDP.protocol(
            MAGIC + DISCOVERY_LEN + DISCOVERY_ID,
            (broadcast_address, PORT),
            OrviboUDP.check_discovery_packet,
            timeout,
            retry,
            is_broadcast=True,
        )
        if out_data:
            hosts = dict()
            for d_a in out_data:
                data = d_a[0]
                keyv = "%s:%d" % d_a[1]
                if keyv not in hosts:
                    if data.find(DISCOVERY_ALLONE) >= 0:
                        tp = DISCOVERY_ALLONE
                    elif data.find(DISCOVERY_S20) >= 0:
                        tp = DISCOVERY_S20
                    else:
                        _LOGGER.warning(
                            "Unknown device type %s %s",
                            keyv,
                            OrviboUDP.print_mac(data[31:37]),
                        )
                        continue
                    dev = dict(
                        hp=d_a[1],
                        type=tp,
                        mac=data[7:13],
                        mytime=struct.unpack("<I", data[37:41])[0],
                        raw=data,
                    )
                    _LOGGER.info("Discovered device %s", dev)
                    hosts[keyv] = dev
            return hosts
        else:
            return dict()
