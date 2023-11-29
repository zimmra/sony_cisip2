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

import asyncio
import logging

# Define a connection check interval (in seconds)
CONNECTION_CHECK_INTERVAL = 60

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


_LOGGER = logging.getLogger(__name__)

def initialize_hass_data(hass, domain):
    """Initialize the Home Assistant data structure for Sony CISIP2 if not already initialized."""
    if domain not in hass.data:
        hass.data[domain] = {}

async def try_connect(controller, max_retries=3, delay=1):
    """Attempt to connect with retries and exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            if await controller.connect():
                return True
        except Exception as e:
            _LOGGER.error(f'Attempt {attempt} failed: {e}')
        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    return False

async def check_connection_and_reconnect(controller, hass):
    """Check the connection and attempt to reconnect if necessary."""
    while True:
        if not controller.is_connected: 
            _LOGGER.warning("Connection lost. Attempting to reconnect...")
            if await try_connect(controller):
                _LOGGER.info("Reconnected to Sony CISIP2.")
            else:
                _LOGGER.error("Reconnection failed.")
        await asyncio.sleep(CONNECTION_CHECK_INTERVAL)

async def try_get_mac_address(controller, max_retries=3, delay=1):
    """Attempt to get the MAC address with retries and exponential backoff."""
    for attempt in range(1, max_retries + 1):
        try:
            if not controller.is_connected:
                _LOGGER.warning("Connection lost. Attempting to reconnect to get mac address...")
                if await try_connect(controller):
                    _LOGGER.info("Reconnected to Sony CISIP2.")
                    mac_address = await controller.get_feature("network.macaddress")
                    if mac_address:
                        return mac_address
            else:
                mac_address = await controller.get_feature("network.macaddress")
                if mac_address:
                    return mac_address
        except asyncio.CancelledError:
            _LOGGER.error(f'Operation cancelled during attempt {attempt} to get MAC address. Retrying.')
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
        except Exception as e:
            _LOGGER.error(f'Attempt {attempt} to get MAC address failed: {e}')
        if attempt < max_retries:
            await asyncio.sleep(delay)
            delay *= 2  # Exponential backoff
    return None


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
    if not await try_connect(controller):
        _LOGGER.error("Unable to connect to Sony CISIP2 after retries.")
        return True  # Allow Home Assistant to continue starting

    # Fetch the MAC address as a unique identifier
    mac_address = await try_get_mac_address(controller)
    if not mac_address:
        # Try to find MAC address from device_tracker entities
        for entity_id, state in hass.states.async_all("device_tracker"):
            if state.attributes.get("ip") == host:
                mac_address = state.attributes.get("mac_address")
                if mac_address:
                    break
        
        if not mac_address:
            _LOGGER.error("Unable to retrieve MAC address after retries and device_tracker lookup.")
            mac_address = None
            return True
    sony_hwversion = await controller.get_feature("system.modeltype")
    sony_swversion = await controller.get_feature("system.version")
    sony_hwversion = MODEL_MAP.get(sony_hwversion, 'STR-ZAxx00ES')

    # Store the MAC address and the controller instance for use by the platform
    hass.data[DOMAIN]['controller'] = controller
    hass.data[DOMAIN]['mac_address'] = mac_address
    hass.data[DOMAIN]['sony_hwversion'] = sony_hwversion
    hass.data[DOMAIN]['sony_swversion'] = sony_swversion
    hass.data[DOMAIN]['connection_monitor'] = hass.loop.create_task(
        check_connection_and_reconnect(controller, hass)
    )

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
    if not await try_connect(controller):
        _LOGGER.error("Unable to connect to Sony CISIP2 after retries.")
        return True  # Allow Home Assistant to continue starting

    # Retrieve the MAC address to use as a unique identifier
    mac_address = await try_get_mac_address(controller)
    if not mac_address:
        # Try to find MAC address from device_tracker entities
        for entity_id, state in hass.states.async_all("device_tracker"):
            if state.attributes.get("ip") == entry.data["host"]:
                mac_address = state.attributes.get("mac_address")
                if mac_address:
                    break
        
        if not mac_address:
            _LOGGER.error("Unable to retrieve MAC address after retries and device_tracker lookup.")
            return True

    # Access the device registry directly without await
    device_registry = hass.helpers.device_registry.async_get(hass)
    # Create a unique device name by getting the MAC address
    mac_for_id = mac_address.replace(":", "").lower() if mac_address else None
    unique_name = f"Sony Receiver {mac_for_id}" if mac_for_id else f"Sony Receiver MISSINGMAC"
    entered_name = entry.data["name"]
    sony_hwversion = await controller.get_feature("system.modeltype")
    sony_swversion = await controller.get_feature("system.version")
    sony_hwversion = MODEL_MAP.get(sony_hwversion, 'STR-ZAxx00ES')
    # Create a device in Home Assistant for this Sony CISIP2 platform using the MAC address
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, mac_for_id)} if mac_for_id else {(DOMAIN, entry.data["host"])},  # Use MAC address as a unique identifier, with host fallback
        name = entered_name if entered_name else unique_name,
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
    hass.data[DOMAIN]['connection_monitor'] = hass.loop.create_task(
        check_connection_and_reconnect(controller, hass)
    )


    # Forward the setup to the media_player platform, passing the device info
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "media_player")
    )
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Sony CISIP2 config entry."""
    # Cancel the connection monitoring task
    if 'connection_monitor' in hass.data[DOMAIN]:
        hass.data[DOMAIN]['connection_monitor'].cancel()
        hass.data[DOMAIN].pop('connection_monitor')
    # Add other data keys to remove if any
    # Remove the controller and other related data
    domain_data = hass.data[DOMAIN]
    domain_data.pop("controller", None)
    domain_data.pop("mac_address", None)
    domain_data.pop("sony_hwversion", None)
    domain_data.pop("sony_swversion", None)

    # Forward the unload to the media_player platform
    unload_successful = await hass.config_entries.async_forward_entry_unload(entry, "media_player")

    # Clean up domain data if unload successful
    if unload_successful:
        hass.data.pop(DOMAIN, None)

    return unload_successful

