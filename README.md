# RF Motion (Zigbee bulbs)

A Home Assistant integration that turns the Zigbee bulbs you already own into a
motion sensor. No extra sensor, no hub, no cloud.

It works like a simple, DIY take on Philips Hue MotionAware™: when someone
moves through a room, their body disturbs the radio signal between each bulb
and your Zigbee coordinator. RF Motion watches that signal strength (RSSI) and
reports motion when it changes.

> **Not affiliated with Philips or Signify.** This doesn't use or emulate
> MotionAware. It's an independent, much simpler approach.

## Requirements

- Home Assistant **2026.10** or newer
- **ZHA** (Zigbee Home Automation) with your bulbs paired to it
- **3 or more mains-powered Zigbee bulbs** in the same room. More bulbs, spread
  around the room, give better coverage.

Zigbee2MQTT and the Philips Hue integration are **not** supported.

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories** → add
   `https://github.com/LeonardoPahim/ha-rf-motion`, category **Integration**.
2. Install **RF Motion (Zigbee bulbs)**.
3. Restart Home Assistant.

### Manual

1. Copy `custom_components/rf_motion` into your HA `config/custom_components/` folder.
2. Restart Home Assistant.

## Setup

**Settings → Devices & services → Add integration → RF Motion (Zigbee bulbs)**

| Option | Default | What it does |
|---|---|---|
| Name | RF Motion | Name of the motion sensor entity |
| ZHA lights | – | The bulbs to listen to |
| Active from / until | 12:00 / 21:00 | Detection only runs inside this window. The sensor is **unavailable** outside it |
| Turn off after no motion for | 5 min | How long the sensor stays on after the last movement |
| Disturbance threshold | 2 dB | How far a bulb's signal must move from its recent average to count |
| Disturbances needed to trigger | 2 | Filters out one-off spikes… |
| …within | 60 s | …by requiring this many disturbances in this time |
| Poll interval per bulb | 2 s | How often each bulb is checked |

To change settings later: **Devices & services → RF Motion → Configure**.
You can add the integration more than once, for example one entry per room.

## What you get

`binary_sensor.<name>`: a motion sensor (`on` / `off` / `unavailable`) with these attributes:

- `last_motion`: when motion was last detected
- `last_trigger_light`: which bulb saw the last disturbance
- `active_hours`, `lights`: your current settings

### Example automation

```yaml
alias: Living room lights follow RF motion
triggers:
  - trigger: state
    entity_id: binary_sensor.rf_motion
    to: "off"
actions:
  - action: light.turn_off
    target:
      area_id: living_room
```

Because the sensor goes `unavailable` (not `off`) when the active window
ends, an automation like this won't turn your lights off at the end of the
window while you're still in the room.

## Tuning

1. Leave the room empty for a few minutes. The sensor should stay `off`.
   If it turns on by itself, raise **Disturbance threshold** (try 3 dB) or
   **Disturbances needed** (try 3).
2. Walk around normally. If the sensor doesn't turn on, lower the threshold
   (1.5 dB) or add bulbs on the other side of the room.
3. To see what it's doing, add this to `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.rf_motion: debug
   ```
   Each disturbance is then logged with the bulb name and how many dB it moved.

## Limitations

- **Movement only.** Someone sitting still won't be detected. For that, use an
  mmWave presence sensor.
- **Coverage follows the radio paths.** It measures bulb → coordinator links, so
  it mainly sees motion between the bulbs and your Zigbee stick. Placing the
  coordinator so those paths cross the room helps.
- **Adds a little Zigbee traffic.** That's one small attribute read per bulb per poll
  interval (4 bulbs at 2 s = 2 messages/s). That's fine for most networks. Raise
  the interval if yours is busy.
- Walls, metal furniture, Wi-Fi interference, pets and people in the next room
  can all cause false triggers. Tune the threshold for your space.

## How it works

Every poll, RF Motion reads the On/Off attribute of each bulb through ZHA. That's
harmless and doesn't change the light. Then it takes the RSSI that ZHA recorded
for the reply. Each bulb keeps a rolling median of its last 10 readings. A reading
that moves away from that median by at least the threshold counts as a
*disturbance*. When enough disturbances happen within the time window, the
sensor turns `on`. It turns `off` once no qualifying motion has been seen for the
hold time.
