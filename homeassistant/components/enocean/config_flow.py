"""Config flow to configure the EnOcean component."""
# from operator import itemgetter

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE

from .const import DOMAIN

# from homeassistant.core import callback
# import homeassistant.helpers.config_validation as cv


# _GETKEY = itemgetter(CONF_DEVICE) # (CONF_HOST, CONF_PORT)


@config_entries.HANDLERS.register(DOMAIN)
class EnOceanFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a EnOcean config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Init EnOceanFlowHandler."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            if not self.hass.config_entries.async_entries(CONF_DEVICE):
                return self.async_create_entry(
                    title=user_input[CONF_DEVICE], data=user_input
                )
            self._errors[CONF_DEVICE] = "device_exists"

        return await self._show_config_form(device=None,)

    async def _show_config_form(self, device=None):
        """Show the configuration form to edit location data."""

        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_DEVICE, default=device): str}),
            errors=self._errors,
        )

    # async def async_step_import(self, import_config):
    #     pass
    # #     """Import a config entry from configuration.yaml."""
    # #     if self._async_current_entries():
    # #         return self.async_abort(reason="single_instance_allowed")

    # # #     # entries = self.hass.config_entries.async_entries(DOMAIN)
    # # #     # import_key = _GETKEY(import_config)
    # # #     # for entry in entries:
    # # #     #     if _GETKEY(entry.data) == import_key:
    # # #     #         return self.async_abort(reason="already_setup")

    # #     #return self.async_create_entry(title="configuration.yaml", data=import_config)
    # #     return self.async_abort(reason="no import")

    async def async_step_onboarding(self, data=None):
        """Onboarding."""
        pass

    # # #     """Handle a flow initialized by onboarding."""
    # #     if self._async_current_entries():
    # #         return self.async_abort(reason="single_instance_allowed")
    # #     return self.async_create_entry(
    # #         title="configuration.yaml", data=import_config
    # #     )
