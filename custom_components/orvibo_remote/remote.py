"""Remote control support for Orvibo AllOne."""
from __future__ import annotations

import sys
import logging
import voluptuous as vol
from base64 import b64decode
from collections.abc import Iterable
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_IP_ADDRESS, CONF_NAME
from homeassistant.components.remote import RemoteEntity, PLATFORM_SCHEMA
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .orvibo.orvibo import Orvibo, OrviboException

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Orvibo AllOne remote"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_IP_ADDRESS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
):
    """Set up the AllOne remotes platform."""

    ip_address = config[CONF_IP_ADDRESS]
    name = config[CONF_NAME]

    devices = []
    try:
        _LOGGER.debug("Discovering AllOne device at IP %s", ip_address)
        device: Orvibo = Orvibo.discover(ip=ip_address) # pyright: ignore[reportAssignmentType]
        add_entities([OrviboRemote(name, device)])
    except OrviboException:
        _LOGGER.exception("Unable to discover AllOne devices")

    if not len(devices):
        _LOGGER.warning("No AllOne device has been found in network")

    add_entities(devices)


class OrviboRemote(RemoteEntity):
    """Representation of a AllOne Remote."""

    device: Orvibo

    def __init__(self, name: str, device: Orvibo) -> None:
        """Initialize the entity."""
        self._name = name
        self._device = device

        if self._device.mac is not None:
            self._attr_unique_id = self._device.mac.hex()
        else:
            self._attr_unique_id = f"orvibo-{sys.maxsize - id(self)}"

    def _decode_command(self, command: str | bytes | bytearray) -> bytes:
        """Decode command in format that is suitable for IR emitting"""
        if isinstance(command, str):
            if command.startswith("b64:"):
                return b64decode(command[4:])
            raise ValueError("Unable to decode the command")

        if isinstance(command, bytearray):
            return bytes(command)

        if isinstance(command, bytes):
            # No need to decode, assuming it is raw
            return command

        raise ValueError("Unable to decode the command")

    def send_command(self, command: Iterable[str | bytes], **kwargs: Any) -> None:
        """Send a command to device."""
        if command is None:
            _LOGGER.debug("No command provided to send")
            return

        for encoded_command in command:
            raw_command = self._decode_command(encoded_command)
            _LOGGER.info("Running AllOne command => [%s]", raw_command.hex())
            result = self._device.emit_ir(raw_command)

            _LOGGER.debug("Emit OK") if result else _LOGGER.error("Emit failed => [%s]", raw_command.hex())
