#!/bin/bash

check_status() {
    if [ $? -ne 0 ]; then
        echo "Error: $1 failed. Exiting."
        exit 1
    fi
}

clear
echo "
██████╗ ██████╗ ███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ 
██╔══██╗██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██║   ██║██║     ██╔══██╗██╔══██╗
██████╔╝██████╔╝██╔████╔██║██║   ██║██║  ██║██║   ██║██║     ███████║██████╔╝
██╔═══╝ ██╔══██╗██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║     ██╔══██║██╔══██╗
██║     ██████╔╝██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║
╚═╝     ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
"

git clone https://github.com/PBModular/bot PBModular
check_status "Git clone"

cd PBModular

if [ ! -d "venv" ]; then
    python3 -m venv venv
    check_status "Virtual environment creation"
fi

source venv/bin/activate
check_status "Virtual environment activation"

pip install --upgrade pip
check_status "Pip upgrade"

pip install -r requirements.txt
check_status "Dependency installation"

if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
    check_status "Config file copy"
fi

clear

echo "
██████╗ ██████╗ ███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ 
██╔══██╗██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██║   ██║██║     ██╔══██╗██╔══██╗
██████╔╝██████╔╝██╔████╔██║██║   ██║██║  ██║██║   ██║██║     ███████║██████╔╝
██╔═══╝ ██╔══██╗██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║     ██╔══██║██╔══██╗
██║     ██████╔╝██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║
╚═╝     ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
"

read -p "Enter bot token: " bottoken
read -p "Enter API ID: " api_id
read -p "Enter API Hash: " api_hash
read -p "Enter your Telegram username/ID: " username
read -p "Choose your language (ru/en/ua): " language

sed -i "s/token: null/token: $bottoken/" config.yaml
sed -i "s/api-id: null/api-id: $api_id/" config.yaml
sed -i "s/api-hash: null/api-hash: $api_hash/" config.yaml
sed -i "s/owner: \"sanyapilot\"/owner: \"$username\"/" config.yaml
sed -i "s/language: ru/language: $language/" config.yaml

clear

python3 main.py
