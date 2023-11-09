"""
Sony CISIP2 integration for Home Assistant.
"""

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from .const import DOMAIN, DEFAULT_PORT
from python_sonycisip2 import SonyCISIP2


MODEL_MAP = {
    'Z11': 'STR-ZA1100ES',
    'Z21': 'STR-ZA2100ES',
    'Z31': 'STR-ZA3100ES'
}

# Configuration schema for the 'configuration.yaml' entry
CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required("host"): cv.string,
        vol.Optional("port", default=DEFAULT_PORT): cv.port,
    })
}, extra=vol.ALLOW_EXTRA)

def initialize_hass_data(hass, domain):
    """Initialize the Home Assistant data structure for Sony CISIP2 if not already initialized."""
    if domain not in hass.data:
        hass.data[domain] = {}

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Sony CISIP2 component from configuration.yaml."""
    # Initialize hass.data[DOMAIN] and receiver_count
    initialize_hass_data(hass, DOMAIN)
    
    if DOMAIN not in config:
        return True  # Component not set up in configuration.yaml, proceed with UI setup

    conf = config[DOMAIN]
    host = conf["host"]
    port = conf.get("port", DEFAULT_PORT)

    # Initialize the Sony CISIP2 controller
    controller = SonyCISIP2(host, port)
    if not await controller.connect():
        return False  # Unable to connect, do not proceed with setup

    # Fetch the MAC address as a unique identifier
    mac_address = await controller.get_feature("network.macaddress")
    if not mac_address:
        return False  # Unable to retrieve MAC address, do not proceed with setup
    sony_hwversion = await controller.get_feature("system.modeltype")
    sony_swversion = await controller.get_feature("system.version")
    sony_hwversion = MODEL_MAP.get(sony_hwversion, 'STR-ZAxx00ES')

    # Store the MAC address and the controller instance for use by the platform
    hass.data[DOMAIN]['controller'] = controller
    hass.data[DOMAIN]['mac_address'] = mac_address
    hass.data[DOMAIN]['sony_hwversion'] = sony_hwversion
    hass.data[DOMAIN]['sony_swversion'] = sony_swversion

    # Define discovery_info with desired parameters
    discovery_info = {
        "host": host,
        "port": port,
        "platform_name": "Sony CISIP2"
    }

    # If set up via `configuration.yaml`, forward to platform setup with discovery_info
    hass.async_create_task(
        hass.helpers.discovery.async_load_platform('media_player', DOMAIN, discovery_info, config)
    )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Sony CISIP2 from a config entry."""
    # Initialize hass.data[DOMAIN]
    initialize_hass_data(hass, DOMAIN)

    controller = SonyCISIP2(entry.data["host"], entry.data.get("port", DEFAULT_PORT))
    if not await controller.connect():
        return False

    # Retrieve the MAC address to use as a unique identifier
    mac_address = await controller.get_feature("network.macaddress")
    if not mac_address:
        return False  # Unable to retrieve MAC address, do not proceed with setup

    # Access the device registry directly without await
    device_registry = hass.helpers.device_registry.async_get(hass)
    # Create a unique device name by getting the MAC address
    mac_for_id = mac_address.replace(":", "").lower() if mac_address else None
    unique_name = f"Sony Receiver {mac_for_id}" if mac_for_id else f"Sony Receiver MISSINGMAC"
    sony_hwversion = await controller.get_feature("system.modeltype")
    sony_swversion = await controller.get_feature("system.version")
    sony_hwversion = modelmap.get(sony_hwversion, 'STR-ZAxx00ES')
    # Create a device in Home Assistant for this Sony CISIP2 platform using the MAC address
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac_for_id)} if mac_for_id else {(DOMAIN, entry.data["host"])},  # Use MAC address as a unique identifier, with host fallback
        name=unique_name,
        manufacturer="Sony",
        model=sony_hwversion,
        sw_version=sony_swversion,
        # via_device=(DOMAIN, device.id) if 'device' in hass.data[DOMAIN] else None
    )

    # Increment and store the receiver count in hass.data
    # hass.data[DOMAIN]['receiver_count'] = receiver_count

    # Store the controller, device, and MAC address in hass.data
    hass.data[DOMAIN]['controller'] = controller
    hass.data[DOMAIN]['device'] = device
    hass.data[DOMAIN]['mac_address'] = mac_address
    hass.data[DOMAIN]['sony_hwversion'] = sony_hwversion
    hass.data[DOMAIN]['sony_swversion'] = sony_swversion


    # Forward the setup to the media_player platform, passing the device info
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Sony CISIP2 config entry."""
    # Remove the controller and MAC address
    hass.data[DOMAIN].pop("controller", None)
    hass.data[DOMAIN].pop("mac_address", None)
    # Forward the unload to the media_player platform
    return await hass.config_entries.async_forward_entry_unload(entry, "media_player")
