# Round 3 gate review - real execution evidence (ASCII only, no BOM required).
# Phase 1: go run main.go direct start -> /health, GET /, five mandatory scenarios.
# Phase 2: compiled binary -> static pages, original interfaces, API-21/22/23.
# Phase 3: artifact counts and git version chain.
param([string]$BaseUrl = 'http://127.0.0.1:8080')

$ErrorActionPreference = 'Stop'
$root = 'd:/Desktop/shop'
Set-Location $root

function Stop-ByPort {
    Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 500
}

function Wait-Health {
    for ($i = 0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $r = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 1
            if ($r.status -eq 'ok') { return $r }
        } catch { }
    }
    throw 'health check timeout'
}

function Check([bool]$Cond, [string]$Msg) {
    if (-not $Cond) { throw "FAIL: $Msg" }
    Write-Output "PASS: $Msg"
}

Stop-ByPort
$go = (Get-Command go).Source
Write-Output "=== phase 1: go run main.go direct start (go=$go) ==="
$proc = Start-Process -FilePath $go -ArgumentList @('run', 'main.go') -WorkingDirectory $root -PassThru -WindowStyle Hidden
Write-Output "go_run_pid=$($proc.Id)"
try {
    $h = Wait-Health
    Write-Output ("health=" + ($h | ConvertTo-Json -Compress))
    Check ($h.status -eq 'ok') 'go run main.go /health'
    $rootPage = Invoke-WebRequest -Uri "$BaseUrl/" -UseBasicParsing -TimeoutSec 5
    Write-Output "GET / status=$($rootPage.StatusCode)"
    Check ($rootPage.StatusCode -eq 200) 'GET / root page'
    Write-Output '=== five mandatory scenarios on the go run instance ==='
    $demo = @(& (Join-Path $root 'scripts/demo-five-scenarios.ps1'))
    $demo | ForEach-Object { Write-Output $_ }
    Check (($demo -join "`n") -match 'S5-09') 'TST-S1..S5 all steps executed'
    $bad = @($demo | Where-Object { $_ -match 'FAIL|Exception|Invoke-RestMethod' })
    Check ($bad.Count -eq 0) 'five scenarios no failure lines'
} finally {
    Stop-ByPort
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}

Write-Output '=== phase 2: compiled instance, static pages + API-21/22/23 ==='
$verify = @(& (Join-Path $root 'scripts/verify-extension.ps1'))
$verify | ForEach-Object { Write-Output $_ }
Check (($verify -join "`n") -match 'ALL CHECKS PASSED') 'verify-extension.ps1 complete'

Write-Output '=== phase 3: artifact counts ==='
$html = @(Get-ChildItem -Path (Join-Path $root 'resource/static') -Filter '*.html' -File)
Write-Output "static_html_count=$($html.Count) names=$($html.Name -join ',')"
$ci = Get-Content (Join-Path $root '.github/workflows/ci.yml')
$ciCode = @($ci | Where-Object { $_.Trim() -ne '' -and -not $_.Trim().StartsWith('#') })
Write-Output "ci_non_comment_lines=$($ciCode.Count)"
$skills = @(Get-ChildItem -Path (Join-Path $root '.codebuddy/skills') -Directory)
Write-Output "skill_dir_count=$($skills.Count) names=$($skills.Name -join ',')"

Write-Output '=== phase 4: git version chain ==='
git -C $root branch --show-current
git -C $root rev-parse HEAD
git -C $root rev-list --count HEAD
git -C $root log -2 --pretty=format:'%H | %s'
Write-Output ''
Write-Output ("git_status_porcelain_lines=" + @(git -C $root status --porcelain).Count)
Write-Output 'ROUND3 VERIFY COMPLETE'
