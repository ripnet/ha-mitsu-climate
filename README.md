# Mitsubishi Climate Lookup

A Home Assistant custom integration that wraps an existing climate entity reporting in
Celsius (e.g. an ESPHome [mitsubishi_itp](https://github.com/muart-group/esphome-components)
heat pump) and exposes it in whole degrees Fahrenheit using **Mitsubishi's own C↔F lookup
table** instead of the standard formula.

Mitsubishi thermostats (e.g. the MHK2) don't convert with `F = C × 9/5 + 32`. For example,
both 20.0 °C and 20.5 °C display as 68 °F, and 21.0 °C displays as 69 °F where standard
math gives 70. Without this wrapper, Home Assistant and the wall thermostat disagree.

The table comes from the
[muart-group docs](https://muart-group.github.io/user/configuration/useful-snippets#use-mitsubishi-temperature-conversion)
and has been spot-checked against a real MHK2 (20.5 °C → 68 °F setpoint, 21.0 °C → 69 °F room).

## What it does

- Reads the source entity's native °C values directly (no lossy F→C→F round trip) and
  converts them with the lookup table.
- Converts °F setpoints back to °C. When several °C values map to the same °F, the
  *reverse policy* (lowest/highest) picks which one is sent.
- Mirrors HVAC mode, action, fan, swing and preset from the source, and forwards changes
  to it, including turn on/off.
- Uses the source's real setpoint limits (e.g. 16–31 °C → 61–88 °F).

Only single-setpoint control is supported. With mitsubishi_itp v2 firmware (which reports
low/high setpoints), setting a temperature works in HEAT and COOL; in OFF or FAN_ONLY,
Home Assistant rejects it, because there's no active setpoint.

## Installation (HACS)

1. HACS → ⋮ → Custom repositories → add `https://github.com/ripnet/ha-mitsu-climate`,
   type **Integration**.
2. Install **Mitsubishi Climate Lookup** and restart Home Assistant.
3. Settings → Devices & services → Add integration → **Mitsubishi Climate Lookup**, then pick
   the source climate entity.

## Development

The primary repository is on a private Forgejo instance; GitHub is a push mirror, so changes
made directly on GitHub are overwritten. Releases are created automatically when a `v*` tag
matching `manifest.json`'s `version` is pushed.
