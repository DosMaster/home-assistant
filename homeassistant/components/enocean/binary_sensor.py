"""Support for EnOcean binary sensors."""
import logging

import voluptuous as vol

from homeassistant.components import enocean
from homeassistant.components.binary_sensor import (  # PLATFORM_SCHEMA,
    DEVICE_CLASSES_SCHEMA,
    BinarySensorDevice,
)
from homeassistant.components.enocean import PLATFORM_SCHEMA
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ID, CONF_NAME
import homeassistant.helpers.area_registry as ar
import homeassistant.helpers.config_validation as cv

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "EnOcean binary sensor"
DEPENDENCIES = ["enocean"]
EVENT_BUTTON_PRESSED = "button_pressed"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    }
)

entities = {}


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Binary Sensor platform for EnOcean."""

    """Ignore if no config entry exist"""
    if not hass.config_entries.async_entries(DOMAIN):
        return

    dev_id = config.get(CONF_ID)
    dev_name = config.get(CONF_NAME)
    device_class = config.get(CONF_DEVICE_CLASS)

    """
    add_entities([EnOceanBinarySensor(dev_id, dev_name, device_class)])
    """

    # dm
    entity = EnOceanBinarySensor(dev_id, dev_name, device_class)
    setup_platform_dm(hass, config, add_entities, entity)


class EnOceanBinarySensor(enocean.EnOceanDevice, BinarySensorDevice):
    """Representation of EnOcean binary sensors such as wall switches.

    Supported EEPs (EnOcean Equipment Profiles):
    - F6-02-01 (Light and Blind Control - Application Style 2)
    - F6-02-02 (Light and Blind Control - Application Style 1)
    """

    def __init__(self, dev_id, dev_name, device_class):
        """Initialize the EnOcean binary sensor."""
        super().__init__(dev_id, dev_name, __name__)  # dm
        self._device_class = device_class
        self.which = -1
        self.onoff = -1

    @property
    def name(self):
        """Return the default name for the binary sensor."""
        return self.dev_name

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._device_class

    def value_changed(self, packet):
        """Fire an event with the data that have changed.

        This method is called when there is an incoming packet associated
        with this platform.

        Example packet data:
        - 2nd button pressed
            ['0xf6', '0x10', '0x00', '0x2d', '0xcf', '0x45', '0x30']
        - button released
            ['0xf6', '0x00', '0x00', '0x2d', '0xcf', '0x45', '0x20']
        """
        # Energy Bow
        pushed = None

        if packet.data[6] == 0x30:
            pushed = 1
        elif packet.data[6] == 0x20:
            pushed = 0

        self.schedule_update_ha_state()

        action = packet.data[1]
        if action == 0x70:
            self.which = 0
            self.onoff = 0
        elif action == 0x50:
            self.which = 0
            self.onoff = 1
        elif action == 0x30:
            self.which = 1
            self.onoff = 0
        elif action == 0x10:
            self.which = 1
            self.onoff = 1
        elif action == 0x37:
            self.which = 10
            self.onoff = 0
        elif action == 0x15:
            self.which = 10
            self.onoff = 1
        elif action == 0x00:
            self.which = -1
            self.onoff = -1
        self.hass.bus.fire(
            EVENT_BUTTON_PRESSED,
            {
                "id": self.dev_id,
                "pushed": pushed,
                "which": self.which,
                "onoff": self.onoff,
            },
        )


# dm
def setup_platform_dm(hass, config, add_entities, entity):
    """Set up platform entry."""
    entity._area_name = config.get("area_name")
    entity._manufacturer = config.get("manufacturer")
    entity._model = config.get("model")
    entities[entity.dev_name] = entity


# dm
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the EnOcean config entry."""

    area_registry = await ar.async_get_registry(hass)

    areas = area_registry.async_list_areas()

    for key, entity in entities.items():
        for area in areas:
            if entity._area_name:
                if entity.area_name.lower() == area.name.lower():
                    entity._area_id = area.id
                    entity._area_name = entity.area_name
        _LOGGER.debug("Adding entity: %s", entity.dev_name)

    async_add_entities(entities.values(), True)
