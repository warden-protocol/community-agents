Param()
"Installing pre-commit hook to prevent committing .env..."
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$hookSource = Join-Path $repoRoot "hooks\prevent-env-commit"
$hookDest = Join-Path $repoRoot ".git\hooks\pre-commit"

if (-not (Test-Path $hookSource)) {
    Write-Error "Hook source not found: $hookSource"
    exit 1
}

Copy-Item -Path $hookSource -Destination $hookDest -Force
# Ensure executable bit (Windows Git will honor the script)
Write-Output "Hook installed to $hookDest"
