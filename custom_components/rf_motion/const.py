"""Constants for RF Motion."""

DOMAIN = "rf_motion"

CONF_LIGHTS = "lights"
CONF_START = "start"
CONF_END = "end"
CONF_HOLD_MINUTES = "hold_minutes"
CONF_THRESHOLD_DB = "threshold_db"
CONF_POLL_SECONDS = "poll_seconds"
CONF_EVENTS_REQUIRED = "events_required"
CONF_EVENT_WINDOW = "event_window_seconds"

DEFAULTS = {
    CONF_START: "12:00:00",
    CONF_END: "21:00:00",
    CONF_HOLD_MINUTES: 5,
    CONF_THRESHOLD_DB: 2.0,
    CONF_POLL_SECONDS: 2.0,
    CONF_EVENTS_REQUIRED: 2,
    CONF_EVENT_WINDOW: 60,
}

MEDIAN_SAMPLES = 10
SIGNAL_UPDATE = "rf_motion_update_{}"
