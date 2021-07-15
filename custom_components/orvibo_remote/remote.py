"""Remote control support for Orvibo AllOne."""
from __future__ import annotations

import logging
from base64 import b64decode
from binascii import hexlify
from collections.abc import Iterable
from typing import Any, Union

from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .asyncio_orvibo.allone import AllOne
from .asyncio_orvibo.orvibo_udp import OrviboUDP

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Orvibo AllOne remote"


async def async_setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Set up the AllOne remotes platform."""

    discovered_devices = await AllOne.discovery()
    if not len(discovered_devices):
        _LOGGER.warning("No AllOne device has been found in network")

    devices = []
    for _, discovered_device in discovered_devices.items():
        try:
            instance = OrviboRemote(DEFAULT_NAME, discovered_device)

            if instance:
                _LOGGER.info("Initialized AllOne at %s", discovered_device)
                devices.append(instance)
            else:
                _LOGGER.error(
                    "Unable to find provided AllOne instance at %s",
                    discovered_device,
                )
        except Exception:
            _LOGGER.error("AllOne at %s couldn't be initialized", discovered_device)

    async_add_entities(devices)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the AllOne remotes config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities)


def _decode_command(command: Union[str, bytes]) -> bytes:
    """Decode command in format that is suitable for IR emitting"""
    if type(command) is str and command.startswith("b64:"):
        return b64decode(command.replace("b64:", ""))
    elif type(command) is bytes:
        # No need to decode, assuming it is raw
        return command

    raise ValueError(f"Unable to decode the command [{command}]")


class OrviboRemote(RemoteEntity):
    """Representation of a AllOne Remote."""

    device: AllOne
    _attr_is_on: bool = False

    def __init__(self, name: str, device: AllOne) -> None:
        """Initialize the entity."""
        self._name = name
        self._device = device

        self._attr_unique_id = OrviboUDP.print_mac(self._device.mac)

    @property
    def is_on(self) -> bool:
        """Return True if entity is on."""
        return self._attr_is_on

    def turn_on(self, **kwargs: Any) -> None:
        _LOGGER.warning("Turn on is not implemented for this platform")
        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        _LOGGER.warning("Turn off is not implemented for this platform")
        self._attr_is_on = False

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a command to device."""
        for encoded_command in command:
            _LOGGER.info("Running AllOne command => [%s]", encoded_command)
            raw_command = _decode_command(encoded_command)
            rv = await self._device.emit_ir(raw_command)
            if rv:
                _LOGGER.debug("Emit OK %s", hexlify(rv).decode("utf-8"))
            else:
                _LOGGER.error("Emit failed %s", encoded_command)

