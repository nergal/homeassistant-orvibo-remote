# Homeassistant Orvibo remote

[![hacs_badge][hasc-shield]](https://github.com/custom-components/hacs)
![Project Stage][stage-shield]
[![Code style: black][black-shield]](https://github.com/psf/black)
![GitHub][license-shield]

> :warning: **DISCLAIMER:** This code is an early alpha release with all related consequences. If you decide to use it, any feedback is appreciated

Remote integration for Orvibo AllOne IR remote. Designed to be used with [smartHomeHub/SmartIR](https://github.com/smartHomeHub/SmartIR) integration.

## Installation
You can install this remote via HACS, just add it as a custom repository by clicking a three dots in the top left corder on a HACS page.

Configuration example:
``` yaml
orvibo_remote:
remote:
  - platform: orvibo_remote
    host: 192.168.1.1
    name: Orvibo AllOne
```

Configuration example with a SmartIR:
``` yaml
orvibo_remote:
remote:
  - platform: orvibo_remote
    host: 192.168.1.93
    name: Orvibo AllOne

smartir:
climate:
  - platform: smartir
    name: Living AC
    unique_id: living_ac
    device_code: 1066
    controller_data: remote.orvibo_remote_xxxxxxxxxxxx
```

> Small notice about included sources of asyncio_orvibo - it is a slightly modified code, and it has to be there to avoid raising an issue using a `reuse_address = True` inside that lib.

## Disclaimer
This project is not affiliated, associated, authorized, endorsed by, or in any way officially connected with the Shenzhen ORVIBO Technology Co., LTD, or any of its subsidiaries or its affiliates. The official Orvibo website can be found at https://www.orvibo.com/en.

## License
This project is under the MIT license.

[!["Buy Me A Coffee"][coffee-shield]](https://www.buymeacoffee.com/nalecz)


[license-shield]: https://img.shields.io/github/license/nergal/homeassistant-orvibo-remote
[hasc-shield]: https://img.shields.io/badge/HACS-Custom-orange.svg
[coffee-shield]: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
[stage-shield]: https://img.shields.io/badge/project%20stage-stage-orange.svg
[black-shield]: https://img.shields.io/badge/code%20style-black-000000.svg