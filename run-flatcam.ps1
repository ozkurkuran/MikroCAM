$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    Write-Error 'Missing checkout environment: create .venv with the Python version in .python-version.' -ErrorAction Continue
    exit 1
}

$version = (Get-Content -LiteralPath (Join-Path $PSScriptRoot '.python-version') -Raw).Trim()
$target = ($version.Split('.')[0..1]) -join '.'
& $python -c "import sys, struct, sysconfig; expected = tuple(map(int, sys.argv[1].split('.'))); valid = sys.implementation.name == 'cpython' and sys.version_info[:2] == expected and struct.calcsize('P') == 8 and not sysconfig.get_config_var('Py_GIL_DISABLED'); sys.exit(0 if valid else 1)" $target
if ($LASTEXITCODE -ne 0) {
    Write-Error "Invalid checkout interpreter: require standard CPython $target x64 (not free-threaded; tested version $version). Recreate .venv." -ErrorAction Continue
    exit 1
}

$env:QT_API = 'pyqt6'
Push-Location -LiteralPath $PSScriptRoot
try {
    & $python (Join-Path $PSScriptRoot 'flatcam.py') @args
    $status = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $status
