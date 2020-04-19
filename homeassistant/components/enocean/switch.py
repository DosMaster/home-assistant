"""Support for EnOcean switches."""
import logging

import voluptuous as vol

# dm
# from homeassistant.components.switch import PLATFORM_SCHEMA #dm
from homeassistant.components import enocean
from homeassistant.components.enocean import PLATFORM_SCHEMA
from homeassistant.const import CONF_DEVICE_CLASS, CONF_ID, CONF_NAME, STATE_ON  # dm
import homeassistant.helpers.area_registry as ar
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import ToggleEntity
from homeassistant.helpers.restore_state import RestoreEntity  # dm

_LOGGER = logging.getLogger(__name__)

CONF_CHANNEL = "channel"
DEFAULT_NAME = "EnOcean Switch"

CONF_SENDER_ID = "sender_id"
DEVICE_CLASS_SWITCH = "switch"
DEVICE_CLASS_SWITCH_ELTAKO = "switch_eltako"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_CHANNEL, default=0): cv.positive_int,
        vol.Optional(CONF_DEVICE_CLASS, default=DEVICE_CLASS_SWITCH): cv.string,  # dm
        vol.Optional(CONF_SENDER_ID): vol.All(cv.ensure_list, [vol.Coerce(int)]),  # dm
    }
)

entities = []


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the EnOcean switch platform."""
    channel = config.get(CONF_CHANNEL)
    dev_id = config.get(CONF_ID)
    dev_name = config.get(CONF_NAME)
    dev_class = config.get(CONF_DEVICE_CLASS)  # dm

    # add_entities([EnOceanSwitch(dev_id, dev_name, channel)]) #dm

    # dm
    if dev_class == DEVICE_CLASS_SWITCH:
        entity = EnOceanSwitch(dev_id, dev_name, channel)
    elif dev_class == DEVICE_CLASS_SWITCH_ELTAKO:
        sender_id = config.get(CONF_SENDER_ID)
        entity = EnOceanSwitchEltako(dev_id, dev_name, channel, sender_id)
    setup_platform_dm(hass, config, add_entities, entity)


class EnOceanSwitch(enocean.EnOceanDevice, ToggleEntity, RestoreEntity):
    """Representation of an EnOcean switch device."""

    def __init__(self, dev_id, dev_name, channel):
        """Initialize the EnOcean switch device."""
        super().__init__(dev_id, dev_name)
        self._light = None
        self._on_state = False
        self._on_state2 = False
        self.channel = channel

        # dm
        if self.channel:
            self._unique_id = self._unique_id + channel

    @property
    def is_on(self):
        """Return whether the switch is on or off."""
        return self._on_state

    @property
    def name(self):
        """Return the device name."""
        return self.dev_name

    def turn_on(self, **kwargs):
        """Turn on the switch."""
        optional = [0x03]
        optional.extend(self.dev_id)
        optional.extend([0xFF, 0x00])
        self.send_command(
            data=[0xD2, 0x01, self.channel & 0xFF, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00],
            optional=optional,
            packet_type=0x01,
        )
        self._on_state = True

        # dm
        if self.added_to_hass:
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off the switch."""
        optional = [0x03]
        optional.extend(self.dev_id)
        optional.extend([0xFF, 0x00])
        self.send_command(
            data=[0xD2, 0x01, self.channel & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            optional=optional,
            packet_type=0x01,
        )
        self._on_state = False

        # dm
        if self.added_to_hass:
            self.schedule_update_ha_state()

    def value_changed(self, packet):
        """Update the internal state of the switch."""
        if packet.data[0] == 0xA5:
            # power meter telegram, turn on if > 10 watts
            packet.parse_eep(0x12, 0x01)
            if packet.parsed["DT"]["raw_value"] == 1:
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                watts = raw_val / (10 ** divisor)
                if watts > 1:
                    self._on_state = True
                    self.schedule_update_ha_state()
        elif packet.data[0] == 0xD2:
            # actuator status telegram
            packet.parse_eep(0x01, 0x01)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    self._on_state = output > 0
                    if self.added_to_hass:  # dm
                        self.schedule_update_ha_state()

    # dm
    async def async_added_to_hass(self):
        """Restore device state (ON/OFF/Brightness)."""
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()

        if old_state is not None:
            self._on_state = old_state.state == STATE_ON

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attr = {}
        return attr


# dm
class EnOceanSwitchEltako(enocean.EnOceanDevice, ToggleEntity, RestoreEntity):
    """Representation of an EnOcean switch device."""

    def __init__(self, dev_id, dev_name, channel, sender_id):
        """Initialize the EnOcean switch device."""
        super().__init__(dev_id, dev_name, __name__)
        self._light = None
        self._on_state = False
        self._on_state2 = False
        self.channel = channel
        self._sender_id = sender_id

        if self._sender_id is None:
            self._sender_id = dev_id

        if channel:
            self._unique_id = self._unique_id + "_" + str(channel)

    @property
    def is_on(self):
        """Return whether the switch is on or off."""
        return self._on_state

    @property
    def name(self):
        """Return the device name."""
        return self.dev_name

    def turn_on(self, **kwargs):
        """Turn on the switch."""
        if self.channel == 0:
            data = 0x70
        elif self.channel == 1:
            data = 0x30
        elif self.channel == 10:
            data = 0x37
        else:
            data = 0x00

        if data > 0x00:
            command = [0xF6, data]
            command.extend(self._sender_id)
            command.extend([0x00])
            self.send_command(command, [], 0x01)
            command = [0xF6, 0x00]
            command.extend(self._sender_id)
            command.extend([0x00])
            self.send_command(command, [], 0x01)
            self._on_state = True
        else:
            _LOGGER.error("Unsupported channel: %s (%s)", self.channel, self.dev_name)

        # dm
        if self.added_to_hass:
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn off the switch."""
        if self.channel == 0:
            data = 0x50
        elif self.channel == 1:
            data = 0x10
        elif self.channel == 10:
            data = 0x15
        else:
            data = 0x00

        if data > 0x00:
            command = [0xF6, data]
            command.extend(self._sender_id)
            command.extend([0x00])
            self.send_command(command, [], 0x01)
            command = [0xF6, 0x00]
            command.extend(self._sender_id)
            command.extend([0x00])
            self.send_command(command, [], 0x01)
            self._on_state = False
        else:
            _LOGGER.error("Unsupported channel: %s (%s)", self.channel, self.dev_name)

        # dm
        if self.added_to_hass:
            self.schedule_update_ha_state()

    def value_changed(self, packet):
        """Update the internal state of the switch."""
        if packet.data[0] == 0xA5:
            # power meter telegram, turn on if > 10 watts
            packet.parse_eep(0x12, 0x01)
            if packet.parsed["DT"]["raw_value"] == 1:
                raw_val = packet.parsed["MR"]["raw_value"]
                divisor = packet.parsed["DIV"]["raw_value"]
                watts = raw_val / (10 ** divisor)
                if watts > 1:
                    self._on_state = True
                    self.schedule_update_ha_state()
        elif packet.data[0] == 0xD2:
            # actuator status telegram
            packet.parse_eep(0x01, 0x01)
            if packet.parsed["CMD"]["raw_value"] == 4:
                channel = packet.parsed["IO"]["raw_value"]
                output = packet.parsed["OV"]["raw_value"]
                if channel == self.channel:
                    self._on_state = output > 0
                    self.schedule_update_ha_state()
        elif packet.data[0] == 0xF6:
            # rocker switch telegram
            packet.parse_eep(0x02, 0x02)
            rocker_action = (
                (packet.parsed["R1"]["raw_value"] << 5)
                + (packet.parsed["EB"]["raw_value"] << 4)
                + (packet.parsed["R2"]["raw_value"] << 1)
                + packet.parsed["SA"]["raw_value"]
            )
            if rocker_action == 0x70:
                self._on_state = True
                channel = 0
            elif rocker_action == 0x30:
                self._on_state = True
                channel = 1
            elif rocker_action == 0x37:
                self._on_state = True
                channel = 10
            elif rocker_action == 0x50:
                self._on_state = False
                channel = 0
            elif rocker_action == 0x10:
                self._on_state = False
                channel = 1
            elif rocker_action == 0x15:
                self._on_state = False
                channel = 10
            else:
                self._on_state = False
                channel = 99

        if channel == self.channel:
            if self.added_to_hass:  # dm
                self.schedule_update_ha_state()

    # dm
    async def async_added_to_hass(self):
        """Restore device state (ON/OFF/Brightness)."""
        await super().async_added_to_hass()

        old_state = await self.async_get_last_state()

        if old_state is not None:
            self._on_state = old_state.state == STATE_ON

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        attr = {}
        return attr


# dm
def setup_platform_dm(hass, config, add_entities, entity):
    """Set platform entry."""
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
