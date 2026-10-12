"""Tests for the ZTM Tracker config flow."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from homeassistant.data_entry_flow import FlowResultType

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from custom_components.ztm_tracker.config_flow import (
    ZTMTrackerConfigFlow,
    ZTMTrackerOptionsFlow,
)
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


@pytest.mark.asyncio
async def test_config_flow_user_step_shows_form():
    """The initial config flow should show a config form."""
    flow = ZTMTrackerConfigFlow()
    flow.hass = MagicMock()

    result = await flow.async_step_user()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert "data_schema" in result


@pytest.mark.asyncio
async def test_config_flow_user_step_creates_entry():
    """Submitting valid user input should create a config entry."""
    flow = ZTMTrackerConfigFlow()
    flow.hass = MagicMock()
    user_input = {
        CONF_DEVICE_TRACKERS: ["device_tracker.home"],
        CONF_RADIUS: 50,
        CONF_DATA_FILE: "https://example.com/data",
        CONF_SHOTS_IN: 2,
        CONF_SHOTS_OUT: 3,
        CONF_AUTOMATIC_INTERVAL: 5,
        CONF_GPS_TIME_OFFSET: 120,
        CONF_LINES_WHITELIST: "1,2,5",
    }

    result = await flow.async_step_user(user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "ZTM Tracker"
    assert result["data"] == user_input


@pytest.mark.asyncio
async def test_options_flow_init_shows_form():
    """The options flow should display the editable form."""
    config_entry = MagicMock()
    config_entry.entry_id = "test-entry"
    config_entry.domain = "ztm_tracker"
    config_entry.data = {
        CONF_DEVICE_TRACKERS: ["device_tracker.home"],
        CONF_RADIUS: 50,
        CONF_DATA_FILE: "https://example.com/data",
        CONF_SHOTS_IN: 2,
        CONF_SHOTS_OUT: 3,
        CONF_AUTOMATIC_INTERVAL: 5,
        CONF_GPS_TIME_OFFSET: 120,
        CONF_LINES_WHITELIST: "1,2,5",
    }
    config_entry.options = {}

    flow = ZTMTrackerOptionsFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_get_known_entry.return_value = config_entry
    flow.handler = config_entry.entry_id

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_init_creates_entry():
    """Submitting options should create an options entry."""
    config_entry = MagicMock()
    config_entry.entry_id = "test-entry"
    config_entry.domain = "ztm_tracker"
    config_entry.data = {
        CONF_DEVICE_TRACKERS: ["device_tracker.home"],
        CONF_RADIUS: 50,
        CONF_DATA_FILE: "https://example.com/data",
        CONF_SHOTS_IN: 2,
        CONF_SHOTS_OUT: 3,
        CONF_AUTOMATIC_INTERVAL: 5,
        CONF_GPS_TIME_OFFSET: 120,
        CONF_LINES_WHITELIST: "1,2,5",
    }
    config_entry.options = {}

    flow = ZTMTrackerOptionsFlow()
    flow.hass = MagicMock()
    flow.hass.config_entries.async_get_known_entry.return_value = config_entry
    flow.handler = config_entry.entry_id
    user_input = {
        CONF_DEVICE_TRACKERS: ["device_tracker.home"],
        CONF_RADIUS: 75,
        CONF_DATA_FILE: "https://example.com/updated-data",
        CONF_SHOTS_IN: 3,
        CONF_SHOTS_OUT: 4,
        CONF_AUTOMATIC_INTERVAL: 10,
        CONF_GPS_TIME_OFFSET: 180,
        CONF_LINES_WHITELIST: "2,5,11",
    }

    result = await flow.async_step_init(user_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == ""
    assert result["data"] == user_input
