![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black) ![Windows](https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows11&logoColor=white)

# PBModular

#### A simple modular bot for anything you code.

![](https://img.shields.io/github/languages/code-size/PBModular/bot) ![](https://img.shields.io/github/license/PBModular/bot) ![](https://img.shields.io/badge/python-%3E%203.9-blue)

## Features

- Modularity

- Linux, Windows and Android (Termux) support >.<

  > To work on Windows and Android, you must remove the uvloop dependency from the requrements.txt before installing

- Open Source, lol

## Installation

> You can use `install.sh/ps1` bash/powershell installation scripts (thanks to @vilander1337) or proceed with manual installation below
## For linux distros
  ```bash
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/pbmodular/bot/master/install.sh)"
  ```
## For windows (run in powershell)
  ```pwsh
  iex ((New-Object System.Net.WebClient).DownloadString('https://raw.githubusercontent.com/PBModular/bot/master/install.ps1'))
  ```
## Manual installation

  ```bash
  sh -c "$(curl -fsSL https://raw.githubusercontent.com/pbmodular/bot/master/install.sh)"
  ```
## Manual installation

1. Clone repository  
   
   ```bash
   git clone https://github.com/PBModular/bot PBModular
   ```

2. Install Python packages (and setup venv, if you want)
   
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Copy `config.example.yaml` to `config.yaml`

4. Edit `config.yaml`

5. Run it!
   
   ```bash
   python main.py
   ```

To run bot automatically at system boot (if you're using systemd and Linux) you can use this example systemd daemon:

```systemd
[Unit]
Description=Any description of daemon here
After=network.target

[Service]
WorkingDirectory=/path/to/bot/sources
Type=simple
User=cooluser
# If you don't use venv, change python path to /usr/bin/python3 in a command below
ExecStart=/path/to/bot/sources/venv/bin/python3 -u /path/to/bot/sources/main.py
# Restart bot after fail
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Wiki translation

English wiki is in progress now... Currently the only available language is russian.

## Windows support
It should be mentioned that Windows support is not gueranteed at all! Something can break randomly just because we are writing for *nix environment.

## Authors

- [@SanyaPilot](https://github.com/SanyaPilot)
- [@CakesTwix](https://github.com/CakesTwix)

## Contributing

Contributions are always welcome!

## License

[GNU GPLv3](https://github.com/SanyaPilot/PBModular/blob/master/LICENSE)
