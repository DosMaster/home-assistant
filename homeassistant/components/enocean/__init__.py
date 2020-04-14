"""Support for EnOcean devices."""
import logging
from typing import Optional  # Any, Callable, Dict, List, Union

from enocean.communicators.serialcommunicator import SerialCommunicator
from enocean.protocol.packet import Packet, RadioPacket
import enocean.utils as eu
from enocean.utils import combine_hex
import voluptuous as vol

from homeassistant import const as ha_const
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_DEVICE
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)

DOMAIN = "enocean"
DATA_ENOCEAN = "enocean"

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_DEVICE): cv.string})}, extra=vol.ALLOW_EXTRA
)

SIGNAL_RECEIVE_MESSAGE = "enocean.receive_message"
SIGNAL_SEND_MESSAGE = "enocean.send_message"

DATA_ENOCEAN_CONFIG = "enocean_config"
DATA_ENOCEAN_HASS_CONFIG = "enocean_hass_config"
DATA_ENOCEAN_CONFIG_ID = "enocean_config_id"
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional("area_name"): cv.string,
        vol.Optional("manufacturer"): cv.string,
        vol.Optional("model"): cv.string,
    }
)

ENOCEAN_COMPONENTS = [
    "binary_sensor",
    "light",
    "sensor",
    "switch",
]


def setup(hass, config):
    """Set up the EnOcean component."""
    """
    serial_dev = config[DOMAIN].get(CONF_DEVICE)
    dongle = EnOceanDongle(hass, serial_dev)
    hass.data[DATA_ENOCEAN] = dongle
    """
    # dm
    _setup_dm(hass, config)

    return True


class EnOceanDongle:
    """Representation of an EnOcean dongle."""

    def __init__(self, hass, ser):
        """Initialize the EnOcean dongle."""

        """
        self.__communicator = SerialCommunicator(port=ser, callback=self.callback)
        self.__communicator.start()
        self.hass = hass
        self.hass.helpers.dispatcher.dispatcher_connect(
            SIGNAL_SEND_MESSAGE, self._send_message_callback
        )
        """
        self.hass = hass
        self.ser = ser
        self._dispatcher_disconnect = None

    async def async_initialize(self):
        """Initialize serial communication."""

        self.__communicator = SerialCommunicator(port=self.ser, callback=self.callback)
        self.__communicator.start()
        self._dispatcher_disconnect = self.hass.helpers.dispatcher.async_dispatcher_connect(
            SIGNAL_SEND_MESSAGE, self._send_message_callback
        )

    def _send_message_callback(self, command):
        """Send a command through the EnOcean dongle."""
        self.__communicator.send(command)

    def callback(self, packet):
        """Handle EnOcean device's callback.

        This is the callback function called by python-enocan whenever there
        is an incoming packet.
        """

        if isinstance(packet, RadioPacket):
            _LOGGER.debug("Received radio packet: %s", packet)
            self.hass.helpers.dispatcher.dispatcher_send(SIGNAL_RECEIVE_MESSAGE, packet)

    # dm
    async def async_reconnect(self):
        """reconnect."""
        pass

    async def async_disconnect(self):
        """disconnect."""
        self._dispatcher_disconnect()
        self.__communicator.stop()
        _LOGGER.info("Serial port closed.")
        pass


class EnOceanDevice(Entity):
    """Parent class for all devices associated with the EnOcean component."""

    def __init__(self, dev_id, dev_name="EnOcean device", orgname=""):
        """Initialize the device."""
        self.dev_id = dev_id
        self.dev_name = dev_name

        # dm
        self._unique_id = eu.to_hex_string(dev_id)
        self._area_id = None
        self._area_name = None
        self._via_device_id = None
        self._manufacturer = None
        self._model = None
        self._unique_id = eu.to_hex_string(dev_id)
        self._dispatcher_disconnect = None
        self.added_to_hass = False

        lastdot = orgname.rfind(".")
        if lastdot >= 0:
            self._unique_id = self._unique_id + "_" + orgname[lastdot + 1 :]
        else:
            self._unique_id = self._unique_id + "_" + orgname

        self._unique_id = self._unique_id + "_" + self.dev_name

        self._unique_id = slugify(self._unique_id)
        a = 0
        if a == 0:
            a = 1

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.added_to_hass = True
        self._dispatcher_disconnect = self.hass.helpers.dispatcher.async_dispatcher_connect(
            SIGNAL_RECEIVE_MESSAGE, self._message_received_callback
        )

    def _message_received_callback(self, packet):
        """Handle incoming packets."""

        if packet.sender_int == combine_hex(self.dev_id):
            self.value_changed(packet)

    def value_changed(self, packet):
        """Update the internal state of the device when a packet arrives."""

    def send_command(self, data, optional, packet_type):
        """Send a command via the EnOcean dongle."""

        if data[0] == 0xF6 or data[0] == 0xD5:
            sender = data[2:6]
        elif data[0] == 0xA5:
            sender = data[5:9]
        else:
            sender = [0x00, 0x00, 0x00, 0x00]

        receiver = [0xFF, 0xFF, 0xFF, 0xFF]

        packet = Packet(packet_type, data=data, optional=optional)
        _LOGGER.debug(
            "Sending radio packet: %s->%s %s",
            eu.to_hex_string(sender),
            eu.to_hex_string(receiver),
            packet,
        )
        self.hass.helpers.dispatcher.dispatcher_send(SIGNAL_SEND_MESSAGE, packet)

        if self.added_to_hass:
            self.schedule_update_ha_state()

    # dm
    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.name, self.unique_id)
            },
            "name": self.name,
            "area_id": self.area_id,
            "via_device_id": self.via_device_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
        }

    # dm
    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    # dm
    @property
    def area_name(self):
        """Return the area id."""
        return self._area_name

    # dm
    @property
    def area_id(self):
        """Return the area id."""
        return self._area_id

    # dm
    @property
    def via_device_id(self):
        """Return the area id."""
        return self._via_device_id

    # dm
    @property
    def manufacturer(self):
        """Return the area id."""
        return self._manufacturer

    # dm
    @property
    def model(self):
        """Return the area id."""
        return self._model

    # dm
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""

        if self.dev_name in self.platform.entities:
            del self.platform.entities[self.dev_name]

        # self.platform.entities.pop(self)

        if self._dispatcher_disconnect is not None:
            self._dispatcher_disconnect()

        pass

        # # Only go further if the device/entity should be removed from registries
        # # due to a removal of the HmIP device.
        # if self.hmip_device_removed:
        #     del self._hap.hmip_device_by_entity_id[self.entity_id]
        #     await self.async_remove_from_registries()

    # dm
    async def async_remove_from_registries(self) -> None:
        """Remove entity/device from registry."""
        pass

        # # Remove callback from device.
        # self._device.remove_callback(self._async_device_changed)
        # self._device.remove_callback(self._async_device_removed)

        # if not self.registry_entry:
        #     return

        # device_id = self.registry_entry.device_id
        # if device_id:
        #     # Remove from device registry.
        #     device_registry = await dr.async_get_registry(self.hass)
        #     if device_id in device_registry.devices:
        #         # This will also remove associated entities from entity registry.
        #         device_registry.async_remove_device(device_id)
        # else:
        #     # Remove from entity registry.
        #     # Only relevant for entities that do not belong to a device.
        #     entity_id = self.registry_entry.entity_id
        #     if entity_id:
        #         entity_registry = await er.async_get_registry(self.hass)
        #         if entity_id in entity_registry.entities:
        #             entity_registry.async_remove(entity_id)

    # dm
    @callback
    def _async_device_removed(self, *args, **kwargs) -> None:
        """Handle hmip device removal."""
        pass

        # # Set marker showing that the HmIP device hase been removed.
        # self.hmip_device_removed = True
        # self.hass.async_create_task(self.async_remove())

    # dm
    @callback
    def _async_device_changed(self, *args, **kwargs) -> None:
        """Handle device state changes."""
        pass

        # # Don't update disabled entities
        # if self.enabled:
        #     _LOGGER.debug("Event %s (%s)", self.name, self._device.modelType)
        #     self.async_schedule_update_ha_state()
        # else:
        #     _LOGGER.debug(
        #         "Device Changed Event for %s (%s) not fired. Entity is disabled.",
        #         self.name,
        #         self._device.modelType,
        #     )


# dm
async def async_setup(hass, config):
    """Set up configured EnOcean."""

    # result = await hass.async_add_executor_job(
    #     component.setup, hass, processed_config  # type: ignore
    # )

    # if not hass.config_entries.async_entries(DOMAIN):
    #     hass.async_create_task(
    #         hass.config_entries.flow.async_init(
    #             DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={"Device": serial_dev}
    #         )
    #     )

    # serial_dev = config[DOMAIN].get(CONF_DEVICE)
    # dongle = EnOceanDongle(hass, serial_dev)
    # hass.data[DATA_ENOCEAN] = dongle

    # result = await hass.async_add_executor_job(_setup_dm(hass, config))

    return True


async def async_setup_entry(hass, config_entry):
    """Set up configured EnOcean."""

    # conf = hass.data.get(DATA_ENOCEAN_CONFIG)

    # # Config entry was created because user had configuration.yaml entry
    # # They removed that, so remove entry.
    # if conf is None and config_entry.source == config_entries.SOURCE_IMPORT:
    #     hass.async_create_task(hass.config_entries.async_remove(config_entry.entry_id))
    #     return False

    # areas = await async_get_registry(hass)

    # hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setup(config_entry, "binary_sensor")
    # )
    # hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setup(config_entry, "light")
    # )
    # hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    # )
    # hass.async_create_task(
    #     hass.config_entries.async_forward_entry_setup(config_entry, "switch")
    # )

    # serial_dev = config[DOMAIN].get(CONF_DEVICE)
    serial_dev = config_entry.data.get(CONF_DEVICE)
    dongle = EnOceanDongle(hass, serial_dev)
    await dongle.async_initialize()
    hass.data[DATA_ENOCEAN] = dongle

    # Set up platforms
    for component in ENOCEAN_COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )
        _LOGGER.debug("Component %s setup started.", component)

    async def async_enocean_shutdown(event):
        """Handle shutdown tasks."""
        dongle = hass.data.get(DATA_ENOCEAN)
        if isinstance(dongle, EnOceanDongle):
            await dongle.async_disconnect()
            hass.data.pop(DATA_ENOCEAN)

    hass.bus.async_listen_once(
        ha_const.EVENT_HOMEASSISTANT_STOP, async_enocean_shutdown
    )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload configured EnOcean."""
    # hass.data.pop(DATA_ENOCEAN)
    # hass.data.pop(DATA_ENOCEAN_HASS_CONFIG)
    # hass.data.pop(DATA_ENOCEAN_CONFIG)

    # dongle = hass.data.get(DATA_ENOCEAN)
    # if isinstance(dongle, EnOceanDongle):
    #     await dongle.disconnect()
    #     hass.data.pop(DATA_ENOCEAN)
    #     # hass.data.pop(DATA_ENOCEAN_HASS_CONFIG)
    #     # hass.data.pop(DATA_ENOCEAN_CONFIG)

    # await hass.config_entries.async_forward_entry_unload(config_entry, "binary_sensor")
    # await hass.config_entries.async_forward_entry_unload(config_entry, "light")
    # await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    # await hass.config_entries.async_forward_entry_unload(config_entry, "switch")

    # Unload up platforms
    # for component in ENOCEAN_COMPONENTS:
    #     await hass.config_entries.async_forward_entry_unload(config_entry, component)
    #     _LOGGER.debug("Component %s unloaded.", component)

    return True


async def async_remove_entry(hass, entry) -> None:
    """Handle removal of an entry."""
    return True


def _setup_dm(hass, config):
    """Set up the EnOcean component."""

    if hass.config_entries.async_entries(DOMAIN):
        pass
    else:
        conf: Optional[ConfigType] = config.get(DOMAIN)

        if conf:
            serial_dev = config[DOMAIN].get(CONF_DEVICE)
            dongle = EnOceanDongle(hass, serial_dev)
            hass.data[DATA_ENOCEAN] = dongle

    # # We need this because discovery can cause components to be set up and
    # # otherwise it will not load the users config.
    # # This needs a better solution.
    # hass.data[DATA_ENOCEAN_HASS_CONFIG] = config

    # if conf is None:
    #     # If we have a config entry, setup is done by that config entry.
    #     # If there is no config entry, this should fail.
    #     return bool(hass.config_entries.async_entries(DOMAIN))

    # conf = dict(conf)

    # hass.data[DATA_ENOCEAN_CONFIG] = conf

    return True
