<h1 align="center">PBModular</h1>

<p align="center">
  A lightweight and flexible modular bot framework on Pyrogram.
</p>

<p align="center">
  <a href="https://pbmodular.github.io/wiki/"><img src="https://img.shields.io/badge/documentation-english-blue.svg?style=for-the-badge" alt="English Docs"></a>
  <a href="https://pbmodular.github.io/wiki/ru/"><img src="https://img.shields.io/badge/документация-русский-blue.svg?style=for-the-badge" alt="Russian Docs"></a>
  <a href="https://t.me/PBModular_chat"><img src="https://img.shields.io/badge/telegram-chat-26A5E4.svg?style=for-the-badge&logo=telegram" alt="Telegram Chat"></a>
</p>

<p align="center">
  <img alt="Python Version" src="https://img.shields.io/badge/python-%3E=3.11-blue?style=flat-square&logo=python&logoColor=ffdd54">
  <img alt="GitHub License" src="https://img.shields.io/github/license/PBModular/bot?style=flat-square">
  <img alt="GitHub code size in bytes" src="https://img.shields.io/github/languages/code-size/PBModular/bot?style=flat-square">
  <br>
  <img alt="Linux" src="https://img.shields.io/badge/Linux-FCC624?style=flat-square&logo=linux&logoColor=black">
  <img alt="Windows" src="https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows11&logoColor=white">
</p>

PBModular is a lightweight and flexible bot framework designed to be something between a userbot and a traditional bot, giving you the power to automate tasks and extend functionality with ease.

---

## Table of Contents

- [Key Features](#key-features)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Installation](#quick-installation-linuxwindows)
  - [Manual Installation](#manual-installation)
- [Running as a Systemd Service](#running-as-a-systemd-service-linux)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Contributors](#contributors)
- [License](#license)

---

## Key Features

*   **Modular Design:** Easily extend and customize your bot's features with a plugin-based architecture. Explore official [modules](https://github.com/PBModular/).
*   **Cross-Platform:** Supports Linux, Windows, and Android (Termux).
*   **Open Source:** Contribute, modify, and adapt the bot to your specific needs under the GPLv3 license.

> **Note for Windows and Android:** Remove the `uvloop` dependency from `requirements.txt` before installation, as it is not supported on these platforms.

## Getting Started

### Prerequisites

Make sure you have the following software installed on your system:
*   [Python](https://www.python.org/downloads/) (version 3.11 or newer)
*   [Git](https://git-scm.com/downloads/)

### Quick Installation (Linux/Windows)

We provide convenient installation scripts for Linux and Windows:

**Linux (Bash):**

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/PBModular/bot/refs/heads/master/install.sh)"
```

**Windows (PowerShell):**

```powershell
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/PBModular/bot/refs/heads/master/install.ps1'))
```

### Manual Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/PBModular/bot PBModular
   cd PBModular
   ```

2. **Create and activate a virtual environment (recommended):**

   ```bash
   # For Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # For Windows
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your bot:**

   ```bash
   # Create the config file from the example
   cp config.example.yaml config.yaml

   # Edit the configuration file with your favorite editor
   nano config.yaml 
   ```

5. **Run the bot:**

   ```bash
   python main.py
   ```

## Running as a Systemd Service (Linux)

Use this example systemd service file to run your bot automatically at system boot. Create a file like `/etc/systemd/system/pbmodular.service`:

```systemd
[Unit]
Description=PBModular Bot
After=network.target

[Service]
WorkingDirectory=/path/to/bot/sources
Type=simple
User=your_user
# If not using a venv, change this path to your system's python executable
ExecStart=/path/to/bot/sources/venv/bin/python3 -u /path/to/bot/sources/main.py
# Restart bot after fail
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Remember to replace `/path/to/bot/sources` and `your_user`. Then, enable and start the service:
```bash
sudo systemctl enable --now pbmodular.service
```

## Documentation

Full documentation, including module development guides, is available on our wiki:

*   **English:** [https://pbmodular.github.io/wiki/](https://pbmodular.github.io/wiki/)
*   **Russian:** [https://pbmodular.github.io/wiki/ru/](https://pbmodular.github.io/wiki/ru/)

## Contributing

We welcome contributions! Feel free to open issues, submit pull requests, or join the discussion. A good place to start is our community chat.

*   **Bug Reports & Feature Requests:** [Create an issue](https://github.com/PBModular/bot/issues)
*   **Community Chat:** [Join us on Telegram](https://t.me/+2iDmbf1VE39hOWZi)

Want to contribute documentation in your language? Contact [@SanyaPilot](https://github.com/SanyaPilot) or [@Ultra119](https://github.com/Ultra119).

## Contributors

A big thanks to everyone who has contributed to PBModular!

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/SanyaPilot"><img src="https://avatars.githubusercontent.com/u/29630471?v=4?s=100" width="100px;" alt="SanyaPilot"/><br /><sub><b>SanyaPilot</b></sub></a><br /><a href="https://github.com/PBModular/bot/commits?author=SanyaPilot" title="Code">💻</a> <a href="#maintenance-SanyaPilot" title="Initial Idea and Realisation">💡</a> <a href="#doc-SanyaPilot" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Ultra119"><img src="https://avatars.githubusercontent.com/u/64977575?v=4?s=100" width="100px;" alt="Ultra119"/><br /><sub><b>Ultra119</b></sub></a><br /> <a href="#maintenance-Ultra119" title="Maintenance">🚧</a> <a href="https://github.com/PBModular/bot/commits?author=Ultra119" title="Code">💻</a> <a href="#doc-Ultra119" title="Documentation">📖</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/CakesTwix"><img src="https://avatars.githubusercontent.com/u/57946485?v=4?s=100" width="100px;" alt="CakesTwix"/><br /><sub><b>CakesTwix</b></sub></a><br /><a href="#translation-CakesTwix" title="Translation">🌍</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/vilander1337"><img src="https://avatars.githubusercontent.com/u/111059518?v=4?s=100" width="100px;" alt="vilander1337"/><br /><sub><b>vilander1337</b></sub></a><br /><a href="#doc-vilander1337" title="Documentation">📖</a> <a href="https://github.com/PBModular/bot/commits?author=vilander1337" title="Code">💻</a></td>
    </tr>
  </tbody>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

## License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](https://github.com/PBModular/bot/blob/master/LICENSE) file for details.
