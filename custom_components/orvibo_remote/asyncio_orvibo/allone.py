"""
Created on 25 apr 2019

@author: Matteo
"""
import asyncio
import binascii
import logging
import struct
import time
from random import randint

from . import _LOGGER
from .const import CD_CONTINUE_WAITING, CD_RETURN_IMMEDIATELY
from .orvibo_udp import DISCOVERY_ALLONE, MAGIC, PADDING_1, OrviboUDP

LEARNIR_ID = b"\x6c\x73"
LEARNIR_LEN = b"\x00\x18"
LEARNIR_2 = b"\x01\x00\x00\x00\x00\x00"
EMITIR_ID = b"\x69\x63"
EMITIR_2 = b"\x65\x00\x00\x00"

LEARN_MAX_TIME = 40
# Datagram protocol


class AllOne(OrviboUDP):
    def check_emitir_packet(self, data, addr):
        return (
            CD_RETURN_IMMEDIATELY
            if len(data) >= 6 and data[4:6] == EMITIR_ID and self.is_my_mac(data)
            else CD_CONTINUE_WAITING
        )

    async def emit_ir(self, irc, timeout=-1, retry=3):
        if await self.subscribe_if_necessary():
            plen = struct.pack(">H", len(irc) + 26)
            ilen = struct.pack("<H", len(irc))
            rnd = struct.pack("<H", randint(0, 65535))
            pkt = (
                MAGIC
                + plen
                + EMITIR_ID
                + self.mac
                + PADDING_1
                + EMITIR_2
                + rnd
                + ilen
                + irc
            )
            timeout = self.timeout if timeout <= 0 else timeout
            rv = await OrviboUDP.protocol(
                pkt, self.hp, self.check_emitir_packet, timeout, retry
            )
            if rv:
                return rv[0]
        return None

    def check_learnir_init_packet(self, data, addr):
        return (
            CD_RETURN_IMMEDIATELY
            if len(data) >= 6
            and data[4:6] == (LEARNIR_ID)
            and data[2:4] == LEARNIR_LEN
            and self.is_my_mac(data)
            else CD_CONTINUE_WAITING
        )

    def check_learnir_get_packet(self, data, addr):
        return (
            CD_RETURN_IMMEDIATELY
            if len(data) >= 6
            and data[4:6] == (LEARNIR_ID)
            and data[2:4] > LEARNIR_LEN
            and self.is_my_mac(data)
            else CD_CONTINUE_WAITING
        )

    async def enter_learning_mode(self, timeout=-1, retry=3):
        if await self.subscribe_if_necessary():
            pkt = MAGIC + LEARNIR_LEN + LEARNIR_ID + self.mac + PADDING_1 + LEARNIR_2
            timeout = self.timeout if timeout <= 0 else timeout
            if await OrviboUDP.protocol(
                pkt, self.hp, self.check_learnir_init_packet, timeout, retry
            ):
                self.learning_time = time.time()
                return True
        return False

    async def get_learned_key(self, timeout=30):
        to = min(LEARN_MAX_TIME - (time.time() - self.learning_time), timeout)
        if to > 0:
            rv = await OrviboUDP.protocol(
                None, self.hp, self.check_learnir_get_packet, to, 1
            )
            if rv and len(rv[0]) > 26:
                return rv[0][26:]
        return None

    @staticmethod
    async def discovery(broadcast_address="255.255.255.255", timeout=5, retry=3):
        disc = await OrviboUDP.discovery(broadcast_address, timeout, retry)
        hosts = dict()
        for k, v in disc.items():
            if v["type"] == DISCOVERY_ALLONE:
                hosts[k] = AllOne(**v)
        return hosts


if __name__ == "__main__":  # pragma: no cover
    import sys

    async def testFake(n):
        for i in range(n):
            _LOGGER.debug("Counter is %d", i)
            await asyncio.sleep(1)

    async def discoveryTest():
        v = await AllOne.discovery("192.168.25.255", 7, 3)
        if v:
            _LOGGER.info("Discovery str %s", v)
        else:
            _LOGGER.warning("Discovery failed")

    async def subscribe_test():
        a = AllOne(("192.168.25.41", 10000), b"\xac\xcf\x23\x72\x5a\x50")
        rv = await a.subscribe_if_necessary()
        if rv:
            _LOGGER.info("Subscribe OK")
        else:
            _LOGGER.warning("Subscribe failed")

    async def emit_test(keystr):
        payload = binascii.unhexlify(keystr)
        a = AllOne(("192.168.25.41", 10000), b"\xac\xcf\x23\x72\x5a\x50")
        rv = await a.emit_ir(payload)
        if rv:
            _LOGGER.info("Emit OK %s", binascii.hexlify(rv).decode("utf-8"))
        else:
            _LOGGER.warning("Emit failed")

    async def learn_test():
        a = AllOne(("192.168.25.41", 10000), b"\xac\xcf\x23\x72\x5a\x50")
        rv = await a.enter_learning_mode()
        if rv:
            _LOGGER.info("Entered learning mode: please press key")
            rv = await a.get_learned_key()
            if rv:
                _LOGGER.info("Obtained %s", binascii.hexlify(rv).decode("utf-8"))
            else:
                _LOGGER.warning("No key pressed")
        else:
            _LOGGER.warning("Enter learning failed")

    _LOGGER.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    _LOGGER.addHandler(handler)
    loop = asyncio.get_event_loop()
    try:
        # asyncio.ensure_future(testFake(10))
        # loop.run_until_complete(emit_test('00000000a801000000000000000098018e11951127029b0625029906270299062702380227023a0225023802270238022d023202270299062702990627029806270238022702380227023802270238022802370227023802270238022702980627023802240245021c02380227023802270238022702980627029c0623023802270298062702990627029b062502990627029906270220b7a1119d11270299062702990628029b06250238022702380227023802270238022702380227029906270299062702990627023802270238022a0234022702380227023802260238022702380226029a06260238022602380226023802260241021e02380227029b0624029906270238022702980627029b0625029906270299062702990629021db79f11a2112502990627029b0625029906270238022702380227023802270238022a02350227029906270299062702990628023702260238022702380227023802270238022702380226023b02240299062702380226023802270238022602380227023c0223029906270299062702380226029b062402990627029906270299062802980627020000'))
        loop.run_until_complete(discoveryTest())
        loop.run_until_complete(subscribe_test())
        loop.run_until_complete(
            emit_test(
                "00000000ec000000000000000000dc00d2008604d200ec02d400e80ad4000d05d9000b05d2008404d4007103d4008132d400fc03d4001e06d400ec02d400ec02d4009705d2008404d400ec02d400ea02dc00ffff283e0100d200fd03d4008404d400ec02d400eb0ad2000d05d4000d05d4008404d4007103d6008132d200fd03d400610ad4002e07d400ec02d4009405d4008504d300ec02d400ea02d400ffff333e0100cc00fd03d4008404d300ed02d300eb0ad1000e05d3000e05d4008404d4007203d3008432d100fd03d300640ad1002f07d300ed02d3009505d3008504d400ee02d000eb02d3000000"
            )
        )
        # loop.run_until_complete(learn_test())
    except BaseException as ex:
        _LOGGER.error("Test error %s", str(ex))
    finally:
        loop.close()
