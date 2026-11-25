"""Config and options flow for RF Motion."""
from __future__ import annotations

from typing import Any

import probatio as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector as sel

from .const import (
    CONF_END, CONF_EVENT_WINDOW, CONF_EVENTS_REQUIRED, CONF_HOLD_MINUTES, CONF_LIGHTS,
    CONF_POLL_SECONDS, CONF_START, CONF_THRESHOLD_DB, DEFAULTS, DOMAIN,
)


def _num(lo, hi, step, unit=None):
    extra = {"unit_of_measurement": unit} if unit else {}
    return sel.NumberSelector(sel.NumberSelectorConfig(
        min=lo, max=hi, step=step, mode=sel.NumberSelectorMode.BOX, **extra))


def _fields(cur: dict) -> dict:
    g = lambda k: cur.get(k, DEFAULTS.get(k))  # noqa: E731
    return {
        vol.Required(CONF_LIGHTS, default=cur.get(CONF_LIGHTS, [])): sel.EntitySelector(
            sel.EntitySelectorConfig(domain="light", integration="zha", multiple=True)),
        vol.Required(CONF_START, default=g(CONF_START)): sel.TimeSelector(),
        vol.Required(CONF_END, default=g(CONF_END)): sel.TimeSelector(),
        vol.Required(CONF_HOLD_MINUTES, default=g(CONF_HOLD_MINUTES)): _num(1, 60, 1, "min"),
        vol.Required(CONF_THRESHOLD_DB, default=g(CONF_THRESHOLD_DB)): _num(1, 10, 0.5, "dB"),
        vol.Required(CONF_EVENTS_REQUIRED, default=g(CONF_EVENTS_REQUIRED)): _num(1, 10, 1),
        vol.Required(CONF_EVENT_WINDOW, default=g(CONF_EVENT_WINDOW)): _num(10, 600, 5, "s"),
        vol.Required(CONF_POLL_SECONDS, default=g(CONF_POLL_SECONDS)): _num(1, 30, 0.5, "s"),
    }


class RFMotionConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            if len(user_input[CONF_LIGHTS]) < 1:
                errors[CONF_LIGHTS] = "no_lights"
            else:
                name = user_input.pop(CONF_NAME)
                return self.async_create_entry(title=name, data=user_input)
        schema = vol.Schema({vol.Required(CONF_NAME, default="RF Motion"): str, **_fields(user_input or {})})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RFMotionOptionsFlow()


class RFMotionOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        cur = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=vol.Schema(_fields(cur)))
