<#
.SYNOPSIS
    Prepares a WSL distro with SageMath (via Miniforge/conda-forge) so that
    run_pipeline.py can use it. Safe to re-run: each step is skipped if
    already done.

.PARAMETER Distro
    Name of the WSL distro to use. If omitted, the first installed distro
    is used (or Ubuntu is installed if none exists).
#>

param(
    [string]$Distro = ""
)

$ErrorActionPreference = "Stop"

function Get-FirstInstalledDistro {
    $raw = wsl.exe -l -q 2>$null
    $names = $raw | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ -ne "" }
    # Excluir las distros internas de Docker Desktop: no tienen un userland
    # Linux normal (ni siquiera bash), asi que no sirven para instalar Sage.
    $names = $names | Where-Object { $_ -notin @("docker-desktop", "docker-desktop-data") }
    return $names | Select-Object -First 1
}

Write-Host "== 1/4: Comprobando WSL =="
wsl.exe --status *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "WSL no esta disponible. Instalalo con 'wsl --install', reinicia el equipo y vuelve a ejecutar este script."
    exit 1
}

if (-not $Distro) {
    $Distro = Get-FirstInstalledDistro
}

if (-not $Distro) {
    Write-Host "No hay ninguna distro de WSL instalada. Instalando Ubuntu..."
    wsl.exe --install -d Ubuntu
    Write-Error "Reinicia el equipo si se te pide, crea el usuario de Ubuntu la primera vez que la abras, y vuelve a ejecutar este script."
    exit 1
}

Write-Host "Usando distro: $Distro"

Write-Host "`n== 2/4: Comprobando Miniforge =="
wsl.exe -d $Distro -- bash -lc 'test -d "$HOME/miniforge3"'
if ($LASTEXITCODE -eq 0) {
    Write-Host "Miniforge ya estaba instalado, se omite."
} else {
    Write-Host "Instalando Miniforge (conda + mamba)..."
    wsl.exe -d $Distro -- bash -lc @'
set -e
cd "$HOME"
curl -fsSL -o Miniforge3.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3.sh -b -p "$HOME/miniforge3"
rm -f Miniforge3.sh
'@
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Fallo instalando Miniforge."
        exit 1
    }
}

Write-Host "`n== 3/4: Comprobando entorno conda 'sage' =="
wsl.exe -d $Distro -- bash -lc 'test -d "$HOME/miniforge3/envs/sage"'
if ($LASTEXITCODE -eq 0) {
    Write-Host "El entorno 'sage' ya existia, se omite."
} else {
    Write-Host "Instalando SageMath desde conda-forge (puede tardar 15-30 minutos)..."
    wsl.exe -d $Distro -- bash -lc @'
set -e
source "$HOME/miniforge3/etc/profile.d/conda.sh"
source "$HOME/miniforge3/etc/profile.d/mamba.sh"
mamba create -y -n sage -c conda-forge sage python=3.12
'@
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Fallo instalando SageMath."
        exit 1
    }
}

Write-Host "`n== 4/4: Verificando instalacion =="
wsl.exe -d $Distro -- bash -lc 'source "$HOME/miniforge3/etc/profile.d/conda.sh" && conda activate sage && sage --version'
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSageMath listo en la distro '$Distro'. Ya puedes usar run_pipeline.py"
} else {
    Write-Error "La verificacion final de Sage fallo."
    exit 1
}
