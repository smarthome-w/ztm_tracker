"""Config flow for ZTM Tracker custom component."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_RADIUS
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_DEVICE_TRACKERS,
    CONF_DATA_FILE,
    CONF_SHOTS_IN,
    CONF_SHOTS_OUT,
    CONF_AUTOMATIC_INTERVAL,
    CONF_GPS_TIME_OFFSET,
    CONF_LINES_WHITELIST, # Added constant
    DEFAULT_RADIUS,
    DEFAULT_DATA_FILE,
    DEFAULT_SHOTS_IN,
    DEFAULT_SHOTS_OUT,
    DEFAULT_AUTOMATIC_INTERVAL,
    DEFAULT_GPS_TIME_OFFSET,
    DEFAULT_LINES_WHITELIST, # Added default value
)

class ZTMTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ZTM Tracker."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # You might want to add validation here, e.g., for data_file URL
            return self.async_create_entry(title="ZTM Tracker", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_DEVICE_TRACKERS, default=["device_tracker.waldek"]):
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="device_tracker", multiple=True)
                ),
            vol.Optional(CONF_RADIUS, default=DEFAULT_RADIUS): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(CONF_DATA_FILE, default=DEFAULT_DATA_FILE): str,
            vol.Optional(CONF_SHOTS_IN, default=DEFAULT_SHOTS_IN): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(CONF_SHOTS_OUT, default=DEFAULT_SHOTS_OUT): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(CONF_AUTOMATIC_INTERVAL, default=DEFAULT_AUTOMATIC_INTERVAL): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(CONF_GPS_TIME_OFFSET, default=DEFAULT_GPS_TIME_OFFSET): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Optional(CONF_LINES_WHITELIST, default=DEFAULT_LINES_WHITELIST): str # Added here
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )

    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ZTMTrackerOptionsFlow(config_entry)

class ZTMTrackerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ZTM Tracker."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry # Store config_entry for access to data/options

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_data = self.config_entry.data
        current_options = self.config_entry.options

        options_schema = vol.Schema({
            vol.Required(
                CONF_DEVICE_TRACKERS,
                default=current_options.get(CONF_DEVICE_TRACKERS, current_data.get(CONF_DEVICE_TRACKERS, ["device_tracker.waldek"])),
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="device_tracker", multiple=True)
            ),
            vol.Optional(
                CONF_RADIUS,
                default=current_options.get(CONF_RADIUS, current_data.get(CONF_RADIUS, DEFAULT_RADIUS)),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_DATA_FILE,
                default=current_options.get(CONF_DATA_FILE, current_data.get(CONF_DATA_FILE, DEFAULT_DATA_FILE)),
            ): str,
            vol.Optional(
                CONF_SHOTS_IN,
                default=current_options.get(CONF_SHOTS_IN, current_data.get(CONF_SHOTS_IN, DEFAULT_SHOTS_IN)),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_SHOTS_OUT,
                default=current_options.get(CONF_SHOTS_OUT, current_data.get(CONF_SHOTS_OUT, DEFAULT_SHOTS_OUT)),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_AUTOMATIC_INTERVAL,
                default=current_options.get(CONF_AUTOMATIC_INTERVAL, current_data.get(CONF_AUTOMATIC_INTERVAL, DEFAULT_AUTOMATIC_INTERVAL)),
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional(
                CONF_GPS_TIME_OFFSET,
                default=current_options.get(CONF_GPS_TIME_OFFSET, current_data.get(CONF_GPS_TIME_OFFSET, DEFAULT_GPS_TIME_OFFSET)),
            ): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Optional(
                CONF_LINES_WHITELIST, # Added here
                default=current_options.get(CONF_LINES_WHITELIST, current_data.get(CONF_LINES_WHITELIST, DEFAULT_LINES_WHITELIST)), # Added here
            ): str,
        })

        return self.async_show_form(
            step_id="init", data_schema=options_schema
        )
