import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from .const import DOMAIN, DEFAULT_PORT

from python_sonycisip2 import SonyCISIP2

class SonyCISIP2ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            # Validate user input
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            name = user_input.get(CONF_NAME, f"Sony Receiver {host}")

            try:
                # Attempt to connect to the Sony device
                controller = SonyCISIP2(host, port)
                await controller.connect()

                # If successful, create the config entry
                return self.async_create_entry(title=name, data=user_input)

            except ConnectionError:
                errors["base"] = "cannot_connect"

            except Exception:  # Handle unexpected exceptions
                errors["base"] = "unknown_error"

        # Display the form for user input
        data_schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            vol.Optional(CONF_NAME): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
    
#     @callback
#     def async_get_options_flow(config_entry):
#         """Get the options flow for this handler."""
#         return SonyCISIP2OptionsFlowHandler(config_entry)

# class SonyCISIP2OptionsFlowHandler(config_entries.OptionsFlow):
#     async def async_step_init(self, user_input=None):
#         """Manage the options."""
#         return await self.async_step_options_1()

#     async def async_step_options_1(self, user_input=None):
#         """Manage the Sony CISIP2 options."""
#         if user_input is not None:
#             # Update options
#             return self.async_create_entry(title="", data=user_input)

#         # Define the options schema here if needed
#         options_schema = vol.Schema({
#             # Define your options fields here
#         })

#         return self.async_show_form(
#             step_id="options_1",
#             data_schema=options_schema
#         )
