"""RSSI-based motion detection engine using ZHA internals."""
from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, time as dtime
import logging
import statistics
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import (
    CONF_END, CONF_EVENT_WINDOW, CONF_EVENTS_REQUIRED, CONF_HOLD_MINUTES, CONF_LIGHTS,
    CONF_POLL_SECONDS, CONF_START, CONF_THRESHOLD_DB, DEFAULTS, MEDIAN_SAMPLES, SIGNAL_UPDATE,
)

_LOGGER = logging.getLogger(__name__)
ON_OFF_CLUSTER = 0x0006
READ_TIMEOUT = 5


class RFMotionEngine:
    """Polls ZHA bulbs and turns RSSI disturbances into a motion state."""

    def __init__(self, hass: HomeAssistant, entry_id: str, cfg: dict) -> None:
        self.hass = hass
        self.entry_id = entry_id
        get = lambda k: cfg.get(k, DEFAULTS.get(k))  # noqa: E731
        self.lights: list[str] = cfg[CONF_LIGHTS]
        self.start = dtime.fromisoformat(get(CONF_START))
        self.end = dtime.fromisoformat(get(CONF_END))
        self.hold = float(get(CONF_HOLD_MINUTES)) * 60
        self.threshold = float(get(CONF_THRESHOLD_DB))
        self.poll = float(get(CONF_POLL_SECONDS))
        self.events_required = int(get(CONF_EVENTS_REQUIRED))
        self.event_window = float(get(CONF_EVENT_WINDOW))

        self.available = False
        self.motion = False
        self.last_motion: datetime | None = None
        self.last_trigger_light: str | None = None
        self.last_rssi: dict[str, int] = {}
        self._reset()

    # ---------- detection ----------
    def _reset(self) -> None:
        self._hist: dict[str, deque[int]] = {e: deque(maxlen=MEDIAN_SAMPLES) for e in self.lights}
        self._events: deque[float] = deque()
        self._last_event_mono = 0.0
        self.motion = False

    def _feed(self, light: str, rssi: int, now: float) -> None:
        hist = self._hist[light]
        if len(hist) >= MEDIAN_SAMPLES // 2:
            dev = abs(rssi - statistics.median(hist))
            if dev >= self.threshold:
                _LOGGER.debug("disturbance %s rssi=%s dev=%.1f", light, rssi, dev)
                self._events.append(now)
                self.last_trigger_light = light
        hist.append(rssi)
        while self._events and now - self._events[0] > self.event_window:
            self._events.popleft()
        if len(self._events) >= self.events_required:
            self._last_event_mono = now
            self.last_motion = dt_util.now()

    def _is_active(self) -> bool:
        now = dt_util.now().time()
        if self.start <= self.end:
            return self.start <= now < self.end
        return now >= self.start or now < self.end  # window crosses midnight

    # ---------- ZHA access ----------
    def _resolve_clusters(self) -> dict[str, object]:
        """Map light entity_id -> (zha device, on/off cluster)."""
        from homeassistant.components.zha.helpers import get_zha_gateway
        from zigpy.types import EUI64

        gateway = get_zha_gateway(self.hass)
        ent_reg, dev_reg = er.async_get(self.hass), dr.async_get(self.hass)
        out = {}
        for entity_id in self.lights:
            ent = ent_reg.async_get(entity_id)
            dev = dev_reg.async_get(ent.device_id) if ent and ent.device_id else None
            ieee = next((i for d, i in (dev.identifiers if dev else ()) if d == "zha"), None)
            zdev = gateway.get_device(EUI64.convert(ieee)) if ieee else None
            if zdev is None:
                _LOGGER.warning("%s is not a ZHA device; skipping", entity_id)
                continue
            cluster = None
            for ep_id, types in zdev.async_get_clusters().items():
                if ep_id != 0 and ON_OFF_CLUSTER in types.get("in", {}):
                    cluster = types["in"][ON_OFF_CLUSTER]
                    break
            if cluster is None:
                _LOGGER.warning("%s has no On/Off cluster; skipping", entity_id)
                continue
            out[entity_id] = (zdev, cluster)
        return out

    # ---------- main loop ----------
    def _notify(self) -> None:
        async_dispatcher_send(self.hass, SIGNAL_UPDATE.format(self.entry_id))

    async def run(self) -> None:
        clusters: dict[str, object] = {}
        while True:
            try:
                if not self._is_active():
                    if self.available:
                        self.available = False
                        self._reset()
                        self._notify()
                        _LOGGER.info("outside active hours; idle")
                    await asyncio.sleep(30)
                    continue
                if not self.available:
                    self.available = True
                    self._notify()
                    _LOGGER.info("active; polling %d lights", len(self.lights))

                if not clusters:
                    clusters = self._resolve_clusters()
                    if not clusters:
                        await asyncio.sleep(30)
                        continue

                step = self.poll / len(clusters)
                for entity_id, (zdev, cluster) in clusters.items():
                    t = time.monotonic()
                    try:
                        async with asyncio.timeout(READ_TIMEOUT):
                            await cluster.read_attributes(["on_off"], allow_cache=False, only_cache=False)
                        rssi = zdev.rssi
                        if rssi is not None:
                            self.last_rssi[entity_id] = rssi
                            self._feed(entity_id, rssi, t)
                    except (TimeoutError, Exception) as err:  # noqa: BLE001
                        _LOGGER.debug("read failed for %s: %s", entity_id, err)
                    await asyncio.sleep(max(0.0, step - (time.monotonic() - t)))

                motion = self._last_event_mono > 0 and time.monotonic() - self._last_event_mono < self.hold
                if motion != self.motion:
                    self.motion = motion
                    _LOGGER.info("motion -> %s", "on" if motion else "off")
                    self._notify()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                _LOGGER.exception("RF motion loop error; retrying in 10s")
                clusters = {}
                await asyncio.sleep(10)
