"""The ZTM Tracker custom component."""
import asyncio
import logging
from datetime import timedelta, datetime
import math
import zoneinfo # For timezone handling (Python 3.9+)

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_RADIUS, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import async_track_state_change, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import aiohttp_client

from .const import (
    DOMAIN,
    CONF_DEVICE_TRACKERS,
    CONF_DATA_FILE,
    CONF_SHOTS_IN,
    CONF_SHOTS_OUT,
    CONF_AUTOMATIC_INTERVAL,
    CONF_GPS_TIME_OFFSET,
    CONF_LINES_WHITELIST,
    DEFAULT_RADIUS,
    DEFAULT_DATA_FILE,
    DEFAULT_SHOTS_IN,
    DEFAULT_SHOTS_OUT,
    DEFAULT_AUTOMATIC_INTERVAL,
    DEFAULT_GPS_TIME_OFFSET,
    DEFAULT_LINES_WHITELIST,
)

_LOGGER = logging.getLogger(__name__)

# Constants for Earth's radius in meters for Haversine formula
EARTH_RADIUS_METERS = 6371000

# Define the CET timezone
try:
    CET_TIMEZONE = zoneinfo.ZoneInfo("Europe/Warsaw") # Poland's timezone, which uses CET/CEST
except zoneinfo.ZoneInfoNotFoundError:
    _LOGGER.error("Timezone 'Europe/Warsaw' not found. This might be a problem with the system's timezone data.")
    CET_TIMEZONE = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up ZTM Tracker from a config entry."""
    _LOGGER.debug("Setting up ZTM Tracker component from config entry.")
    hass.data.setdefault(DOMAIN, {})

    coordinator = ZTMTrackerCoordinator(hass, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
        await coordinator.async_init_listeners()
    except ConfigEntryNotReady as ex:
        _LOGGER.error("ZTM Tracker failed to initialize: %s", ex)
        raise
    except Exception as ex:
        _LOGGER.error("ZTM Tracker failed to initialize due to unexpected error: %s", ex)
        raise ConfigEntryNotReady(f"Failed to initialize ZTM Tracker: {ex}") from ex

    hass.data[DOMAIN][entry.entry_id] = coordinator

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    )

    entry.add_update_listener(async_reload_entry)

    _LOGGER.info("ZTM Tracker component setup complete.")
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.debug("ZTM Tracker: Entering async_unload_entry.")
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        coordinator: ZTMTrackerCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        if coordinator:
            coordinator.async_unload()
        _LOGGER.info("ZTM Tracker config entry unloaded.")
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    _LOGGER.info("Reloading ZTM Tracker config entry.")
    await async_unload_entry(hass, entry)
    hass.config_entries.async_setup(entry.entry_id)

class ZTMTrackerCoordinator(DataUpdateCoordinator):
    """My custom coordinator for the ZTM Tracker."""

    def __init__(self, hass, config_entry):
        """Initialize my coordinator."""
        self.config_entry = config_entry
        self.hass = hass
        self.device_trackers = self.config_entry.options.get(CONF_DEVICE_TRACKERS, self.config_entry.data.get(CONF_DEVICE_TRACKERS))
        self.radius = self.config_entry.options.get(CONF_RADIUS, self.config_entry.data.get(CONF_RADIUS, DEFAULT_RADIUS))
        self.data_file = self.config_entry.options.get(CONF_DATA_FILE, self.config_entry.data.get(CONF_DATA_FILE, DEFAULT_DATA_FILE))
        self.shots_in = self.config_entry.options.get(CONF_SHOTS_IN, self.config_entry.data.get(CONF_SHOTS_IN, DEFAULT_SHOTS_IN))
        self.shots_out = self.config_entry.options.get(CONF_SHOTS_OUT, self.config_entry.data.get(CONF_SHOTS_OUT, DEFAULT_SHOTS_OUT))
        self.automatic_interval = self.config_entry.options.get(CONF_AUTOMATIC_INTERVAL, self.config_entry.data.get(CONF_AUTOMATIC_INTERVAL, DEFAULT_AUTOMATIC_INTERVAL))
        self.gps_time_offset = self.config_entry.options.get(CONF_GPS_TIME_OFFSET, self.config_entry.data.get(CONF_GPS_TIME_OFFSET, DEFAULT_GPS_TIME_OFFSET))
        self.lines_whitelist = self.config_entry.options.get(CONF_LINES_WHITELIST, self.config_entry.data.get(CONF_LINES_WHITELIST, DEFAULT_LINES_WHITELIST))
        
        # Internal state
        self._vehicle_data = {}
        self._tracker_locations = {}
        self._last_route_seen = {}
        self._event_data = {}

        # Listeners for device tracker state changes
        self._listeners = []
        self._state_change_listener_handles = []
        self._time_listener_handle = None

        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            # Update interval. Optional.
            update_interval=timedelta(minutes=self.automatic_interval),
        )

    def async_unload(self):
        """Unload the listeners."""
        for unsubscribe in self._state_change_listener_handles:
            unsubscribe()
        self._state_change_listener_handles = []
        if self._time_listener_handle:
            self._time_listener_handle()
            self._time_listener_handle = None

    def get_current_events(self):
        """Return the current events data."""
        return self._event_data

    def get_last_route(self, device_tracker_id):
        """Return the last seen route for a given device tracker."""
        return self._last_route_seen.get(device_tracker_id, "Unknown")

    async def async_init_listeners(self):
        """Set up all listeners."""
        _LOGGER.debug("Initializing listeners.")
        # We need to wait for the device trackers to become available
        await self._async_wait_for_device_trackers()

        # Listen for state changes on each configured device tracker
        self._state_change_listener_handles = async_track_state_change(
            self.hass, self.device_trackers, self._async_device_tracker_state_change
        )
        
        # Set up a time listener to force a data update
        self._time_listener_handle = async_track_time_interval(
            self.hass, self._async_time_listener, timedelta(minutes=self.automatic_interval)
        )
        _LOGGER.info("Listeners initialized successfully.")

    async def _async_wait_for_device_trackers(self):
        """Wait for the initial states of device trackers to be available."""
        _LOGGER.debug("Waiting for initial device tracker states...")
        max_attempts = 10
        attempt = 0
        while attempt < max_attempts:
            all_available = True
            for tracker_id in self.device_trackers:
                state = self.hass.states.get(tracker_id)
                if state is None or state.state == STATE_UNAVAILABLE:
                    all_available = False
                    break
            if all_available:
                _LOGGER.debug("All device trackers available. Proceeding.")
                return
            await asyncio.sleep(1)
            attempt += 1
        
        _LOGGER.warning("Timed out waiting for device trackers to become available. Some trackers might be unavailable.")


    async def _async_device_tracker_state_change(self, entity_id, old_state, new_state):
        """Handle device tracker state changes."""
        _LOGGER.debug("State change detected for %s.", entity_id)
        if new_state is None or new_state.state == STATE_UNAVAILABLE:
            _LOGGER.debug("New state for %s is unavailable, skipping update.", entity_id)
            return

        latitude = new_state.attributes.get('latitude')
        longitude = new_state.attributes.get('longitude')

        if latitude is not None and longitude is not None:
            self._tracker_locations[entity_id] = {'latitude': latitude, 'longitude': longitude}
            _LOGGER.debug("Location updated for %s: %s", entity_id, self._tracker_locations[entity_id])
            await self.async_request_refresh()
        else:
            _LOGGER.warning("State change for %s has no latitude or longitude.", entity_id)


    async def _async_time_listener(self, now):
        """Handle a time-based refresh."""
        _LOGGER.debug("Time listener triggered at %s. Requesting refresh.", now)
        await self.async_request_refresh()


    async def _async_update_data(self):
        """Fetch data from ZTM API and process it."""
        _LOGGER.debug("Starting data update from ZTM API.")
        
        # First, update vehicle data
        await self._async_fetch_vehicle_data()
        
        # Then, process events based on tracker locations and vehicle data
        self._async_process_events()
        
        # Return event data for the coordinator's use
        return self._event_data

    async def _async_fetch_vehicle_data(self):
        """Fetch real-time vehicle data from the ZTM API."""
        try:
            websession = aiohttp_client.async_get_clientsession(self.hass)
            
            # Use aiohttp client for fetching data
            async with async_timeout.timeout(30):
                response = await websession.get(self.data_file)
                response.raise_for_status()
                data = await response.json()
            
            if data and 'vehicles' in data:
                # Store the raw vehicle data, using 'vehicleId' as the key
                # Corrected to use lowercase 'vehicles' and 'vehicleId'
                self._vehicle_data = {v.get('vehicleId'): v for v in data.get('vehicles', [])}
                _LOGGER.info("Successfully fetched %d vehicle entries.", len(self._vehicle_data))
            else:
                _LOGGER.warning("ZTM API returned no vehicle data.")

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching data from ZTM API: {err}") from err
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout while fetching data from ZTM API.")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error while fetching data: {err}") from err

    def _async_process_events(self):
        """Process events based on vehicle and device tracker data."""
        new_event_data = {}
        for tracker_id, tracker_location in self._tracker_locations.items():
            _LOGGER.debug("Processing events for tracker %s at location %s.", tracker_id, tracker_location)
            
            # Get the friendly name of the device tracker
            tracker_state = self.hass.states.get(tracker_id)
            tracker_name = tracker_state.name if tracker_state and tracker_state.name else tracker_id
            
            # Find the closest vehicle for this tracker
            closest_vehicle = self._find_closest_vehicle(tracker_location)
            
            if closest_vehicle:
                vehicle_id = closest_vehicle.get('vehicleId')
                distance_to_vehicle = closest_vehicle.get('distance')
                
                # Check for "shots in" condition
                if distance_to_vehicle <= self.radius:
                    _LOGGER.info("Vehicle %s is within radius for tracker %s.", vehicle_id, tracker_id)
                    
                    # Update the last seen route immediately upon detection
                    route = closest_vehicle.get('routeShortName', 'Unknown')
                    new_last_route = f"{tracker_name} - {route}"
                    if self._last_route_seen.get(tracker_id) != new_last_route:
                        self._last_route_seen[tracker_id] = new_last_route
                        _LOGGER.info("Last route for tracker %s updated to: %s", tracker_id, new_last_route)
                    
                    # Check if this vehicle has already been seen by this tracker
                    if self._event_data.get(tracker_id) and self._event_data[tracker_id].get('vehicle') == vehicle_id:
                        # Increment 'shots_in' count
                        shots_in = self._event_data[tracker_id].get('shots_in', 0) + 1
                        _LOGGER.debug("Incrementing shots_in for tracker %s. New count: %d", tracker_id, shots_in)
                        new_event_data[tracker_id] = {
                            'vehicle': vehicle_id,
                            'shots_in': shots_in,
                            'shots_out': 0, # Reset shots_out
                            'ztm_vehicle': closest_vehicle, # Keep a reference to the vehicle data
                            'event_summary': f"Tracker {tracker_name} is near route {route}"
                        }
                    else:
                        # First time seeing this vehicle, create a new event
                        _LOGGER.info("New vehicle %s detected within radius for tracker %s.", vehicle_id, tracker_id)
                        new_event_data[tracker_id] = {
                            'vehicle': vehicle_id,
                            'shots_in': 1,
                            'shots_out': 0,
                            'ztm_vehicle': closest_vehicle,
                            'event_summary': f"Tracker {tracker_name} is near route {route}"
                        }

                else: # Vehicle is outside the radius
                    # Check if there was a previous event for this tracker
                    if self._event_data.get(tracker_id):
                        shots_out = self._event_data[tracker_id].get('shots_out', 0) + 1
                        _LOGGER.debug("Incrementing shots_out for tracker %s. New count: %d", tracker_id, shots_out)
                        
                        # Continue the event if shots_out limit is not reached
                        if shots_out < self.shots_out:
                            _LOGGER.debug("Tracker %s is moving away, but event continues.", tracker_id)
                            new_event_data[tracker_id] = {
                                'vehicle': self._event_data[tracker_id].get('vehicle'),
                                'shots_in': self._event_data[tracker_id].get('shots_in', 0),
                                'shots_out': shots_out,
                                'ztm_vehicle': self._event_data[tracker_id].get('ztm_vehicle'),
                                'event_summary': self._event_data[tracker_id].get('event_summary')
                            }
                        else:
                            # Event is considered ended
                            _LOGGER.info("Event ended for tracker %s. Vehicle %s is too far away.", tracker_id, self._event_data[tracker_id].get('vehicle'))
                            # The event is not added to new_event_data, so it will be removed.
            else:
                _LOGGER.debug("No vehicles found for tracker %s.", tracker_id)
                # If there was a previous event, start counting shots out
                if self._event_data.get(tracker_id):
                    shots_out = self._event_data[tracker_id].get('shots_out', 0) + 1
                    if shots_out < self.shots_out:
                         _LOGGER.debug("Tracker %s is far from any vehicle, but event continues.", tracker_id)
                         new_event_data[tracker_id] = {
                            'vehicle': self._event_data[tracker_id].get('vehicle'),
                            'shots_in': self._event_data[tracker_id].get('shots_in', 0),
                            'shots_out': shots_out,
                            'ztm_vehicle': self._event_data[tracker_id].get('ztm_vehicle'),
                            'event_summary': self._event_data[tracker_id].get('event_summary')
                        }
                    else:
                        _LOGGER.info("Event ended for tracker %s. No vehicle nearby.", tracker_id)
        
        # Update the main event data dictionary
        self._event_data = new_event_data
        _LOGGER.info("Event processing complete. Found %d active events.", len(self._event_data))


    def _find_closest_vehicle(self, tracker_location):
        """Find the closest vehicle to a given tracker location, respecting filters."""
        if not self._vehicle_data:
            _LOGGER.debug("No vehicle data available.")
            return None

        # Prepare whitelist
        lines_whitelist = {line.strip() for line in self.lines_whitelist.split(',') if line.strip()}
        
        min_distance = float('inf')
        closest_vehicle = None

        for vehicle in self._vehicle_data.values():
            # Corrected to use lowercase keys
            vehicle_lat = vehicle.get('lat')
            vehicle_lon = vehicle.get('lon')
            vehicle_route = vehicle.get('routeShortName')
            # Updated to use the correct field name 'generated' for the timestamp, based on user feedback.
            vehicle_gps_timestamp_str = vehicle.get('generated')

            if vehicle_lat is None or vehicle_lon is None or vehicle_route is None or vehicle_gps_timestamp_str is None:
                _LOGGER.debug("Skipping vehicle due to missing data: %s", vehicle)
                continue

            # Apply lines whitelist filter
            if lines_whitelist and vehicle_route not in lines_whitelist:
                _LOGGER.debug("Skipping vehicle with route '%s' as it's not in the whitelist: %s", vehicle_route, lines_whitelist)
                continue

            # Apply GPS time offset filter
            if CET_TIMEZONE:
                try:
                    # Parse the ISO 8601 string to a datetime object. The 'Z' at the end indicates UTC.
                    gps_time = datetime.fromisoformat(vehicle_gps_timestamp_str.replace('Z', '+00:00')).astimezone(CET_TIMEZONE)
                    current_time = datetime.now(CET_TIMEZONE)
                    time_diff = abs((current_time - gps_time).total_seconds())

                    if time_diff > self.gps_time_offset:
                        _LOGGER.debug("Skipping vehicle %s due to GPS time offset. Diff: %s", vehicle.get('vehicleId'), time_diff)
                        continue
                except (ValueError, TypeError) as e:
                    _LOGGER.warning("Could not parse GPS timestamp for vehicle %s: %s", vehicle.get('vehicleId'), e)
                    continue

            # Calculate distance using the Haversine formula
            distance = self._haversine(
                tracker_location['latitude'],
                tracker_location['longitude'],
                vehicle_lat,
                vehicle_lon
            )

            if distance < min_distance:
                min_distance = distance
                closest_vehicle = vehicle
                closest_vehicle['distance'] = distance # Add distance to the vehicle dict

        _LOGGER.debug("Closest vehicle found: %s with distance: %s", closest_vehicle.get('vehicleId') if closest_vehicle else "None", min_distance if closest_vehicle else "N/A")
        
        return closest_vehicle

    def _haversine(self, lat1, lon1, lat2, lon2):
        """
        Calculate the distance between two points on Earth using the Haversine formula.
        Returns distance in meters.
        """
        # Convert degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = EARTH_RADIUS_METERS * c
        
        return distance
