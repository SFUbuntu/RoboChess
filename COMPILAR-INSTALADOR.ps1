param(
    [string]$ISCC = '',
    [switch]$RebuildEngines
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

python -m venv .build-venv
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno Python' }

$buildPython = Join-Path $PSScriptRoot '.build-venv/Scripts/python.exe'
& $buildPython -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias' }

$buildArguments = @('build_windows.py')
if ($RebuildEngines) { $buildArguments += '--rebuild-engines' }
& $buildPython @buildArguments
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del ejecutable' }

if (-not $ISCC) {
    $compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($compilerCommand) { $ISCC = $compilerCommand.Source }
}
if (-not $ISCC) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe"
    )
    $ISCC = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $ISCC -or -not (Test-Path -LiteralPath $ISCC)) {
    throw 'Instala Inno Setup o pasa -ISCC con la ruta a ISCC.exe. El programa ya esta en dist\RoboChess.'
}

& $ISCC installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del instalador' }
