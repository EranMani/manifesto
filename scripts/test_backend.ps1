<#
.SYNOPSIS
    Run the backend test suite inside the Docker backend container, against
    the Dockerized PostgreSQL database (hostname `db`, per docker-compose.yml).

.PARAMETER CollectOnly
    Pass --collect-only to pytest instead of running the tests.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/test_backend.ps1
    powershell -ExecutionPolicy Bypass -File scripts/test_backend.ps1 -CollectOnly
#>
param(
    [switch]$CollectOnly
)

$pytestArgs = @("uv", "run", "pytest", "tests/")
if ($CollectOnly) {
    $pytestArgs += "--collect-only"
}

docker compose run --rm backend @pytestArgs

exit $LASTEXITCODE
