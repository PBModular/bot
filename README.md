# PBModular

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) 
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) 
![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows11&logoColor=white)

![Python Version](https://img.shields.io/badge/python-%3E%203.11-blue)
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/PBModular/bot)
![GitHub](https://img.shields.io/github/license/PBModular/bot)

PBModular is a lightweight and flexible bot framework designed for anything you code. Something between a userbot and a standard bot.

## Key Features

* **Modular Design:** Easily extend and customize your bot features with a plugin-based [modules](https://github.com/PBModular/)
* **Cross-Platform:** Supports Linux, Windows, and Android (Termux).
  * **Note for Windows and Android:** Remove the `uvloop` dependency from `requirements.txt` before installation.
* **Open Source:** Contribute, modify, and adapt the bot to your specific needs.

## Getting Started

### Quick Installation (Linux/Windows)

We provide convenient installation scripts for Linux and Windows:

**Linux:**

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/pbmodular/bot/master/install.sh)"
```

**Windows (PowerShell):**

```powershell
iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/PBModular/bot/master/install.ps1'))
```

### Manual Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/PBModular/bot PBModular
   ```

2. **Install dependencies (using a virtual environment is recommended):**

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure your bot:**

   ```bash
   cp config.example.yaml config.yaml
   nano config.yaml # Edit the configuration file
   ```

4. **Run the bot:**

   ```bash
   python main.py
   ```

## Running as a Systemd Service (Linux)

Use this example systemd service file to run your bot automatically at system boot:

```systemd
[Unit]
Description=PBModular Bot
After=network.target

[Service]
WorkingDirectory=/path/to/bot/sources
Type=simple
User=your_user
# If you don't use venv, change python path to /usr/bin/python3 in a command below
ExecStart=/path/to/bot/sources/venv/bin/python3 -u /path/to/bot/sources/main.py
# Restart bot after fail
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Remember to replace placeholders like `/path/to/bot/sources` and `your_user` with your actual paths and username.

## Documentation

* **Russian:** [https://pbmodular.github.io/wiki/ru/](https://pbmodular.github.io/wiki/ru/)
* **English:** [https://pbmodular.github.io/wiki/](https://pbmodular.github.io/wiki/)

Want to contribute documentation in your language? Contact [@SanyaPilot](https://github.com/SanyaPilot) or [@Ultra119](https://github.com/Ultra119)

## Windows Support Notice

While we strive for cross-platform compatibility, Windows support is not fully guaranteed. Minor issues might arise due to the primary development environment being *nix-based.

## Contributors

* **[@SanyaPilot](https://github.com/SanyaPilot)** ([Telegram](https://t.me/sanyapilot)) - Bot core, wiki
* **[@CakesTwix](https://github.com/CakesTwix)** ([Telegram](https://t.me/CakesTwix)) - Translations
* **[@vilander1337](https://github.com/vilander1337)** - Gitbook documentation, scripts
* **[@Ultra119](https://github.com/Ultra119)** ([Telegram](https://t.me/Ultra119)) - New features, wiki site

## Contributing

We welcome contributions! Feel free to open issues, submit pull requests, or join the discussion in our [Telegram Chat](https://t.me/PBModular_chat)

## License

[GNU GPLv3](https://github.com/SanyaPilot/PBModular/blob/master/LICENSE) 
