
"""Media player platform for Sony CISIP2 component."""

import logging
from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import volume as volume_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ZONES = ["main", "zone2", "zone3"]

# Define supported features for the media player
SUPPORTED_FEATURES = (
    SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOUND_MODE
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_STEP
)

# Source mappings that handle multiple receiver source keys
SOURCE_MAPPINGS = {
    'dvd': 'BD/DVD',
    'sat': 'SAT/CATV',
    'stb': 'STB',
    'fm': 'FM',
    'catv': 'SAT/CATV',  # Kept because it should map to 'SAT/CATV' as well
    'aux': 'AUX',
    'tv': 'TV',
    'game': 'GAME',
    'video': 'VIDEO',
    'sacd': 'CD/SACD',
    'am': 'AM',
    'tuner': 'TUNER',
    'bd': 'BD/DVD',
    'cd': 'CD/SACD',  # Kept because it should map to 'CD/SACD' as well
}

# Reverse mapping for setting the source
REVERSE_SOURCE_MAPPINGS = {
    'BD/DVD': 'bd',  # Preferred command string
    'SAT/CATV': 'sat',  # Preferred command string
    'STB': 'stb',
    'FM': 'fm',
    'AUX': 'aux',
    'TV': 'tv',
    'GAME': 'game',
    'VIDEO': 'video',
    'CD/SACD': 'cd',  # Preferred command string
    'AM': 'am',
    'TUNER': 'tuner',
}

MODEL_MAP = {
    'Z11': 'STR-ZA1100ES',
    'Z21': 'STR-ZA2100ES',
    'Z31': 'STR-ZA3100ES'
}

SOUND_MODE_MAP = {
    '2ch Stereo': '2ch',
    'Analog Direct': 'direct',
    'Auto Format Decode': 'afd',
    'Multi-Channel Stereo': 'multi',
    'Dolby Surround': 'dolby',
    'DTS Neural:X': 'neuralx'
}

class SonyCISIP2MediaPlayer(MediaPlayerEntity):
    def __init__(self, hass: HomeAssistant, controller, mac_address, zone, sony_hwversion, sony_swversion):
        """Initialize the SonyCISIP2MediaPlayer."""
        self._hass = hass
        self._controller = controller
        self._mac_address = mac_address
        self._sony_hwversion = sony_hwversion
        self._sony_swversion = sony_swversion
        self._state = None
        self._zone = zone  # Add a zone attribute
        self._source = None
        self._sound_mode = None
        self._mute = None
        self._volume = None
        self._volumedisplay_mode = 'step'  # Default to 'step' until updated

        # Initialize logger
        self.logger = logging.getLogger(__name__)

    # Properties to set default name and entity_id from mac address
    @property
    def name(self):
        """Return the name of the media player with a unique identifier."""
        mac_for_name = self._mac_address.replace(":", "").lower() if self._mac_address else None
        unique_name = f"Sony Receiver {mac_for_name}-{self._zone}"
        return unique_name
    
    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return 'mdi:audio-video'
    
    @property
    def device_class(self):
        """Return the device class of the media player."""
        return 'receiver'
    
    @property
    def device_info(self):
        """Return device information about this Sony CISIP2 receiver."""
        # Use the consistent naming convention for the device name
        mac_for_id = self._mac_address.replace(":", "").lower() if self._mac_address else None
        sony_hwversion = self._sony_hwversion if self._sony_hwversion else None
        sony_swversion = self._sony_swversion if self._sony_swversion else "Unknown"
        sony_hwversion = MODEL_MAP.get(sony_hwversion, 'STR-ZAxx00ES')
        unique_name = f"Sony Receiver {mac_for_id}"
        return {
            "identifiers": {(DOMAIN, mac_for_id)} if mac_for_id else {(DOMAIN, self._controller.host)},
            "name": unique_name,
            "manufacturer": "Sony",
            "model": sony_hwversion,
            "sw_version": sony_swversion,
            # "via_device": (DOMAIN, self._hass.data[DOMAIN]["device"].id),
        }

    @property
    def unique_id(self):
        """Return a unique ID for the media player."""
        mac_for_id = self._mac_address.replace(":", "").lower() if self._mac_address else None
        unique_id = f"sony_cisip2_{mac_for_id}_{self._zone}"
        return unique_id

    async def async_added_to_hass(self):
        """Register callbacks for state updates and get initial states."""
        _LOGGER.debug(f"Setting up '{self._zone}' zone media player: Registering callback and retrieving initial state.")
        try:
            self._controller.register_notification_callback(self.handle_notification)
            _LOGGER.debug(f"Registering notification callback for '{self._zone}' with id {id(self.handle_notification)}")
            await self.retrieve_initial_states()
        except Exception as e:
            _LOGGER.error(f"Error in async_added_to_hass: {e}")

    async def retrieve_initial_states(self):
        """Retrieve initial states for power, volume, source, and mute."""
        _LOGGER.debug(f"Retrieving initial states for '{self._zone}' zone.")
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        try:
            power_state = await self._controller.get_feature(f"{feature_prefix}power")
            _LOGGER.debug(f"Initial retrieved state for '{self._zone}.power' is: {power_state}")
            if power_state == 'on':
                self._state = 'on'
                self._source = await self._controller.get_feature(f"{feature_prefix}input")
                self._volumestep = await self._controller.get_feature(f"{feature_prefix}volumestep")
                self._sound_mode = await self._controller.get_feature("audio.soundfield")
                mute_state = await self._controller.get_feature(f"{feature_prefix}mute")

                # Update rest of the states based on retrieved values.
                self._mute = mute_state == 'on'
                if isinstance(self._volumestep, (int, float)):
                    self._volume = self._volumestep / 100
                else:
                    self._volume = None

                # Log all the retrieved initial states for the zone.
                _LOGGER.debug(f"Initial state for '{self._zone}.input' is: {self._source}")
                _LOGGER.debug(f"Initial state for '{self._zone}.mute' is: {mute_state}")
                _LOGGER.debug(f"Initial state for '{self._zone}.volumestep' is: {self._volumestep}")
            elif power_state == 'off':
                # Zone is off, set the power state and log it.
                self._state = 'off'
                _LOGGER.debug(f"Zone '{self._zone}' is off, setting power state to off.")
            else:
                _LOGGER.error(f"Unexpected power state value '{power_state}' for '{self._zone}' zone.")

            # Update HA state after initial state retrieval.
            _LOGGER.debug(f"Saving State for '{self._zone}'")
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error(f"Error retrieving initial states for '{self._zone}' zone: {e}")

    async def handle_notification(self, message):
        """Handle notifications from the Sony receiver."""
        feature = message.get("feature")
        value = message.get("value")
        zone_prefix = f"{self._zone}." if self._zone != "main" else "main."

        _LOGGER.debug(f"Processing notification for '{self._zone}' with feature '{feature}': {value}")

        # Check if the feature starts with the zone prefix.
        if feature.startswith(zone_prefix):
            feature_key = feature.replace(zone_prefix, "")
            
            # Map the feature key to the correct attribute of the entity
            if feature_key == 'power':
                self._state = 'on' if value == 'on' else 'off'
            elif feature_key == 'input':
                self._source = value
            elif feature_key == 'mute':
                self._mute = value == 'on'
            elif feature_key == 'volumestep':
                self._volume = int(value) / 100  # Convert to percentage
            
            # After processing, update the state in Home Assistant.
            self.async_write_ha_state()
            _LOGGER.debug(f"Updated '{self._zone}' zone state to: {self._state}")

        else:
            # Log ignored notifications not for this zone
            _LOGGER.debug(f"Ignoring notification for {feature}, not for zone {self._zone}")
    
    async def async_turn_on(self):
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        await self._controller.set_feature(f"{feature_prefix}power", 'on')

    async def async_turn_off(self):
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        await self._controller.set_feature(f"{feature_prefix}power", 'off')

    async def async_mute_volume(self, mute):
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        await self._controller.set_feature(f"{feature_prefix}mute", 'on' if mute else 'off')

    async def async_set_volume_level(self, volume):
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        if self._volumedisplay_mode == 'db':
            db_volume = volume_util.percentage_to_db(volume, -92.0, 23.0)
            await self._controller.set_feature(f"{feature_prefix}volumedb", db_volume)
        elif self._volumedisplay_mode == 'step':
            step_volume = int(volume * 100)
            await self._controller.set_feature(f"{feature_prefix}volumestep", step_volume)

    async def async_volume_up(self):
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        await self._controller.set_feature(f"{feature_prefix}volume+", 'pulse')

    async def async_volume_down(self):
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        await self._controller.set_feature(f"{feature_prefix}volume-", 'pulse')


    @property
    def state(self):
        return self._state

    @property
    def source_list(self):
        """Return the list of available input sources."""
        # Adjust source list based on zone
        if self._zone in ["zone2", "zone3"]:
            return ["MAIN SOURCE"] + sorted(set(SOURCE_MAPPINGS.values()))
        return sorted(set(SOURCE_MAPPINGS.values()))
    
    @property
    def sound_mode(self):
        """Return the current sound mode."""
        if self._sound_mode is None:
            return None
        for readable, command in SOUND_MODE_MAP.items():
            if command == self._sound_mode:
                return readable
        return self._sound_mode  # If not found in the mapping, return the raw source

    @property
    def sound_mode_list(self):
        """Return the list of available sound modes."""
        return sorted(set(SOUND_MODE_MAP.keys()))

    async def async_select_sound_mode(self, sound_mode):
        """Set the sound mode of the media player."""
        command_value = SOUND_MODE_MAP.get(sound_mode)
        if command_value is None:
            # Handle the error: the sound_mode is not recognized
            _LOGGER.error("Unsupported sound mode: %s", sound_mode)
            return

        # Use the command to set the sound mode
        try:
            await self._controller.set_feature('audio.soundfield', command_value)
        except Exception as e:
            _LOGGER.error("Error setting sound mode: %s", e)
            # Handle any exceptions, possibly re-throwing them or logging them as needed

    @property
    def source(self):
        """Return the current input source from the mapping or raw if not mapped."""
        if self._source is None:
            return None  # If source is None, return None without trying to map it
        # Check for 'source' and return 'MAIN SOURCE' if it matches
        if self._source == "source":
            return "MAIN SOURCE"

        # Use the cleaned-up mapping to convert the source command to a human-readable source name
        # Handling multiple receiver source keys mapping to a single Home Assistant source value
        for command, readable in SOURCE_MAPPINGS.items():
            if command == self._source:
                return readable
        return self._source  # If not found in the mapping, return the raw source

    async def async_select_source(self, source):
        """Select the input source."""
        feature_prefix = f"{self._zone}." if self._zone != "main" else "main."
        command_value = None

        if source == "MAIN SOURCE" and self._zone in ["zone2", "zone3"]:
            command_value = await self._controller.get_feature("main.input")
            _LOGGER.debug(f"Source 'MAIN SOURCE' selected, setting '{feature_prefix}input' to follow the main zone.")
        else:
            for readable, command in REVERSE_SOURCE_MAPPINGS.items():
                if source == readable:
                    command_value = command
                    _LOGGER.debug(f"Setting source '{source}' for {self._zone} to command value '{command_value}'.")
                    break

        if command_value:
            await self._controller.set_feature(f"{feature_prefix}input", command_value)
            _LOGGER.debug(f"Command '{feature_prefix}input': '{command_value}' sent to receiver.")
        else:
            _LOGGER.error(f"Unknown source '{source}' selected for {self._zone} zone.")

    @property
    def is_volume_muted(self):
        return self._mute

    @property
    def volume_level(self):
        return self._volume

    @property
    def supported_features(self):
        return SUPPORTED_FEATURES

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Sony CISIP2 media player platform."""

    if discovery_info is None:
        return  # Discovery info is missing, so we can't proceed

    zone = discovery_info.get('zone', 'main')

    controller = hass.data[DOMAIN]['controller']
    mac_address = hass.data[DOMAIN]['mac_address']  # Use the MAC address from hass.data
    sony_hwversion = hass.data[DOMAIN]['sony_hwversion']
    sony_swversion = hass.data[DOMAIN]['sony_swversion']
    entities = []
    for zone in ZONES:
        player = SonyCISIP2MediaPlayer(hass, controller, mac_address, zone, sony_hwversion, sony_swversion)
        entities.append(player)

    async_add_entities(entities)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up Sony CISIP2 media player based on a config entry."""
    
    zone = entry.data.get('zone', 'main') 

    controller = hass.data[DOMAIN]['controller']
    mac_address = hass.data[DOMAIN]['mac_address']  # Use the MAC address from hass.data
    sony_hwversion = hass.data[DOMAIN]['sony_hwversion']
    sony_swversion = hass.data[DOMAIN]['sony_swversion']
    entities = []
    for zone in ZONES:
        player = SonyCISIP2MediaPlayer(hass, controller, mac_address, zone, sony_hwversion, sony_swversion)
        entities.append(player)
    async_add_entities(entities)
