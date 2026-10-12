"""Unit tests for the ZTM Tracker coordinator."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.ztm_tracker import ZTMTrackerCoordinator
from custom_components.ztm_tracker.const import (
    CONF_AUTOMATIC_INTERVAL,
    CONF_DATA_FILE,
    CONF_DEVICE_TRACKERS,
    CONF_GPS_TIME_OFFSET,
    CONF_LINES_WHITELIST,
    CONF_RADIUS,
    CONF_SHOTS_IN,
    CONF_SHOTS_OUT,
)


def _make_entry():
    """Build a minimal config entry-like object for coordinator tests."""
    return SimpleNamespace(
        options={},
        data={
            CONF_DEVICE_TRACKERS: ["device_tracker.home"],
            CONF_RADIUS: 50,
            CONF_DATA_FILE: "https://example.com/data",
            CONF_SHOTS_IN: 2,
            CONF_SHOTS_OUT: 3,
            CONF_AUTOMATIC_INTERVAL: 5,
            CONF_GPS_TIME_OFFSET: 120,
            CONF_LINES_WHITELIST: "1,2,5",
        },
        entry_id="entry-123",
    )


def _make_coordinator():
    """Create a coordinator instance without triggering Home Assistant's coordinator init."""
    hass = MagicMock()
    hass.states = {
        "device_tracker.home": SimpleNamespace(name="Home", state="home"),
    }
    entry = _make_entry()

    coordinator = object.__new__(ZTMTrackerCoordinator)
    coordinator.config_entry = entry
    coordinator.hass = hass
    coordinator.device_trackers = entry.data[CONF_DEVICE_TRACKERS]
    coordinator.radius = entry.data[CONF_RADIUS]
    coordinator.data_file = entry.data[CONF_DATA_FILE]
    coordinator.shots_in = entry.data[CONF_SHOTS_IN]
    coordinator.shots_out = entry.data[CONF_SHOTS_OUT]
    coordinator.automatic_interval = entry.data[CONF_AUTOMATIC_INTERVAL]
    coordinator.gps_time_offset = entry.data[CONF_GPS_TIME_OFFSET]
    coordinator.lines_whitelist = entry.data[CONF_LINES_WHITELIST]
    coordinator._vehicle_data = {}
    coordinator._tracker_locations = {}
    coordinator._last_route_seen = {}
    coordinator._event_data = {}
    return coordinator, hass


def test_haversine_returns_zero_for_the_same_point():
    """The haversine formula should return zero distance for identical coordinates."""
    coordinator, _ = _make_coordinator()

    distance = coordinator._haversine(52.2297, 21.0122, 52.2297, 21.0122)

    assert distance == 0.0


def test_find_closest_vehicle_ignores_non_whitelisted_and_stale_vehicles():
    """Only the nearest valid vehicle should be selected."""
    coordinator, _ = _make_coordinator()
    now = datetime.now(timezone.utc)
    valid_vehicle = {
        "vehicleId": "v-1",
        "routeShortName": "1",
        "lat": 52.2301,
        "lon": 21.0101,
        "generated": now.isoformat().replace("+00:00", "Z"),
    }
    wrong_route_vehicle = {
        "vehicleId": "v-2",
        "routeShortName": "99",
        "lat": 52.2300,
        "lon": 21.0100,
        "generated": now.isoformat().replace("+00:00", "Z"),
    }
    stale_vehicle = {
        "vehicleId": "v-3",
        "routeShortName": "2",
        "lat": 52.2302,
        "lon": 21.0102,
        "generated": (now - timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
    }
    coordinator._vehicle_data = {
        valid_vehicle["vehicleId"]: valid_vehicle,
        wrong_route_vehicle["vehicleId"]: wrong_route_vehicle,
        stale_vehicle["vehicleId"]: stale_vehicle,
    }

    chosen = coordinator._find_closest_vehicle({"latitude": 52.2297, "longitude": 21.0122})

    assert chosen is not None
    assert chosen["vehicleId"] == "v-1"


def test_process_events_creates_new_event_and_updates_last_route():
    """A nearby vehicle should create an active event and record the last route seen."""
    coordinator, _ = _make_coordinator()
    tracker_id = "device_tracker.home"
    coordinator._tracker_locations = {
        tracker_id: {"latitude": 52.2297, "longitude": 21.0122},
    }
    coordinator._vehicle_data = {
        "v-1": {
            "vehicleId": "v-1",
            "routeShortName": "1",
            "lat": 52.22972,
            "lon": 21.01225,
            "generated": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    }
    coordinator._event_data = {}

    coordinator._async_process_events()

    event = coordinator._event_data[tracker_id]
    assert event["vehicle"] == "v-1"
    assert event["shots_in"] == 1
    assert coordinator._last_route_seen[tracker_id] == "Home - 1"


def test_process_events_removes_event_after_shots_out_limit():
    """A stale event should be ended once the shots-out limit is reached."""
    coordinator, _ = _make_coordinator()
    tracker_id = "device_tracker.home"
    coordinator._tracker_locations = {
        tracker_id: {"latitude": 0.0, "longitude": 0.0},
    }
    coordinator._vehicle_data = {}
    coordinator._event_data = {
        tracker_id: {
            "vehicle": "v-1",
            "shots_in": 1,
            "shots_out": 2,
            "ztm_vehicle": {"vehicleId": "v-1", "routeShortName": "1"},
            "event_summary": "Home near route 1",
        }
    }

    coordinator._async_process_events()

    assert tracker_id not in coordinator._event_data
