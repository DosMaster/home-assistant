"""Support for EnOcean light sources."""
import logging

import voluptuous as vol

# dm
from homeassistant.components import enocean
from homeassistant.components.enocean import PLATFORM_SCHEMA  # dm
from homeassistant.components.light import (  # PLATFORM_SCHEMA,
    ATTR_BRIGHTNESS,
    SUPPORT_BRIGHTNESS,
    Light,
)
from homeassistant.const import CONF_ID, CONF_NAME, STATE_ON  # dm
import homeassistant.helpers.area_registry as ar
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.restore_state import RestoreEntity

# import math #dm


_LOGGER = logging.getLogger(__name__)

CONF_SENDER_ID = "sender_id"


CONF_DEVICE_TYPE = "device_type"

DEFAULT_NAME = "EnOcean Light"
SUPPORT_ENOCEAN = SUPPORT_BRIGHTNESS

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ID, default=[]): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Required(CONF_SENDER_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_TYPE, default="std"): cv.string,  # dm
    }
)

entities = []  # dm


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the EnOcean light platform."""
    sender_id = config.get(CONF_SENDER_ID)
    dev_name = config.get(CONF_NAME)
    dev_id = config.get(CONF_ID)
    dev_type = config.get(CONF_DEVICE_TYPE)  # dm

    """
    add_entities([EnOceanLight(sender_id, dev_id, dev_name)])
    """

    # dm
    entity = EnOceanLight(sender_id, dev_id, dev_name, dev_type)
    setup_platform_dm(hass, config, add_entities, entity)


class EnOceanLight(enocean.EnOceanDevice, Light, RestoreEntity):
    """Representation of an EnOcean light source."""

    def __init__(self, sender_id, dev_id, dev_name, dev_type):  # dm
        """Initialize the EnOcean light source."""
        super().__init__(dev_id, dev_name, __name__)  # dm
        self._on_state = False
        self._brightness = 50
        self._sender_id = sender_id
        self._dev_type = dev_type

        # dm
        if dev_type.lower() == "std" or dev_type.lower() == "fud14":
            self.dev_type = dev_type.lower()
        else:
            self.dev_type = None
            _LOGGER.warning('device_type "%s" (%s) unknown', dev_type, dev_name)

    @property
    def name(self):
        """Return the name of the device if any."""
        return self.dev_name

    @property
    def brightness(self):
        """Brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def is_on(self):
        """If light is on."""
        return self._on_state

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_ENOCEAN

    def turn_on(self, **kwargs):
        """Turn the light source on or sets a specific dimmer value."""
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if brightness is not None:
            self._brightness = brightness

        bval = round(self._brightness / 256.0 * 100.0)  # dm
        if bval == 0:
            bval = 1
        command = [0xA5, 0x02, bval, 0x01, 0x09]
        command.extend(self._sender_id)
        command.extend([0x00])
        self.send_command(command, [], 0x01)
        self._on_state = True

    def turn_off(self, **kwargs):
        """Turn the light source off."""
        if self.dev_type == "fud14":  # dm
            command = [0xA5, 0x02, 0x00, 0x01, 0x08]  # dm
        else:  # dm
            command = [0xA5, 0x02, 0x00, 0x01, 0x09]
        command.extend(self._sender_id)
        command.extend([0x00])
        self.send_command(command, [], 0x01)
        self._on_state = False

    def value_changed(self, packet):
        """Update the internal state of this device.

        Dimmer devices like Eltako FUD61 send telegram in different RORGs.
        We only care about the 4BS (0xA5).
        """
        if packet.data[0] == 0xA5 and packet.data[1] == 0x02:
            val = packet.data[2]
            if self.dev_type == "fud14":  # dm
                if (packet.data[4] & 0x01) == 1:  # dm
                    self._brightness = round(val / 100.0 * 256.0)  # dm
                    self._on_state = True  # dm
                else:  # dm
                    self._on_state = False  # dm
            else:  # dm
                self._brightness = round(val / 100.0 * 256.0)
                self._on_state = bool(val != 0)

            if self.added_to_hass:
                self.schedule_update_ha_state()

    # dm
    async def async_added_to_hass(self):
        """Restore device state (ON/OFF/Brightness)."""
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()

        if old_state is not None:
            self._on_state = old_state.state == STATE_ON

        # Restore the brightness of dimmable devices
        if (
            old_state is not None
            and old_state.attributes.get(ATTR_BRIGHTNESS) is not None
        ):
            self._brightness = int(old_state.attributes[ATTR_BRIGHTNESS])

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attr = {}
        if self._brightness is not None:
            attr[ATTR_BRIGHTNESS] = self._brightness
        return attr


# dm
def setup_platform_dm(hass, config, add_entities, entity):
    """Set platform."""
    entity._area_name = config.get("area_name")
    entity._manufacturer = config.get("manufacturer")
    entity._model = config.get("model")
    entities.append(entity)


# dm
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the EnOcean config entry."""

    area_registry = await ar.async_get_registry(hass)

    areas = area_registry.async_list_areas()

    for entity in entities:
        for area in areas:
            if entity._area_name:
                if entity.area_name.lower() == area.name.lower():
                    entity._area_id = area.id
                    entity._area_name = entity.area_name

    async_add_entities(entities, True)
