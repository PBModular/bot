Set-ExecutionPolicy Unrestricted -Scope Process

Clear-Host

Write-Output "
██████╗ ██████╗ ███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ 
██╔══██╗██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██║   ██║██║     ██╔══██╗██╔══██╗
██████╔╝██████╔╝██╔████╔██║██║   ██║██║  ██║██║   ██║██║     ███████║██████╔╝
██╔═══╝ ██╔══██╗██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║     ██╔══██║██╔══██╗
██║     ██████╔╝██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║
╚═╝     ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
"

git clone https://github.com/PBModular/bot PBModular
if ($LASTEXITCODE -ne 0) {
    Write-Error "Git clone failed. Exiting."
    exit 1
}

cd PBModular

if (-not (Test-Path "venv")) {
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Virtual environment creation failed. Exiting."
        exit 1
    }
}

.\venv\Scripts\Activate.ps1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Virtual environment activation failed. Exiting."
    exit 1
}

pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Error "Pip upgrade failed. Exiting."
    exit 1
}

(Get-Content -Path "requirements.txt") | Where-Object { $_ -notmatch 'uvloop' } | Set-Content -Path "requirements.txt"

pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Error "Dependency installation failed. Exiting."
    exit 1
}

if (-not (Test-Path "config.yaml")) {
    Copy-Item config.example.yaml config.yaml
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Config file copy failed. Exiting."
        exit 1
    }
}

Clear-Host

Write-Output "
██████╗ ██████╗ ███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗██╗      █████╗ ██████╗ 
██╔══██╗██╔══██╗████╗ ████║██╔═══██╗██╔══██╗██║   ██║██║     ██╔══██╗██╔══██╗
██████╔╝██████╔╝██╔████╔██║██║   ██║██║  ██║██║   ██║██║     ███████║██████╔╝
██╔═══╝ ██╔══██╗██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║     ██╔══██║██╔══██╗
██║     ██████╔╝██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝███████╗██║  ██║██║  ██║
╚═╝     ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
"

$bottoken = Read-Host "Enter bot token: "
$api_id = Read-Host "Enter API ID: "
$api_hash = Read-Host "Enter API Hash: "
$username = Read-Host "Enter your Telegram username/ID: "
$language = Read-Host "Choose your language (ru/en/ua): "

$configContent = Get-Content -Path "config.yaml"
$configContent -replace 'token: null', "token: $bottoken" |
    ForEach-Object { $_ -replace 'api-id: null', "api-id: $api_id" } |
    ForEach-Object { $_ -replace 'api-hash: null', "api-hash: $api_hash" } |
    ForEach-Object { $_ -replace 'owner: "sanyapilot"', "owner: `"$username`"" } |
    ForEach-Object { $_ -replace 'language: ru', "language: $language" } |
    Set-Content -Path "config.yaml"

Clear-Host

python .\main.py
