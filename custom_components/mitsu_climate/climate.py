"""Wrapper climate entity that uses a lookup table for C<->F conversion."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_REVERSE_POLICY,
    CONF_SOURCE_ENTITY,
    MAX_F,
    MIN_F,
    c_to_f,
    f_to_c,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate entity from a config entry."""
    async_add_entities([LookupClimate(
        hass,
        name=entry.data[CONF_NAME],
        source_entity=entry.data[CONF_SOURCE_ENTITY],
        reverse_policy=entry.data.get(CONF_REVERSE_POLICY, "lowest"),
        unique_id=entry.entry_id,
    )])


class LookupClimate(ClimateEntity):
    """Climate entity that wraps another climate entity with lookup-table conversion."""

    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_target_temperature_step = 1
    _attr_precision = 1
    _attr_min_temp = MIN_F
    _attr_max_temp = MAX_F

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        source_entity: str,
        reverse_policy: str,
        unique_id: str,
    ) -> None:
        """Initialize."""
        self.hass = hass
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._source_entity = source_entity
        self._reverse_policy = reverse_policy

        self._attr_hvac_mode = None
        self._attr_hvac_modes = [HVACMode.OFF]
        self._attr_hvac_action = None
        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_supported_features = ClimateEntityFeature(0)
        self._attr_available = False
        # Mode lists (populated from source)
        self._attr_fan_modes = None
        self._attr_fan_mode = None
        self._attr_swing_modes = None
        self._attr_swing_mode = None
        self._attr_preset_modes = None
        self._attr_preset_mode = None

    async def async_added_to_hass(self) -> None:
        """Register listener on the source entity."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._source_entity], self._source_changed
            )
        )
        state = self.hass.states.get(self._source_entity)
        if state is not None:
            self._update_from_source(state)

    @callback
    def _source_changed(self, event: Event) -> None:
        """Handle state change of the wrapped entity."""
        new_state: State | None = event.data.get("new_state")
        if new_state is None:
            return
        self._update_from_source(new_state)
        self.async_write_ha_state()

    def _update_from_source(self, state: State) -> None:
        """Copy relevant state from the source entity, converting temps."""
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            self._attr_available = False
            self._attr_current_temperature = None
            self._attr_target_temperature = None
            return

        self._attr_available = True
        attrs = state.attributes

        try:
            self._attr_hvac_mode = HVACMode(state.state)
        except ValueError:
            self._attr_hvac_mode = None

        # hvac_action is what the unit is currently doing (heating/cooling/
        # idle/off/fan). Separate from hvac_mode which is what it's set to.
        action = attrs.get("hvac_action")
        if action is not None:
            try:
                self._attr_hvac_action = HVACAction(action)
            except ValueError:
                self._attr_hvac_action = None
        else:
            self._attr_hvac_action = None

        modes = attrs.get("hvac_modes")
        if modes:
            try:
                self._attr_hvac_modes = [HVACMode(m) for m in modes]
            except ValueError:
                self._attr_hvac_modes = [HVACMode.OFF]
        self._attr_supported_features = ClimateEntityFeature(
            attrs.get("supported_features", 0)
        )

        # Mirror fan / swing / preset so capability_attributes doesn't blow up
        self._attr_fan_modes = attrs.get("fan_modes")
        self._attr_fan_mode = attrs.get("fan_mode")
        self._attr_swing_modes = attrs.get("swing_modes")
        self._attr_swing_mode = attrs.get("swing_mode")
        self._attr_preset_modes = attrs.get("preset_modes")
        self._attr_preset_mode = attrs.get("preset_mode")

        # Get the actual ClimateEntity instance so we can read its native
        # (unconverted) temperature values directly, bypassing HA's automatic
        # display-unit conversion. This avoids a lossy F->C->F round trip.
        component: EntityComponent | None = self.hass.data.get("climate")
        source_entity = (
            component.get_entity(self._source_entity) if component else None
        )

        if source_entity is not None:
            current_c = source_entity.current_temperature
            target_c = source_entity.target_temperature
            native_unit = source_entity.temperature_unit
            _LOGGER.debug(
                "%s: read native values current=%r target=%r (unit=%s)",
                self._source_entity, current_c, target_c, native_unit,
            )
            # Sanity check: if the device's native unit isn't C, our lookup
            # table is wrong. Warn once.
            if native_unit != UnitOfTemperature.CELSIUS:
                _LOGGER.warning(
                    "%s has native unit %s; lookup table is indexed in Celsius. "
                    "Results may be incorrect.",
                    self._source_entity, native_unit,
                )
        else:
            # Fallback if the entity object isn't accessible yet -- read the
            # state attributes (which HA may have converted). This only runs
            # transiently during startup.
            current_c = attrs.get("current_temperature")
            target_c = attrs.get("temperature")

        def _safe_c_to_f(val: Any) -> int | None:
            if val is None:
                return None
            try:
                return c_to_f(float(val))
            except (TypeError, ValueError):
                _LOGGER.warning(
                    "Could not convert temperature value %r (type=%s) from %s",
                    val, type(val).__name__, self._source_entity,
                )
                return None

        self._attr_current_temperature = _safe_c_to_f(current_c)
        self._attr_target_temperature = _safe_c_to_f(target_c)

        _LOGGER.debug(
            "%s: native current(C)=%r target(C)=%r -> F current=%s target=%s",
            self._source_entity, current_c, target_c,
            self._attr_current_temperature, self._attr_target_temperature,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature. Input is in F; convert to C via lookup."""
        temp_f = kwargs.get(ATTR_TEMPERATURE)
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)

        if temp_f is None:
            _LOGGER.warning(
                "lookup_climate does not yet support target_temp_low/high"
            )
            return

        temp_f_int = int(round(float(temp_f)))
        temp_c = f_to_c(temp_f_int, self._reverse_policy)

        # Call the source entity's method directly with the native C value,
        # skipping the service layer (which would apply unit conversion).
        component: EntityComponent | None = self.hass.data.get("climate")
        source_entity = (
            component.get_entity(self._source_entity) if component else None
        )

        _LOGGER.debug(
            "Setting %s: %s°F (user) -> %s°C native (policy=%s)",
            self._source_entity, temp_f_int, temp_c, self._reverse_policy,
        )

        if source_entity is not None:
            kw = {ATTR_TEMPERATURE: temp_c}
            if hvac_mode is not None:
                kw[ATTR_HVAC_MODE] = hvac_mode
            await source_entity.async_set_temperature(**kw)
        else:
            # Fallback: call via the service layer. HA will apply display-unit
            # conversion, so we have to pre-convert if we're in Imperial.
            display_unit = self.hass.config.units.temperature_unit
            temp_to_send = (
                (temp_c * 9 / 5) + 32
                if display_unit == UnitOfTemperature.FAHRENHEIT
                else temp_c
            )
            service_data: dict[str, Any] = {
                "entity_id": self._source_entity,
                ATTR_TEMPERATURE: temp_to_send,
            }
            if hvac_mode is not None:
                service_data[ATTR_HVAC_MODE] = hvac_mode
            await self.hass.services.async_call(
                "climate", "set_temperature", service_data, blocking=True,
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Forward HVAC mode changes to the source entity."""
        await self.hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": self._source_entity, "hvac_mode": hvac_mode},
            blocking=True,
        )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Forward fan mode changes to the source entity."""
        await self.hass.services.async_call(
            "climate",
            "set_fan_mode",
            {"entity_id": self._source_entity, "fan_mode": fan_mode},
            blocking=True,
        )

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Forward swing mode changes to the source entity."""
        await self.hass.services.async_call(
            "climate",
            "set_swing_mode",
            {"entity_id": self._source_entity, "swing_mode": swing_mode},
            blocking=True,
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Forward preset mode changes to the source entity."""
        await self.hass.services.async_call(
            "climate",
            "set_preset_mode",
            {"entity_id": self._source_entity, "preset_mode": preset_mode},
            blocking=True,
        )
