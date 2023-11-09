# Sony ES Custom Component for Home Assistant

This custom component integrates Sony ES AV Receivers (STR-ZAxx00ES series) with Home Assistant, allowing for control and automation within your smart home ecosystem. Currently tested and confirmed working with STR-ZA2100ES.

Uses the Python library python_sonycisip2 for communication, found at [zimmra/python_sonycisip](https://github.com/zimmra/python_sonycisip2)

## Features

- **Multi-Zone Control**: Creates a `media_player` entity within the parent device for individual each of the receiver's zones.
- **Input Switching**: Allows input source switching directly from Home Assistant.
- **Volume Control**: Manage the volume for each zone through the Home Assistant interface.
- **Power Control**: Power on or off each zone independently.
- **Real-Time State**: The receiver's state is updated in real-time through broadcast messages.

## Installation

You can install this custom component via HACS or manually. 

### Via HACS

1. Open HACS in Home Assistant.
2. Navigate to 'Integrations' and then the '+ Explore & Add Repositories' button.
3. Search for `Sony CISIP2` and select it.
4. Click 'Install' and select the latest version.
5. Restart Home Assistant.

### Manual Installation

1. Download the `sony_cisip2` repository from GitHub.
2. Unpack the release and copy the `sony_cisip2` folder to your `custom_components` directory in Home Assistant.
3. Restart Home Assistant.

## Configuration

### Through the UI

1. Navigate to 'Configuration' -> 'Integrations'.
2. Click on the '+ Add Integration' button.
3. Search for `Sony CISIP2`.
4. Follow the on-screen instructions to configure the receiver.

### Via `configuration.yaml` (Advanced)

Add the following lines to your `configuration.yaml` file:

```yaml
sony_cisip2:
    host: IP_ADDRESS
    port: 33336 # Default port, known working for x100ES series. x000ES series may need port 33335
```

Replace `IP_ADDRESS` with the IP address of your receiver.

## Usage

After installation and configuration, you can control your Sony ES AV Receiver through the Home Assistant interface.

- **Media Control**: Use Home Assistant to control play, pause, stop, and other media commands.
- **Volume Adjustment**: Adjust volume through the Home Assistant interface or automate it based on different scenes or triggers.
- **Source Selection**: Change the input source of your receiver directly from the Home Assistant dashboard.
- **Power Management**: Turn your receiver or individual zones on and off.

## Known Issues

- `SOURCE` input command isn't working via IP, investigating. May not be possible. `SOURCE` is intended for `zone2` and `zone3` to match the `main` zones source

## Not Tested

- Only tested with STR-ZA2100ES
- No tests with multiple receivers conducted

## Support

For issues, questions, and more information, visit the [Issues](https://github.com/zimmra/sony_cisip2/issues) section of this GitHub repository.

## Contributing

Contributions are welcome! If you'd like to contribute, please fork the repository and submit a pull request.

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## Acknowledgments

- Thanks to everyone who has contributed to the project!
- Special thanks to the developers of Home Assistant for their continued dedication to the open-source community.
