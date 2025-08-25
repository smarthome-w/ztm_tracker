"""Sensor platform for ZTM Tracker."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import ZTMTrackerCoordinator # Corrected import statement

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the ZTM Tracker sensor from a config entry."""
    _LOGGER.debug("Setting up ZTM Tracker sensor platform for entry: %s", config_entry.entry_id)
    coordinator: ZTMTrackerCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Create the sensor entities for each device tracker
    entities = []
    for device_tracker in coordinator.device_trackers:
        # Create the ZTM Events sensor for the device tracker
        entities.append(ZTMTrackerEventsSensor(coordinator, config_entry, device_tracker))
        # Create the Last Route sensor for the device tracker
        entities.append(ZTMTrackerLastRouteSensor(coordinator, config_entry, device_tracker))

    _LOGGER.debug("Adding %d sensor entities.", len(entities))
    async_add_entities(entities)
    _LOGGER.info("ZTM Tracker sensor entities added.")

class ZTMTrackerEventsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a ZTM Tracker Events Sensor."""

    def __init__(self, coordinator: ZTMTrackerCoordinator, config_entry: ConfigEntry, device_tracker_id: str) -> None:
        """Initialize the ZTM Tracker Events sensor."""
        super().__init__(coordinator)
        self._device_tracker_id = device_tracker_id
        self._name = f"ZTM Tracker Events ({device_tracker_id.split('.')[-1]})"
        # The unique_id incorporates the config entry ID and device tracker entity ID
        self._unique_id = f"{config_entry.entry_id}_events_{device_tracker_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name
    
    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        event = self.coordinator.get_current_events().get(self._device_tracker_id)
        if event and event.get('ztm_vehicle'):
            return event['ztm_vehicle'].get('routeShortName')
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        event = self.coordinator.get_current_events().get(self._device_tracker_id)
        if event and event.get('ztm_vehicle'):
            # Return a copy to prevent accidental modification
            attributes = event['ztm_vehicle'].copy()
            attributes['distance'] = f"{event.get('distance', 0):.2f}m"
            _LOGGER.debug("Updating extra_state_attributes for %s: %s", self.unique_id, attributes)
            return attributes
        return {}

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return None 

    @property
    def available(self) -> bool:
        """Return True if the sensor is available. Always available to prevent 'unavailable' state."""
        return True

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        _LOGGER.debug("ZTMTrackerEventsSensor %s async_added_to_hass called.", self.unique_id)
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        _LOGGER.debug("ZTMTrackerEventsSensor %s _handle_coordinator_update called. Coordinator data: %s", self.unique_id, self.coordinator.data)
        self.async_write_ha_state()

class ZTMTrackerLastRouteSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor for the last detected ZTM route."""

    def __init__(self, coordinator: ZTMTrackerCoordinator, config_entry: ConfigEntry, device_tracker_id: str) -> None:
        """Initialize the ZTM Tracker Last Route sensor."""
        super().__init__(coordinator)
        self._device_tracker_id = device_tracker_id
        self._name = f"ZTM Tracker Last Route ({device_tracker_id.split('.')[-1]})"
        self._unique_id = f"{config_entry.entry_id}_last_route_{device_tracker_id}"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID for this entity."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        # Get the last route from the coordinator for the specific device tracker.
        return self.coordinator.get_last_route(self._device_tracker_id)

    @property
    def available(self) -> bool:
        """Return True if the sensor is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
