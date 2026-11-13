# 独立测试 Agent 原始执行输出采集脚本（只执行命令并原样记录输出，不做任何加工）
$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$out = "evidence/sessions/test-agent/测试执行原始输出.txt"
if (Test-Path $out) { Remove-Item $out -Force }

function Section([string]$title) {
    "" | Out-File -FilePath $out -Append -Encoding utf8
    "================================================================================" | Out-File -FilePath $out -Append -Encoding utf8
    ("== " + $title) | Out-File -FilePath $out -Append -Encoding utf8
    "================================================================================" | Out-File -FilePath $out -Append -Encoding utf8
}

function Run([string]$cmdText, [scriptblock]$block) {
    ("`$ " + $cmdText) | Out-File -FilePath $out -Append -Encoding utf8
    & $block 2>&1 | Out-File -FilePath $out -Append -Encoding utf8
    ("EXITCODE=" + $LASTEXITCODE) | Out-File -FilePath $out -Append -Encoding utf8
    "" | Out-File -FilePath $out -Append -Encoding utf8
}

Section "环境与版本基线（独立测试 Agent 实测，非转述）"
Run "git rev-parse HEAD; git --no-pager log --oneline -1; git --no-pager branch --show-current; go version; go env CGO_ENABLED" {
    git rev-parse HEAD
    git --no-pager log --oneline -1
    git --no-pager branch --show-current
    go version
    go env CGO_ENABLED
}

Section "质量门禁 1/4：gofmt -l ."
Run "gofmt -l ." { gofmt -l . }

Section "质量门禁 2/4：go vet ./..."
Run "go vet ./..." { go vet ./... }

Section "质量门禁 3/4：go build ./..."
Run "go build ./..." { go build ./... }

Section "质量门禁 4/4：go test -count=1 ./..."
Run "go test -count=1 ./..." { go test -count=1 ./... }

Section "并发竞争检测：go test -count=1 -race ./server/service/ （本机无 CGO/gcc，如实记录）"
Run "go test -count=1 -race ./server/service/" { go test -count=1 -race ./server/service/ }

Section "环境限制取证：本机无 gcc / clang / mysql（禁止使用 WSL）"
Run "where.exe gcc; where.exe clang; where.exe mysql" {
    where.exe gcc
    where.exe clang
    where.exe mysql
}

Section "覆盖率统计：go test -count=1 -coverpkg=./... -coverprofile=..."
Run "go test -count=1 -coverpkg=./... -coverprofile=evidence/sessions/test-agent/_raw_coverprofile.out ./..." {
    go test -count=1 "-coverpkg=./..." -coverprofile="evidence/sessions/test-agent/_raw_coverprofile.out" ./...
}

Section "覆盖率汇总：go tool cover -func（末 3 行）"
Run "go tool cover -func=evidence/sessions/test-agent/_raw_coverprofile.out | Select-Object -Last 3" {
    go tool cover -func="evidence/sessions/test-agent/_raw_coverprofile.out" | Select-Object -Last 3
}

Section "按包覆盖率（去重合并后统计）"
Run "python covpkg2.py" { python "$env:TEMP\covpkg2.py" }

Section "独立黑盒探测脚本执行（demo-memory 模式，GVA_ADDR=:18099，不连接 MySQL）"
Run "python evidence/sessions/test-agent/黑盒探测脚本.py" {
    python "evidence/sessions/test-agent/黑盒探测脚本.py"
}

Write-Host "written: $out"
