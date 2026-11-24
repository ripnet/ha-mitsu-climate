
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import CONF_REVERSE_POLICY, CONF_SOURCE_ENTITY, DOMAIN


class LookupClimateConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lookup Climate."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (the only step we need)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            source = user_input[CONF_SOURCE_ENTITY]

            # Prevent creating two wrappers for the same source entity
            await self.async_set_unique_id(f"mitsu_climate_{source}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data=user_input,
            )

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_SOURCE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="climate"),
            ),
            vol.Required(CONF_REVERSE_POLICY, default="lowest"):
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["lowest", "highest"],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key="reverse_policy",
                    ),
                ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )