# Round 3 code-artifact completion verification (ASCII only, no BOM needed).
# Starts two fresh processes built from the same `go run main.go` entry point,
# so the five mandatory scenarios and the new artifact checks never share state.
param([string]$BaseUrl = 'http://127.0.0.1:8080')

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$exe = Join-Path $env:TEMP 'shop-trade-verify.exe'
go build -o $exe .
if ($LASTEXITCODE -ne 0) { throw 'go build failed' }

function Wait-Health {
    for ($i = 0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 400
        try {
            $r = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 1
            if ($r.status -eq 'ok') { return $r }
        } catch { }
    }
    throw 'health check timeout'
}

function Start-Demo {
    $p = Start-Process -FilePath $exe -WorkingDirectory $root -PassThru -WindowStyle Hidden
    $null = Wait-Health
    return $p
}

function Stop-Demo($p) {
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Milliseconds 400
}

function Call([string]$Method, [string]$Path, [string]$Account, $Body) {
    $params = @{
        Method = $Method; Uri = $BaseUrl + $Path
        Headers = @{ 'X-Demo-Account' = $Account }; TimeoutSec = 5
    }
    if ($null -ne $Body) {
        $params.Body = ($Body | ConvertTo-Json -Compress)
        $params.ContentType = 'application/json'
    }
    return Invoke-RestMethod @params
}

function Check([bool]$Cond, [string]$Msg) {
    if (-not $Cond) { throw "FAIL: $Msg" }
    Write-Output "PASS: $Msg"
}

# ---- process 1: original five mandatory scenarios ----
$p1 = Start-Demo
try {
    $demo = & (Join-Path $root 'scripts/demo-five-scenarios.ps1')
    $demo | Select-Object -Last 3 | ForEach-Object { Write-Output $_ }
    Check (($demo -join "`n") -match 'S5-09') 'five scenarios script completed (S1..S5)'
} finally { Stop-Demo $p1 }

# ---- process 2: static pages, original interfaces, new interfaces ----
$p2 = Start-Demo
try {
    $health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 3
    Check ($health.status -eq 'ok') 'health endpoint'

    foreach ($f in @('/', '/static/index.html', '/static/app.css', '/static/app.js',
            '/static/v01-goods.html', '/static/v02-orders.html', '/static/v03-goods-admin.html',
            '/static/v04-ops-summary.html', '/static/v05-shipment-list.html',
            '/static/v06-shipment-form.html', '/static/v07-refund-review.html',
            '/static/v08-late-payment.html')) {
        $r = Invoke-WebRequest -Uri ($BaseUrl + $f) -TimeoutSec 5 -UseBasicParsing
        Check ($r.StatusCode -eq 200) "static $f"
    }

    $me = Call 'GET' '/api/v1/me' 'buyer01' $null
    Check ($me.code -eq '0' -and $me.data.user_id -eq 1001) 'API-19 identity'
    $goods = Call 'GET' '/api/v1/goods' 'buyer01' $null
    Check ($goods.code -eq '0' -and $goods.data.count -ge 2) 'API-18 goods'
    $clock = Call 'GET' '/api/v1/admin/clock' 'ops01' $null
    Check ($clock.code -eq '0') 'API-20 clock'
    $summary = Call 'GET' '/api/v1/ops/summary' 'ops01' $null
    Check ($summary.code -eq '0') 'API-16 summary'

    $created = Call 'POST' '/api/v1/orders' 'buyer01' @{ goods_id = 1; quantity = 1 }
    Check ($created.code -eq '0') 'API-01 create order'
    $orderNo = $created.data.order_no
    $before = Call 'GET' "/api/v1/orders/$orderNo" 'buyer01' $null

    $price = Call 'POST' '/api/v1/admin/goods/1/price' 'ops01' @{ unit_price = 13000; reason = 'price adjustment' }
    Check ($price.code -eq '0' -and $price.data.new_unit_price -eq 13000) 'API-21 reprice'
    $afterGoods = Call 'GET' '/api/v1/goods' 'buyer01' $null
    Check ($afterGoods.data.items[0].unit_price -eq 13000) 'API-18 shows new price'
    $after = Call 'GET' "/api/v1/orders/$orderNo" 'buyer01' $null
    Check ($after.data.unit_price -eq $before.data.unit_price -and $after.data.total_amount -eq $before.data.total_amount) 'existing order amount snapshot unchanged (M-12)'
    $denied = Call 'POST' '/api/v1/admin/goods/1/price' 'buyer01' @{ unit_price = 14000; reason = 'x' }
    Check ($denied.code -eq 'M-20') 'API-21 role isolation'

    $timeout = Call 'POST' '/api/v1/payment/timeout' 'mock01' @{ order_no = $orderNo; channel_trade_no = 'TO-VERIFY-1'; reason = 'channel timeout' }
    Check ($timeout.code -eq '0' -and $timeout.data.order_status_unchanged -eq $true) 'API-22 timeout notice'
    $dup = Call 'POST' '/api/v1/payment/timeout' 'mock01' @{ order_no = $orderNo; channel_trade_no = 'TO-VERIFY-1'; reason = 'channel timeout' }
    Check ($dup.code -eq '0' -and $dup.data.duplicate -eq $true) 'API-22 idempotent duplicate'
    $status = Call 'GET' "/api/v1/orders/$orderNo/status" 'buyer01' $null
    Check ($status.data.status -eq $created.data.status) 'API-17 status unchanged after timeout notice'

    $check = Call 'GET' "/api/v1/ops/stock-check/$orderNo" 'ops01' $null
    Check ($check.code -eq '0' -and $check.data.consistent -eq $true) 'API-23 per-order stock check'
    $checkDenied = Call 'GET' "/api/v1/ops/stock-check/$orderNo" 'buyer01' $null
    Check ($checkDenied.code -eq 'M-20') 'API-23 role isolation'
} finally { Stop-Demo $p2 }

Write-Output 'ALL CHECKS PASSED: original interfaces and five scenarios intact, new artifacts verified'
