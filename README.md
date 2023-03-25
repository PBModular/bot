![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)

# PBModular

#### A simple modular bot for anything you code.

![](https://img.shields.io/github/languages/code-size/SanyaPilot/PBModular) ![](https://img.shields.io/github/license/SanyaPilot/PBModular) ![](https://img.shields.io/badge/python-%3E%203.9-blue)


## Features

- Modularity
- Linux support >.<
- Open Source, lol

## Authors

- [@SanyaPilot](https://github.com/SanyaPilot)
- [@CakesTwix](https://github.com/CakesTwix)

## Contributing

Contributions are always welcome!

## License

[GNU GPLv3](https://github.com/SanyaPilot/PBModular/blob/master/LICENSE)

## Installation

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


