"""Remote control support for Orvibo AllOne."""
from __future__ import annotations

import sys
import logging
from base64 import b64decode
from collections.abc import Iterable
from typing import Any, Dict, Iterator, List, Union
from pprint import pprint

from homeassistant.components.remote import RemoteEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType

from .orvibo.orvibo import Orvibo, OrviboException

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Orvibo AllOne remote"


async def async_setup_platform(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info=None,
):
    """Set up the AllOne remotes platform."""

    devices = []

    _LOGGER.info("System byte order is %s", sys.byteorder)

    try:
        discovered_devices: Dict[str, List[str]] = Orvibo.discover()
        discovered_devices_payload: Iterator[List[str]] = filter(
            lambda x: x[2] == Orvibo.TYPE_IRDA, discovered_devices.values()
        )

        for discovered_device_payload in discovered_devices_payload:
            ip = discovered_device_payload[0]
            try:
                device = Orvibo(*discovered_device_payload)
                instance = OrviboRemote(DEFAULT_NAME, device)

                if instance:
                    _LOGGER.info("Initialized AllOne at %s", ip)
                    devices.append(instance)
                else:
                    _LOGGER.error(
                        "Unable to find provided AllOne instance at %s",
                        ip,
                    )
            except Exception as e:
                _LOGGER.error("AllOne at %s couldn't be initialized", ip, e)
    except OrviboException as e:
        _LOGGER.error("Unable to discover AllOne devices", e)

    if not len(devices):
        _LOGGER.warning("No AllOne device has been found in network")

    async_add_entities(devices)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigType,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the AllOne remotes config entry."""
    await async_setup_platform(hass, config_entry, async_add_entities)


class OrviboRemote(RemoteEntity):
    """Representation of a AllOne Remote."""

    device: Orvibo
    _attr_is_on: bool = False

    def __init__(self, name: str, device: Orvibo) -> None:
        """Initialize the entity."""
        self._name = name
        self._device = device

        self._attr_unique_id = self._device.mac.hex()

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

    def _decode_command(self, command: Union[str, bytes]) -> bytes:
        """Decode command in format that is suitable for IR emitting"""
        if type(command) is str and command.startswith("b64:"):
            return b64decode(command.replace("b64:", ""))
        elif type(command) is bytes:
            # No need to decode, assuming it is raw
            return command

        raise ValueError("Unable to decode the command")

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send a command to device."""
        for encoded_command in command:
            raw_command = self._decode_command(encoded_command)
            _LOGGER.info("Running AllOne command => [%s]", raw_command.hex())
            result = self._device.emit_ir(raw_command)

            _LOGGER.debug("Emit OK") if result else _LOGGER.error("Emit failed => [%s]", raw_command.hex())
