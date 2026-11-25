"""Motion binary sensor for RF Motion."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import SIGNAL_UPDATE
from .engine import RFMotionEngine


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([RFMotionBinarySensor(entry)])


class RFMotionBinarySensor(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_should_poll = False
    _attr_icon = "mdi:motion-sensor"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._engine: RFMotionEngine = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_motion"
        self._attr_name = entry.title

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE.format(self._entry.entry_id), self._update))

    @callback
    def _update(self) -> None:
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self._engine.available

    @property
    def is_on(self) -> bool:
        return self._engine.motion

    @property
    def extra_state_attributes(self) -> dict:
        e = self._engine
        return {
            "active_hours": f"{e.start:%H:%M}-{e.end:%H:%M}",
            "last_motion": e.last_motion.isoformat(timespec="seconds") if e.last_motion else None,
            "last_trigger_light": e.last_trigger_light,
            "lights": e.lights,
        }
