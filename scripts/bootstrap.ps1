<#
.SYNOPSIS
    InfraNOC - Bootstrap de ambiente (instala todas as ferramentas necessarias).

.DESCRIPTION
    Rode este script UMA VEZ em um PC novo (Windows 11) para instalar tudo que o
    InfraNOC precisa: Python 3.12, uv, Node 22, Git, GitHub CLI, VS Code, Docker
    Desktop, VMware Workstation (manual), 7zip.

    O CODIGO e os DADOS ficam no SSD; este script instala as FERRAMENTAS que
    executam o projeto (elas nao rodam a partir do SSD - precisam estar na maquina).

.USAGE
    1. Abra o PowerShell COMO ADMINISTRADOR
    2. Se necessario, libere a execucao de scripts nesta sessao:
         Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    3. Rode:
         .\bootstrap.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "==== InfraNOC :: Bootstrap de ambiente ====" -ForegroundColor Cyan
Write-Host ""

# --- Verifica se e admin ---
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
          ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[X] Rode este script COMO ADMINISTRADOR." -ForegroundColor Red
    Write-Host "    (Menu Iniciar > PowerShell > botao direito > Executar como administrador)"
    exit 1
}

# --- Verifica winget ---
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "[X] winget nao encontrado. Instale o 'App Installer' pela Microsoft Store e tente de novo." -ForegroundColor Red
    exit 1
}

# --- Recursos do Windows: WSL2 + VirtualMachinePlatform ---
Write-Host "[*] Habilitando WSL2 e VirtualMachinePlatform (pode pedir reinicio depois)..." -ForegroundColor Yellow
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart | Out-Null
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart | Out-Null

# --- Instala ferramentas via winget ---
$apps = @(
    @{ id = "Microsoft.PowerShell";        name = "PowerShell 7" },
    @{ id = "Microsoft.WindowsTerminal";   name = "Windows Terminal" },
    @{ id = "Git.Git";                     name = "Git" },
    @{ id = "GitHub.cli";                  name = "GitHub CLI" },
    @{ id = "Microsoft.VisualStudioCode";  name = "VS Code" },
    @{ id = "Python.Python.3.12";          name = "Python 3.12" },
    @{ id = "OpenJS.NodeJS.LTS";           name = "Node.js LTS" },
    @{ id = "Docker.DockerDesktop";        name = "Docker Desktop" },
    @{ id = "7zip.7zip";                   name = "7-Zip" }
)

foreach ($app in $apps) {
    Write-Host "[*] Instalando $($app.name) ($($app.id))..." -ForegroundColor Yellow
    winget install --id $($app.id) --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] $($app.name)" -ForegroundColor Green
    } else {
        Write-Host "    [!] $($app.name) retornou codigo $LASTEXITCODE (pode ja estar instalado)." -ForegroundColor DarkYellow
    }
}

# --- uv (gerenciador Python) - instalador oficial ---
Write-Host "[*] Instalando uv (gerenciador de pacotes Python)..." -ForegroundColor Yellow
try {
    powershell -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    Write-Host "    [OK] uv" -ForegroundColor Green
} catch {
    Write-Host "    [!] Falha ao instalar uv. Instale manualmente: https://astral.sh/uv" -ForegroundColor DarkYellow
}

# --- .wslconfig (limita RAM do WSL - critico com 16GB) ---
Write-Host "[*] Escrevendo .wslconfig (limita WSL a 4GB RAM)..." -ForegroundColor Yellow
@"
[wsl2]
memory=4GB
processors=4
swap=2GB
localhostForwarding=true

[experimental]
autoMemoryReclaim=gradual
sparseVhd=true
"@ | Out-File -Encoding ASCII "$env:USERPROFILE\.wslconfig"
Write-Host "    [OK] .wslconfig" -ForegroundColor Green

Write-Host ""
Write-Host "==== Instalacao concluida ====" -ForegroundColor Cyan
Write-Host ""
Write-Host "PROXIMOS PASSOS MANUAIS:" -ForegroundColor White
Write-Host "  1. REINICIE o computador (para WSL2/VirtualMachinePlatform)."
Write-Host "  2. Apos reiniciar, rode: wsl --set-default-version 2; wsl --update"
Write-Host "  3. Instale o VMware Workstation Pro (nao esta no winget):"
Write-Host "     https://profile.broadcom.com/  ->  'Use for Personal Use' (gratis)"
Write-Host "  4. Abra o Docker Desktop uma vez e ajuste:"
Write-Host "     Settings > Resources > Disk image location  ->  D:\Lab\InfraNOC\data\docker"
Write-Host "  5. Autentique o Git/GitHub:  gh auth login"
Write-Host ""
Write-Host "Depois disso, para rodar o backend (veja backend\README.md):" -ForegroundColor White
Write-Host "     cd D:\Lab\InfraNOC\src\infranoc\backend"
Write-Host "     uv sync"
Write-Host "     docker compose -f compose\docker-compose.dev.yml up -d   (a partir da raiz do repo)"
Write-Host "     uv run alembic upgrade head"
Write-Host "     uv run python -m app.seed"
Write-Host "     uv run uvicorn app.main:app --reload --port 8080"
