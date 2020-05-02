# ad_narodmon_sender
Appdaemon app for sending sensor data from home assistant to narodmon.ru

## Installation

Download the `narodmon_sender` directory from inside the `apps` directory here to your local `apps` directory, then configure parametrs in `config.yaml` file inside `narodmon_sender` folfer.

## App configuration

```yaml
narodmon_sender:
  module: narodmon_sender
  class: narodmon_sender
  narodmon_device_mac:
  narodmon_device_name:
  hass_coordinates_entity:
  hass_sensor_entities:
```

key | optional | type | default | description
-- | -- | -- | -- | --
`module` | False | string | narodmon_sender | The module name of the app.
`class` | False | string | narodmon_sender | The name of the Class.
`narodmon_device_mac` | False | string | | MAC-address to identify your device on narodmon.ru
`narodmon_device_name` | True | string | | Name for your device
`hass_coordinates_entity` | True | string | | Home assistant zone entity_id for getting latitude and longitude, helps auto placing device on map
`hass_sensor_entities` | False | string | | Comma-separated home assistant sensor entity_id`s (without spaces)

## Example app configuration

```yaml
narodmon_sender:
  module: narodmon_sender
  class: narodmon_sender
  narodmon_device_mac: AABBCCDDEEFF
  narodmon_device_name: Xiaomi_WSDCGQ01LM
  hass_coordinates_entity: zone.home
  hass_sensor_entities: sensor.outside_temperature,sensor.outside_humidity
  ```
