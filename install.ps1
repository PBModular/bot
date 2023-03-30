Set-ExecutionPolicy Unrestricted

Clear-Host

Write-Output "
        _/_/_/    _/_/_/    _/      _/                  _/            _/                      
       _/    _/  _/    _/  _/_/  _/_/    _/_/      _/_/_/  _/    _/  _/    _/_/_/  _/  _/_/   
      _/_/_/    _/_/_/    _/  _/  _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/_/        
     _/        _/    _/  _/      _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/           
    _/        _/_/_/    _/      _/    _/_/      _/_/_/    _/_/_/  _/    _/_/_/  _/            
"

git clone https://github.com/PBModular/bot PBModular

cd PBModular

python -m venv venv

.\venv\Scripts\activate.ps1

pip install -r requirements.txt

Copy-Item config.example.yaml config.yaml

Clear-Host

Write-Output "
        _/_/_/    _/_/_/    _/      _/                  _/            _/                      
       _/    _/  _/    _/  _/_/  _/_/    _/_/      _/_/_/  _/    _/  _/    _/_/_/  _/  _/_/   
      _/_/_/    _/_/_/    _/  _/  _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/_/        
     _/        _/    _/  _/      _/  _/    _/  _/    _/  _/    _/  _/  _/    _/  _/           
    _/        _/_/_/    _/      _/    _/_/      _/_/_/    _/_/_/  _/    _/_/_/  _/            
"

$bottoken = Read-Host "Enter bot token"
$api_id = Read-Host "Enter api id"
$api_hash = Read-Host "Enter api hash"
$username = Read-Host "Enter telegram username/id"

(Get-Content -Path "config.yaml") -replace 'token: null', ('token: ' + $bottoken) | Set-Content -Path "config.yaml"
(Get-Content -Path "config.yaml") -replace 'api-id: null', ('api-id: ' + $api_id) | Set-Content -Path "config.yaml"
(Get-Content -Path "config.yaml") -replace 'api-hash: null', ('api-hash: ' + $api_hash) | Set-Content -Path "config.yaml"
(Get-Content -Path "config.yaml") -replace 'owner: "sanyapilot"', ('owner: ' + $username) | Set-Content -Path "config.yaml"

Clear-Host

python main.py 
