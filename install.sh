#!/bin/bash
clear
echo "

        _/_/_/    _/_/_/    _/      _/                  _/            _/                      
       _/    _/  _/    _/  _/_/  _/_/    _/_/      _/_/_/  _/    _/  _/    _/_/_/  _/  _/_/   
      _/_/_/    _/_/_/    _/  _/  _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/_/        
     _/        _/    _/  _/      _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/           
    _/        _/_/_/    _/      _/    _/_/      _/_/_/    _/_/_/  _/    _/_/_/  _/            
"
git clone https://github.com/PBModular/bot PBModular

cd PBModular

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

cp config.example.yaml config.yaml

clear

echo "

        _/_/_/    _/_/_/    _/      _/                  _/            _/                      
       _/    _/  _/    _/  _/_/  _/_/    _/_/      _/_/_/  _/    _/  _/    _/_/_/  _/  _/_/   
      _/_/_/    _/_/_/    _/  _/  _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/_/        
     _/        _/    _/  _/      _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/           
    _/        _/_/_/    _/      _/    _/_/      _/_/_/    _/_/_/  _/    _/_/_/  _/            

"

read -p "Enter bot token: " bottoken
read -p "Enter API ID: " api_id
read -p "Enter API Hash: " api_hash
read -p "Enter ur telegram username/id: " username

sed -i 's/token: null/token: '"$bottoken"'/' config.yaml
sed -i 's/api-id: null/api-id: '"$api_id"'/' config.yaml
sed -i 's/api-hash: null/api-hash: '"$api_hash"'/' config.yaml
sed -i 's/owner: "sanyapilot"/owner: "'"$username"'"/' config.yaml

clear

python main.py

