"""Constants for the ZTM Tracker custom component."""

DOMAIN = "ztm_tracker"

CONF_DEVICE_TRACKERS = "device_trackers"
CONF_RADIUS = "radius"
CONF_DATA_FILE = "data_file"
CONF_SHOTS_IN = "shots_in"
CONF_SHOTS_OUT = "shots_out"
CONF_AUTOMATIC_INTERVAL = "automatic_interval"
CONF_GPS_TIME_OFFSET = "gps_time_offset"
CONF_LINES_WHITELIST = "lines_whitelist" # Added new constant

DEFAULT_RADIUS = 50  # meters
DEFAULT_DATA_FILE = "https://ckan2.multimediagdansk.pl/gpsPositions?v=2"
DEFAULT_SHOTS_IN = 2
DEFAULT_SHOTS_OUT = 3
DEFAULT_AUTOMATIC_INTERVAL = 3  # minutes
DEFAULT_GPS_TIME_OFFSET = 120 # Added default value for GPS time offset in seconds
DEFAULT_LINES_WHITELIST = "2,5,12,169,171,179,6,8,11" # Added default value for lines whitelist
